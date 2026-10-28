
import sys

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
MAGENTA = "\033[35m"
BLUE = "\033[34m"

PREFIX = f"{BOLD}{CYAN}[traceback]{RESET}"


def banner():
    """Print the traceback header banner."""
    print(f"\n{PREFIX} {BOLD}Autonomous Terminal CLI Debugger{RESET}")
    print(f"{PREFIX} {DIM}Powered by Nebius Token Factory & NVIDIA Nemotron{RESET}\n")


def status_fail(cmd_str: str, exit_code: int):
    """Notify that the target command terminated with non-zero exit code."""
    print(f"{PREFIX} {YELLOW}⚡ Command exited with error:{RESET} {BOLD}{cmd_str}{RESET} {RED}(code {exit_code}){RESET}")


def status_parse(file_path: str, line_no: int, exc_type: str, exc_msg: str):
    """Notify that stack trace parser located local user-space error frame."""
    print(f"{PREFIX} {BLUE}🔍 Localized Failure Frame:{RESET} {BOLD}{file_path}:{line_no}{RESET}")
    print(f"{PREFIX}    {RED}▸ {exc_type}:{RESET} {exc_msg}")


def status_tavily_start():
    """Notify that Tavily web research is executing."""
    print(f"{PREFIX} {MAGENTA}🌐 Tavily Research:{RESET} Querying error fix context & documentation...")


def status_tavily_done(found: bool):
    """Notify Tavily research outcome."""
    if found:
        print(f"{PREFIX}    {GREEN}✔ External solution context retrieved{RESET}")
    else:
        print(f"{PREFIX}    {DIM}Skipped (no TAVILY_API_KEY or query timeout){RESET}")


def status_fast_tier(model: str):
    """Notify fast tier Nemotron triage start."""
    print(f"{PREFIX} {CYAN}⚡ Fast Tier Triage:{RESET} {DIM}{model}{RESET}")


def status_triage_result(invariant: str):
    """Print diagnosed failure invariant."""
    print(f"{PREFIX}    {YELLOW}Root Cause Invariant:{RESET} {invariant}")


def status_heavy_tier(model: str, max_hyp: int):
    """Notify heavy tier Nemotron patch generation."""
    print(f"{PREFIX} {MAGENTA}🧠 Heavy Tier Synthesis:{RESET} {DIM}{model}{RESET}")
    print(f"{PREFIX}    Generating up to {BOLD}{max_hyp}{RESET} competing speculative patch hypotheses...")


def status_branch_test(idx: int, total: int, branch_name: str):
    """Print speculative branch evaluation start."""
    sys.stdout.write(f"{PREFIX} {CYAN}🌿 Testing candidate [{idx}/{total}] on '{branch_name}'... {RESET}")
    sys.stdout.flush()


def status_branch_result(passed: bool, exit_code: int = 0):
    """Print speculative branch evaluation result."""
    if passed:
        print(f"{GREEN}{BOLD}PASSED (code 0) ✔{RESET}")
    else:
        print(f"{RED}FAILED (code {exit_code}) ✖{RESET}")


def status_winner(branch_name: str, patch_diff: str = ""):
    """Print winning branch notification and colored unified diff."""
    print(f"\n{PREFIX} {GREEN}{BOLD}🏆 Winning patch verified and merged!{RESET} {DIM}(from {branch_name}){RESET}")
    if patch_diff:
        print(f"\n{DIM}{'─' * 60}{RESET}")
        for line in patch_diff.splitlines():
            if line.startswith("+++") or line.startswith("---"):
                print(f"{BOLD}{line}{RESET}")
            elif line.startswith("+"):
                print(f"{GREEN}{line}{RESET}")
            elif line.startswith("-"):
                print(f"{RED}{line}{RESET}")
            elif line.startswith("@@"):
                print(f"{CYAN}{line}{RESET}")
            else:
                print(f"{DIM}{line}{RESET}")
        print(f"{DIM}{'─' * 60}{RESET}\n")


def status_rollback():
    """Print rollback notification when all candidates fail."""
    print(f"\n{PREFIX} {RED}{BOLD}✖ All speculative patch hypotheses failed.{RESET}")
    print(f"{PREFIX} {YELLOW}Repository restored to initial clean checkpoint.{RESET}\n")
