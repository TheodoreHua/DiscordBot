from nextcord.ext import commands

class ServerSettings(commands.Cog, name="Server Settings"):
    def __init__(self, client, bot_config, server_config, user_config):
        self.client = client
        self.bot_config = bot_config
        self.server_config = server_config
        self.user_config = user_config

    @commands.command(brief="Set the bot's prefix for this server", usage="<prefix>")
    @commands.guild_only()
    async def setprefix(self, ctx, *, prefix):
        """Change the bot's prefix for this server. If you mess something up you can always kick the bot and re-invite
        it to reset the server's entire config"""
        self.server_config[str(ctx.guild.id)]["prefix"] = prefix
        self.server_config.write_config()
        await ctx.send("Bot prefix successfully changed to `{}`.".format(prefix))
