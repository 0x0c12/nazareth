from discord.ext import commands
import config
import random
import asyncio
import time

eggs_basket = {
    "gay": "i know you like kissing men, but i just can't prove it",
    "femboy": ["astolfo.", "totsuka saiki.", "ruka urushibara.", "twilight😳"],
    "sakura": '''I miss Sakura no Uta, ever since the DMCA incident it has been so silent. I no longer wake up to the beautiful sounds of Sakura no Uta, now it's just quiet and silent. I get up out of my bed and walk through the silent halls, devoid of heaven's greatest song, where I sit and eat a bowl of wheat flakes in silence, get ready for my dull workday, and make my way there in the silence that is a Sakura no Utaless world. I sit in the same monotone office cubicle, bloodshot eyes, red from my constant crying over the loss of Sakura no Uta and the dull dead expression from a life without which that I love. I go home, dull and without the will to eat or freshen up. I walk towards my room where the once Sakura no Uta-themed room of mine is now back to the dull and bleakness of yellow beige and white, as I sit in front of the only thing that is Sakura no Uta-themed left, my Shrine, I sit there and cry in prayer, hoping that one day it will come back to us, that Sakura no Uta will come back to me. As I sit there and pray and cry into the night in the silence of my lonely home, I get up and go lay in bed, such a dull bed of a dark blue blanket and a pillow, I lay there and whisper one more silent prayer. A prayer of "my beloved Sakura no Uta, please return to me my love" and I drift into sleep as I cry once. I dream a dream where I always hope to dream of a time I used to love but get nothing but nightmares now about my loss of Sakura no Uta and my loss of love. How I miss those days of joy and love with Sakura no Uta. How I miss Sakura no Uta''',
    "727": "https://tenor.com/view/wysi-gif-20492142",
    "osu": "just play more",
    "rotten apple": "https://files.catbox.moe/36hdqe.mp4",
    "rotten": "https://files.catbox.moe/36hdqe.mp4",
    "bad apple": "https://files.catbox.moe/36hdqe.mp4",
    "black and white": "https://files.catbox.moe/36hdqe.mp4",
    "lebanese": "okay, so you like kissing women?",
    "lesbian": "okay, so you like kissing women?",
    "yuri": "OMG I LOVEEEEE YURIII AHHHH. BUT I'M NOT GAY. GIRLS KISS OTHER GIRLS AND NO ONE BATS AN EYE",
    "?": ["wouldn't you like to know weather boy", "i prefer kanye"],
    "autism": "AUTISM SPEAKING LISTEN AND LEARN 🔇🗣️",
    "house": "https://tenor.com/view/dr-house-pill-hospital-dr-chase-house-gif-12906407686605985396",
    "please": "say pretty please🥺",
    "pretty please": "suck my wully👅",
    "💔": "https://files.catbox.moe/kt8hqw.mp4",
    "😔": "https://files.catbox.moe/kt8hqw.mp4",
    "😭": "https://files.catbox.moe/kt8hqw.mp4",
    "🥀": "https://files.catbox.moe/kt8hqw.mp4",
    "unicore": "https://cdn.discordapp.com/icons/1432012006571118634/d599d284bfdfa64a34ab203da75dc9a8.png?size=1024"
}

class EasterEggs(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_trigger = {}
        self.cooldown = 2

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.channel.id not in config.brainrot_channels:
            return
        
        if message.author.bot:
            return

        if message.content.startswith(self.bot.command_prefix):
            return
        
        con = message.content.lower()
        matches = []
        for egg, response in eggs_basket.items():
            if egg in con:
                
                if egg == "pretty please":
                    await message.reply(response, mention_author=False)
                    return
                matches.append(response)

                '''
                user_id = message.author.id
                now = time.monotonic()

                last = self.last_trigger.get(user_id, 0)
                if now - last < self.cooldown:
                    await message.reply("woah, slow down there", mention_author=True)
                    return
                self.last_trigger[user_id] = now
                '''
                                            
        if matches:
            response = random.choice(matches)
            if isinstance(response, list):
                response = random.choice(response)
            await message.reply(response, mention_author=False)

async def setup(bot):
    await bot.add_cog(EasterEggs(bot))
