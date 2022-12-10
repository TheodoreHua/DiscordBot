import logging
from datetime import timedelta
from difflib import SequenceMatcher
from os import environ, getenv
from traceback import format_tb

import nextcord
from nextcord.ext import commands
from dotenv import load_dotenv

from cogs import cogs
from helpers import *
from helpers.help_command import BotHelp

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] (%(name)s): %(message)s'")

assert_data()
bot_config, user_config = BotConfig(), UserConfig()
server_config = ServerConfig(bot_config)
intents = nextcord.Intents.all()
allowed_mentions = nextcord.AllowedMentions(everyone=False, replied_user=False)
client = commands.Bot(command_prefix=server_config.get_prefix, intents=intents,
                      owner_id=bot_config["owner_id"], description=bot_config["description"],
                      allowed_mentions=allowed_mentions, help_command=BotHelp(bot_config))

for cog in cogs:
    client.add_cog(cog(client, bot_config, server_config, user_config))
    logging.info("Initialized cog " + cog.__name__)


@client.event
async def on_ready():
    user_config.check_values()
    server_config.check_servers(client.guilds)
    await client.change_presence(status=nextcord.Status.online, activity=nextcord.Game(bot_config["status"]))
    print("Bot has been initiated")


@client.event
async def on_guild_join(guild):
    server_config.add_guild(guild)
    logging.info("Processed guild {} ({})".format(guild.name, guild.id))


@client.event
async def on_guild_remove(guild):
    server_config.remove_guild(guild)
    logging.info("Removed"
                 " guild {} ({})".format(guild.name, guild.id))


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("**Missing Required Argument**: {}.".format(error.param.name))
    elif isinstance(error, commands.BadArgument):
        await ctx.send("**Bad Argument**: Check the documentation on how to use this command")
    elif isinstance(error, commands.CommandNotFound):
        def similar(a, b):
            return SequenceMatcher(None, a, b).ratio()

        command = ctx.message.content.split(" ")[0]
        command_similarities = {}
        for cmd in client.commands:
            command_similarities[similar(command, cmd.name)] = cmd.name

        highest_command = max([*command_similarities]), command_similarities[max([*command_similarities])]
        if len(command_similarities) == 0 or highest_command[0] < 0.55:
            await ctx.send("**Command Not Found**: Run {}help for a list of commands.".format(ctx.prefix))
        else:
            await ctx.send("**Command Not Found**: Did you mean `{}`?".format(highest_command[1]))
    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(
            "This command is on cooldown, try again in **{}**.".format(str(timedelta(seconds=error.retry_after))
                                                                       .split(".")[0]))
    elif isinstance(error, commands.MissingPermissions):
        await ctx.send("**Missing Permissions**: You need `{}`."
                       .format(", ".join(x.replace("_", " ").title() for x in error.missing_permissions)))
    elif isinstance(error, commands.BotMissingPermissions):
        await ctx.send("**Bot Missing Permissions*: {}, please add the permissions to the bot."
                       .format(", ".join(x.replace("_", " ").title() for x in error.missing_permissions)))
    elif isinstance(error, commands.NotOwner):
        await ctx.send("**Not Owner**: Only the owner of the bot can execute this command")
    elif isinstance(error, commands.NoPrivateMessage):
        await ctx.send("**No Private Message**: This command can only be used in guilds, not private messages")
    elif isinstance(error, commands.PrivateMessageOnly):
        await ctx.send("**Private Message Only**: This command can only be used in (DM/PM)s")
    elif isinstance(error, commands.CheckFailure):
        await ctx.send("**Check Failure**: A check required to run this command has failed, most likely meaning you "
                       "don't have permissions.")
    else:
        logging.error(
            "Error occurred attempting to execute '{}' by user {}\n{}\n{}".format(
                ctx.invoked_with, ctx.author.id, repr(error), "\n".join(format_tb(error.__traceback__))) +
            ("{}\n{}".format(repr(error.__cause__), "\n".join(format_tb(error.__cause__.__traceback__)))
             if error.__cause__ is not None else ""))
        await ctx.send(embed=nextcord.Embed(
            description=":x: An internal exception occurred while running this command.", colour=nextcord.Colour.red()))


@client.slash_command()
async def ping(interaction: nextcord.Interaction):
    await interaction.response.send_message("Pong! `{:,.4f}ms`".format(client.latency * 1000))


if __name__ == "__main__":
    if "BOT_TOKEN" not in environ:
        load_dotenv()
    BOT_TOKEN = getenv("BOT_TOKEN")
    if BOT_TOKEN is None:
        logging.fatal("BOT_TOKEN could not be loaded from system environment variables or .env file")
        exit()

    client.run(BOT_TOKEN)
