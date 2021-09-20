import itertools
from math import ceil

import nextcord
from nextcord.ext.commands import Group, HelpCommand

from helpers.views import HelpPager

class BotHelp(HelpCommand):
    def __init__(self, **options):
        super().__init__(**options)
        self.f = {}

    def add_commands(self, commands, *, heading):
        """Adds a list of formatted commands under a field title."""
        if not commands:
            return
        if heading not in self.f:
            self.f[heading] = []

        for command in commands:
            if isinstance(command, Group):
                name = "**__{}__**".format(command.name)
            else:
                name = "**{}**".format(command.name)
            entry = "{} - {}".format(name, command.name or "")
            if len("\n".join(self.f[heading] + [entry])) > 1024:
                heading += " Continued"
                self.f[heading] = []
            self.f[heading].append(entry)

    async def send(self):
        msg = await self.get_destination().send("Processing...")
        view = HelpPager(self.context, msg, 1, ceil(len(self.f) / 25), self.f, "Help")
        await msg.edit(None, embed=view.generate_embed(), view=view)

    async def command_callback(self, ctx, *, command=None):
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
        em = nextcord.Embed(title="{}{} {}".format(self.context.clean_prefix, command.name, command.usage or ""),
                            description=command.help or command.brief or None, colour=nextcord.Colour.random())
        em.add_field(name="Category", value=command.cog_name if command.cog_name is not None else "Uncategorized")
        if len(command.aliases) > 0:
            em.add_field(name="Command Aliases", value=" ".join(["`{}`".format(i) for i in command.aliases]))
        await self.get_destination().send(embed=em)

    async def send_group_help(self, group):
        # TODO: make group help
        pass

    async def send_cog_help(self, cog):
        # TODO: make cog help
        pass
