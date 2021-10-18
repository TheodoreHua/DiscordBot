import logging
import random
import re
import typing
from datetime import datetime
from difflib import SequenceMatcher

import dateparser
import nextcord
import requests
from nextcord.ext import commands
from typed_flags import TypedFlags

from helpers.funcs import cut_mentions, get_webhook
from helpers.views import IndividualPager, DeleteResponse

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] (%(name)s): %(message)s'")

class TimestampFormatConverter(commands.Converter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.styles = ['t', 'T', 'd', 'D', 'f', 'F', 'R']

    async def convert(self, ctx, argument):
        if argument not in self.styles:
            raise commands.BadArgument
        return ":" + argument


class Utility(commands.Cog):
    def __init__(self, client, bot_config, server_config, user_config):
        self.client = client
        self.bot_config = bot_config
        self.server_config = server_config
        self.user_config = user_config

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.guild is not None:
            if len(msg.mentions) > 0:
                msg.mentions = [i for i in msg.mentions if i.id != msg.author.id]
            if len(msg.mentions) == 1:
                if str(msg.mentions[0].id) in self.server_config[str(msg.guild.id)]["nopings"]:
                    rep = await msg.reply(embed=nextcord.Embed(
                            title="Please do not ping " + msg.mentions[0].display_name,
                            description="This user has requested that the following message be sent when people ping "
                                        "them:\n" + "\n".join(["> {}".format(i) for i in self.server_config
                            [str(msg.guild.id)]["nopings"][str(msg.mentions[0].id)].split("\n")]),
                            colour=self.bot_config["embed_colour"]))
                    v = DeleteResponse(rep, msg.author.id)
                    await rep.edit(view=v)
            elif 1 < len(msg.mentions) <= 25:
                em = nextcord.Embed(title="Do not ping these users",
                                    description="These users have requested not to be pinged, below is a list of these "
                                                "users, and a custom message supplied by them to go "
                                                "along with it.", colour=self.bot_config["embed_colour"])
                for i in msg.mentions:
                    if str(i.id) in self.server_config[str(msg.guild.id)]["nopings"]:
                        em.add_field(name=i.display_name,
                                     value=self.server_config[str(msg.guild.id)]["nopings"][str(i.id)], inline=False)
                rep = await msg.reply(embed=em)
                v = DeleteResponse(rep, msg.author.id)
                await rep.edit(view=v)

    @commands.command(aliases=["pfp"], brief="Get a user's profile picture")
    async def avatar(self, ctx, user: nextcord.User = None):
        """Get a user's profile picture, or run the command by itself for your own profile picture."""
        if user is None:
            user = ctx.message.author
        em = nextcord.Embed(description=user.mention + "'s Avatar", colour=self.bot_config["embed_colour"])
        em.set_image(url=user.display_avatar.url)

        await ctx.send(embed=em)

    @commands.command(brief="Roll some dice", aliases=["roll"])
    async def dice(self, ctx, amount: int, sides: int):
        """Roll some dice, by default it'll be a 1d6 (one 6-sided die), however you can roll more dice with varying
        number of sides."""
        if amount > 100 or sides > 10000000000000000:
            await ctx.send("Woahhh, slow down there. That's too large, Discord can't handle it!")
            return
        rolled = []
        for _ in range(amount):
            rolled.append(random.randint(1, sides))

        await ctx.send("**Result:** {}d{} ({})\n**Total**: {}".format(amount, sides, ", ".join(str(i) for i in rolled),
                                                                      sum(rolled)))

    @commands.command(brief="Choose between a couple options")
    async def choose(self, ctx, *options):
        """Provide a list of options for the bot to choose 1 out of seperated by spaces. For options with spaces in
        them, enclose it in double quotes."""
        await ctx.send("I choose: `{}`".format(random.choice(options)))

    @commands.command(brief="Show the bots ping")
    async def ping(self, ctx):
        """Show the bots ping, up to 4 decimal points"""
        await ctx.send("Pong! `{:,.4f}ms`".format(self.client.latency * 1000))

    @commands.command(brief="Show info about this server")
    @commands.guild_only()
    async def serverinfo(self, ctx):
        """Show various information about the server the command is run in"""
        g = ctx.guild
        fields = {
            "ID": str(g.id),
            "Emojis": "{:,}/{:,}".format(len(g.emojis), g.emoji_limit),
            "Stickers": "{:,}/{:,}".format(len(g.stickers), g.sticker_limit),
            "Region": str(g.region),
            "Created At": g.created_at.strftime("%Y-%m-%d %H:%M UTC"),
            "Members": "**Humans:** {:,}\n**Bots:** {:,}\n**Total:** {:,}".format(len(g.humans), len(g.bots),
                                                                                  g.member_count)
        }

        em = nextcord.Embed(title=g.name, description=g.description, colour=self.bot_config["embed_colour"])
        em.set_author(name="Server Owner: {}".format(str(g.owner)),
                      icon_url=g.owner.display_avatar.url)
        if g.icon is not None:
            em.set_thumbnail(url=g.icon.url)
        if g.banner is not None:
            em.set_image(url=g.banner.url)

        for name, value in fields.items():
            em.add_field(name=name, value=value)
        em.add_field(name="Roles", value=cut_mentions(reversed(g.roles), 1024), inline=False)
        em.add_field(name="Channels", value=cut_mentions(g.text_channels, 1024), inline=False)

        await ctx.send(embed=em)

    @commands.command(brief="Show info about a user")
    async def userinfo(self, ctx, user: nextcord.User):
        """Show general info about a user (doesn't have to be in the server). To see info specific to this server use
        memberinfo"""
        em = nextcord.Embed(colour=self.bot_config["embed_colour"])
        em.set_thumbnail(url=user.display_avatar.url)
        em.set_author(name=str(user), icon_url=user.display_avatar.url)
        em.add_field(name="ID", value=str(user.id))
        em.add_field(name="Created At", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S.%f UTC"))
        em.add_field(name="Bot", value=user.bot)

        await ctx.message.channel.send(embed=em)

    @commands.command(brief="Show info about a member")
    @commands.guild_only()
    async def memberinfo(self, ctx, member: nextcord.Member):
        """Show info about a member, specific to this server"""
        em = nextcord.Embed(description=member.mention, colour=self.bot_config["embed_colour"])
        em.set_thumbnail(url=member.display_avatar.url)
        em.set_author(name=str(member), icon_url=member.display_avatar.url)
        fields = {
            "Nickname": member.nick,
            "ID": member.id,
            "Joined At": member.joined_at.strftime("%Y-%m-%d %H:%M:%S.%f UTC"),
            "Created At": member.created_at.strftime("%Y-%m-%d %H:%M:%S.%f UTC"),
            "Status": member.status,
            "Display Colour": f"RGB: {member.colour.to_rgb()}\nHEX: {str(member.colour)}",
            "Bot": member.bot,
            "System User": member.system
        }

        for name, value in fields.items():
            em.add_field(name=name, value=value)

        em.add_field(name="Roles", value=cut_mentions(member.roles, 1024), inline=False)
        guildperms = member.guild_permissions
        key_perms = {"Administrator": guildperms.administrator, "Ban Members": guildperms.ban_members,
                     "Kick Members": guildperms.kick_members, "Manage Channels": guildperms.manage_channels,
                     "Manage Server": guildperms.manage_guild, "Manage Roles": guildperms.manage_roles,
                     "Manage Nicknames": guildperms.manage_nicknames, "Mute Members": guildperms.mute_members,
                     "Deafen Members": guildperms.deafen_members, "Move Members": guildperms.deafen_members}
        key_permissions = [i for i, j in key_perms.items() if j]
        em.add_field(name="Key Permissions:",
                     value=", ".join(x for x in key_permissions) if len(key_permissions) > 0 else "None", inline=False)

        await ctx.message.channel.send(embed=em)

    @commands.command(brief="Send animated emojis in your message without nitro", aliases=["ae"], usage="<message>")
    @commands.guild_only()
    async def animatedemoji(self, ctx, *, message):
        """Send animated emojis in your message without nitro. Replace the location you want the emote with :emote name
        here:. You should only use this if you don't have nitro, or it'll probably mess up with Discord's autocomplete.
        For example: Hello :animated wave:."""
        def similar(a, b):
            return SequenceMatcher(None, a, b).ratio()

        await ctx.message.delete()
        new_str = message
        tbr = re.findall(r":.*?:", message)

        for emoji_name in tbr:
            emoji_similaritys = {}
            for emoji in ctx.guild.emojis:
                if emoji.animated:
                    emoji_similaritys[similar(emoji_name[1:-1], emoji.name)] = emoji
            highest_emoji = max([*emoji_similaritys]), emoji_similaritys[max([*emoji_similaritys])]
            if highest_emoji[0] < 0.1:
                await ctx.send("Could not find any emojis that match `{}`".format(emoji_name[1:-1]), delete_after=5)
                return
            new_str = new_str.replace(emoji_name, "<a:{}:{}>".format(highest_emoji[1].name, str(highest_emoji[1].id)))

        webhook = await get_webhook(ctx, self.client)
        await webhook.send(content=new_str, username=ctx.author.display_name, avatar_url=ctx.author.display_avatar.url)

    @commands.command(brief="Send a message as another user (to impersonate them)", usage="<user> <message>")
    @commands.guild_only()
    async def impersonate(self, ctx, user: typing.Union[nextcord.Member, nextcord.User], *, message):
        """Impersonate another user with the power of webhooks! Basically this allows you to send a message with another
         user's profile picture and name, note that the role colour WILL be white and there'll be a bot tag, there's
          nothing I can do about that as it's just how it works."""
        await ctx.message.delete()

        webhook = await get_webhook(ctx, self.client)
        await webhook.send(content=message, username=user.display_name, avatar_url=user.display_avatar.url)

    @commands.command(brief="Send a message as a custom user",
                      usage="<message> --username:=<username> --avatar:=[avatar url]")
    @commands.guild_only()
    async def usersend(self, ctx, *, args: TypedFlags):
        """Send a message as a custom user, basically a one-time-use Tupper (if you know what I'm talking about).
        Username and message flags are required, avatar is optional (you can also upload an avatar as a file)."""
        await ctx.message.delete()
        if "username" not in args or None not in args:
            raise commands.BadArgument()

        if len(ctx.message.attachments) >= 1:
            args["avatar"] = ctx.message.attachments[0].url
        supported_image_extension = ["JPEG", "JPG", "GIF", "WEBM", "BMP", "TIFF", "PNG"]
        if "avatar" in args:
            con = False
            for extension in supported_image_extension:
                if extension.lower() in args["avatar"].lower():
                    con = True
                    break
            if not con:
                await ctx.send(
                    "The avatar link is not in the correct format. Supported formats are {}".format(
                        ", ".join("." + x for x in supported_image_extension)
                    ), delete_after=5)
                return
        else:
            args["avatar"] = None

        webhook = await get_webhook(ctx, self.client)
        await webhook.send(content=" ".join(args[None]), username=args["username"], avatar_url=args["avatar"])

    @commands.command(brief="Get information about a Minecraft player")
    async def playerinfo(self, ctx, player):
        """Get various information about a Minecraft player, including their current skin, username history, and UUID"""
        r = requests.get("https://api.mojang.com/users/profiles/minecraft/" + player)
        if r.ok and r.status_code not in [204, 400]:
            js = r.json()
            username = js["name"]
            uuid = js["id"]
        else:
            if r.status_code in [204, 400]:
                await ctx.send("I can't seem to find that Minecraft user on Mojang servers, is it a non-paid MC"
                               "account?")
            else:
                await ctx.send("It seems like the Mojang API is currently broken, try again later?")
            return

        rhistory = requests.get("https://api.mojang.com/user/profiles/{}/names".format(uuid))
        if rhistory.ok and rhistory.status_code not in [204, 400]:
            history = rhistory.json()
        else:
            if rhistory.status_code in [204, 400]:
                await ctx.send("I can't seem to find that Minecraft user on Mojang servers, is it a non-paid MC"
                               "account?")
            else:
                await ctx.send("It seems like the Mojang API is currently broken, try again later?")
            return
        e = nextcord.Embed(title=username, description="**Username History:**\n" +
                                                       "\n".join(["- " + i["name"] for i in reversed(history)]),
                           colour=self.bot_config["embed_colour"])
        e.set_thumbnail(url="https://crafatar.com/avatars/{}?overlay".format(uuid))
        e.set_image(url="https://crafatar.com/renders/body/{}?overlay".format(uuid))
        e.set_footer(text="Thanks to Crafatar for providing the skin renders.")
        e.add_field(name="UUID", value=uuid)
        await ctx.send(embed=e)

    @commands.command(brief="Send longer messages", aliases=["combinemessage", "cm"])
    @commands.guild_only()
    async def messagecombine(self, ctx, msg1: nextcord.Message, msg2: nextcord.Message, delete_originals: bool = False):
        """Combine two existing 2000 character messages into one 4000 character message. By default the original 2
        messages are not deleted, you can pass an extra bool value to delete them."""
        await ctx.message.delete()
        new_message = msg1.content + "\n" + msg2.content
        if len(new_message) > 4096:
            return await ctx.send("New message too long", delete_after=15)
        em = nextcord.Embed(description=new_message)
        em.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=em)

        if delete_originals:
            await msg1.delete()
            await msg2.delete()

    @commands.command(brief="Send hyperlinks using embeds", aliases=["embeddescription", "ed", "h"],
                      usage="<message>")
    @commands.guild_only()
    async def hyperlink(self, ctx, *, message):
        """Send hyperlinks using embeds, hyperlinks have to be in the format `[text](link)`. All this really does is put
        your text as the description in an embed, so you can use any other formatting embeds have. If you want a more
        advanced command, try the `embedgen` command."""
        await ctx.message.delete()
        em = nextcord.Embed(description=message)
        em.set_author(name=str(ctx.author), icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=em)

    @commands.command(brief="Send a custom embed", aliases=["embedgen", "eg"],
                      usage="--title:=[title] --description:=[description] --colour:=[colour in decimal format] "
                            "--url:=[title url] --footer_text:=[footer text] --footer_icon_url:=[footer icon url] "
                            "--image:=[image] --thumbnail:=[thumbnail] --author_name:=[author name] "
                            "--author_icon_url:=[author icon url] --author_url:=[author url]")
    @commands.guild_only()
    async def embed(self, ctx, *, args: TypedFlags):
        """Send your own custom embed, all embed options are available under flags (as seen in the usage help). You can
        define your own custom fields by using flags as well, you just can't name them anything that already exists. For
        example the flag `--Test Field:=Something` would result in a field named `Test Field` with a value of
        `Something` Keep in mind Discord embed limits, they apply. If you don't know the type of value you have to pass
        into certain options, you're going to run into issues. That's why it's recommended to leave this for people who
        know what they're doing. One very common one is colour, it has to be in decimal form, not hex. Some image
        arguments only work if their text is defined, for example `footer_icon_url` only works if `footer_text` is
        defined."""
        await ctx.message.delete()
        reserved_opts = [None, 'title', 'description', 'colour', 'url', 'footer_text', 'footer_icon_url', 'image',
                         'thumbnail', 'author_name', 'author_icon_url', 'author_url']
        try:
            e = nextcord.Embed.Empty
            em = nextcord.Embed(title=args.get('title', e), description=args.get('description', e),
                                colour=int(args.get('colour')) if 'colour' in args else e, url=args.get('url', e))
            if "footer_text" in args:
                em.set_footer(text=args.get('footer_text', e), icon_url=args.get('footer_icon_url', e))
            if "image" in args:
                em.set_image(url=args.get('image', e))
            if "thumbnail" in args:
                em.set_thumbnail(url=args.get('thumbnail', e))
            if "author_name" in args or "author_icon_url" in args:
                em.set_author(name=args.get('author_name', ''), icon_url=args.get('author_icon_url', e),
                              url=args.get('author_url', e))
            for i in reserved_opts:
                try:
                    del args[i]
                except KeyError:
                    pass
            c = 0
            for n, v in args.items():
                if c >= 25:
                    return await ctx.send("Too many fields")
                em.add_field(name=n, value=v)
                c += 1
        except ValueError:
            return await ctx.send("Some conversion failed, likely due to an invalid value", delete_after=15)
        except nextcord.HTTPException:
            return await ctx.send("Invalid value in embed, couldn't send it", delete_after=15)
        webhook = await get_webhook(ctx, self.client)
        await webhook.send(embed=em, username=ctx.author.display_name, avatar_url=ctx.author.display_avatar.url)

    @commands.command(brief="Search urban dictionary", usage="<term>", aliases=["ud"])
    async def urbandictionary(self, ctx, *, term):
        """Search for a term on urban dictionary and get the results"""
        try:
            r = requests.get("https://mashape-community-urban-dictionary.p.rapidapi.com/define", headers={
                "x-rapidapi-host": "mashape-community-urban-dictionary.p.rapidapi.com",
                "x-rapidapi-key": self.bot_config["ud_rapidapi_key"]
            }, params={"term": term})
        except ConnectionError:
            logging.exception("Received error while attempting urban dictionary command")
            return await ctx.send("An error occurred, try again later.")
        if not r.ok:
            return await ctx.send("Error retrieving response from Urban Dictionary, try again later.")
        else:
            results = r.json()["list"]
            if len(results) == 0:
                return await ctx.send("No results found")
            elif len(results) == 1:
                em = nextcord.Embed(title=results[0]["word"], description=results[0]["definition"],
                                    colour=self.bot_config["embed_colour"])
                em.set_author(name=results[0]["author"])
                em.add_field(name="Example", value=results[0]["example"], inline=False)
                em.add_field(name="Thumbs Up", value="{:,}".format(results[0]["thumbs_up"]))
                em.add_field(name="Thumbs Down", value="{:,}".format(results[0]["thumbs_down"]))
                em.add_field(name="Link", value="[{}]({})".format(results[0]["word"], results[0]["permalink"]))
                await ctx.send(embed=em)
            else:
                msg = await ctx.send("Processing...")
                v = IndividualPager(ctx, msg, 1, [
                    "**Word**: [{}]({})\n**Author**: `{}`\n\n{}".format(i["word"], i["permalink"], i["author"],
                                                                        i["definition"]) for i in results],
                                    last_page=len(results), title=term, timeout=120)
                await msg.edit(None, embed=v.generate_embed(), view=v)

    @commands.command(aliases=["paste", "pastebin", "haste", "uploadtext"], brief="Upload text to hastebin",
                      usage="<text>")
    @commands.cooldown(2, 60)
    async def hastebin(self, ctx, *, text):
        """Easily upload text from Discord to a hastebin instance, you can also do this manually without a cooldown
        online"""
        r = requests.post(self.bot_config["hastebin"] + "documents", data=text.strip().encode("utf-8"))
        if not r.ok:
            return await ctx.reply("Error occurred while attempting to upload to hastebin, try again later")
        await ctx.reply(self.bot_config["hastebin"] + r.json()["key"])

    @commands.command(brief="Send a timestamp", usage="[format] <timestamp>", aliases=["ts"])
    async def timestamp(self, ctx, frmt: typing.Optional[TimestampFormatConverter] = "", *, timestamp):
        """Convert date time, date, or just time (with timezones) to a Discord timestamp. See the
        [discord api docs](https://discord.com/developers/docs/reference#message-formatting-timestamp-styles) for
        format options."""
        parsed = dateparser.parse(timestamp)
        if parsed is None:
            return await ctx.send("Unable to parse given timestamp, try a more standard format")
        else:
            ts = "<t:{}{}>".format(int(datetime.timestamp(parsed)), frmt)
            return await ctx.send("{0} (to use it in chat, enter `{0}` where you want it). The preview at the front of "
                                  "the message should be the timestamp in your local time, if it doesn't match up with "
                                  "what you expect, try again with a different format.".format(ts))

    @commands.command(brief="Notify people not to ping you", aliases=["noping"], usage="<message>")
    @commands.guild_only()
    async def nopings(self, ctx, *, message):
        """Automatically tell people not to ping you, with a custom message that'll be sent when they ping you.
        This command toggles the feature per-server."""
        if str(ctx.author.id) in self.server_config[str(ctx.guild.id)]["nopings"]:
            return await ctx.send("You already have pings disabled")
        elif len(message) > 1028:
            return await ctx.send("The custom message is too long")
        self.server_config[str(ctx.guild.id)]["nopings"][str(ctx.author.id)] = message
        self.server_config.write_config()
        await ctx.send("Successfully added to the no pings list")

    @commands.command(brief="Disable the no ping feature", aliases=["disablenoping"])
    @commands.guild_only()
    async def disablenopings(self, ctx):
        if str(ctx.author.id) not in self.server_config[str(ctx.guild.id)]["nopings"]:
            return await ctx.send("You don't have pings disabled")
        del self.server_config[str(ctx.guild.id)]["nopings"][str(ctx.author.id)]
        self.server_config.write_config()
        await ctx.send("Successfully removed from the no pings list")
