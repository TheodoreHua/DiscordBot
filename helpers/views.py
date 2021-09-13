import nextcord

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
