import os
import shlex
import subprocess
from dataclasses import dataclass
from typing import List, Optional

from . import config


@dataclass
class CommandResult:
    stdout: str
    stderr: str
    returncode: int

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _read_sudo_password() -> Optional[str]:
    if config.SUDO_PASS_FILE.exists():
        data = config.SUDO_PASS_FILE.read_text(encoding="utf-8").strip()
        return data if data else None
    return None


def run_command(
    cmd: List[str],
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    input_text: Optional[str] = None,
    timeout: Optional[int] = None,
) -> CommandResult:
    merged_env = os.environ.copy()
    if env:
        merged_env.update(env)
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        env=merged_env,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return CommandResult(
        stdout=completed.stdout,
        stderr=completed.stderr,
        returncode=completed.returncode,
    )


def run_sudo(
    cmd: List[str],
    cwd: Optional[str] = None,
    env: Optional[dict] = None,
    timeout: Optional[int] = None,
) -> CommandResult:
    password = _read_sudo_password()
    if password:
        sudo_cmd = ["sudo", "-S"] + cmd
        return run_command(sudo_cmd, cwd=cwd, env=env, input_text=password + "\n", timeout=timeout)
    sudo_cmd = ["sudo"] + cmd
    return run_command(sudo_cmd, cwd=cwd, env=env, timeout=timeout)


def docker_exec(
    command: str,
    user: Optional[str] = None,
    project: Optional[str] = None,
    domain: Optional[str] = None,
    use_base_env: bool = True,
    timeout: Optional[int] = None,
) -> CommandResult:
    parts = []
    if user or project or domain:
        args = []
        if user:
            args.append(f"--user {shlex.quote(user)}")
        if project:
            args.append(f"--project {shlex.quote(project)}")
        if domain:
            args.append(f"--domain {shlex.quote(domain)}")
        parts.append(f"source {config.CURRENT_USER_SCRIPT} {' '.join(args)}")
    if use_base_env:
        parts.append("source /opt/miniconda/etc/profile.d/conda.sh")
        parts.append("conda activate base")
        parts.append("export PYTHONPATH=/root:${PYTHONPATH:-}")
    parts.append(command)
    shell_cmd = " && ".join(parts)
    return run_sudo(
        [
            "docker",
            "exec",
            "-i",
            config.CONTAINER_NAME,
            "bash",
            "-lc",
            shell_cmd,
        ],
        env=config.DOCKER_ENV,
        timeout=timeout,
    )


def docker_exec_simple(command: str, timeout: Optional[int] = None) -> CommandResult:
    return run_sudo(
        ["docker", "exec", "-i", config.CONTAINER_NAME, "bash", "-lc", command],
        env=config.DOCKER_ENV,
        timeout=timeout,
    )


def docker_cp_to_container(src: str, dest: str) -> CommandResult:
    return run_sudo(
        ["docker", "cp", src, f"{config.CONTAINER_NAME}:{dest}"],
        env=config.DOCKER_ENV,
    )


def docker_cp_from_container(src: str, dest: str) -> CommandResult:
    return run_sudo(
        ["docker", "cp", f"{config.CONTAINER_NAME}:{src}", dest],
        env=config.DOCKER_ENV,
    )


def docker_container_status() -> CommandResult:
    return run_sudo(
        ["docker", "inspect", "-f", "{{.State.Status}}", config.CONTAINER_NAME],
        env=config.DOCKER_ENV,
    )
