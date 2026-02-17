# funny story actually, i accidentally wiped this whole database interface file and forgot to commit changes
# and this broke most of the bot
# now i spent hours and hours trying to get this to work and then i just said
# firetruck it, let ai do what its best at: GENERATE CODE. I already had the logic and the dependencies of other modules
# so i just fed the AI overlords my entire codebase and made it generate this whole interface again
# lesson: PLEASE COMMIT EVERYTIME SOMETHING WORKS MAN, I'M TELLING YOU IT'LL SAVE YOU FROM A LOT OF HEADACHE
# I WOULD RATHER DEFENESTRATE MYSELF THAN FIGHT A HALLUCINATING AI TRYING TO DO GOD KNOWS WHAT WITH MY CODEBASE
# SO MUCH SO THAT I HAVE NO IDEA WHAT'S GOING ON
# anyway, i guess that's enough
# fin

import aiosqlite
import asyncio

class NzDatabase:
    def __init__(self, path="nazareth.db"):
        self.path = path
        self.loop = asyncio.get_event_loop()
        # Schedule table initialization in the background
        self.loop.create_task(self.init_tables())

    async def init_tables(self):
        """Ensure all necessary tables exist"""
        async with aiosqlite.connect(self.path) as db:
            # Verification table
            await db.execute("""
                CREATE TABLE IF NOT EXISTS Verification (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    verified INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (guild_id, user_id)
                )
            """)
            # Guild roles for verification
            await db.execute("""
                CREATE TABLE IF NOT EXISTS GuildRoles (
                    guild_id INTEGER PRIMARY KEY,
                    role_id INTEGER
                )
            """)
            # Social credits
            await db.execute("""
                CREATE TABLE IF NOT EXISTS SocialCredits (
                    user_id INTEGER PRIMARY KEY,
                    credits INTEGER DEFAULT 0,
                    profile TEXT DEFAULT 'broke',
                    taxes REAL DEFAULT 0
                )
            """)
            # Sticky channels
            await db.execute("""
                CREATE TABLE IF NOT EXISTS StickyChannels (
                    channel_id INTEGER PRIMARY KEY,
                    content TEXT,
                    message_id INTEGER
                )
            """)
            await db.commit()

    # ===== Verification methods =====
    async def set_verified_role(self, guild_id: int, role_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                INSERT INTO GuildRoles(guild_id, role_id)
                VALUES (?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET role_id=excluded.role_id
            """, (guild_id, role_id))
            await db.commit()

    async def get_guild_role_id(self, guild_id: int):
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT role_id FROM GuildRoles WHERE guild_id=?", (guild_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else None

    async def set_user_verification(self, guild_id: int, user_id: int, verified: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                INSERT INTO Verification(guild_id, user_id, verified)
                VALUES (?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET verified=excluded.verified
            """, (guild_id, user_id, verified))
            await db.commit()

    async def is_verified(self, guild_id: int, user_id: int):
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute("""
                SELECT verified FROM Verification WHERE guild_id=? AND user_id=?
            """, (guild_id, user_id))
            row = await cursor.fetchone()
            return bool(row[0]) if row else False

    # ===== Social credits =====
    async def get_credits(self, user_id: int):
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT credits FROM SocialCredits WHERE user_id=?", (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def get_profile(self, user_id: int):
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT profile FROM SocialCredits WHERE user_id=?", (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else "broke"

    async def get_taxes(self, user_id: int):
        async with aiosqlite.connect(self.path) as db:
            cursor = await db.execute(
                "SELECT taxes FROM SocialCredits WHERE user_id=?", (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row else 0.0

    async def update_credits(self, user_id: int, amount: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                INSERT INTO SocialCredits(user_id, credits)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET credits = credits + excluded.credits
            """, (user_id, amount))
            await db.commit()

    async def update_profile(self, user_id: int, profile: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                INSERT INTO SocialCredits(user_id, profile)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET profile=excluded.profile
            """, (user_id, profile))
            await db.commit()

    async def update_taxes(self, user_id: int, taxes: float):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                INSERT INTO SocialCredits(user_id, taxes)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET taxes=excluded.taxes
            """, (user_id, taxes))
            await db.commit()

    # ===== Sticky channels =====
    async def add_sticky_channel(self, channel_id: int, content: str):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                INSERT INTO StickyChannels(channel_id, content)
                VALUES (?, ?)
                ON CONFLICT(channel_id) DO UPDATE SET content=excluded.content
            """, (channel_id, content))
            await db.commit()

    async def remove_sticky_channel(self, channel_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute(
                "DELETE FROM StickyChannels WHERE channel_id=?", (channel_id,)
            )
            await db.commit()

    async def set_sticky_message_id(self, channel_id: int, message_id: int):
        async with aiosqlite.connect(self.path) as db:
            await db.execute("""
                UPDATE StickyChannels SET message_id=? WHERE channel_id=?
            """, (message_id, channel_id))
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
