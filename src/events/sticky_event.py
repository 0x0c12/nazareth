from discord.ext import commands

class NzStickyHandler(commands.Cog):
    """Handles sticky message reposting automatically"""
    def __init__(self, bot, sticky_db):
        self.bot = bot
        self.sticky_db = sticky_db
        self.sticky_cache = {}  # channel_id -> {content, message_id, last_msg_id}

    async def load_cache(self):
        self.sticky_cache = await self.sticky_db.get_sticky_channels()

    @commands.Cog.listener()
    async def on_ready(self):
        await self.load_cache()

    @commands.Cog.listener()
    async def on_message(self, message):
        channel_data = self.sticky_cache.get(message.channel.id)
        if not channel_data:
            return

        # Ignore the sticky itself and any bot messages
        if message.author.bot or message.id == channel_data.get("last_msg_id"):
            return

        # Delete previous sticky
        last_msg_id = channel_data.get("last_msg_id")
        if last_msg_id:
            try:
                old_msg = await message.channel.fetch_message(last_msg_id)
                if old_msg:
                    await old_msg.delete()
            except Exception:
                pass

        # Send new sticky
        content = channel_data.get("content")
        if not content:
            return

        sticky_msg = await message.channel.send(content)

        # Update runtime cache
        channel_data["last_msg_id"] = sticky_msg.id

        # Update DB message_id only if sticky ID changed
        if sticky_msg.id != channel_data.get("message_id"):
            await self.sticky_db.set_message_id(message.channel.id, sticky_msg.id)
            channel_data["message_id"] = sticky_msg.id


async def setup(bot):
    from cogs.nz_sticky_db import NzStickyDb
    sticky_db = NzStickyDb("nazareth.db")
    await bot.add_cog(NzStickyHandler(bot, sticky_db))
