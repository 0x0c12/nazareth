from discord.ext import commands

class MessageLogger(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        print(f'Message from {message.author}: {message.content}')

async def setup(bot):
    await bot.add_cog(MessageLogger(bot))
