import asyncio
import logging
import time
from datetime import timedelta
from distutils.util import strtobool

import discord
from discord.ext import commands
from typed_flags import TypedFlags

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] (%(name)s): %(message)s'")


class Reminder:
    def __init__(self, send_time: float, member: discord.Member, message: str, dm: bool, embed_colour: int,
                 original_message: discord.Message, channel: discord.TextChannel):
        """Create a Reminder object

        :param send_time: When the reminder should be sent
        :param member: Member who requested the reminder
        :param message: Message associated with the reminder provided by the requester
        :param dm: Whether or not the reminder should be DMed to the requester
        :param embed_colour: Colour of the reminder embed
        :param original_message: Original message in which they requested the reminder
        :param channel: Channel in which the reminder was requested
        """
        self.t = send_time
        self.member = member
        self.channel = channel
        self.message = message
        self.original_message = original_message
        self.dm = dm
        self.embed_colour = embed_colour

    async def send_reminder(self, notify_time):
        """Send the reminder to the pre-designated location

        :param int notify_time: UNIX time in which the reminder was caught and the request to send was initiated
        """
        em = discord.Embed(title="Here's your reminder!", description=self.message, colour=self.embed_colour)
        em.add_field(name="Reminder ID", value="[{}]({})".format(self.original_message.id,
                                                                 self.original_message.jump_url))
        em.add_field(name="Late By", value=str(timedelta(seconds=notify_time - self.t)))
        if self.dm:
            await self.member.send(embed=em)
        else:
            await self.channel.send("{}, here's your reminder!".format(self.member.mention), embed=em)


class Reminders(commands.Cog):
    def __init__(self, client, bot_config, server_config, user_config):
        self.client = client
        self.bot_config = bot_config
        self.server_config = server_config
        self.user_config = user_config
        self.reminders = {}

    async def check_reminders(self):
        """Loop to check for any reminders every 5 seconds"""
        while self is self.client.get_cog("Reminders"):
            rm = []
            for reminder in self.reminders.values():
                t = time.time()
                if reminder.t <= t:
                    await reminder.send_reminder(t)
                    rm.append(reminder)
            if rm:
                for r in rm:
                    del self.reminders[r.original_message.id]
                    try:
                        del self.user_config["reminders"][str(r.original_message.id)]
                    except KeyError:
                        logging.exception("Exception attempting to delete reminder from file")
                    self.user_config.write_config()
            await asyncio.sleep(5)

    @commands.Cog.listener()
    async def on_ready(self):
        for k, reminder in self.user_config["reminders"].items():
            try:
                g = self.client.get_guild(reminder["guild"])
                c = g.get_channel(reminder["channel"])
                r = Reminder(reminder["send_time"], g.get_member(reminder["member"]), reminder["message"],
                             reminder["dm"], reminder["embed_colour"],
                             await c.fetch_message(reminder["original_message"]), c)
            except (Exception,):  # To get PyCharm to get off of my back
                logging.exception("Failed to parse values for reminder '{}'".format(repr(reminder)))
                del self.reminders[k]
                continue
            self.reminders[r.original_message.id] = r
            logging.info("Incomplete reminder '{}' by {} added to reminder list after restart".format(
                r.message, str(r.member)))
        asyncio.get_event_loop().create_task(self.check_reminders())

    @commands.command(brief="Remind you of something later", aliases=["remindme"],
                      usage="<reminder message> --days:=[days] --hours:=[hours] --minutes:=[minutes] "
                            "--seconds:=[seconds] --dm:=[yes/no]")
    @commands.guild_only()
    async def addreminder(self, ctx, *, args: TypedFlags):
        """Have the bot remind you of something after a certain amount of time. The variance for the reminder time is
        usually at most 5 seconds."""
        try:
            seconds = 0
            if "days" in args:
                seconds += int(args["days"]) * 86400
            if "hours" in args:
                seconds += int(args["hours"]) * 3600
            if "minutes" in args:
                seconds += int(args["minutes"]) * 60
            if "seconds" in args:
                seconds += int(args["seconds"])
        except ValueError as e:
            raise commands.BadArgument from e
        if seconds == 0:
            await ctx.send("Time has to be more than 0 seconds")
            return
        if seconds > 1209600:
            await ctx.send("The maximum amount of time for a reminder is 2 weeks later")
            return
        dm = False
        if "dm" in args:
            try:
                dm = strtobool(args["dm"])
            except ValueError as e:
                raise commands.BadArgument from e

        r = Reminder(time.time() + seconds, ctx.author, " ".join(args[None]), dm,
                     self.bot_config["embed_colour"], ctx.message, ctx.message.channel)
        self.reminders[ctx.message.id] = r

        em = discord.Embed(title="I'll remind you in " + str(timedelta(seconds=seconds)), description=r.message,
                            colour=self.bot_config["embed_colour"])
        em.add_field(name="Reminder ID", value="[{}]({})".format(r.original_message.id, r.original_message.jump_url))
        if dm:
            try:
                await ctx.message.author.send(embed=em)
            except discord.Forbidden:
                await ctx.send("You selected the DM option but the bot is unable to send you DMs. Check that you have "
                               "DMs enabled for this server and that the bot isn't blocked.")
                del self.reminders[ctx.message.id]
                return
        else:
            await ctx.send(embed=em)

        self.user_config["reminders"][str(ctx.message.id)] = {"send_time": r.t, "member": r.member.id,
                                                              "message": r.message, "dm": r.dm,
                                                              "embed_colour": r.embed_colour,
                                                              "original_message": r.original_message.id,
                                                              "channel": r.channel.id, "guild": ctx.guild.id}
        self.user_config.write_config()

    @commands.command(brief="Remove a reminder", aliases=["forgetme"])
    async def removereminder(self, ctx, original_message: discord.Message):
        """Remove a reminder, to specify which reminder, you have to provide a message URL or ID (the message in which
        you sent the initial reminder request). The ID should be available in the confirmation message, you can also get
        it yourself if you have developer mode on. The URL should be available by using Discord's 'Copy message link'
        button."""
        if original_message.id not in self.reminders:
            await ctx.send("That doesn't seem to be a valid reminder? Maybe it's already gone off, it's already been "
                           "deleted, or the message link is incorrect.")
            return
        del self.reminders[original_message.id]
        del self.user_config["reminders"][str(original_message.id)]
        self.user_config.write_config()

        await ctx.send(embed=discord.Embed(title="Reminder removed", description="Reminder ID: [{}]({})".format(
            original_message.id, original_message.jump_url), colour=self.bot_config["embed_colour"]))
