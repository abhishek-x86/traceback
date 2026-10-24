import sys
from traceback.agent import DebugAgent
from traceback.config import load_config
from traceback.git_engine import GitEngineError, GitManager
from traceback.parser import parse_trace
from traceback.runner import run_command


def _log(prefix: str, message: str) -> None:
    print(f"[{prefix}] {message}")

def run_pipeline(target_cmd: list[str]) -> int:
    cfg = load_config()
    
    try:
        git = GitManager()
    except GitEngineError as err:
        _log("ERROR", str(err))
        return 1

    _log("RUN", f"Executing target: {' '.join(target_cmd)}")
    initial_run = run_command(target_cmd, timeout=cfg.timeout_seconds)
    if initial_run.passed:
        _log("PASS", "Target command succeeded with exit code 0. Nothing to fix.")
        return 0

    _log("FAIL", f"Command failed with exit code {initial_run.exit_code}. Parsing trace...")
    err_ctx = parse_trace(initial_run.stderr, initial_run.stdout)
    if not err_ctx.target_file:
        _log("WARN", "Could not localize a source file in the project repository from the trace.")
        return initial_run.exit_code

    line_info = err_ctx.line_number or "?"
    _log("TARGET", f"Identified {err_ctx.target_file.name}:{line_info} ({err_ctx.error_type})")

    _log("GIT", "Anchoring base state checkpoint...")
    git.prepare_checkpoint()

    agent = DebugAgent(cfg, repo_root=git.root)
    _log("TRIAGE", "Querying triage model for failure invariant...")
    diagnosis = agent.triage_failure(err_ctx)
    _log("INVARIANT", diagnosis)

    _log("SYNTH", f"Generating {cfg.max_hypotheses} speculative patch hypotheses...")
    hypotheses = agent.generate_hypotheses(err_ctx, diagnosis, count=cfg.max_hypotheses)
    if not hypotheses:
        _log("ABORT", "Model failed to synthesize valid unified diffs.")
        git.rollback()
        return 1

    winning_branch: str | None = None

    for hyp in hypotheses:
        _log("BRANCH", f"Evaluating Hypothesis #{hyp.index}: '{hyp.title}'")
        attempt_branch = git.fork_root(hyp.index)

        applied = git.apply_patch(hyp.diff, f"fix(traceback): attempt #{hyp.index} - {hyp.title}")
        if not applied:
            _log("SKIP", f"Patch #{hyp.index} failed git apply pre-check.")
            git.prune(attempt_branch)
            continue

        _log("TEST", f"Verifying fix on branch {attempt_branch}...")
        test_run = run_command(target_cmd, timeout=cfg.timeout_seconds)

        if test_run.passed:
            _log("SUCCESS", f"Hypothesis #{hyp.index} resolved the failure!")
            winning_branch = attempt_branch
            break

        _log("REJECT", f"Hypothesis #{hyp.index} failed (exit code {test_run.exit_code}).")
        git.prune(attempt_branch)

    if winning_branch:
        git.resolve_winner(winning_branch)
        _log("DONE", f"Cleaned up failed branches. Active on verified fix: {winning_branch}")
        return 0

    _log("FAILED", "All speculative hypotheses failed to resolve the issue. Rolling back...")
    git.rollback()
    return 1

def main() -> None:
    args = sys.argv[1:]
    if not args:
        print("Usage: traceback <command> [args...]")
        print("Example: traceback pytest tests/")
        sys.exit(1)

    sys.exit(run_pipeline(args))

if __name__ == "__main__":
    main()