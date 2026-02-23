import time
from datetime import datetime
from typing import Optional
import struct
import aiohttp
import asyncio
import zipfile
from pathlib import Path

class OsuNotLinked(Exception):
    pass

class OsuUserNotFound(Exception):
    pass

class OsuService:
    CACHE_TTL = 300 # TO after 5 mins ig

    def __init__(self, osu_client, db, osu_cookie):
        self.client = osu_client
        self.db = db
        self.osu_cookie = osu_cookie
        self.cache = {}  # osu_id -> {"data": user, "timestamp": float}

    def _extract_osz(self, osz_path: Path, songs_dir: Path) -> Path:
        beatmapset_id = osz_path.stem
        extract_path = songs_dir / beatmapset_id
        
        if extract_path.exists():
            print("Already extracted.")
            return

        extract_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(osz_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

        print(f"Extracted to: {extract_path}")
        return extract_path
    
    def _extract_beatmap_md5(self, replay_path: Path) -> str:
        with open(replay_path, "rb") as f:
            f.read(1)  # game mode
            f.read(4)  # version
    
            def read_string(file):
                indicator = file.read(1)
                if indicator == b"\x00":
                    return ""
                length = 0
                shift = 0
                while True:
                    byte = file.read(1)[0]
                    length |= (byte & 0x7F) << shift
                    if not (byte & 0x80):
                        break
                    shift += 7
                return file.read(length).decode()
    
            return read_string(f) # md5 :D

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

    async def download_beatmap_from_replay(self, replay_file_name: Path) -> Path:
        base_path = Path('/home/twilight/dev/nazareth/src/services/osu')
        replay_path = base_path / replay_file_name
        beatmap_checksum = self._extract_beatmap_md5(replay_path)

        if beatmap_checksum == "":
            raise Exception("Replay does not contain a valid beatmap checksum.")

        '''
        beatmap_id = await self.client.__http.make_request(
            Path("beatmaps/lookup"),
            checksum=beatmap_checksum
        )['id']
        '''

        # download_url = f"https://osu.ppy.sh/osu/{beatmap_id}"
        beatmap = await self.client.lookup_beatmap(checksum=beatmap_checksum)
        download_url = f"https://osu.ppy.sh/beatmapsets/{beatmap.beatmapset.id}/download"
        headers = {
            "Cookie": f"osu_session={self.osu_cookie}",
            "Host": "osu.ppy.sh",
            "Referer": f"https://osu.ppy.sh/beatmapsets/{beatmap.beatmapset.id}",
            "User-Agent": "Mozilla/5.0",
            "Accept": "*/*",
            "Set-Fetch-Dest": "document",
            "Set-Fetch-Mode": "navigate",
            "Set-Fetch-Site": "same-origin"
        }

        output_path = base_path / "beatmap_cache" / f"{beatmap.beatmapset.id}.osz"
        print(f"Using output path: {output_path}")
        
        # caching :D
        if output_path.exists():
            print("Using cached beatmapset: ", beatmap.beatmapset.id)
            return output_path

        print(f"Download url of beatmap: {download_url}")

        async with aiohttp.ClientSession() as session:
            # Redirect phase
            async with session.get(download_url, headers=headers, allow_redirects=False) as resp:
                if resp.status not in (301, 302):
                    raise Exception(f"Unexpected status: {resp.status}") 

                cdn_url = resp.headers.get("Location")
                print("CDN url: ", cdn_url)

                if not cdn_url:
                    raise Exception("No cdn URL found")

            # Actually downloading
            async with session.get(cdn_url) as cdn_resp:
                if cdn_resp.status != 200:
                    raise Exception(f"CDN download failed: {cdn_resp.status}")

                content = await cdn_resp.read()

        with open(output_path, "wb") as f:
            f.write(content)

        print("Downloaded beatmapset:", beatmap.beatmapset.id)
        osz_unpacked_path = base_path / "beatmap_cache"
        self._extract_osz(output_path, osz_unpacked_path)

        await asyncio.sleep(2)
        replay_path.unlink()
        return output_path
