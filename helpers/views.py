from datetime import timedelta
from math import ceil

import nextcord

# noinspection PyUnusedLocal
class RpsChoice(nextcord.ui.View):
    def __init__(self, expected_uid):
        """Create an RpsChoice view

        :param int expected_uid: User ID of the expected reactant
        """
        super().__init__(timeout=30)
        self.choice = None
        self.expected_uid = expected_uid

    async def default_response(self, interaction: nextcord.Interaction, choice):
        """Response method called by button's in this class

        :param interaction: Interaction associated with button choice
        :param str choice: RPS Choice
        :return:
        """
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
        """Create an AcceptDecline view

        :param int expected_uid: User ID of the expected reactant
        :param int timeout: Timeout for the view
        """
        super().__init__(timeout=timeout)
        self.status = None
        self.expected_uid = expected_uid

    async def default_response(self, interaction, accepted: bool):
        """Response method called by button's in this class

        :param interaction:
        :param bool accepted:
        :return:
        """
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
class DeleteResponse(nextcord.ui.View):
    def __init__(self, message, replied_author_id=None, timeout=60):
        """Create a DeleteResponse view, it deletes the provided message when the author clicks the button

        :param nextcord.Message message: Message to delete when the button is clicked
        :param int replied_author_id: User ID of the author in which the response is for, if none any person can delete
        the message
        :param int timeout: Timeout for the button
        """

        super().__init__(timeout=timeout)
        self.original_message = message
        self.replied_author_id = replied_author_id

    async def on_timeout(self):
        self.stop()
        await self.original_message.edit(view=None)

    @nextcord.ui.button(label="Delete", emoji="🗑️", style=nextcord.ButtonStyle.red)
    async def delete(self, button: nextcord.ui.Button, interaction: nextcord.Interaction):
        if self.replied_author_id is None or self.replied_author_id == interaction.user.id:
            await self.original_message.delete()
            await interaction.response.send_message("Message deleted.", ephemeral=True)
        else:
            await interaction.response.send_message("You're not the person this message is in reply to, as such you "
                                                    "can't delete it.", ephemeral=True)


# noinspection PyUnusedLocal
class GenericPager(nextcord.ui.View):
    def __init__(self, ctx, original_message, page, entries, last_page=None, title=None, line_separator="\n\n", ipp=10,
                 timeout=300):
        """Create a GenericPager view

        :param ctx: Context associated with the view
        :param nextcord.Message original_message: The message the bot sent with the view (and embed)
        :param int page: Default starting page number
        :param list entries: Entries to be paginated
        :param int last_page: Last page number
        :param str title: Embed title
        :param str line_separator: Separator between entries
        :param int ipp: Items Per Page, number of entries per page
        :param int timeout: Timeout for the page buttons
        """
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.original_message = original_message
        self.page = page
        self.last_page = last_page or ceil(len(entries) / ipp)
        self.entries = entries
        self.title = title
        self.line_separator = line_separator
        self.ipp = ipp
        self.expected_uid = ctx.author.id

    def generate_embed(self):
        """Generate the embed for a certain page

        :return: Generated webhook for the current page
        :rtype: nextcord.Embed
        """
        si = (self.page - 1) * self.ipp
        em = nextcord.Embed(title=self.title, description=self.line_separator.join(self.entries[si:si + self.ipp]),
                            colour=nextcord.Colour.random())
        em.set_footer(text="Page {:,}/{:,}".format(self.page, self.last_page),
                      icon_url=self.ctx.author.display_avatar.url)
        return em

    async def resp(self, interaction: nextcord.Interaction, new_page):
        """Response method called by button's in this class

        :param interaction: Interaction associated with the button press
        :param int new_page: New page number after button changes
        :return:
        """
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


class IndividualPager(GenericPager):
    def generate_embed(self):
        em = nextcord.Embed(title=self.title, description=self.entries[self.page - 1],
                            colour=nextcord.Colour.random())
        em.set_footer(text="Page {:,}/{:,}".format(self.page, self.last_page),
                      icon_url=self.ctx.author.display_avatar.url)
        return em


# noinspection PyUnusedLocal
class MusicQueuePager(GenericPager):
    def __init__(self, page, last_page, pages, current_song, ctx, msg, total_duration):
        """Create a MusicQueuePager view

        :param int page: Default starting page number
        :param int last_page: Last page number
        :param list pages: Pages to go through
        :param current_song: Current song at time of generation
        :param ctx: Context associated with the view
        :param nextcord.Message msg: Original message containing the view and embed
        :param int total_duration: Total duration of all songs in the queue in seconds
        """
        super().__init__(ctx, msg, page, pages, last_page=last_page)
        self.pages = pages
        self.msg = msg
        self.current_song = current_song
        self.total_duration = total_duration

    def generate_embed(self):
        """Generate the embed for a queue page

        :return: Generated webhook for the current page
        :rtype: nextcord.Embed
        """
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
        """Response method called by button's in this class

        :param interaction:
        :param int new_page:
        :return:
        """
        if interaction.user.id != self.expected_uid:
            return await interaction.response.send_message("You weren't the one who sent the command!", ephemeral=True)
        elif not self.last_page >= new_page >= 1:
            return await interaction.response.send_message("You've already reached the first/last page", ephemeral=True)
        self.page = new_page

        await self.msg.edit(embed=self.generate_embed())

class HelpPager(GenericPager):
    def __init__(self, ctx, original_message, page, entries, last_page=None, title=None, line_separator="\n\n", ipp=10,
                 timeout=300, description=None):
        """Create a GenericPager view

        :param ctx: Context associated with the view
        :param nextcord.Message original_message: The message the bot sent with the view (and embed)
        :param int page: Default starting page number
        :param list entries: Entries to be paginated
        :param int last_page: Last page number
        :param str title: Embed title
        :param str line_separator: Separator between entries
        :param int ipp: Items Per Page, number of entries per page
        :param int timeout: Timeout for the page buttons
        :param str description: Bot description (rendered in Embed description portion)
        """
        super().__init__(ctx, original_message, page, entries, last_page, title, line_separator, ipp, timeout)
        self.description = description

    def generate_embed(self):
        si = (self.page - 1) * 25
        fs = sorted(self.entries)[si:si + 25]
        em = nextcord.Embed(title=self.title, description=self.description, colour=nextcord.Colour.random())
        em.set_footer(text="Page {:,}/{:,}".format(self.page, self.last_page),
                      icon_url=self.ctx.author.display_avatar.url)
        for n in fs:
            em.add_field(name=n, value="\n".join(self.entries[n]), inline=False)
        return em
