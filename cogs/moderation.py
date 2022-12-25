import logging

from discord.ext import commands

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] (%(name)s): %(message)s'")

class Moderation(commands.Cog):
    def __init__(self, client, bot_config, server_config, user_config):
        self.client = client
        self.bot_config = bot_config
        self.server_config = server_config
        self.user_config = user_config

    @commands.command(brief="Remove a certain number of messages from the current channel", aliases=["purge"])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def prune(self, ctx, amount: int):
        """Remove a certain number of messages from the current channel very fast, note that too large of a number could
        cause issues"""
        await ctx.message.delete()
        await ctx.message.channel.purge(limit=amount)
        await ctx.send("Successfully purged `{:,}` messages from this channel.".format(amount), delete_after=5)
