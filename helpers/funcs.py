import nextcord

def cut_mentions(objs, max_length) -> str:
    rf = ""
    for r in objs:
        if len(rf.strip() + r.mention) >= max_length - 3:
            rf = rf.strip() + "..."
            break
        else:
            rf += r.mention + " "
    return rf.strip()

async def get_webhook(ctx, client) -> nextcord.Webhook:
    webhook = None
    for hook in await ctx.message.channel.webhooks():
        if hook.user.id == client.user.id:
            webhook = hook
            break
    if webhook is None:
        webhook = await ctx.message.channel.create_webhook(name="Bored Webhook")

    return webhook
