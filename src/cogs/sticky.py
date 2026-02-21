from discord.ext import commands
from cogs.nz_sticky_db import NzStickyDb

class NzSticky(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sticky_db = NzStickyDb("nazareth.db")

    @commands.group(name="sticky", invoke_without_command=True)
    async def sticky(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send(
                "```Available subcommands:\nadd <content> - adds a sticky message to this channel\nremove - removes the sticky message```"
            )

    @sticky.command(name="add")
    async def sticky_add(self, ctx, *, content: str = None):
        if not content:
            await ctx.send("```Usage: ~sticky add <content>```")
            return

        # Add to DB
        await self.sticky_db.add_channel(ctx.channel.id, content)

        # Update runtime cache
        handler = self.bot.get_cog("NzStickyHandler")
        if handler:
            handler.sticky_cache[ctx.channel.id] = {"content": content, "message_id": None, "last_msg_id": None}

            # Post sticky immediately
            sticky_msg = await ctx.send(content)
            handler.sticky_cache[ctx.channel.id]["last_msg_id"] = sticky_msg.id

            # Save message_id in DB
            await self.sticky_db.set_message_id(ctx.channel.id, sticky_msg.id)

        await ctx.send("Sticky added to this channel!")

    @sticky.command(name="remove")
    async def sticky_remove(self, ctx):
        # Remove from DB
        await self.sticky_db.remove_channel(ctx.channel.id)

        # Remove from cache and delete last posted sticky
        handler = self.bot.get_cog("NzStickyHandler")
        if handler and ctx.channel.id in handler.sticky_cache:
            last_msg_id = handler.sticky_cache[ctx.channel.id].get("last_msg_id")
            if last_msg_id:
                try:
                    old_msg = await ctx.channel.fetch_message(last_msg_id)
                    if old_msg:
                        await old_msg.delete()
                except Exception:
                    pass
            handler.sticky_cache.pop(ctx.channel.id)

        await ctx.send("Sticky removed from this channel!")


async def setup(bot):
    await bot.add_cog(NzSticky(bot))
