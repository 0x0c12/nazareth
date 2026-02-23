from discord.ext import commands
import discord
import random as rand
import time
import asyncio
import struct
import aiohttp
from pathlib import Path

DANSER_PATH = "/usr/bin/danser-cli"
USER_COOLDOWN = 300

class NzOsu(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.service = bot.osu_service
        self.valid_modes = {"osu", "taiko", "mania", "fruits"}

        self.render_queue = asyncio.Queue()
        self.users_rendering = set()
        self.cooldowns = {}
        self.worker_task = bot.loop.create_task(self._render_worker())

    async def _render_worker(self):
        await self.bot.wait_until_ready()

        while not self.bot.is_closed():
            ctx, attachment = await self.render_queue.get()

            try:
                await self._process_render(ctx, attachment)
            except Exception as e:
                await ctx.send(f"```Render failed: {e}```")

            self.users_rendering.discard(ctx.author.id)
            self.render_queue.task_done()

    async def _process_render(self, ctx, attachment):
        await ctx.send("```Rendering started...```")

        base_path = Path("/home/twilight/dev/nazareth/src/services/osu")
        replay_file_name = "replay.osr"
        replay_path = base_path / replay_file_name

        await attachment.save(replay_path)

        beatmap_path = await self.service.download_beatmap_from_replay(
            replay_file_name
        )

        process = await asyncio.create_subprocess_exec(
            DANSER_PATH,
            "-replay", str(base_path / replay_file_name),
            "-record",
            "-out", replay_file_name,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        await process.communicate()

        '''
        if not output_path.exists():
            raise Exception("Video not generated.")
        '''

        await ctx.send("```Uploading render...```")
        replay_file_path = Path('/home/twilight/.local/share/danser/videos/replay.osr.mp4')

        async def upload_to_catbox(file_path: str) -> str:
            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as f:
                    data = aiohttp.FormData()
                    data.add_field("reqtype", "fileupload")
                    data.add_field("userhash", "")
                    data.add_field("fileToUpload", f, filename=file_path.name)
                    async with session.post("https://catbox.moe/user/api.php", data=data) as resp:
                        resp.raise_for_status()
                        return await resp.text()
        replay_url = await upload_to_catbox(replay_file_path)
        await ctx.send(replay_url)
        replay_file_path.unlink()

    async def _get_queue_position(self, user_id):
        for idx, (ctx, _) in enumerate(self.render_queue._queue):
            if ctx.author.id == user_id:
                return idx + 1
        return 1

    @commands.group(name="osu", invoke_without_command=True)
    async def osu(self, ctx):
        await ctx.send("```Available subcommands\nlink\nunlink\nprofile\ntop\nrecent_score\nskin_random\nrender```")

    @commands.cooldown(1, USER_COOLDOWN, commands.BucketType.user)
    @osu.command(name="render")
    async def render(self, ctx):
        attachment = (
            ctx.message.attachments
            or (
                ctx.message.reference
                and (await ctx.message.channel.fetch_message(ctx.message.reference.message_id)).attachments
            )
            or [None]
        )[0]
        
        if not attachment:
            return await ctx.send("```Please attach a .osr replay file.```")

        if not attachment.filename.endswith(".osr"):
            return await ctx.send("```Invalid file. Please upload a .osr replay.```")

        user_id = ctx.author.id
        now = time.time()

        if user_id in self.cooldowns:
            remaining = USER_COOLDOWN - (now - self.cooldowns[user_id])
            if remaining > 0:
                return await ctx.send(
                    f"```You are on cooldown.\nTry again in {int(remaining)} seconds.```"
                )
        if user_id in self.users_rendering:
            position = await self._get_queue_position(user_id)
            return await ctx.send(
                f"```You already have a render queued.\nPosition in queue: {position}```"
            )

        self.users_rendering.add(user_id)
        self.cooldowns[user_id] = now
        await self.render_queue.put((ctx, attachment))

        position = self.render_queue.qsize()

        await ctx.send(
            f"```Replay added to queue.\nPosition: {position}```"
        )
            
    @osu.command(name="link")
    async def link(self, ctx, username):
        try:
            await self.service.link_user(ctx.author.id, username) 
            await ctx.send(f"```Linked to osu user: {username}```")
        except Exception as e:
            await ctx.send(f"```Link failed: {e}```")

    @osu.command(name="profile")
    async def profile(self, ctx, memb: discord.Member | None = None, mod: str = 'osu'):
        member = memb.id if memb is not None else ctx.author.id
        mode = mod

        mode = mode.lower()
        if mode not in self.valid_modes:
            mode = 'osu'

        try:
            user = await self.service.get_profile(member, mode)
            stats = user.statistics

            prof_embed = discord.Embed(
                title=f"{user.username} ({mode})",
                url=f"https://osu.ppy.sh/{user.id}",
                color=discord.Color.pink()
            )

            prof_embed.set_thumbnail(url=user.avatar_url)
            
            prof_embed.add_field(
                name="Rank",
                value=f"#{stats.global_rank:,} ({user.country_code} #{stats.country_rank:})",
                inline=False
            )

            prof_embed.add_field(
                name="Statistics",
                value=(
                    f"PP: **{stats.pp:,}**\n"
                    f"Accuracy: **{stats.accuracy*100:.2f}%**\n"
                    f"Level: **{stats.level.current}**\n"
                    f"Playtime: **{stats.play_time//3600} hrs**"
                ),
                inline=True
            )

            prof_embed.set_footer(text=f"joined osu! at {str(user.join_date)[:-6]}")

            await ctx.send(embed=prof_embed)
        except Exception as e:
            await ctx.send(f"Error: {e}")

    @osu.command(name="top")
    async def top(self, ctx, memb:discord.Member | None = None, mod: str = 'osu'):
        member = memb.id if memb is not None else ctx.author.id
        mode = mod

        mode = mode.lower()
        if mode not in self.valid_modes:
            mode = 'osu'

        try:
            user = await self.service.get_profile(member, mode)
            scores = await self.service.get_top(member, mode)

            beatmap_base = "https://osu.ppy.sh/beatmaps"
            
            tembed = discord.Embed(
                title=f"{user.username} - Top 10 plays",
                url=f"https://osu.ppy.sh/users/{user.id}",
                color=discord.Color.pink()
            )
            
            tembed.set_image(url=scores[0].beatmapset.covers.cover)

            tembed.set_thumbnail(url=user.avatar_url)

            lines = []

            for i, score in enumerate(scores, start=1):
                beatmap_url = f"{beatmap_base}/{score.beatmap.id}"
                mods = "".join(m.mod.value for m in score.mods) or "NM"
                acc = f"{score.accuracy * 100:.2f}%"

                lines.append(
                    f"**{i}.** "
                    f"[{score.beatmapset.title} [{score.beatmap.version} - {score.beatmap.difficulty_rating:.1f}*]]({beatmap_url})\n"
                    f"**{score.pp:.0f}pp** - {acc} - {score.max_combo}x +{mods}"
                )

            tembed.description = "\n\n".join(lines)
            tembed.set_footer(text=f"{user.playmode.value} | Ordered by performance")

            await ctx.send(embed=tembed)
        except Exception as e:
            await ctx.send(f"```Error: {e}```")

    @osu.command(name="recent_score", aliases=['rs'])
    async def recent_score(self, ctx, memb: discord.Member | None = None, mod: str = 'osu'):
        member = memb.id if memb is not None else ctx.author.id
        mode = mod

        mode = mode.lower()
        if mode not in self.valid_modes:
            mode = 'osu'

        try:
            user = await self.service.get_profile(member, mode)
            score = await self.service.get_recent(member, mode)

            r_embed = discord.Embed(
                description=f"### [{score.beatmapset.title} [{score.beatmap.version}]]({score.beatmap.url})",
                color=discord.Color.pink()
            )

            r_embed.set_author(
                name=f"{user.username} - recent play",
                icon_url=user.avatar_url
            )

            # r_embed.set_thumbnail(url=user.avatar_url)
            r_embed.set_image(url=score.beatmapset.covers.cover)

            pp_str = f"{score.pp:.2f}" if score.pp is not None else "0 PP :P"
            r_embed.add_field(name="PP", value=pp_str)
            r_embed.add_field(name="Accuracy", value=f"{score.accuracy * 100:.2f}% ({"F" if not score.passed else score.rank.value})")
            r_embed.add_field(name="Combo", value=f"{score.max_combo}x ({score.statistics.miss} miss)")
            r_embed.set_footer(text=f"SR: {score.beatmap.difficulty_rating:.2f}* +{"".join(m.mod.value for m in score.mods) or "NM"} | mapped by {score.beatmapset.creator}")

            await ctx.send(embed=r_embed)
        except Exception as e:
            await ctx.send(f"```Error: {e}```")

    @osu.command(name="skin_random", aliases=['skr'])
    async def skin_random(self, ctx):
        try:
            base_url = "https://skins.osuck.net/skins/"
            skin_id = str(rand.randint(1, 4000))
            await ctx.send(base_url + skin_id)
        except Exception as e:
            await ctx.send(f"```I honestly have NO IDEA how this command failed\n{e}```")

    @osu.command(name="unlink")
    async def unlink(self, ctx):
        try:
            await self.service.unlink_user(ctx.author.id)
            await ctx.send("```Unlinked successfully```")
        except Exception as e:
            await ctx.send(f"Unlink failed: {e}")

async def setup(bot):
    await bot.add_cog(NzOsu(bot))
