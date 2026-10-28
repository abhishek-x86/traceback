import sys
from traceback import hud
from traceback.agent import DebugAgent
from traceback.config import load_config
from traceback.git_engine import GitEngineError, GitManager
from traceback.parser import parse_trace
from traceback.runner import run_command


def run_pipeline(target_cmd: list[str]) -> int:
    cfg = load_config()
    
    # 1. Print visual banner at start
    hud.banner()

    try:
        git = GitManager()
    except GitEngineError as err:
        print(f"[ERROR] {err}")
        return 1

    initial_run = run_command(target_cmd, timeout=cfg.timeout_seconds)
    if initial_run.passed:
        print("[traceback] ✔ Target command succeeded with exit code 0. Nothing to fix.")
        return 0

    # 2. Command failure badge
    hud.status_fail(" ".join(target_cmd), initial_run.exit_code)

    # 3. Stack trace parsing
    err_ctx = parse_trace(initial_run.stderr, initial_run.stdout)
    if not err_ctx.target_file:
        print("[traceback] ⚠ Could not localize a source file in the project repository from the trace.")
        return initial_run.exit_code

    line_info = err_ctx.line_number or 0
    hud.status_parse(str(err_ctx.target_file), line_info, err_ctx.error_type, err_ctx.error_message)

    # 4. Checkpoint git state
    git.prepare_checkpoint()

    # 5. Fast Tier Triage (Nemotron-3_5-Lightning)
    agent = DebugAgent(cfg, repo_root=git.root)
    hud.status_fast_tier(cfg.fast_tier)
    diagnosis = agent.triage_failure(err_ctx)
    hud.status_triage_result(diagnosis)

    # 6. Heavy Tier Synthesis (Nemotron-3-Ultra-550b)
    hud.status_heavy_tier(cfg.heavy_tier, cfg.max_hypotheses)
    hypotheses = agent.generate_hypotheses(err_ctx, diagnosis, count=cfg.max_hypotheses)
    if not hypotheses:
        print("[traceback] ✖ Model failed to synthesize valid unified diffs.")
        git.rollback()
        return 1

    winning_branch: str | None = None
    winning_diff: str = ""

    # 7. Speculative Branch Testing Loop
    for idx, hyp in enumerate(hypotheses, start=1):
        attempt_branch = git.fork_root(hyp.index)
        hud.status_branch_test(idx, len(hypotheses), attempt_branch)

        applied = git.apply_patch(hyp.diff, f"fix(traceback): attempt #{hyp.index} - {hyp.title}")
        if not applied:
            hud.status_branch_result(False, exit_code=1)
            git.prune(attempt_branch)
            continue

        test_run = run_command(target_cmd, timeout=cfg.timeout_seconds)

        if test_run.passed:
            hud.status_branch_result(True)
            winning_branch = attempt_branch
            winning_diff = hyp.diff
            break

        hud.status_branch_result(False, exit_code=test_run.exit_code)
        git.prune(attempt_branch)

    # 8. Winner Resolution or Rollback
    if winning_branch:
        git.resolve_winner(winning_branch)
        hud.status_winner(winning_branch, winning_diff)
        return 0

    hud.status_rollback()
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
