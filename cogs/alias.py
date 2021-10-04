import nextcord
from nextcord.ext import commands

from helpers.views import GenericPager

class Alias(commands.Cog):
    def __init__(self, client, bot_config, server_config, user_config):
        self.client = client
        self.bot_config = bot_config
        self.server_config = server_config
        self.user_config = user_config

    @commands.command(brief="Call upon an alias", aliases=["a", "tag"], usage="<alias>")
    @commands.guild_only()
    async def alias(self, ctx, *, name):
        name = name.lower()
        if name not in self.server_config[str(ctx.guild.id)]["aliases"]:
            return await ctx.send("`{}` is not a valid alias name. Use the `aliases` command to get a list of aliases."
                                  .format(name))
        em = nextcord.Embed(description=self.server_config[str(ctx.guild.id)]["aliases"][name],
                            colour=self.bot_config["embed_colour"])
        em.set_author(name="{}alias {}".format(ctx.clean_prefix, name))
        await ctx.send(embed=em)

    @commands.command(brief="Add a message alias that can be called upon at any time", usage="\"<name>\" <message>")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    async def addalias(self, ctx, name, *, message):
        """Add a message alias that can be called upon by using \"alias <name>\" at any time. They are not case
        sensitive."""
        name = name.lower()
        if name in self.server_config[str(ctx.guild.id)]["aliases"]:
            return await ctx.send("`{}` is already an alias name for this server".format(name))
        self.server_config[str(ctx.guild.id)]["aliases"][name] = message
        self.server_config.write_config()
        em = nextcord.Embed(description=message, colour=self.bot_config["embed_colour"])
        em.set_author(name="{}alias {}".format(ctx.clean_prefix, name))
        await ctx.send(embed=em)

    @commands.command(brief="Remove a message alias", usage="<alias>")
    @commands.guild_only()
    @commands.has_guild_permissions(manage_messages=True)
    async def removealias(self, ctx, *, name):
        """Remove an alias from the server"""
        name = name.lower()
        if name not in self.server_config[str(ctx.guild.id)]["aliases"]:
            return await ctx.send("`{}` is not an alias name for this server".format(name))
        del self.server_config[str(ctx.guild.id)]["aliases"][name]
        self.server_config.write_config()
        await ctx.send("Alias `{}` removed".format(name))

    @commands.command(brief="Get a list of aliases")
    @commands.guild_only()
    async def aliases(self, ctx):
        """Get a list of all aliases in the server"""
        aliases = list(self.server_config[str(ctx.guild.id)]["aliases"].keys())
        if len(aliases) < 1:
            return await ctx.send("This server has no aliases, create one with the `addalias` command")
        msg = await ctx.send("Processing...")
        view = GenericPager(ctx, msg, 1, aliases, title="Aliases for " + ctx.guild.name, line_separator="\n",
                            timeout=120)
        await msg.edit(None, embed=view.generate_embed(), view=view)
