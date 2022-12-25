import asyncio
import random
from datetime import timedelta
from math import ceil

import discord
import yt_dlp
from async_timeout import timeout
from discord.ext import commands

from helpers.views import MusicQueuePager

ytdl = yt_dlp.YoutubeDL({'format': 'bestaudio/best', 'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
                             'restrictfilenames': True, 'noplaylist': True, 'nocheckcertificate': True,
                             'ignoreerrors': False, 'quiet': True, 'no_warnings': True, 'default_search': 'auto',
                             'source_address': '0.0.0.0'})


class YTDLError(Exception):
    pass


class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, channel, source: discord.FFmpegPCMAudio, *, data: dict, volume: float):
        super().__init__(source, volume)
        self.channel = channel
        self.data = data

        self.title = data.get('title')
        self.thumbnail = data.get('thumbnail')
        self.duration = data.get('duration')
        self.url = data.get('webpage_url')
        self.stream_url = data.get('url')

    @classmethod
    def create_source_from_data(cls, channel, data, volume=0.5):
        return cls(channel, discord.FFmpegPCMAudio(data['url'], **{
            'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5', 'options': '-dn -vn'}),
                   data=data, volume=volume)


class Player:
    def __init__(self, ctx: commands.Context):
        self.ctx = ctx
        self.client = ctx.bot
        self.text_channel = ctx.channel
        self.guild = ctx.guild
        self._cog = ctx.cog

        self.queue = asyncio.Queue()
        self.next = asyncio.Event()
        self.current_song = None
        self.force_play = None
        self.skips = []
        self.playing = True
        self.volume = 0.5

        ctx.bot.loop.create_task(self.player_loop())

    def __len__(self):
        return self.queue.qsize()

    async def player_loop(self):
        """Loop that actually plays the songs"""
        await self.client.wait_until_ready()

        while not self.client.is_closed() and self.playing:
            self.next.clear()

            if self.force_play is None:
                try:
                    async with timeout(300):
                        data = await self.queue.get()
                except asyncio.TimeoutError:
                    await self.text_channel.send("Disconnected after being inactive for 5 minutes")
                    return self.destroy(self.guild)
            else:
                data = self.force_play
                self.force_play = None

            try:
                data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(
                    data.get('webpage_url') or data.get('url'), download=False))
            except yt_dlp.utils.DownloadError:
                await self.text_channel.send(":x: An error has occurred playing `{}`".format(data.get('title', 'Unknown Song')))
                continue
            s = YTDLSource.create_source_from_data(self.text_channel, data, self.volume)
            self.current_song = s

            self.ctx.voice_client.play(s, after=lambda _: self.client.loop.call_soon_threadsafe(self.next.set))
            await self.next.wait()

            try:
                s.cleanup()
            except ValueError:
                pass
            self.current_song = None
            self.skips = []
            if len([i for i in self.ctx.guild.get_member(self.client.user.id).voice.channel.members if not i.bot]) == 0:
                await self.text_channel.send("Disconnected due to the VC being empty")
                return self.destroy(self.guild)

    def get_current_song(self):
        """Get the current song that should be playing in the player"""
        return self.current_song

    def shuffle(self):
        """Shuffle the queue"""
        # noinspection PyProtectedMember
        # noinspection PyUnresolvedReferences
        random.shuffle(self.queue._queue)

    def empty(self):
        """Check if the queue is empty"""
        return self.queue.empty()

    def clear(self):
        """Clear the queue"""
        for _ in range(self.queue.qsize()):
            self.queue.get_nowait()
            self.queue.task_done()

    def get_total_duration(self):
        """Get the total duration of the queue"""
        d = self.current_song.duration if self.current_song is not None else 0
        # noinspection PyProtectedMember
        # noinspection PyUnresolvedReferences
        for s in list(self.queue._queue):
            d += s.get('duration')

        return d

    def destroy(self, guild):
        return self.client.loop.create_task(self._cog.cleanup(guild))


class Music(commands.Cog):
    def __init__(self, client: commands.Bot, bot_config, server_config, user_config):
        self.client = client
        self.bot_config = bot_config
        self.server_config = server_config
        self.user_config = user_config
        self.q = {}

    def get_player(self, ctx):
        """Retrieve the guild player, or generate one"""
        try:
            player = self.q[ctx.guild.id]
        except KeyError:
            player = Player(ctx)
            self.q[ctx.guild.id] = player
        return player

    async def handle_join(self, ctx: commands.Context):
        """Join a voice channel"""
        if ctx.voice_client is None:
            if ctx.author.voice is None:
                await ctx.message.reply("You are not in a voice channel")
                return
            return await ctx.author.voice.channel.connect()
        else:
            if ctx.author.voice.channel == ctx.guild.get_member(self.client.user.id).voice.channel:
                return True
            else:
                await ctx.message.reply("The bot is currently in another Voice Channel")
                return

    async def cleanup(self, guild):
        """Disconnect from and clean up a guild"""
        player = self.q[guild.id]
        player.playing = False
        try:
            await guild.voice_client.disconnect()
        except AttributeError:
            pass
        try:
            del self.q[guild.id]
        except KeyError:
            pass

    @staticmethod
    async def get_data(url):
        """Get the YTDL data associated with a URL

        :param str url: URL to query for
        """
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False, process=False))
        if data is None:
            raise YTDLError("Couldn't find anything that matches `{}`".format(url))
        return data

    @commands.command(brief="Play a song or playlist from YouTube", aliases=['p'], usage="<youtube url>")
    @commands.guild_only()
    async def play(self, ctx, *, url):
        """Play a song from YouTube in VC, playlists are not currently supported."""
        if await self.handle_join(ctx) is None:
            return
        await ctx.send("**Joined** `{}`".format(ctx.author.voice.channel.name))
        try:
            await ctx.send("**Searching `{}`**".format(url))
            p = await self.get_data(url)
        except (YTDLError, yt_dlp.utils.DownloadError) as e:
            await ctx.message.reply(":x: `{}`".format(e))
            return
        player = self.get_player(ctx)
        if 'url' in p and 'ytsearch' in p["url"]:
            return await ctx.message.reply(":x: Searching is not currently supported")
        elif 'watch?v=' in url and "list=" in url:
            return await ctx.message.reply(":x: Combo video & playlist links are not supported (when you copy the link "
                                           "to a song's that's also in a playlist's webpage). Please provide just the "
                                           "song link or just the playlist link. Just the playlist link is the view "
                                           "all songs page.")
        elif 'entries' in p:
            c = 0
            failed = []
            for i in p['entries']:
                if i.get('duration') is None:
                    failed.append(i.get('title'))
                    continue
                await player.queue.put(i)
                c += 1
            em = discord.Embed(description="[{}]({}) by {}".format(p['title'], p['webpage_url'], p['uploader']),
                                colour=self.bot_config["embed_colour"])
            em.set_author(icon_url=ctx.author.avatar.url, name="Playlist added to queue")
            em.add_field(name="Enqueued", value="`{:,}` songs".format(c))
            if len(failed) > 0:
                private = 0
                deleted = 0
                other = []
                for i in failed:
                    if i == "[Private video]":
                        private += 1
                    elif i == "[Deleted video]":
                        deleted += 1
                    else:
                        other.append(i)
                if private > 0: em.add_field(name="Ignored (Private)", value="`{:,}`".format(private))
                if deleted > 0: em.add_field(name="Ignored (Deleted)", value="`{:,}`".format(deleted))
                if len(other) > 0:
                    em.add_field(name="Failed to Add:", value="`{}`".format("`, `".join(other)), inline=False)
            await ctx.message.reply(embed=em)
        else:
            await player.queue.put(p)
            await ctx.message.reply("**Added** `{}` **to queue**".format(p['title']))

    @commands.command(brief="Pause the current song")
    @commands.guild_only()
    async def pause(self, ctx):
        """Pause the player, note that this will also pause the bot's automatic idle leaving, so make sure to either
        unpause it or run the leave command when you no longer need the music bot."""
        vc = ctx.voice_client
        if not vc or not vc.is_playing():
            return await ctx.send("I'm not currently playing anything")
        elif vc.is_paused():
            return await ctx.send("The player is already paused")

        vc.pause()
        await ctx.message.reply("**Paused**")

    @commands.command(brief="Resume the currently paused song", aliases=['unpause'])
    @commands.guild_only()
    async def resume(self, ctx):
        """Resume the player"""
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        elif not vc.is_paused():
            return await ctx.send("The player is not paused")

        vc.resume()
        await ctx.message.reply("**Resumed**")

    @commands.command(brief="Leave the VC", aliases=["stop"])
    @commands.guild_only()
    async def leave(self, ctx: commands.Context):
        """Have the bot leave the VC and cleanup any settings (queue and volume will reset)"""
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        elif ctx.author.voice is None or ctx.guild.get_member(
                ctx.bot.user.id).voice.channel != ctx.author.voice.channel:
            return await ctx.send("You must be connected to the bot's VC")

        oc = ctx.author.voice.channel.name
        await self.cleanup(ctx.guild)
        await ctx.message.reply("Left `{}`".format(oc))

    @commands.command(brief="Set the volume", usage="<percentage>")
    @commands.guild_only()
    async def volume(self, ctx, *, volume: float = 0.5):
        """Set the volume of the music player, may take a couple seconds to take effect. This only affects the current
        session, it'll reset to the default whenever a new session occurs, or don't provide a parameter to reset to
        default manually. Note that this affects everyone on the server, if you want to only turn it quieter for you,
        use your client side volume controls."""
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        if not 0 < volume < 101:
            return await ctx.message.reply("Please enter a value between 1 and 100")

        player = self.get_player(ctx)
        if vc.source:
            vc.source.volume = volume / 100
        player.volume = volume / 100
        await ctx.message.reply("**Set the volume to ** `{}%`".format(volume))

    @commands.command(brief="Shuffle the queue")
    @commands.guild_only()
    async def shuffle(self, ctx):
        """Shuffle the queue, this does not change the currently playing song. You'll have to skip it."""
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        player = self.get_player(ctx)
        if player.empty():
            return await ctx.send("Cannot shuffle an empty queue")
        else:
            player.shuffle()
            await ctx.message.reply("**Queue Shuffled**")

    @commands.command(brief="Clear the queue")
    @commands.guild_only()
    async def clear(self, ctx):
        """Clear the queue, this does not stop the currently playing song. You'll have to skip it."""
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        player = self.get_player(ctx)
        if player.empty():
            return await ctx.send("The queue is already empty")
        else:
            player.clear()
            await ctx.message.reply("**Queue Cleared** command")

    @commands.command(brief="Skip the song", aliases=['s'])
    @commands.guild_only()
    async def skip(self, ctx):
        """Vote to skip the current song, if there are more than 2 people on the VC, you'll need at least half to vote
        to skip"""
        vc = ctx.voice_client
        bm = ctx.guild.get_member(self.client.user.id)
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        elif vc.is_paused():
            return await ctx.send("The player is currently paused, unpause before you skip")
        elif not vc.is_playing():
            return await ctx.send("The player is not currently playing anything")
        elif ctx.author.voice is None or bm.voice.channel != ctx.author.voice.channel:
            return await ctx.send("You must be in the bot's VC to use this command")

        player = self.get_player(ctx)
        vc_count = len([i for i in bm.voice.channel.members if not i.bot])
        h = ceil(vc_count / 2)
        if ctx.author.id in player.skips:
            return await ctx.send("You have already voted to skip! ({:,}/{:,} people)".format(len(player.skips), h))
        player.skips.append(ctx.author.id)
        if vc_count <= 2:
            vc.stop()
            await ctx.message.reply("**Skipped!**")
        elif len(player.skips) >= h:
            os = len(player.skips)
            vc.stop()
            await ctx.message.reply("**Skipped!** ({:,}/{:,} people)".format(os, h))
        else:
            await ctx.message.reply("**Skipping?** ({:,}/{:,} people)".format(len(player.skips), h))

    @commands.command(brief="Force skip a song", aliases=['fs'])
    @commands.guild_only()
    @commands.has_permissions(manage_messages=True)
    async def forceskip(self, ctx):
        """Forcefully skip the current song, without voting"""
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        elif vc.is_paused():
            return await ctx.send("The player is currently paused, unpause before you skip")
        elif not vc.is_playing():
            return await ctx.send("The player is not currently playing anything")

        vc.stop()
        await ctx.message.reply("**Force Skipped!**")

    @commands.command(brief="Play a song immediately", aliases=['ps'], usage="<youtube url>")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    async def playskip(self, ctx, *, url):
        """Skip the current song and play this one instead"""
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        try:
            await ctx.send("**Searching `{}`**".format(url))
            p = await self.get_data(url)
        except YTDLError:
            await ctx.message.reply(":x: " + str(YTDLError))
            return
        player = self.get_player(ctx)
        if 'url' in p and 'ytsearch' in p["url"]:
            return await ctx.message.reply(":x: Searching is not currently supported")
        elif 'entries' in p or "list=" in url:
            return await ctx.message.reply(":x: Playlists are not allowed for playskip")
        else:
            if player.empty():
                await player.queue.put(p)
            else:
                player.force_play = p
                vc.stop()
            await ctx.message.reply("**Skipped current song to play** `{}` **instead**".format(p['title']))

    @commands.command(brief="Rickroll yourself", hidden=True)
    @commands.guild_only()
    @commands.cooldown(1, 600)
    async def rickroll(self, ctx):
        """You found an easter egg! Skip the current song and play a rickroll instead."""
        await ctx.message.delete()
        if await self.handle_join(ctx) is None:
            return
        vc = ctx.voice_client
        player = self.get_player(ctx)
        d = await self.get_data("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        if player.empty():
            await player.queue.put(d)
        else:
            player.force_play = d
            vc.stop()

    @commands.command(brief="See information about the current song", aliases=['np', 'current'])
    @commands.guild_only()
    async def nowplaying(self, ctx):
        """Show information about the currently playing song"""
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        player = self.get_player(ctx)
        if player.current_song is None:
            return await ctx.send("I'm not currently playing anything")
        s = player.current_song
        em = discord.Embed(description="[{}]({})".format(s.title, s.url), colour=self.bot_config["embed_colour"])
        em.set_author(icon_url=self.client.user.display_avatar.url, name="Now Playing")
        em.set_thumbnail(url=s.thumbnail)
        em.add_field(name="Duration", value=str(timedelta(seconds=s.duration)))

        await ctx.message.reply(embed=em)

    @commands.command(brief="See the queue of songs", aliases=['q'])
    @commands.guild_only()
    async def queue(self, ctx):
        """Get a list of all songs currently in the queue"""
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        player = self.get_player(ctx)
        if player.empty():
            return await ctx.send('There are currently no more queued songs.')

        # noinspection PyProtectedMember
        # noinspection PyUnresolvedReferences
        pages = list(player.queue._queue)
        last_page, total_duration = ceil(len(pages) / 10), player.get_total_duration()
        msg = await ctx.send("**Processing...**")
        view = MusicQueuePager(1, last_page, pages, player.current_song, ctx, msg, total_duration)
        await msg.edit(content="", embed=view.generate_embed(), view=view)
