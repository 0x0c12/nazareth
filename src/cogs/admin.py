from discord.ext import commands
import os
import importlib
import config

class NzCogManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="reload")
    @commands.is_owner()
    async def reload_cog(self, ctx, cog: str = None):
        if cog is None:
            await ctx.send("Usage: `~reload <cog_name>` or `~reload all`")
            return
        
        folders = [config.cog_folder, config.event_folder]
        if cog.lower() == "all":
            importlib.reload(config)

            current_extensions = set(self.bot.extensions.keys())
            cog_files = set()

            for folder in folders:
                for f in os.listdir(folder):
                    if f.endswith(".py") and not f.startswith("_"):
                        cog_files.add(f"{folder}.{f[:-3]}")
                            
            success = []
            failed = []

            for ext in current_extensions & cog_files:
                try:
                    await self.bot.reload_extension(ext)
                    success.append(f"Reloaded {ext}")
                except Exception as e:
                    failed.append(f"{ext}: {e}")
                    
            for ext in current_extensions - cog_files:
                try:
                    await self.bot.unload_extension(ext)
                    success.append(f"Unloaded {ext}")
                except Exception as e:
                    failed.append(f"{ext}: {e}")

            for ext in cog_files - current_extensions:
                try:
                    await self.bot.load_extension(ext)
                    success.append(f"Loaded {ext}")
                except Exception as e:
                    failed.append(f"{ext}: {e}")

            msg = "\n".join(success)
            if failed:
                msg += "\nFailed:\n" + "\n".join(failed)

            await ctx.send(f"```{msg}```")
            return
        
        tgt_ext = None

        for folder in folders:
            if os.path.exists(os.path.join(folder, f"{cog}.py")):
                tgt_ext = f"{folder}.{cog}"
                break
            
        if not tgt_ext:
            await ctx.send(f"`{cog}` is not a valid cog.")
            return
            
        try:
            await self.bot.reload_extension(tgt_ext)
            await ctx.send(f"Reloaded cog: `{cog}`")
        except Exception as e:
            await ctx.send(f"Failed to reload cog `{cog}`:\n```{e}```")

async def setup(bot):
    await bot.add_cog(NzCogManager(bot))
