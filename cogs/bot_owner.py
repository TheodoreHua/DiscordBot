import asyncio
import logging
import sys

import nextcord
from nextcord.ext import commands

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] (%(name)s): %(message)s'")


class BotOwner(commands.Cog):
    def __init__(self, client, bot_config, server_config, user_config):
        self.client = client
        self.bot_config = bot_config
        self.server_config = server_config
        self.user_config = user_config

    @commands.command(hidden=True)
    @commands.is_owner()
    async def setstatus(self, ctx, *, status):
        await ctx.message.delete()
        await self.client.change_presence(status=nextcord.Status.online,
                                          activity=nextcord.Game(status if status != "reset"
                                                                 else self.bot_config["status"]))
        await ctx.send("Bot's status set to `{}` until reset".format(status) if status != "reset" else
                       "Bot's status reset", delete_after=5)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def say(self, ctx, *, message):
        await ctx.message.delete()
        await ctx.send(message)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def spam(self, ctx, number: int, *, message):
        await ctx.message.delete()
        for _ in range(number):
            await ctx.send(message)
            await asyncio.sleep(1)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def fastspam(self, ctx, number: int, *, message):
        await ctx.message.delete()
        for _ in range(number):
            await ctx.send(message)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def restart(self, ctx):
        logging.info("Received restart command, terminating program and letting start script restart it")
        await ctx.send("Restarting...")
        self.server_config.write_config()
        sys.exit()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def exit(self, ctx):
        logging.info("Received exit command, terminating program")
        await ctx.send("Exiting...")
        self.server_config.write_config()
        with open("maintain.txt", "w") as f:
            f.write("n")
        sys.exit()
