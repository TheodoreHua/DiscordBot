import asyncio
import random
import re

import nextcord
import requests
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

    @commands.command(brief="Play a number guess game",
                      help="Try to guess a number between a range, when you guess an incorrect number the "
                           "bot will reply with too high or too low",
                      aliases=["numberguess", "ng"])
    async def numguess(self, ctx, lives: int = 8, upper_bound: int = 100):
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

    @commands.command(brief="Send a minesweeper grid", help="Send a minesweeper grid, there is no win/lose logic, "
                                                            "it's just a grid.")
    async def minesweeper(self, ctx, difficulty="medium", grid_width: int = 5, grid_height: int = 5):
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
