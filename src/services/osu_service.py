import time
from datetime import datetime
from typing import Optional


class OsuNotLinked(Exception):
    pass


class OsuUserNotFound(Exception):
    pass


class OsuService:
    CACHE_TTL = 300 # TO after 5 mins ig

    def __init__(self, osu_client, db):
        self.client = osu_client
        self.db = db
        self.cache = {}  # osu_id -> {"data": user, "timestamp": float}


    async def link_user(self, discord_id: int, username: str):
        try:
            user = await self.client.get_user(username)
        except Exception:
            raise OsuUserNotFound("User not found or API error.")

        await self.db.link_osu(
            discord_id=discord_id,
            osu_id=user.id,
            linked_at=datetime.utcnow().isoformat()
        )

        cache_key = (user.id, None)
        self.cache[cache_key] = {
            "data": user,
            "timestamp": time.time()
        }

        return user

    async def unlink_user(self, discord_id: int):
        await self.db.unlink_osu(discord_id)

    async def get_profile(self, discord_id: int, mode: str | None = None):
        osu_id = await self.db.get_osu_id(discord_id)
        cache_key = (osu_id, mode)

        if not osu_id:
            raise OsuNotLinked("Discord account not linked.")

        cached = self.cache.get(cache_key)

        if cached:
            if time.time() - cached["timestamp"] < self.CACHE_TTL:
                return cached["data"]

        try:
            user = await self.client.get_user(osu_id, key="id", mode=mode)
        except Exception:
            raise OsuUserNotFound("Failed to fetch user.")


        self.cache[cache_key] = {
            "data": user,
            "timestamp": time.time()
        }

        return user

    async def get_top(self, discord_id: int, mode: str):
        osu_id = await self.db.get_osu_id(discord_id)
        if not osu_id:
            raise OsuNotLinked("Discord account not linked.")
        try:
            return await self.client.get_user_scores(
                osu_id,
                type="best",
                mode=mode,
                limit=10
            )
        except Exception:
            raise OsuUserNotFound("Failed to fetch top plays.")
    
    async def get_recent(self, discord_id: int, mode: str):
        osu_id = await self.db.get_osu_id(discord_id)
        if not osu_id:
            raise OsuNotLinked("Discord account not linked.")
        try:
            scores = await self.client.get_user_scores(
                osu_id,
                type="recent",
                mode=mode,
                limit=1,
                include_fails=True
            )
            return scores[0] if scores else None
        except Exception as e:
            raise OsuUserNotFound(f"Failed to fetch recent plays: {e}")
