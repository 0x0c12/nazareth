from discord.ext import commands
import discord

class NzCreds(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(name="creds", invoke_without_commands=True)
    async def creds(self, ctx):
        if ctx.invoked_subcommand is None:
            await ctx.send("```Available subcommands:\nshow - shows the amount of social credts you have\nprofile - describes your profile\ntaxes - shows your tax benefits, negative means you owe money, positive means you ARE owed money```")

    @creds.command(name="show")
    async def show_creds(self, ctx, memb: discord.Member = None):
        member = ctx.author
        if memb is not None:
            member = memb
        credits = await self.bot.db.get_credits(member.id)
        await ctx.send(f"{member.display_name} has {credits} credits.")
        
    @creds.command(name="profile")
    async def show_profile(self, ctx, memb: discord.Member = None):
        member = ctx.author
        if memb is not None:
            member = memb
        profile = await self.bot.db.get_profile(member.id)
        await ctx.send(f"{member.display_name}'s profile:\n{profile}")
        
    @creds.command(name="taxes")
    async def show_taxes(self, ctx, memb: discord.Member = None):
        member = ctx.author
        if memb is not None:
            member = memb
        taxes = await self.bot.db.get_taxes(member.id)
        await ctx.send(f"{member.display_name}'s tax benefits: {taxes}")

async def setup(bot):
    await bot.add_cog(NzCreds(bot))
