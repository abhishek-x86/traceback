import os
import subprocess
from dataclasses import dataclass


@dataclass
class CommandResult:
    command: list[str]
    exit_code: int
    stdout: str
    stderr: str

    @property
    def passed(self) -> bool:
        return self.exit_code == 0

def _to_str(data: bytes | str | None) -> str:
    if data is None:
        return ""
    if isinstance(data, bytes):
        return data.decode("utf-8", errors="replace")
    return data

def run_command(cmd: list[str], timeout: int = 30) -> CommandResult:
    if not cmd:
        return CommandResult([], 1, "", "No command provided")

    env = os.environ.copy()
    for var in ("PYTHONPATH", "PYTHONHOME", "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH"):
        env.pop(var, None)

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            env=env,
            timeout=timeout,
            check=False,
        )
        return CommandResult(cmd, proc.returncode, proc.stdout, proc.stderr)
    except subprocess.TimeoutExpired as exc:
        out = _to_str(exc.stdout)
        err = _to_str(exc.stderr) or f"Timed out after {timeout}s"
        return CommandResult(cmd, 124, out, err)
    except OSError as exc:
        return CommandResult(cmd, 1, "", str(exc))