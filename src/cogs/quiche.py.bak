import discord
from discord.ext import commands
import asyncio
from pathlib import Path
import tempfile
import shutil
import subprocess
import re
import time

from config import QUICHE_DOCKER_IMAGE, QUICHE_TIMEOUT


class SessionManager:
    def __init__(self, docker_image: str):
        self.docker_image = docker_image
        self.container_id = None
        self.temp_dir = None

    async def start_session(self, temp_dir: Path):
        self.temp_dir = temp_dir
        proc = await asyncio.create_subprocess_exec(
            "docker", "run", "-d",
            "--network", "bridge",  # allow limited network
            "--memory", "512m",
            "--cpus", "1",
            "--pids-limit", "128",
            "--security-opt", "no-new-privileges",
            "--cap-drop", "ALL",
            "-v", f"{temp_dir}:/home/quiche",
            "--rm",
            self.docker_image,
            "sleep", "infinity",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"Docker run failed: {err.decode()}")
        self.container_id = out.decode().strip()
        return self.container_id

    async def stop_session(self):
        if not self.container_id:
            return
        proc = await asyncio.create_subprocess_exec(
            "docker", "kill", self.container_id,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        await proc.communicate()
        self.container_id = None


class NzQuiche(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.max_sessions = 3
        self.active_sem = asyncio.Semaphore(self.max_sessions)
        self.session_queue = asyncio.Queue()
        self.queued_users = set()
        self.sessions = {}
        self.requirements_path = Path(tempfile.gettempdir()) / "quiche_requirements"

        # cooldown & spam prevention
        self.user_request_counts = {}  # user_id -> (count, last_time)
        self.max_queue_requests = 5
        self.cooldown_seconds = 300  # 5 minutes

        self.queue_loop_task = asyncio.create_task(self.queue_loop())

    # ---- Queue Loop ----
    async def queue_loop(self):
        while True:
            user_id, ctx, main_file = await self.session_queue.get()
            try:
                await self._run_python_session(ctx, main_file)
            except Exception as e:
                await ctx.send(f"```Error in queued session: {e}```")
            finally:
                self.queued_users.discard(user_id)
                self.session_queue.task_done()

    # ---- Enqueue ----
    async def enqueue_python(self, ctx, main_file):
        user_id = ctx.author.id
        now = time.time()

        count, last_time = self.user_request_counts.get(user_id, (0, now))
        if now - last_time > self.cooldown_seconds:
            count = 0  # reset count after cooldown
        count += 1
        self.user_request_counts[user_id] = (count, now)

        if count > self.max_queue_requests:
            await ctx.send("```You have been temporarily rate-limited for spamming the queue. Wait 5 minutes.```")
            return

        if user_id in self.queued_users:
            await ctx.send("```You already have a queued session. Wait for it to start.```")
            return

        self.queued_users.add(user_id)
        await self.session_queue.put((user_id, ctx, main_file))
        await ctx.send(f"```Your Python session has been queued. Position: {len(self.session_queue._queue)}```")

    # ---- Python Session Runner ----
    async def _run_python_session(self, ctx, main_file=None):
        async with self.active_sem:
            temp_dir = Path(tempfile.mkdtemp(prefix=f"quiche_{ctx.author.id}_"))
            session = SessionManager(QUICHE_DOCKER_IMAGE)
            self.sessions[ctx.author.id] = session

            try:
                attachments = list(ctx.message.attachments)
                if ctx.message.reference:
                    try:
                        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                        attachments.extend(ref_msg.attachments)
                    except Exception:
                        pass

                filenames = [a.filename for a in attachments]
                if len(filenames) != len(set(filenames)):
                    await ctx.send("```Error: Duplicate filenames detected.```")
                    return

                for attach in attachments:
                    await attach.save(temp_dir / attach.filename)

                code_match = re.search(r"```(?:py|python)?\n(.*?)```", ctx.message.content, re.DOTALL)
                code_block_used = False
                if code_match:
                    code_content = code_match.group(1)
                    (temp_dir / "main.py").write_text(code_content)
                    code_block_used = True

                py_files = [f for f in temp_dir.iterdir() if f.suffix == ".py"]
                if code_block_used:
                    selected_file = "main.py"
                else:
                    if attachments and not py_files:
                        await ctx.send("```Error: No Python file found among attachments.```")
                        return
                    if len(py_files) == 1 and not main_file:
                        selected_file = py_files[0].name
                    elif len(py_files) > 1 and not main_file:
                        file_list = "\n".join(f.name for f in py_files)
                        await ctx.send(f"```Multiple Python files found:\n{file_list}\nSpecify which to run.```")
                        return
                    elif main_file:
                        if not (temp_dir / main_file).exists():
                            await ctx.send(f"```Main file `{main_file}` not found.```")
                            return
                        selected_file = main_file
                    else:
                        await ctx.send("```Error: No Python file supplied.```")
                        return

                container_id = await session.start_session(temp_dir)

                # persistent requirements
                req_file = self.requirements_path / str(ctx.author.id) / "requirements.txt"
                if req_file.exists():
                    proc = await asyncio.create_subprocess_exec(
                        "docker", "cp",
                        str(req_file),
                        f"{container_id}:/home/quiche/requirements.txt",
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    out, err = await proc.communicate()
                    if proc.returncode != 0:
                        await ctx.send(f"```Copy requirements failed:\n{err.decode()}```")
                        return

                    proc = await asyncio.create_subprocess_exec(
                        "docker", "exec", container_id,
                        "python", "-m", "pip", "install",
                        "-r", "/home/quiche/requirements.txt",
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    out, err = await proc.communicate()
                    if proc.returncode != 0:
                        await ctx.send(f"```Requirements install failed:\n{err.decode()}```")
                        return

                # ---- run code with chunked I/O ----
                proc = await asyncio.create_subprocess_exec(
                    "docker", "exec", "-i", container_id,
                    "python", selected_file,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

                async def stream(pipe, prefix=""):
                    buffer = b""
                    while True:
                        chunk = await pipe.read(256)
                        if not chunk:
                            break
                        buffer += chunk
                        # flush if newline, prompt, or large buffer
                        if b"\n" in buffer or buffer.endswith(b": ") or len(buffer) > 1800:
                            await ctx.send(f"```{prefix}{buffer.decode(errors='replace')}```")
                            buffer = b""
                    if buffer:
                        await ctx.send(f"```{prefix}{buffer.decode(errors='replace')}```")

                async def input_loop(proc, owner_id, channel):
                    def check(m):
                        return m.author.id == owner_id and m.channel == channel

                    while True:
                        try:
                            msg = await self.bot.wait_for("message", check=check, timeout=QUICHE_TIMEOUT)
                        except asyncio.TimeoutError:
                            break

                        if msg.content.strip() in ("~quiche exit", "~queue exit"):
                            proc.kill()
                            break
                        try:
                            proc.stdin.write((msg.content + "\n").encode())
                            await proc.stdin.drain()
                        except Exception:
                            break

                input_task = asyncio.create_task(input_loop(proc, ctx.author.id, ctx.channel))
                stdout_task = asyncio.create_task(stream(proc.stdout))
                stderr_task = asyncio.create_task(stream(proc.stderr, "[stderr] "))

                try:
                    await asyncio.wait_for(proc.wait(), timeout=QUICHE_TIMEOUT)
                except asyncio.TimeoutError:
                    proc.kill()
                    await ctx.send("```Execution timed out.```")

                await input_task
                await stdout_task
                await stderr_task

            finally:
                await session.stop_session()
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                self.sessions.pop(ctx.author.id, None)

    # ---- Command Group ----
    @commands.group(name="quiche", invoke_without_command=True)
    async def quiche(self, ctx):
        await ctx.send(
            "```Subcommands:\n"
            "set_role <@&role_id>\n"
            "requirements <requirements.txt>\n"
            "run <main_file.py>\n"
            "queue```"
        )

    @commands.has_permissions(manage_roles=True)
    @quiche.command(name="set_role")
    async def set_role(self, ctx, role: discord.Role = None):
        if role is None:
            await ctx.send("```Usage: ~quiche set_role <@&role_id>```")
            return
        await self.bot.db.set_quiche_role(ctx.guild.id, role.id)
        await ctx.send(f"```Quiche role successfully set to {role}```")

    @quiche.command(name="requirements")
    async def requirements(self, ctx):
        if not ctx.message.attachments:
            await ctx.send("```Attach a requirements.txt file```")
            return
    
        attach = ctx.message.attachments[0]
        if not attach.filename.lower().endswith(".txt"):
            await ctx.send("```File must be a .txt requirements file```")
            return
        user_path = self.requirements_path / str(ctx.author.id)
        user_path.mkdir(parents=True,exist_ok=True)
        # self.requirements_path.mkdir(parents=True, exist_ok=True)
        # await attach.save(eequirements_path / "requirements.txt")
        await attach.save(user_path / "requirements.txt")
        await ctx.send(f"```Saved requirements.txt persistently for {ctx.author.name}```")

    @quiche.command(name="run")
    async def run_python(self, ctx, *, main_file: str = None):
        await self.enqueue_python(ctx, main_file)

    @quiche.command(name="queue")
    async def show_queue(self, ctx):
        queued_users_info = []
        for uid, _, _ in list(self.session_queue._queue):
            user = ctx.guild.get_member(uid)
            if user:
                queued_users_info.append(user.name)
        active_users_info = [ctx.guild.get_member(uid).name for uid in self.sessions.keys() if ctx.guild.get_member(uid)]
        
        msg = "```Active sessions:\n"
        msg += "\n".join(active_users_info) if active_users_info else "None"
        msg += "\n\nQueued sessions:\n"
        msg += "\n".join(queued_users_info) if queued_users_info else "None"
        msg += "```"
        await ctx.send(msg)


async def setup(bot):
    await bot.add_cog(NzQuiche(bot))
