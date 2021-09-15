import asyncio
import random
from datetime import timedelta
from math import ceil

import nextcord
import youtube_dl
from async_timeout import timeout
from nextcord.ext import commands

from helpers.views import MusicQueuePager

ytdl = youtube_dl.YoutubeDL({'format': 'bestaudio/best', 'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
                             'restrictfilenames': True, 'noplaylist': True, 'nocheckcertificate': True,
                             'ignoreerrors': False, 'quiet': True, 'no_warnings': True, 'default_search': 'auto',
                             'source_address': '0.0.0.0'})


class YTDLError(Exception):
    pass


class YTDLSource(nextcord.PCMVolumeTransformer):
    def __init__(self, channel, source: nextcord.FFmpegPCMAudio, *, data: dict, volume: float):
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
        return cls(channel, nextcord.FFmpegPCMAudio(data['url'], **{
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

            data = await asyncio.get_event_loop().run_in_executor(None, lambda: ytdl.extract_info(
                data.get('webpage_url') or data.get('url'), download=False))
            s = YTDLSource.create_source_from_data(self.text_channel, data, self.volume)
            self.current_song = s

            self.ctx.voice_client.play(s, after=lambda _: self.client.loop.call_soon_threadsafe(self.next.set))
            await self.next.wait()

            s.cleanup()
            self.current_song = None
            if len(self.ctx.guild.get_member(self.client.user.id).voice.channel.members) < 2:
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
        loop = asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False, process=False))
        if data is None:
            raise YTDLError("Couldn't find anything that matches `{}`".format(url))
        return data

    @commands.command(brief="Play a song or playlist from YouTube", aliases=['p'])
    async def play(self, ctx, url):
        if await self.handle_join(ctx) is None:
            return
        await ctx.send("**Joined** `{}`".format(ctx.author.voice.channel.name))
        try:
            await ctx.send("**Searching `{}`**".format(url))
            p = await self.get_data(url)
        except YTDLError:
            await ctx.message.reply(":x: " + str(YTDLError))
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
            for i in p['entries']:
                await player.queue.put(i)
                c += 1
            em = nextcord.Embed(description="[{}]({})".format(p['title'], p['webpage_url']),
                                colour=self.bot_config["embed_colour"])
            em.set_author(icon_url=ctx.author.avatar.url, name="Playlist added to queue")
            em.add_field(name="Playlist Author", value=p['uploader'])
            em.add_field(name="Enqueued", value="`{:,}` songs".format(c))
            await ctx.message.reply(embed=em)
        else:
            await player.queue.put(p)
            await ctx.message.reply("**Added** `{}` **to queue**".format(p['title']))

    @commands.command(brief="Pause the current song")
    async def pause(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_playing():
            return await ctx.send("I'm not currently playing anything")
        elif vc.is_paused():
            return await ctx.send("The player is already paused")

        vc.pause()
        await ctx.message.reply("**Paused**")

    @commands.command(brief="Resume the currently paused song", aliases=['unpause'])
    async def resume(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        elif not vc.is_paused():
            return await ctx.send("The player is not paused")

        vc.resume()
        await ctx.message.reply("**Resumed**")

    @commands.command(brief="Leave the VC", aliases=["stop"])
    async def leave(self, ctx: commands.Context):
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        elif ctx.author.voice is None or ctx.guild.get_member(
                ctx.bot.user.id).voice.channel != ctx.author.voice.channel:
            return await ctx.send("You must be connected to the bot's VC")

        oc = ctx.author.voice.channel.name
        await self.cleanup(ctx.guild)
        await ctx.message.reply("Left `{}`".format(oc))

    @commands.command(brief="Set the volume", help="Set the volume of the music player, may take a couple seconds to "
                                                   "take effect. Don't provide a parameter to reset to default.")
    async def volume(self, ctx, *, volume: float = 0.5):
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
    async def shuffle(self, ctx):
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
    async def clear(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        player = self.get_player(ctx)
        if player.empty():
            return await ctx.send("The queue is already empty")
        else:
            player.clear()
            await ctx.message.reply("**Queue Cleared** command")

    @commands.command(brief="Skip the song")
    async def skip(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        elif vc.is_paused():
            return await ctx.send("The player is currently paused, unpause before you skip")
        elif not vc.is_playing():
            return await ctx.send("The player is not currently playing anything")

        vc.stop()
        await ctx.message.reply("**Skipped!**")

    @commands.command(brief="Play a song immediately", help="Skip the current song play this instead", aliases=['ps'])
    async def playskip(self, ctx, *, url):
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

    @commands.command(brief="Rickroll yourself", help="You found an easter egg! Skip the current song and play a "
                                                      "rickroll next instead.", hidden=True)
    async def rickroll(self, ctx):
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
    async def nowplaying(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        player = self.get_player(ctx)
        if player.current_song is None:
            return await ctx.send("I'm not currently playing anything")
        s = player.current_song
        em = nextcord.Embed(description="[{}]({})".format(s.title, s.url), colour=self.bot_config["embed_colour"])
        em.set_author(icon_url=self.client.user.display_avatar.url, name="Now Playing")
        em.set_thumbnail(url=s.thumbnail)
        em.add_field(name="Duration", value=str(timedelta(seconds=s.duration)))

        await ctx.message.reply(embed=em)

    @commands.command(brief="See the queue of songs", aliases=['q'])
    async def queue(self, ctx):
        vc = ctx.voice_client
        if not vc or not vc.is_connected():
            return await ctx.send("I'm not connected to a VC")
        player = self.get_player(ctx)
        if player.empty():
            return await ctx.send('There are currently no more queued songs.')

        def generate_embed(page):
            desc = ""
            si = (page - 1) * 10
            for i, s in enumerate(pages[si:si + 10]):
                desc += "`{:,}.` [{}]({}) | `{}`\n\n".format(
                    si + 1 + i, s.get('title'), s.get('webpage_url') or
                    "https://www.youtube.com/watch?v=" + s.get('url'), str(timedelta(seconds=s.get('duration'))))
            desc += "**{:,} songs in queue | {} total length**".format(len(pages),
                                                                       str(timedelta(seconds=total_duration)))
            em = nextcord.Embed(title="Queue for " + ctx.guild.name,
                                description=desc, colour=self.bot_config["embed_colour"])
            em.set_footer(text="Page {:,}/{:,}".format(page, last_page), icon_url=ctx.author.display_avatar.url)

            return em

        # noinspection PyProtectedMember
        # noinspection PyUnresolvedReferences
        pages = list(player.queue._queue)
        last_page, total_duration = ceil(len(pages) / 10), player.get_total_duration()
        msg = await ctx.send("**Processing...**")
        view = MusicQueuePager(1, last_page, pages, ctx, msg, total_duration)
        await msg.edit("", embed=generate_embed(view.page), view=view)

# TODO: Voting system for skip
# TODO: Make some commands admin only
