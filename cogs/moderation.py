import logging

import nextcord
from nextcord.ext import commands

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] (%(name)s): %(message)s'")

class Moderation(commands.Cog):
    def __init__(self, client, bot_config, server_config, user_config):
        self.client = client
        self.bot_config = bot_config
        self.server_config = server_config
        self.user_config = user_config

    @commands.Cog.listener()
    async def on_ready(self):
        # Check for any missed archivals while bot was asleep
        for g in self.client.guilds:
            for t in self.server_config[str(g.id)]["auto_unarchive_threads"]:
                thread = await self.client.fetch_channel(t)
                if thread is not None and thread.archived:
                    logging.info("Thread {} ({}) archived while bot was offline, unarchiving"
                                 .format(thread.name, thread.id))
                    await thread.edit(archived=False)

    @commands.Cog.listener()
    async def on_thread_update(self, before: nextcord.Thread, after: nextcord.Thread):
        if not before.archived and after.archived:
            if before.id in self.server_config[str(after.guild.id)]["auto_unarchive_threads"]:
                await after.edit(archived=False)

    @commands.command(brief="Add a thread to the auto unarchive list",
                      help="Enable automatic unarchiving of a thread if it gets archived (either by Discord or by "
                           "a staff member). Discord is a bit buggy so you may need to use the Thread ID rather than "
                           "mentioning it")
    async def autounarchive(self, ctx, thread: nextcord.Thread):
        if thread.id in self.server_config[str(ctx.guild.id)]["auto_unarchive_threads"]:
            await ctx.send("This thread is already in the auto unarchive list, did you mean to remove it?")
            return
        self.server_config[str(ctx.guild.id)]["auto_unarchive_threads"].append(thread.id)
        self.server_config.write_config()

        # Unarchive thread if it's archived at time of adding
        if thread.archived:
            await thread.edit(archived=False)

        await ctx.send("Successfully added {} to auto unarchive list".format(thread.mention))

    @commands.command(brief="Remove a thread from the auto unarchive list",
                      help="Disable automatic unarchiving of a thread. Discord is a bit buggy so you may need to use "
                           "the Thread ID rather than mentioning it")
    async def removeautounarchive(self, ctx, thread: nextcord.Thread):
        if thread.id not in self.server_config[str(ctx.guild.id)]["auto_unarchive_threads"]:
            await ctx.send("This thread is not in the auto unarchive list, did you mean to add it?")
            return
        self.server_config[str(ctx.guild.id)]["auto_unarchive_threads"].remove(thread.id)
        self.server_config.write_config()
        await ctx.send("Successfully removed {} from auto unarchive list".format(thread.mention))

    @commands.command(brief="Remove a certain number of messages from the current channel", aliases=["purge"])
    @commands.has_permissions(manage_messages=True)
    async def prune(self, ctx, amount: int):
        await ctx.message.delete()
        await ctx.message.channel.purge(limit=amount)
        await ctx.send("Successfully purged `{:,}` messages from this channel.".format(amount), delete_after=5)
