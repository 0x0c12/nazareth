import aiosqlite

class NzStickyDb:
    def __init__(self, path="nazareth.db"):
        self.path = path

    async def add_channel(self, channel_id: int, content: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                """
                INSERT INTO StickyChannels(channel_id, content)
                VALUES (?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET
                    content=excluded.content
                """,
                (channel_id, content)
            )
            await db.commit()

    async def remove_channel(self, channel_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "DELETE FROM StickyChannels WHERE channel_id = ?",
                (channel_id,)
            )
            await db.commit()

    async def set_message_id(self, channel_id: int, message_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "UPDATE StickyChannels SET message_id=? WHERE channel_id=?",
                (message_id, channel_id)
            )
            await db.commit()

    async def get_sticky_channels(self):
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT channel_id, content, message_id FROM StickyChannels"
            )
            rows = await cursor.fetchall()
            return {
                row[0]: {"content": row[1], "message_id": row[2], "last_msg_id": None}
                for row in rows
            }

async def setup(bot):
    pass
