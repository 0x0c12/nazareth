import os
from discord.ext import commands
from config import token, prefix
import threading
import asyncio


import discord
intents = discord.Intents.default()
intents.message_content = True
nz = commands.Bot(command_prefix=prefix, intents=intents)

async def load_all_extensions():
    for folder in ["cogs", "events"]:
        folder_path = os.path.join(os.path.dirname(__file__), folder)
        if os.path.exists(folder_path):
            for filename in os.listdir(folder_path):
                if filename.endswith(".py"):
                    await nz.load_extension(f"{folder}.{filename[:-3]}")

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

@nz.event
async def on_ready():
    print(f"Logged in as {nz.user}")

def nz_start():
    asyncio.run(load_all_extensions())
    nz.run(token)
