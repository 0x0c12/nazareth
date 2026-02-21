from discord.ext import commands
import discord

class NzPin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pin")
    async def pin(self, ctx, message_id: int = None):
        if ctx.message.reference is not None:
            msg_to_pin = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        elif message_id is not None:
            try:
                msg_to_pin = await ctx.channel.fetch_message(message_id)
            except:
                await ctx.send("Could not find a message with that ID.")
                return
        else:
            await ctx.send("You must either reply to a message or provide a message ID")
            return                

        try:
            await  msg_to_pin.pin()
            await ctx.send(f"Pinned the message: {msg_to_pin.content[:50]}...")
        except discord.Forbidden:
            await ctx.send("I don't have the permission to pin messages in this channel")
        except discord.HTTPException:
            await ctx.send("Failed to pin the message")
            
    @commands.command(name="unpin")
    async def unpin(self, ctx, message_id: int = None):
        if ctx.message.reference is not None:
            msg_to_unpin = await ctx.channel.fetch_message(ctx.message.reference.message_id)
        elif message_id is not None:
            try:
                msg_to_unpin = await ctx.channel.fetch_message(message_id)
            except:
                await ctx.send("Could not find a message with that ID.")
                return
        else:
            await ctx.send("You must either reply to a message or provide a message ID")
            return                

        try:
            await  msg_to_unpin.unpin()
            await ctx.send(f"Unpinned the message: {msg_to_unpin.content[:50]}...")
        except discord.Forbidden:
            await ctx.send("I don't have the permission to unpin messages in this channel")
        except discord.HTTPException:
            await ctx.send("Failed to pin the message")
        except Exception as e:
            await ctx.send("Couldn't unpin message because {e}")

async def setup(bot):
    await bot.add_cog(NzPin(bot))
