import discord
from discord.ext import commands
import asyncio
from pathlib import Path
import tempfile
import shutil
import os
import subprocess
import time
from config import QUICHE_DOCKER_IMAGE, QUICHE_TIMEOUT

class SessionManager:
    def __init__(self, docker_image: str, session_timeout: int = 600):
        self.docker_image = docker_image
        self.session_timeout = session_timeout
        self.container_id = None
        self.last_active = None
        self.temp_dir = Path(tempfile.mkdtemp(prefix="quiche_session"))
        self.requirements_installed = False

    async def start_session(self):
        # If session exists and is still alive
        if self.container_id and self.last_active and (time.time() - self.last_active < self.session_timeout):
            return self.container_id

        # Clean up old container if exists
        if self.container_id:
            await self.stop_session()

        # Prepare temp directory
        self.temp_dir.mkdir(exist_ok=True, parents=True)

        # Launch container
        proc = await asyncio.create_subprocess_exec(
            "docker", "run", "-d",
            "--network", "none",
            "--memory", "512m",
            "--cpus", "1",
            "--pids-limit", "128",
            "--read-only",
            "--security-opt", "no-new-privileges",
            "--cap-drop", "ALL",
            "-v", f"{self.temp_dir}:/home/quiche",
            "--rm",
            self.docker_image, "sleep", "infinity",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, err = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError(f"Docker run failed: {err.decode()}")

        self.container_id = out.decode().strip()
        self.last_active = time.time()
        return self.container_id

    async def stop_session(self):
        if not self.container_id:
            return
        proc = await asyncio.create_subprocess_exec(
            "docker", "kill", self.container_id,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        await proc.communicate()
        self.container_id = None
        self.last_active = None
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    async def update_activity(self):
        self.last_active = time.time()

class NzQuiche(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.running_session = asyncio.Lock()
        self.venv_path = Path(tempfile.gettempdir()) / "quiche_venv"
        self.session_manager = SessionManager(QUICHE_DOCKER_IMAGE, QUICHE_TIMEOUT)

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
        await ctx.send(f"```Saved requirements.txt to persistent venv at {self.venv_path}```")

    @quiche.command(name="python")
    async def run_python(self, ctx, *, main_file: str):
        if self.running_session.locked():
            await ctx.send("```Another Python session is running. Wait.```")
            return

        async with self.running_session:
            temp_dir = Path(tempfile.gettempdir()) / f"quiche_tmp_{ctx.author.id}"
            temp_dir.mkdir(exist_ok=True)
            try:
                # Save attachments
                attach_path_list = []
                for attach in ctx.message.attachments:
                    await attach.save(temp_dir / attach.filename)
                    attach_path_list.append(temp_dir / attach.filename)
                main_file_path = temp_dir / main_file
                if not main_file_path.exists():
                    await ctx.send(f"```Main file `{main_file}` not found```")
                    return

                # Start or reuse Docker session
                container_id = await self.session_manager.start_session()
                await self.session_manager.update_activity()

                # Copy persistent requirements into container
                req_file = self.venv_path / "requirements.txt"
                if req_file.exists() and not self.session_manager.requirements_installed:
                    await ctx.send("```Installing requirements in container...```")
                    proc = await asyncio.create_subprocess_exec(
                        "docker", "cp", str(req_file), f"{container_id}:/home/quiche/requirements.txt",
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    await proc.communicate()
                    proc = await asyncio.create_subprocess_exec(
                        "docker", "exec", container_id,
                        "pip", "install", "-r", "/home/quiche/requirements.txt",
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE
                    )
                    await proc.communicate()
                    self.session_manager.requirements_installed = True

                await ctx.send(f"```Running {main_file} in Docker container```")

                proc = await asyncio.create_subprocess_exec(
                    "docker", "cp", str(main_file_path), f"{container_id}:/home/quiche/{main_file}",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                await proc.communicate()
                for atmnt in attach_path_list:
                    filename = Path(atmnt).name.strip()
                    proc = await asyncio.create_subprocess_exec(
                            "docker", "cp", str(atmnt), f"{container_id}:/home/quiche/{filename}"
                    )

                proc = await asyncio.create_subprocess_exec(
                    "docker", "exec", container_id, "python", f"/home/quiche/{main_file}",
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                out, err = await proc.communicate()
                output = f"STDOUT:\n{out.decode()}\nSTDERR:\n{err.decode()}"
                if len(output) > 1900:
                    output = output[:1900] + "\n...[truncated]"
                await ctx.send(f"```{output}```")

            finally:
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
async def setup(bot):
    await bot.add_cog(NzQuiche(bot))
