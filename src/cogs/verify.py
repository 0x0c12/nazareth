from discord.ext import commands
import discord

class NzVerification(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    @commands.has_permissions(manage_roles=True)
    async def set_verified_role(self, ctx, role: discord.Role = None):
        if role is None:
            await ctx.send("```Usage: ~set_verified_role <@&role>```")
            return
        await self.bot.db.set_verified_role(ctx.guild.id, role.id)
        await ctx.send(f"Verified role set to {role.name}")

    @set_verified_role.error
    async def set_verified_role_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("```You don't have the permission to use this command.```")

    @commands.command()
    async def verify(self, ctx):
        member = ctx.author

        if (await self.bot.db.is_verified(ctx.guild.id, member.id)):
            await ctx.send(f"```User {member.display_name} has already been verified!```")
            return
                        
        role_id = await self.bot.db.get_guild_role_id(ctx.guild.id)
                    
        if role_id:
            role = ctx.guild.get_role(role_id)
            if role:
                try:
                    await member.add_roles(role)
                except discord.Forbidden:
                    await ctx.send(f"```Error! Insufficient Priveleges!\nI don’t have the permissions to modify roles!```")
                    return
                    
        else:
            await ctx.send(f"```Error! Role not assigned!\nYou must assign a role id using ~set_verified_role <role_id>```")
            return
            
        await ctx.send(f"```{member.display_name} has been verified!```")
        await self.bot.db.set_user_verification(ctx.guild.id, member.id, 1)
        
    @commands.command()
    async def distrust(self, ctx, member: discord.Member = None):
        if member is None:
            await ctx.send(f"```Usage: ~distrust <@user>```")
            return

        if not (await self.bot.db.is_verified(ctx.guild.id, member.id)):
            await ctx.send(f"```User {member.display_name} is already unverified!```")
            return
                        
        role_id = await self.bot.db.get_guild_role_id(ctx.guild.id)
                    
        if role_id:
            role = ctx.guild.get_role(role_id)
            if role:
                try:
                    await member.remove_roles(role)
                except discord.Forbidden:
                    await ctx.send(f"```Error! Couldn't assign role\nReason: I don't have permission to modify roles!```")
                    return
        else:
            await ctx.send(f"```Error! Role not assigned!\nYou must assign a role id using ~set_verified_role <role_id>```")
            return
            
        await ctx.send(f"```{member.display_name} is no longer verified```")
        await self.bot.db.set_user_verification(ctx.guild.id, member.id, 0)

async def setup(bot):
    await bot.add_cog(NzVerification(bot))
