from datetime import timedelta

import nextcord

# noinspection PyUnusedLocal
class RpsChoice(nextcord.ui.View):
    def __init__(self, expected_uid):
        super().__init__(timeout=30)
        self.choice = None
        self.expected_uid = expected_uid

    async def default_response(self, interaction, choice):
        if interaction.user.id != self.expected_uid:
            await interaction.response.send_message("You're not the person who started this game! You can start your "
                                                    "own with the `rockpaperscissors` command.", ephemeral=True)
            return
        self.choice = choice
        self.stop()

    @nextcord.ui.button(label="Rock", emoji="🪨", style=nextcord.ButtonStyle.grey)
    async def rock(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.default_response(interaction, "Rock")

    @nextcord.ui.button(label="Paper", emoji="📝", style=nextcord.ButtonStyle.grey)
    async def paper(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.default_response(interaction, "Paper")

    @nextcord.ui.button(label="Scissors", emoji="✂️", style=nextcord.ButtonStyle.grey)
    async def scissors(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.default_response(interaction, "Scissors")

# noinspection PyUnusedLocal
class AcceptDecline(nextcord.ui.View):
    def __init__(self, expected_uid, timeout):
        super().__init__(timeout=timeout)
        self.status = None
        self.expected_uid = expected_uid

    async def default_response(self, interaction, accepted: bool):
        if interaction.user.id != self.expected_uid:
            await interaction.response.send_message("You weren't the one invited to play this game!", ephemeral=True)
            return
        self.status = accepted
        self.stop()

    @nextcord.ui.button(label="Accept", emoji="✔️", style=nextcord.ButtonStyle.green)
    async def accept(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.default_response(interaction, True)

    @nextcord.ui.button(label="Decline", emoji="❌", style=nextcord.ButtonStyle.red)
    async def decline(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.default_response(interaction, False)

# noinspection PyUnusedLocal
class GenericPager(nextcord.ui.View):
    def __init__(self, ctx, original_message, page, last_page, entries, title=None, line_separator="\n\n", ipp=10,
                 timeout=300):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.original_message = original_message
        self.page = page
        self.last_page = last_page
        self.entries = entries
        self.title = title
        self.line_separator = line_separator
        self.ipp = ipp
        self.expected_uid = ctx.author.id

    def generate_embed(self):
        si = (self.page - 1) * self.ipp
        em = nextcord.Embed(title=self.title, description=self.line_separator.join(self.entries[si:si + self.ipp]),
                            colour=nextcord.Colour.random())
        em.set_footer(text="Page {:,}/{:,}".format(self.page, self.last_page),
                      icon_url=self.ctx.author.display_avatar.url)
        return em

    async def resp(self, interaction: nextcord.Interaction, new_page):
        if interaction.user.id != self.expected_uid:
            return await interaction.response.send_message("You weren't the one who sent the command!", ephemeral=True)
        elif not self.last_page >= new_page >= 1:
            return await interaction.response.send_message("You've already reached the first/last page", ephemeral=True)
        self.page = new_page

        await self.original_message.edit(embed=self.generate_embed())

    @nextcord.ui.button(label="<<", style=nextcord.ButtonStyle.blurple)
    async def first(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.resp(interaction, 1)

    @nextcord.ui.button(label="<", style=nextcord.ButtonStyle.blurple)
    async def before(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.resp(interaction, self.page - 1)

    @nextcord.ui.button(label="Stop Command", emoji="🛑", style=nextcord.ButtonStyle.red)
    async def cancel(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        self.stop()
        await self.original_message.edit(view=None)

    @nextcord.ui.button(label=">", style=nextcord.ButtonStyle.blurple)
    async def after(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.resp(interaction, self.page + 1)

    @nextcord.ui.button(label=">>", style=nextcord.ButtonStyle.blurple)
    async def last(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        await self.resp(interaction, self.last_page)

# noinspection PyUnusedLocal
class MusicQueuePager(GenericPager):
    def __init__(self, page, last_page, pages, current_song, ctx, msg, total_duration):
        super().__init__(ctx, msg, page, last_page, pages)
        self.expected_uid = ctx.author.id
        self.page = page
        self.last_page = last_page
        self.pages = pages
        self.current_song = current_song
        self.ctx = ctx
        self.msg = msg
        self.total_duration = total_duration

    def generate_embed(self):
        desc = "**Current Song: ** [{}]({}) | `{}`\n\n".format(
            self.current_song.title, self.current_song.url, str(timedelta(seconds=self.current_song.duration))
        ) if self.current_song is not None else ""
        si = (self.page - 1) * 10
        for i, s in enumerate(self.pages[si:si + 10]):
            desc += "`{:,}.` [{}]({}) | `{}`\n\n".format(
                si + 1 + i, s.get('title'), s.get('webpage_url') or "https://www.youtube.com/watch?v=" + s.get('url'),
                str(timedelta(seconds=s.get('duration'))))
        desc += "**{:,} songs in queue | {} total length**".format(len(self.pages),
                                                                   str(timedelta(seconds=self.total_duration)))
        em = nextcord.Embed(title="Queue for " + self.ctx.guild.name,
                            description=desc, colour=nextcord.Colour.random())
        em.set_footer(text="Page {:,}/{:,}".format(self.page, self.last_page),
                      icon_url=self.ctx.author.display_avatar.url)

        return em

    async def resp(self, interaction, new_page):
        if interaction.user.id != self.expected_uid:
            return await interaction.response.send_message("You weren't the one who sent the command!", ephemeral=True)
        elif not self.last_page >= new_page >= 1:
            return await interaction.response.send_message("You've already reached the first/last page", ephemeral=True)
        self.page = new_page

        await self.msg.edit(embed=self.generate_embed())

class HelpPager(GenericPager):
    def generate_embed(self):
        desc = self.entries[self.page - 1]
        em = nextcord.Embed(title=self.title, description=desc, colour=nextcord.Colour.random())
        em.set_footer(text="Page {:,}/{:,}".format(self.page, self.last_page),
                      icon_url=self.ctx.author.display_avatar.url)
        return em
