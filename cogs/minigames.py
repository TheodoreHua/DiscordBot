import asyncio
import random
import re

import nextcord
import requests
from deck_of_cards import deck_of_cards
from minesweeperPy import mineGen
from nextcord.ext import commands

from helpers.views import RpsChoice, AcceptDecline


def wf_check(message, ctx, regex=None):
    return message.author == ctx.author and message.channel == ctx.message.channel and \
           (True if regex is None else re.match(regex, message.content))


class Minigames(commands.Cog):
    def __init__(self, client, bot_config, server_config, user_config):
        self.client = client
        self.bot_config = bot_config
        self.server_config = server_config
        self.user_config = user_config

    @commands.command(brief="Play a game of rock paper scissors", aliases=["rps"])
    async def rockpaperscissors(self, ctx):
        """Play rock paper scissors with the bot, not much more to it"""
        view = RpsChoice(ctx.author.id)
        msg = await ctx.send("Choose your hand", view=view)
        if await view.wait():
            await msg.edit("", embed=nextcord.Embed(title="You lost", description="You didn't pick an option in time",
                                                    colour=nextcord.Colour.red()), view=None)

        bot_choice = random.choice(["Rock", "Paper", "Scissors"])
        if bot_choice == view.choice:
            await msg.edit("", embed=nextcord.Embed(
                title="We tied", description="We both picked " + view.choice, colour=nextcord.Colour.yellow()),
                           view=None)
        else:
            wm = {"Rock": "Scissors", "Scissors": "Paper", "Paper": "Rock"}
            if wm[bot_choice] == view.choice:
                await msg.edit("", embed=nextcord.Embed(
                    title="I won", description="I picked {}, you picked {}".format(bot_choice, view.choice),
                    colour=nextcord.Colour.red()), view=None)
            else:
                await msg.edit("", embed=nextcord.Embed(
                    title="You won", description="I picked {}, you picked {}".format(bot_choice, view.choice),
                    colour=nextcord.Colour.green()), view=None)

    @commands.command(brief="Play a game of hangman")
    async def hangman(self, ctx, lives: int = 6):
        """Play a game of hangman, the words are picked from a
        [list of commonish words](https://raw.githubusercontent.com/bevacqua/correcthorse/master/wordlist.json)."""
        word = random.choice(
            requests.get("https://raw.githubusercontent.com/bevacqua/correcthorse/master/wordlist.json").json()).lower()
        guessed_letters = []
        win, desc, col = False, None, None

        em = nextcord.Embed(title="".join(["%" for _ in word]),
                            description="Welcome to Hangman! You have {:,} lives, guess by typing a letter or your full "
                                        "word guess in chat. Valid guesses are alphabet characters and dashes/hyphens. "
                                        "Type `=quit=` to leave the game".format(lives),
                            colour=self.bot_config["embed_colour"])
        em.add_field(name="Lives", value="{:,}".format(lives))
        em.add_field(name="Guessed", value="None", inline=False)
        msg = await ctx.send(embed=em)

        while lives > 0:
            try:
                res = await self.client.wait_for('message',
                                                 check=lambda i: wf_check(i, ctx, r"^(=quit=|[a-zA-Z-]+)$"), timeout=30)
            except asyncio.TimeoutError:
                await msg.edit(embed=nextcord.Embed(title=word, description="You took too long to answer.",
                                                    colour=nextcord.Colour.dark_red()))
                return

            await res.delete()
            guess = res.content.lower()
            if guess == "=quit=":
                await msg.edit(embed=nextcord.Embed(title=word, description="You quit the game.",
                                                    colour=nextcord.Colour.dark_red()))
                return
            elif guess in guessed_letters:
                desc = "You already guessed this letter!"
                col = nextcord.Colour.yellow()
            elif len(guess) == 1:
                guessed_letters.append(guess)
                if all([i in guessed_letters for i in word]):
                    win = True
                elif guess in word:
                    desc = "`{}` is in the word!".format(guess)
                    col = nextcord.Colour.green()
                else:
                    desc = "`{}` is not in the word!".format(guess)
                    col = nextcord.Colour.red()
                    lives -= 1
            else:
                if guess == word:
                    win = True
                else:
                    desc = "That's not it, try again"
                    col = nextcord.Colour.red()
                    lives -= 1

            if win:
                break

            new_em = nextcord.Embed(title="".join(map(lambda i: "%" if i not in guessed_letters else i, word)),
                                    description=desc, colour=col)
            new_em.add_field(name="Lives", value="{:,}".format(lives))
            new_em.add_field(name="Guessed", value="`" + " ".join(
                [i.upper() for i in sorted(guessed_letters)]) + "`" if len(guessed_letters) > 0 else "None")
            await msg.edit(embed=new_em)

        if win:
            await msg.edit(embed=nextcord.Embed(title=word, description="You won with {:,} lives left".format(lives),
                                                colour=nextcord.Colour.dark_green()))
        else:
            await msg.edit(embed=nextcord.Embed(title=word,
                                                description="You ran out of lives, the word was `{}`".format(word),
                                                colour=nextcord.Colour.dark_red()))

    @commands.command(brief="Play a number guess game", aliases=["numberguess", "ng"])
    async def numguess(self, ctx, lives: int = 8, upper_bound: int = 100):
        """Try to guess a number between a range, when you guess an incorrect number the bot will tell you whether the
        number is too high or too low"""
        num = random.randint(0, upper_bound)
        win, desc, col = False, None, None

        em = nextcord.Embed(title="Welcome",
                            description="Welcome to the number guessing game. Guess a number by sending a message then "
                                        "follow the clues to guess the correct number. Type `=quit=` to quit.",
                            colour=self.bot_config["embed_colour"])
        em.add_field(name="Lives", value="{:,}".format(lives))
        em.add_field(name="Range", value="0-{:,}".format(upper_bound))
        msg = await ctx.send(embed=em)

        while lives > 0:
            try:
                res = await self.client.wait_for('message',
                                                 check=lambda i: wf_check(i, ctx, r"^(=quit=|-?\d+)$"), timeout=30)
            except asyncio.TimeoutError:
                await msg.edit(embed=nextcord.Embed(title="Answer: {:,}".format(num),
                                                    description="You took too long to answer.",
                                                    colour=nextcord.Colour.dark_red()))
                return

            await res.delete()
            if res.content == "=quit=":
                await msg.edit(embed=nextcord.Embed(title="Answer: {:,}".format(num),
                                                    description="You quit the game.",
                                                    colour=nextcord.Colour.dark_red()))
                return

            guess = int(res.content)
            if not 0 <= guess <= upper_bound:
                desc = "Your number must be in the range 0-{:,}!".format(upper_bound)
                col = nextcord.Colour.yellow()
            elif guess == num:
                win = True
                break
            elif guess > num:
                desc = "Your guess was **too high**."
                col = nextcord.Colour.red()
                lives -= 1
            elif guess < num:
                desc = "Your guess was **too low**."
                col = nextcord.Colour.red()
                lives -= 1

            new_em = nextcord.Embed(title="Guess: {:,}".format(guess),
                                    description=desc, colour=col)
            new_em.add_field(name="Lives", value="{:,}".format(lives))
            em.add_field(name="Range", value="0-{:,}".format(upper_bound))
            await msg.edit(embed=new_em)

        if win:
            await msg.edit(embed=nextcord.Embed(title="Answer: {:,}".format(num),
                                                description="You won with {:,} lives left".format(lives),
                                                colour=nextcord.Colour.dark_green()))
        else:
            await msg.edit(embed=nextcord.Embed(title="Answer: {:,}".format(num),
                                                description="You ran out of lives",
                                                colour=nextcord.Colour.dark_red()))

    @commands.command(brief="Send a minesweeper grid")
    async def minesweeper(self, ctx, difficulty="medium", grid_width: int = 5, grid_height: int = 5):
        """Send a minesweeper grid, there is no win/lose logic, it's just a grid."""
        if grid_width > 12 or grid_height > 12:
            await ctx.send("The maximum size of the grid is 12 x 12")
        if grid_width < 5 or grid_height < 5:
            await ctx.send("The minimum size of the grid is 5 x 5")
        generator = mineGen(grid_width, grid_height)
        difficulties = {"easy": (10, 20), "medium": (20, 30), "hard": (30, 40)}
        grid_map = {' ': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣', '5': '5️⃣', '6': '6️⃣', '7': '7️⃣',
                    '8': '8️⃣', '9': '9️⃣', 'M': '💣'}

        try:
            mine_percentage = random.randint(difficulties[difficulty.lower()][0],
                                             difficulties[difficulty.lower()][1]) / 100
        except KeyError:
            await ctx.message.channel.send("Please enter a valid difficulty, `easy`, `medium`, or `hard`.")
            return
        num_mine = round(grid_width * grid_height * mine_percentage)
        grid = generator.generateGrid(num_mine)['grid']
        grid_send = ["**Difficulty**: `{}` | **Percentage of Mines**: `{}%` | **Grid Size:** `{}` x `{}`".format(
            difficulty.upper(), round(mine_percentage * 100), str(grid_width), str(grid_height))]
        for r in grid:
            r_str = ""
            for b in r:
                r_str += b.replace(b, "||{}||".format(grid_map[b]))
            grid_send.append(r_str)

        await ctx.send("\n".join(i for i in grid_send))

    @commands.command(brief="Play a game of Tic Tac Toe", aliases=["ttt"])
    async def tictactoe(self, ctx, player: nextcord.Member):
        """Play a game of Tic Tac Toe with another server member"""
        if player == ctx.author or player.bot:
            await ctx.send("You can't invite this player to a game!", delete_after=5)
            return
        confirm = AcceptDecline(player.id, 30)
        msg = await ctx.send("{}, {} wants to play a game of Tic Tac Toe with you, would you like to play?".format(
            player.mention, ctx.author.mention), view=confirm)
        if await confirm.wait() or not confirm.status:
            await msg.edit("Sorry, looks like they didn't want to play.", view=None)
            return
        await msg.delete()

        def descrip_gen(grid):
            desc, c = "", 1
            for i in grid:
                desc += i + " "
                if c == 3:
                    c = 0
                    desc = desc.rstrip() + "\n"
                c += 1
            return desc.rstrip()

        def embed_gen(grid, players, current_player, turn, colour):
            em = nextcord.Embed(title="{} ({}) vs. {} ({})".format(players[1][0].display_name, players[1][2].upper(),
                                                                   players[-1][0].display_name, players[-1][2].upper()),
                                description=descrip_gen(grid), colour=colour)
            em.add_field(name="Current Player", value="{} ({})".format(players[current_player][0].mention,
                                                                       players[current_player][2].upper()))
            em.add_field(name="Turn Number", value=turn)

            return em

        def check_win(grid, check_emoji):
            sets = [[0, 1, 2], [3, 4, 5], [6, 7, 8], [0, 4, 8], [2, 4, 6], [0, 3, 6], [1, 4, 7], [2, 5, 8]]
            for s in sets:
                set_status = True
                for index in s:
                    if grid[index] != check_emoji:
                        set_status = False
                        break
                if set_status:
                    return True
            return False

        def check(reaction, user, current_player, msg, grid):
            return reaction.message.id == msg.id and user.id == current_player.id and reaction.emoji in grid

        emap = {"1": "1️⃣", "2": "2️⃣", "3": "3️⃣", "4": "4️⃣", "5": "5️⃣", "6": "6️⃣", "7": "7️⃣", "8": "8️⃣", "9": "9️⃣",
                "0": "0️⃣", "x": "🇽", "o": "🇴"}
        grid, reacts, turn_number = [emap[str(i)] for i in range(1, 10)], {}, 1
        players, current_player = {1: (ctx.author, nextcord.Colour.blue(), "x"),
                                   -1: (player, nextcord.Colour.yellow(), "o")}, random.choice([1, -1])
        msg = await ctx.send("{}, the game has started. Please wait while I setup the game..."
                             .format(ctx.author.mention),
                             embed=embed_gen(grid, players, current_player, turn_number, players[current_player][1]))
        for emoji in grid:
            reacts[emoji] = await msg.add_reaction(emoji)
        await msg.edit("Game has been successfully setup, you may take your turn")

        while True:
            try:
                react = await self.client.wait_for("reaction_add", check=lambda r, u: check(
                    r, u, players[current_player][0], msg, grid), timeout=30)
            except asyncio.TimeoutError:
                await msg.edit("", embed=nextcord.Embed(title="{} ({}) Wins".format(
                    players[current_player * -1][0].display_name, players[current_player][2].upper()),
                    description="**{} abandoned the match**\n{}".format(players[current_player][0].display_name,
                                                                        descrip_gen(grid)),
                    colour=players[current_player * -1][1]))
                return
            grid = [i if i != react[0].emoji else emap[players[current_player][2]] for i in grid]
            async for user in react[0].users():
                await react[0].remove(user)
                await asyncio.sleep(0.2)

            if all([i == emap[players[current_player][2]] or
                    i == emap[players[current_player * -1][2]] for i in grid]):
                await msg.edit("", embed=nextcord.Embed(title="Tie", description=descrip_gen(grid),
                    colour=nextcord.Colour.orange()))
                return
            if check_win(grid, emap[players[current_player][2]]):
                await msg.edit("", embed=nextcord.Embed(title="{} ({}) Wins".format(
                    players[current_player][0].display_name, players[current_player][2].upper()),
                    description=descrip_gen(grid),
                    colour=players[current_player][1]))
                return
            else:
                current_player *= -1
                turn_number += 1
                await msg.edit("", embed=embed_gen(grid, players, current_player, turn_number,
                                                   players[current_player][1]))

    @commands.command(brief="Play a round of Blackjack", aliases=["bj"])
    async def blackjack(self, ctx):
        """Play a game of Blackjack with the bot as the dealer"""

        def get_card(deck):
            first_len = len(deck.deck)
            card = deck.give_random_card()
            second_len = len(deck.deck)
            for x in range(0, first_len - second_len - 1):
                deck.take_card(card)
            return card

        def get_emoji(value, suit):
            suit_values = {0: "S", 1: "H", 2: "D", 3: "C"}
            suit_letter = suit_values[suit]
            for guild in self.client.guilds:
                for emoji in guild.emojis:
                    if emoji.name == str(value) + suit_letter:
                        return "<:{}:{}>".format(emoji.name, str(emoji.id))
            return "Error: Emoji Not Found"

        def generate_deck(num_deck):
            deck_obj = deck_of_cards.DeckOfCards()
            for x in range(0, num_deck):
                deck_obj.add_deck()
            deck_obj.shuffle_deck()
            return deck_obj

        def get_value(hand):
            val = 0
            for card in hand:
                if card.value > 10:
                    val += 10
                    continue
                if card.value == 1:
                    continue
                val += card.value
            for card in hand:
                if card.value == 1:
                    if val + 11 <= 21:
                        val += 11
                        continue
                    else:
                        val += 1
            return val

        def check_soft(hand):
            val = 0
            for card in hand:
                if card.value > 10:
                    val += 10
                    continue
                if card.value == 1:
                    continue
                val += card.value
            status = []
            for card in hand:
                if card.value == 1:
                    if val + 11 <= 21:
                        status.append(True)
                        val += 11
                    else:
                        status.append(False)
                        val += 1
            for status in status:
                if status:
                    return True
            return False

        def check(message):
            if (message.author == ctx.message.author and message.content.lower() == "hit") or (
                    message.author == ctx.message.author and message.content.lower() == "stand"):
                return True
            return False

        def check_lose(hand):
            val = get_value(hand)
            if val > 21:
                return True
            return False

        def embed_gen(player, dealer, status):
            if status == "lost":
                colour = nextcord.Colour.red()
            elif status == "won":
                colour = nextcord.Colour.green()
            elif status == "tied":
                colour = nextcord.Colour.gold()
            else:
                status = "An Error Has Occured"
                colour = nextcord.Colour.dark_red()
            embed = nextcord.Embed(
                description="You {}!".format(status),
                colour=colour
            )
            embed.set_author(name=ctx.message.author.name + '#' + ctx.message.author.discriminator,
                             icon_url=ctx.message.author.display_avatar.url)
            player_emoji = " ".join(get_emoji(x.value, x.suit) for x in player)
            dealer_emoji = " ".join(get_emoji(x.value, x.suit) for x in dealer)
            player_value = str(get_value(player_hand))
            dealer_value = str(get_value(dealer_hand))
            if check_soft(player_hand):
                player_value = "Soft " + str(get_value(player_hand))
            if check_soft(dealer_hand):
                dealer_value = "Soft " + str(get_value(dealer_hand))
            if get_value(player_hand) == 21:
                player_value = "Blackjack"
            if get_value(dealer_hand) == 21:
                dealer_value = "Blackjack"
            embed.add_field(name="Your Hand:", value="{}\nValue: {}".format(player_emoji, player_value))
            embed.add_field(name="Dealer's Hand:", value="{}\nValue: {}".format(dealer_emoji, dealer_value))
            return embed

        player_hand = []
        dealer_hand = []
        deck = generate_deck(6)
        dealer_hand.append(get_card(deck))
        dealer_hand.append(get_card(deck))
        player_hand.append(get_card(deck))
        player_hand.append(get_card(deck))
        embed = nextcord.Embed(
            description="Type `hit` to draw another card or `stand` to pass. If you don't respond for 1 minute, you lose!",
            colour=nextcord.Colour.blue()
        )
        embed.set_author(name=ctx.message.author.name + '#' + ctx.message.author.discriminator,
                         icon_url=ctx.message.author.display_avatar.url)
        player_emoji = " ".join(get_emoji(x.value, x.suit) for x in player_hand)
        dealer_emoji = get_emoji(dealer_hand[0].value, dealer_hand[0].suit) + " " + "<:blue_back:706507690054123561>"
        player_value = str(get_value(player_hand))
        dealer_value = str(dealer_hand[0].value)
        if dealer_hand[0].value > 10:
            dealer_value = "10"
        if check_soft(player_hand):
            player_value = "Soft " + str(get_value(player_hand))
        if check_soft(dealer_hand) and dealer_hand[0].value == 1:
            dealer_value = "Soft 11"
        embed.add_field(name="Your Hand:", value="{}\nValue: {}".format(player_emoji, player_value))
        embed.add_field(name="Dealer's Hand:", value="{}\nValue: {}".format(dealer_emoji, dealer_value))
        message = await ctx.message.channel.send(embed=embed)
        if check_lose(dealer_hand):
            await message.edit(embed=embed_gen(player_hand, dealer_hand, "won"))
            return
        if get_value(player_hand) == 21:
            await message.edit(embed=embed_gen(player_hand, dealer_hand, "won"))
            return
        if get_value(dealer_hand) == 21:
            await message.edit(embed=embed_gen(player_hand, dealer_hand, "lost"))
            return
        if check_lose(player_hand):
            await message.edit(embed=embed_gen(player_hand, dealer_hand, "lost"))
            return
        while True:
            try:
                choice = await self.client.wait_for("message", check=check, timeout=60)
            except asyncio.TimeoutError:
                await ctx.message.channel.send("You took more than 1 minute to answer, you lost!")
                return
            if choice.content.lower() == "stand":
                break
            player_hand.append(get_card(deck))
            if check_lose(player_hand):
                await message.edit(embed=embed_gen(player_hand, dealer_hand, "lost"))
                return
            if get_value(player_hand) == 21:
                await message.edit(embed=embed_gen(player_hand, dealer_hand, "won"))
                return
            if len(player_hand) >= 7:
                await message.edit(embed=embed_gen(player_hand, dealer_hand, "won"))
                return
            embed = nextcord.Embed(
                description="Type `hit` to draw another card or `stand` to pass. If you don't respond for 1 minute, you lose!",
                colour=nextcord.Colour.blue()
            )
            embed.set_author(name=ctx.message.author.name + '#' + ctx.message.author.discriminator,
                             icon_url=ctx.message.author.display_avatar.url)
            player_emoji = " ".join(get_emoji(x.value, x.suit) for x in player_hand)
            dealer_emoji = get_emoji(dealer_hand[0].value,
                                     dealer_hand[0].suit) + " " + "<:blue_back:706507690054123561>"
            player_value = str(get_value(player_hand))
            dealer_value = str(dealer_hand[0].value)
            if dealer_hand[0].value > 10:
                dealer_value = "10"
            if check_soft(player_hand):
                player_value = "Soft " + str(get_value(player_hand))
            if check_soft(dealer_hand) and dealer_hand[0].value == 1:
                dealer_value = "Soft 11"
            if get_value(player_hand) == 21:
                await message.edit(embed=embed_gen(player_hand, dealer_hand, "won"))
                return
            embed.add_field(name="Your Hand:", value="{}\nValue: {}".format(player_emoji, player_value))
            embed.add_field(name="Dealer's Hand:", value="{}\nValue: {}".format(dealer_emoji, dealer_value))
            await message.edit(embed=embed)
        while get_value(dealer_hand) < 17:
            dealer_hand.append(get_card(deck))
            if check_lose(dealer_hand):
                await message.edit(embed=embed_gen(player_hand, dealer_hand, "won"))
                return
            if get_value(dealer_hand) == 21:
                await message.edit(embed=embed_gen(player_hand, dealer_hand, "lost"))
                return
            if len(dealer_hand) >= 7:
                await message.edit(embed=embed_gen(player_hand, dealer_hand, "lost"))
                return
            embed = nextcord.Embed(
                description="Dealer is playing!",
                colour=nextcord.Colour.orange()
            )
            embed.set_author(name=ctx.message.author.name + '#' + ctx.message.author.discriminator,
                             icon_url=ctx.message.author.display_avatar.url)
            player_emoji = " ".join(get_emoji(x.value, x.suit) for x in player_hand)
            dealer_emoji = " ".join(get_emoji(x.value, x.suit) for x in dealer_hand)
            player_value = str(get_value(player_hand))
            dealer_value = str(get_value(dealer_hand))
            if check_soft(player_hand):
                player_value = "Soft " + str(get_value(player_hand))
            if check_soft(dealer_hand):
                dealer_value = "Soft " + str(get_value(dealer_hand))
            if get_value(player_hand) == 21:
                player_value = "Blackjack"
            if get_value(dealer_hand) == 21:
                dealer_value = "Blackjack"
            embed.add_field(name="Your Hand:", value="{}\nValue: {}".format(player_emoji, player_value))
            embed.add_field(name="Dealer's Hand:", value="{}\nValue: {}".format(dealer_emoji, dealer_value))
            await message.edit(embed=embed)
            await asyncio.sleep(1)
        if get_value(dealer_hand) == get_value(player_hand):
            await message.edit(embed=embed_gen(player_hand, dealer_hand, "tied"))
            return
        winning_value = min([get_value(player_hand), get_value(dealer_hand)],
                            key=lambda list_value: abs(list_value - 21))
        if winning_value == get_value(player_hand):
            await message.edit(embed=embed_gen(player_hand, dealer_hand, "won"))
            return
        await message.edit(embed=embed_gen(player_hand, dealer_hand, "lost"))
        return
