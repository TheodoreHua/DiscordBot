import itertools
from re import sub

import nextcord
from nextcord.ext.commands import Group, HelpCommand

from helpers.views import GenericPager, HelpPager


class BotHelp(HelpCommand):
    def __init__(self, bot_config, **options):
        super().__init__(**options)
        self.bot_config = bot_config
        self.f = {}

    def add_commands(self, commands, *, heading):
        """Adds a list of formatted commands under a field title."""
        if not commands:
            return
        if heading not in self.f:
            self.f[heading] = []

        for command in commands:
            name = ("**__{}__**" if isinstance(command, Group) else "**{}**").format(command.name)
            entry = "{} - {}".format(name, command.brief or "*No command brief*")
            if len("\n".join(self.f[heading] + [entry])) > 1024:
                heading += " Continued"
                self.f[heading] = []
            self.f[heading].append(entry)

    async def send(self):
        """Send a help pager"""
        msg = await self.get_destination().send("Processing...")
        view = HelpPager(self.context, msg, 1, self.f, title="Help", ipp=25, description=self.bot_config["description"])
        await msg.edit(None, embed=view.generate_embed(), view=view)

    async def command_callback(self, ctx, *, command=None):
        """Prepare and generate the help command"""
        await self.prepare_help_command(ctx, command)
        bot = ctx.bot

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        cog = bot.get_cog(command)
        if cog is not None:
            return await self.send_cog_help(cog)

        maybe_coro = nextcord.utils.maybe_coroutine

        keys = command.split(' ')
        cmd = bot.all_commands.get(keys[0])
        if cmd is None:
            string = await maybe_coro(self.command_not_found, self.remove_mentions(keys[0]))
            return await self.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)
            except AttributeError:
                string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                return await self.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                    return await self.send_error_message(string)
                cmd = found

        if isinstance(cmd, Group):
            return await self.send_group_help(cmd)
        else:
            return await self.send_command_help(cmd)

    async def send_bot_help(self, mapping):
        def get_category(command):
            cog = command.cog
            return cog.qualified_name if cog is not None else '\u200bUncategorized'

        filtered = await self.filter_commands(self.context.bot.commands, sort=True, key=get_category)
        to_iterate = itertools.groupby(filtered, key=get_category)

        for category, commands in to_iterate:
            commands = sorted(commands, key=lambda c: c.name)
            self.add_commands(commands, heading=category)
        await self.send()

    async def send_command_help(self, command):
        usg = "{}{} {}".format(self.context.clean_prefix, command.qualified_name, command.usage or "")
        em = nextcord.Embed(title=usg if len(usg) <= 256 else nextcord.Embed.Empty,
                            description=("`{}`\n\n".format(usg) if len(usg) > 256 else "") + sub(r"(?<!\n)\n(?!\n)", " ", command.help or command.brief or ""),
                            colour=nextcord.Colour.random())
        em.add_field(name="Category", value=command.cog_name if command.cog_name is not None else "Uncategorized")
        if len(command.aliases) > 0:
            em.add_field(name="Command Aliases", value=", ".join(["`{}`".format(i) for i in command.aliases]))
        await self.get_destination().send(embed=em)

    async def send_group_help(self, group):
        l = []
        for i in await self.filter_commands(group.commands, sort=True):
            name = ("**__{}__**" if isinstance(i, Group) else "**{}**").format(i.name)
            l.append("{} - {}".format(name, i.brief or "*No command brief*"))
        msg = await self.get_destination().send("Processing...")
        view = GenericPager(self.context, msg, 1, l, ipp=30, line_separator="\n")
        await msg.edit(None, embed=view.generate_embed(), view=view)

    async def send_cog_help(self, cog):
        l = [cog.description + "\n"] if cog.description else []
        for i in await self.filter_commands(cog.get_commands(), sort=True):
            name = ("**__{}__**" if isinstance(i, Group) else "**{}**").format(i.name)
            l.append("{} - {}".format(name, i.brief or "*No command brief*"))
        msg = await self.get_destination().send("Processing...")
        view = GenericPager(self.context, msg, 1, l, title=cog.qualified_name, ipp=30, line_separator="\n")
        await msg.edit(None, embed=view.generate_embed(), view=view)
