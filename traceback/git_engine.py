import subprocess
import uuid
from pathlib import Path


class GitEngineError(Exception):
    pass

class GitManager:
    def __init__(self, cwd: Path | str | None = None) -> None:
        self.root = Path(cwd).resolve() if cwd else Path.cwd()
        self._ensure_repo()
        self.initial_branch = self.current_branch()
        self.checkpoint_sha: str | None = None
        self.created_checkpoint = False
        self.active_branches: list[str] = []

    def run(self, args: list[str], check: bool = True, text_in: str | None = None) -> tuple[int, str, str]:
        proc = subprocess.run(
            ["git"] + args,
            cwd=self.root,
            input=text_in,
            capture_output=True,
            text=True,
            check=False,
        )
        if check and proc.returncode != 0:
            raise GitEngineError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    
    def _ensure_repo(self) -> None:
        code, out, _ = self.run(["rev-parse", "--is-inside-work-tree"], check=False)
        if code != 0 or out != "true":
            raise GitEngineError(f"'{self.root}' is not inside a git repository.")

    def current_branch(self) -> str:
        code, out, _ = self.run(["rev-parse", "--abbrev-ref", "HEAD"], check=False)
        if code == 0 and out != "HEAD":
            return out
        _, sha, _ = self.run(["rev-parse", "HEAD"])
        return sha

    def is_dirty(self) -> bool:
        _, out, _ = self.run(["status", "--porcelain"])
        return bool(out)

    def prepare_checkpoint(self, msg: str = "chore(traceback): snapshot pre-fix") -> str:
        if self.is_dirty():
            self.run(["add", "-A"])
            self.run(["commit", "-m", msg, "--no-verify"])
            self.created_checkpoint = True
        _, sha, _ = self.run(["rev-parse", "HEAD"])
        self.checkpoint_sha = sha
        return sha

    def fork_root(self, attempt: int) -> str:
        base = self.checkpoint_sha or self.prepare_checkpoint()
        branch = f"tb/attempt-{attempt}-{uuid.uuid4().hex[:6]}"
        self.run(["checkout", "-b", branch, base])
        self.active_branches.append(branch)
        return branch

    def fork_child(self, parent_branch: str, step: int) -> str:
        child = f"{parent_branch}.{step}"
        self.run(["checkout", "-b", child, parent_branch])
        self.active_branches.append(child)
        return child

    def apply_patch(self, diff: str, commit_msg: str) -> bool:
        if not diff.strip():
            return False
        check_code, _, _ = self.run(["apply", "--check", "--whitespace=fix", "-"], check=False, text_in=diff)
        if check_code != 0:
            return False
        self.run(["apply", "--whitespace=fix", "-"], text_in=diff)
        self.run(["add", "-A"])
        self.run(["commit", "-m", commit_msg, "--no-verify"])
        return True

    def prune(self, branch: str) -> None:
        if branch in self.active_branches:
            self.active_branches.remove(branch)
        if self.current_branch() == branch:
            fallback = self.initial_branch or self.checkpoint_sha or "main"
            self.run(["checkout", fallback], check=False)
        self.run(["branch", "-D", branch], check=False)

    def resolve_winner(self, winning_branch: str) -> str:
        if self.current_branch() != winning_branch:
            self.run(["checkout", winning_branch])
        for b in list(self.active_branches):
            if b != winning_branch:
                self.prune(b)
        self.active_branches = [winning_branch]
        return winning_branch

    def rollback(self) -> None:
        self.run(["checkout", self.initial_branch], check=False)
        for b in list(self.active_branches):
            self.prune(b)
        self.active_branches.clear()