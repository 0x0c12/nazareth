import os
import asyncio
import threading
import discord
from discord.ext import commands
import config
from cogs.nz_sticky_db import NzStickyDb
from nz_database import NzDatabase

intents = discord.Intents.default()
intents.message_content = True


class Nazareth(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix=config.prefix,
            intents=intents
        )
        self.db=None
        self.sticky_db=None

    async def setup_hook(self):
        self.db = NzDatabase("nazareth.db")
        await self.db.init_tables()
        self.sticky_db = NzStickyDb("nazareth.db")
        # await self.db.init_db()
        folders = [config.cog_folder, config.event_folder]

        for folder in folders:
            for file in os.listdir(folder):
                if file.endswith(".py") and not file.startswith("_"):
                    ext = f"{folder}.{file[:-3]}"
                    try:
                        await self.load_extension(ext)
                        print(f"Loaded {ext}")
                    except Exception as e:
                        print(f"Failed to load {ext}: {e}")

    async def on_ready(self):
        print(f"Logged in as {self.user}")


nz = Nazareth()


def shutdown_handler():
    while True:
        cmd = input().strip().lower()
        if cmd == "q":
            confirm = input("Are you sure you want to shut down the bot? (y/n): ").strip().lower()
            if confirm == "y":
                print("Shutting down...")
                asyncio.run_coroutine_threadsafe(nz.close(), nz.loop)
                break


threading.Thread(target=shutdown_handler, daemon=True).start()

if __name__ == "__main__":
    nz.run(config.token)
