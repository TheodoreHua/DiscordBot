import asyncio
import logging
import json
import sys

import requests
import nextcord
from nextcord.ext import commands

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] (%(name)s): %(message)s'")


class BotOwner(commands.Cog):
    def __init__(self, client, bot_config, server_config, user_config):
        self.client = client
        self.bot_config = bot_config
        self.server_config = server_config
        self.user_config = user_config

    @commands.command(hidden=True)
    @commands.is_owner()
    async def setstatus(self, ctx, *, status):
        if ctx.guild is not None:
            await ctx.message.delete()
        await self.client.change_presence(status=nextcord.Status.online,
                                          activity=nextcord.Game(status if status != "reset"
                                                                 else self.bot_config["status"]))
        await ctx.send("Bot's status set to `{}` until reset".format(status) if status != "reset" else
                       "Bot's status reset", delete_after=5)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def say(self, ctx, *, message):
        if ctx.guild is not None:
            await ctx.message.delete()
        await ctx.send(message)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def spam(self, ctx, number: int, *, message):
        if ctx.guild is not None:
            await ctx.message.delete()
        for _ in range(number):
            await ctx.send(message)
            await asyncio.sleep(1)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def fastspam(self, ctx, number: int, *, message):
        if ctx.guild is not None:
            await ctx.message.delete()
        for _ in range(number):
            await ctx.send(message)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def reinstallrequirements(self, ctx):
        proc = await asyncio.create_subprocess_shell("venv/bin/python -m pip install -r requirements.txt",
                                                     stdout=asyncio.subprocess.PIPE)
        stdout, stderr = await proc.communicate()
        r = requests.post(self.bot_config["hastebin"] + "/documents", data=stdout)
        paste_link = self.bot_config["hastebin"] + r.json()["key"] if r.ok else None
        await ctx.send("{}\n```\n{}\n```".format(paste_link, stdout.decode()[-1900:]))

    @commands.command(hidden=True, usage="<type>")
    @commands.is_owner()
    @commands.dm_only()
    async def showconfig(self, ctx, tp):
        tp = tp.lower()
        if tp == 'server':
            d = self.server_config
        elif tp == 'user':
            d = self.user_config
        else:
            return await ctx.send("Invalid type")
        d = json.dumps(d.__config__, indent=2)
        if len(d) > 1993:
            r = requests.post(self.bot_config["hastebin"] + "/documents", data=d)
            return await ctx.send(self.bot_config["hastebin"] + "/documents", r.json()["key"])
        else:
            return await ctx.send("```json\n{}\n```".format(d),)

    @commands.command(hidden=True)
    @commands.is_owner()
    async def restart(self, ctx, save:bool=True):
        logging.info("Received restart command, terminating program and letting start script restart it")
        await ctx.send("Restarting...")
        if save:
            self.server_config.write_config()
            self.user_config.write_config()
        sys.exit()

    @commands.command(hidden=True)
    @commands.is_owner()
    async def exit(self, ctx):
        logging.info("Received exit command, terminating program")
        await ctx.send("Exiting...")
        self.server_config.write_config()
        self.user_config.write_config()
        with open("maintain.txt", "w") as f:
            f.write("n")
        sys.exit()
