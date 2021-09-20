import random
import re
from difflib import SequenceMatcher

import nextcord
import requests
from nextcord.ext import commands
from typed_flags import TypedFlags

from helpers.funcs import cut_mentions, get_webhook


class Utility(commands.Cog):
    def __init__(self, client, bot_config, server_config, user_config):
        self.client = client
        self.bot_config = bot_config
        self.server_config = server_config
        self.user_config = user_config

    @commands.command(aliases=["pfp"], brief="Get a user's profile picture",
                      help="Get a user's profile picture, or run the command by itself for your own profile picture.")
    async def avatar(self, ctx, user: nextcord.User = None):
        if user is None:
            user = ctx.message.author
        em = nextcord.Embed(description=user.mention + "'s Avatar", colour=self.bot_config["embed_colour"])
        em.set_image(url=user.display_avatar.url)

        await ctx.send(embed=em)

    @commands.command(brief="Roll some dice", help="Roll some dice, by default it'll be a 1d6 (one 6-sided die), "
                                                   "however you can roll more dice with varying number of sides.",
                      aliases=["roll"])
    async def dice(self, ctx, amount: int, sides: int):
        if amount > 100 or sides > 10000000000000000:
            await ctx.send("Woahhh, slow down there. That's too large, Discord can't handle it!")
            return
        rolled = []
        for _ in range(amount):
            rolled.append(random.randint(1, sides))

        await ctx.send("**Result:** {}d{} ({})\n**Total**: {}".format(amount, sides, ", ".join(str(i) for i in rolled),
                                                                      sum(rolled)))

    @commands.command(brief="Choose between a couple options",
                      help="Provide a list of options for the bot to choose 1 out of seperated by spaces. For options"
                           " with spaces in them, enclose it in double quotes.")
    async def choose(self, ctx, *options):
        await ctx.send("I choose: `{}`".format(random.choice(options)))

    @commands.command(brief="Show the bots ping")
    async def ping(self, ctx):
        await ctx.send("Pong! `{:,.4f}ms`".format(self.client.latency * 1000))

    @commands.command(brief="Show info about this server")
    @commands.guild_only()
    async def serverinfo(self, ctx):
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
        em.set_author(name="Server Owner: {}#{}".format(g.owner.name, g.owner.discriminator),
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

    @commands.command(brief="Show info about a user", help="Show info about a user, not specific to this server")
    async def userinfo(self, ctx, user: nextcord.User):
        em = nextcord.Embed(colour=self.bot_config["embed_colour"])
        em.set_thumbnail(url=user.display_avatar.url)
        em.set_author(name=user.name + '#' + user.discriminator, icon_url=user.display_avatar.url)
        em.add_field(name="ID", value=str(user.id))
        em.add_field(name="Created At", value=user.created_at.strftime("%Y-%m-%d %H:%M:%S.%f UTC"))
        em.add_field(name="Bot", value=user.bot)

        await ctx.message.channel.send(embed=em)

    @commands.command(brief="Show info about a member", help="Show info about a user/member, specific to this server")
    @commands.guild_only()
    async def memberinfo(self, ctx, member: nextcord.Member):
        em = nextcord.Embed(description=member.mention, colour=self.bot_config["embed_colour"])
        em.set_thumbnail(url=member.display_avatar.url)
        em.set_author(name=member.name + '#' + member.discriminator, icon_url=member.display_avatar.url)
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

    @commands.command(brief="Send animated emojis in your message without nitro",
                      help="Send animated emojis in your message without nitro. Replace the location you want the "
                           "emote with :emote name here:. You should only use this if you don't have nitro, or it'll "
                           "probably mess up with Discord's autocomplete. For example: Hello :animated wave:.",
                      aliases=["ae"])
    @commands.guild_only()
    async def animatedemoji(self, ctx, *, message):
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

    @commands.command(brief="Send a message as another user (to impersonate them)")
    async def impersonate(self, ctx, user: nextcord.User, *, message):
        await ctx.message.delete()

        webhook = await get_webhook(ctx, self.client)
        await webhook.send(content=message, username=user.display_name, avatar_url=user.display_avatar.url)

    @commands.command(brief="Send a message as a custom user",
                      help="Send a message as a custom user, basically a one-time-use Tupper (if you know what I'm "
                           "talking about). Username and message flags are required, avatar is optional (you can also "
                           "upload an avatar as a file).",
                      usage="<message> --username:=<username> --avatar:=[avatar url]")
    async def usersend(self, ctx, *, args: TypedFlags):
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

    @commands.command(brief="Send longer messages", help="Combine two existing 2000 character messages into one 4000 "
                                                         "character message. By default the original 2 messages "
                                                         "are not deleted, you can pass an extra bool value to delete "
                                                         "them.", aliases=["combinemessage", "cm"])
    async def messagecombine(self, ctx, msg1: nextcord.Message, msg2: nextcord.Message, delete_originals: bool = False):
        await ctx.message.delete()
        new_message = msg1.content + "\n" + msg2.content
        if len(new_message) > 4096:
            return await ctx.send("New message too long", delete_after=15)
        em = nextcord.Embed(description=new_message)
        em.set_author(name=ctx.author.name + "#" + ctx.author.discriminator, icon_url=ctx.author.display_avatar.url)
        await ctx.send(embed=em)

        if delete_originals:
            await msg1.delete()
            await msg2.delete()

    @commands.command(brief="Send hyperlinks using embeds", help="Send hyperlinks using embeds, hyperlinks have to be "
                                                                 "in the format `[text](link)`. All this really does "
                                                                 "is put your text as the description in an embed, so "
                                                                 "you can use any other formatting embeds have. If you "
                                                                 "want a more advanced command, try the embedgen "
                                                                 "command.", aliases=["embeddescription", "ed", "h"])
    async def hyperlink(self, ctx, *, message):
        await ctx.message.delete()
        em = nextcord.Embed(description=message)
        em.set_author(name=ctx.author.name + "#" + ctx.author.discriminator, icon_url=ctx.author.display_avatar.url)

        await ctx.send(embed=em)
