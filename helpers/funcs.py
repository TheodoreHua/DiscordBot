import nextcord

def cut_mentions(objs, max_length) -> str:
    """Cut a list of mentionable objects to a certain length

    :param list objs: A list of objects from Discord that can be mentioned (e.g. Roles, Users, Members, Channels, etc)
    :param int max_length: The maximum length to cut to
    :return: A string cut to the specified length consisting of the mentions
    """
    rf = ""
    for r in objs:
        if len(rf.strip() + r.mention) >= max_length - 3:
            rf = rf.strip() + "..."
            break
        else:
            rf += r.mention + " "
    return rf.strip()

def add_fields(embed, fields):
    """Add fields from a dict to an embed

    :param nextcord.Embed embed:
    :param dict fields:
    """
    for n, v in fields.items():
        embed.add_field(name=n, value=v)

async def get_webhook(ctx, client) -> nextcord.Webhook:
    """

    :param ctx: The context you're looking for a webhook in
    :param client: Bot client object
    :return: A webhook associated with the channel provided in Context
    """
    webhook = None
    for hook in await ctx.message.channel.webhooks():
        if hook.user.id == client.user.id:
            webhook = hook
            break
    if webhook is None:
        webhook = await ctx.message.channel.create_webhook(name="Bored Webhook")

    return webhook
