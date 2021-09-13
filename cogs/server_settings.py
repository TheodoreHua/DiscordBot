from nextcord.ext import commands

class ServerSettings(commands.Cog, name="Server Settings"):
    def __init__(self, client, bot_config, server_config, user_config):
        self.client = client
        self.bot_config = bot_config
        self.server_config = server_config
        self.user_config = user_config

    @commands.command(brief="Set the bot's prefix for this server")
    async def setprefix(self, ctx, *, prefix):
        self.server_config[str(ctx.guild.id)]["prefix"] = prefix
        self.server_config.write_config()
        await ctx.send("Bot prefix successfully changed to `{}`.".format(prefix))
