import discord
from discord.ext import commands
import asyncio
from pathlib import Path
import tempfile
import shutil
import subprocess
import time
import re

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
            "--network", "none",
            "--memory", "512m",
            "--cpus", "1",
            "--pids-limit", "128",
            "--security-opt", "no-new-privileges",
            "--cap-drop", "ALL",
            "-v", f"{temp_dir}:/home/quiche",
            "--rm",
            self.docker_image, "sleep", "infinity",
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
        self.running_session = asyncio.Lock()
        self.venv_path = Path(tempfile.gettempdir()) / "quiche_venv"

    async def cog_check(self, ctx):
        if not ctx.guild:
            await ctx.send("```Commands can only be executed in servers.```")
            return False

        if ctx.command.name == "set_role":
            return True

        try:
            quiche_role_id = await self.bot.db.get_quiche_role(ctx.guild.id)
            if not quiche_role_id:
                await ctx.send("```No role set for quiche.```")
                return False

            role = ctx.guild.get_role(quiche_role_id)
            if role not in ctx.author.roles:
                await ctx.send("```You don't have permission to use this command.```")
                return False

        except Exception as e:
            await ctx.send(f"```Error checking permissions: {e}```")
            return False

        return True

    @commands.group(name="quiche", invoke_without_command=True)
    async def quiche(self, ctx):
        await ctx.send(
            "```Subcommands:\n"
            "set_role <@&role_id>\n"
            "requirements <requirements.txt>\n"
            "python <main_file.py>```"
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

        self.venv_path.mkdir(parents=True, exist_ok=True)
        await attach.save(self.venv_path / "requirements.txt")
        await ctx.send(f"```Saved requirements.txt persistently```")

    @quiche.command(name="python")
    async def run_python(self, ctx, *, main_file: str = None):
        if self.running_session.locked():
            await ctx.send("```Another Python session is running. Wait.```")
            return

        async with self.running_session:
            temp_dir = Path(tempfile.mkdtemp(prefix=f"quiche_{ctx.author.id}_"))
            session = SessionManager(QUICHE_DOCKER_IMAGE)

            try:
                # -----------------------------------
                # Collect attachments (current first)
                # -----------------------------------
                attachments = list(ctx.message.attachments)

                if ctx.message.reference:
                    try:
                        ref_msg = await ctx.channel.fetch_message(ctx.message.reference.message_id)
                        attachments.extend(ref_msg.attachments)
                    except Exception:
                        pass

                # Duplicate filename check
                filenames = [a.filename for a in attachments]
                if len(filenames) != len(set(filenames)):
                    await ctx.send("```Error: Two files with the same name cannot be parsed.```")
                    return

                # Save files
                for attach in attachments:
                    await attach.save(temp_dir / attach.filename)

                py_files = [f for f in temp_dir.iterdir() if f.suffix == ".py"]

                # -----------------------------------
                # Code block support
                # -----------------------------------
                code_match = re.search(
                    r"```(?:py|python)?\n(.*?)```",
                    ctx.message.content,
                    re.DOTALL
                )

                code_block_used = False
                if code_match:
                    code_content = code_match.group(1)
                    main_path = temp_dir / "main.py"
                    main_path.write_text(code_content)
                    code_block_used = True

                # -----------------------------------
                # Resolution rules
                # -----------------------------------
                if code_block_used:
                    selected_file = "main.py"

                else:
                    if attachments and not py_files:
                        if not code_match:
                            await ctx.send("```Error: Files supplied but no Python file found.```")
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

                # -----------------------------------
                # Start container
                # -----------------------------------
                container_id = await session.start_session(temp_dir)

                # -----------------------------------
                # Setup venv
                # -----------------------------------
                
                # -----------------------------------
                # Create virtual environment
                # -----------------------------------
                proc = await asyncio.create_subprocess_exec(
                    "docker", "exec", container_id,
                    "python", "-m", "venv", "/home/quiche/venv",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                out, err = await proc.communicate()
                if proc.returncode != 0:
                    await ctx.send(f"```Venv creation failed:\n{err.decode()}```")
                    return
                
                # -----------------------------------
                # Bootstrap pip (Python 3.12 safe)
                # -----------------------------------
                proc = await asyncio.create_subprocess_exec(
                    "docker", "exec", container_id,
                    "/home/quiche/venv/bin/python",
                    "-m", "ensurepip", "--upgrade",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                out, err = await proc.communicate()
                if proc.returncode != 0:
                    await ctx.send(f"```ensurepip failed:\n{err.decode()}```")
                    return
                
                # -----------------------------------
                # Upgrade pip (optional but safer)
                # -----------------------------------
                proc = await asyncio.create_subprocess_exec(
                    "docker", "exec", container_id,
                    "/home/quiche/venv/bin/python",
                    "-m", "pip", "install", "--upgrade", "pip",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                await proc.communicate()
                
                # -----------------------------------
                # Install requirements (if exists)
                # -----------------------------------
                req_file = self.venv_path / "requirements.txt"
                if req_file.exists():
                
                    # Copy requirements into container
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
                
                    # Install requirements using python -m pip
                    proc = await asyncio.create_subprocess_exec(
                        "docker", "exec", container_id,
                        "/home/quiche/venv/bin/python",
                        "-m", "pip",
                        "install",
                        "-r", "/home/quiche/requirements.txt",
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE
                    )
                    out, err = await proc.communicate()
                    if proc.returncode != 0:
                        await ctx.send(f"```Requirements install failed:\n{err.decode()}```")
                        return                

                def check(m):
                    return m.author == ctx.author and m.channel == ctx.channel

                async def input_loop():
                    while True:
                        try:
                            msg = await self.bot.wait_for("message", check=check, timeout=QUICHE_TIMEOUT)
                        except asyncio.TimeoutError:
                            break

                        if msg.content.strip() == "~quiche exit":
                            proc.kill()
                            break

                        try:
                            proc.stdin.write((msg.content + "\n").encode())
                            await proc.stdin.drain()
                        except Exception:
                            break

                async def stream(pipe, prefix=""):
                    buffer = ""
                    while True:
                        line = await pipe.readline()
                        if not line:
                            break
                        buffer += prefix + line.decode()
                        if len(buffer) > 1800:
                            await ctx.send(f"```{buffer}```")
                            buffer = ""
                    if buffer:
                        await ctx.send(f"```{buffer}```")

                input_task = asyncio.create_task(input_loop())
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


async def setup(bot):
    await bot.add_cog(NzQuiche(bot))
