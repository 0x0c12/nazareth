import discord
from discord.ext import commands
from datetime import datetime
from collections import defaultdict
import asyncio

SESSION_LIMIT = 40

class DmLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.target_id = 1473680563083939962
        self.target = None
        self.sessions = {}
        self.locks = defaultdict(asyncio.Lock)
        # user_id -> {
        #   "message_id": int,
        #   "count": int
        # }

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        if message.guild is not None:
            return

        if message.author.bot:
            return

        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        header = f"# DM Session: {message.author} ({message.author.id})\n\n"
        line = f"[{timestamp}] {message.content}\n"

        user_id = message.author.id

        for attachment in message.attachments:
            line += f"[Attachment] [{attachment.filename}]({attachment.url})\n"
                
        async with self.locks[user_id]:
            content = header + line # simple single instantiation of content variable for all cases :D
            
            # fresh session creation
            if user_id not in self.sessions:
                log_msg = await self.target.send(content)
                self.sessions[user_id] = {
                    "message": log_msg,
                    "count": 1,
                    "content": content
                }
                return

            session = self.sessions[user_id]

            # creating a new session
            if session["count"] >= SESSION_LIMIT:
                log_msg = await self.target.send(content)
                self.sessions[user_id] = {
                    "message": log_msg,
                    "count": 1,
                    "content": content
                }
                return

            # finally get to editing if the previous checks are passed
            try:
                session = self.sessions[user_id]
                log_msg = session["message"]
                
                new_content = session["content"] + line

                # Safety for 2000 char limit
                if len(new_content) > 1900:
                    log_msg = await self.target.send(content)
                    self.sessions[user_id] = {
                        "message": log_msg,
                        "count": 1,
                        "content": content
                    }
                    return

                await log_msg.edit(content=new_content)
                session["content"] = new_content
                session["count"] += 1

            except discord.NotFound:
                # If message deleted manually
                log_msg = await self.target.send(content)
                self.sessions[user_id] = {
                    "message": log_msg,
                    "count": 1,
                    "content": content
                }

async def setup(bot):
    cog = DmLogger(bot)
    target = bot.get_user(cog.target_id)
    
    if target is None:
        target = bot.get_channel(cog.target_id)
    
    if target is None:
        try:
            target = await bot.fetch_channel(cog.target_id)
        except:
            target = await bot.fetch_user(cog.target_id)

    cog.target = target
    await bot.add_cog(cog)
