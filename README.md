traceback

Autonomous terminal CLI debugging wrapper powered by Nebius Token Factory & NVIDIA Nemotron

Built for the Nebius x NVIDIA Global AI Hackathon (Coding and Agentic Engineering Track).

traceback wraps any terminal command (such as pytest or python script.py), intercepts runtime crashes and non-zero exit codes, diagnoses the failure using a two-tier NVIDIA Nemotron architecture on Nebius Token Factory, tests competing unified-diff patches inside isolated Git checkpoint branches, and automatically commits the verified winning patch—with zero external runtime dependencies.

Why traceback?

When a test suite or script crashes in development or CI, developers spend minutes reading stack traces, locating user-space frames, reasoning through edge cases, and manually testing candidate fixes. traceback turns that loop into an autonomous, self-verifying pipeline:

Zero-Dependency Standard Library Core: Built purely on Python >=3.11 standard library modules (urllib.request, subprocess, tomllib, json, re), keeping installation instantaneous and preventing dependency conflicts with the target project.

Two-Tier NVIDIA Nemotron Orchestration on Nebius Token Factory: Pairs low-latency fault triage (nebius/nvidia/Nemotron-3_5-Lightning) with deep multi-hypothesis code synthesis (nebius/nvidia/Nemotron-3-Ultra-550b-a55b).

Speculative Git Branch Isolation: Never mutates your working tree blindly. Every candidate patch is evaluated on an isolated Git branch (git_engine.py), verified by re-running your exact command, and either merged on pass or pruned/rolled back on failure.

Architecture & Autonomous Workflow

When you prefix a command with traceback, the engine executes a 5-stage pipeline:

Stage

Module

Action

1. Intercept & Run

traceback/runner.py

Sanitizes runtime environment variables (PYTHONPATH, PYTHONHOME, LD_LIBRARY_PATH, DYLD_LIBRARY_PATH) and executes <command> [args...]. If exit_code == 0, streams stdout and exits cleanly.

2. Stack Trace Parsing

traceback/parser.py

On non-zero exit, parses stderr and stdout via regex (FRAME_PATTERNS & EXCEPTION_PATTERN), filtering out Python stdlib and site-packages frames to isolate the exact local source file, line number, and a ±10-line code window.

3. Git Checkpointing

traceback/git_engine.py

Calls GitManager.prepare_checkpoint() to snapshot the working repository state before any speculative edits occur.

4. Two-Tier Nemotron Reasoning

traceback/agent.py & traceback/client.py

Fast Tier (Nemotron-3_5-Lightning): Runs agent.triage_failure() to synthesize a concise failure invariant describing the root cause.



Heavy Tier (Nemotron-3-Ultra-550b-a55b): Runs agent.generate_hypotheses() (json_mode=True) with the full file context and triage invariant to generate up to max_hypotheses (default 3) competing unified-diff patches.

5. Speculative Verification

traceback/git_engine.py & traceback/cli.py

Iterates through each candidate patch: forks an isolated branch (git.fork_root(index)), applies the unified diff (git.apply_patch()), and re-executes the target command. The first branch to return exit_code == 0 is merged via git.resolve_winner(); failing branches are pruned via git.prune(), or the repo is restored via git.rollback() if all candidates fail.

How We Used Nebius Token Factory & NVIDIA Open-Source Models

traceback is purpose-built around Nebius Token Factory (https://api.tokenfactory.nebius.com/v1) and NVIDIA Nemotron open-source models:

Fast Tier — nebius/nvidia/Nemotron-3_5-Lightning: Used in agent.triage_failure() for high-speed, low-latency stack trace analysis. Given the exception type, traceback frames, and localized ±10-line code window, Nemotron-3_5-Lightning isolates the exact root-cause failure invariant in milliseconds without burning heavy reasoning tokens.

Heavy Tier — nebius/nvidia/Nemotron-3-Ultra-550b-a55b: Used in agent.generate_hypotheses() with structured JSON output (json_mode=True). Using the fast tier's failure invariant alongside the complete target source file, Nemotron-3-Ultra-550b-a55b generates up to 3 distinct, syntactically valid unified-diff patches to test against the test suite.

Lightweight OpenAI-Compatible Client (traceback/client.py): Connects directly to https://api.tokenfactory.nebius.com/v1/chat/completions over standard library urllib.request, demonstrating how easily Nebius Token Factory integrates into zero-dependency developer tooling.

Prerequisites & Installation

Python: >=3.11

Git: Installed and available on PATH (used by git_engine.py for checkpointing and speculative branch testing)

Nebius API Key: A valid key from Nebius Token Factory

Clone the repository and install in editable mode:

git clone https://github.com/abhishek-x86/traceback.git
cd traceback
pip install -e .


To install optional development and test dependencies (pytest>=8.0, ruff>=0.5.0):

pip install -e ".[dev]"


Configuration

1. Environment Variables (Recommended)

Export your Nebius Token Factory API key before running traceback:

export NEBIUS_API_KEY="your-nebius-api-key"


traceback/config.py automatically checks the following environment variables:

Setting

Supported Environment Variables

Default Fallback

API Key

TRACEBACK_API_KEY, NEBIUS_API_KEY, LLM_API_KEY, OPENAI_API_KEY

Value in traceback.toml

Base URL

TRACEBACK_BASE_URL, NEBIUS_BASE_URL, LLM_BASE_URL, OPENAI_BASE_URL

https://api.tokenfactory.nebius.com/v1

Fast Model

TRACEBACK_FAST_MODEL

nebius/nvidia/Nemotron-3_5-Lightning

Heavy Model

TRACEBACK_HEAVY_MODEL

nebius/nvidia/Nemotron-3-Ultra-550b-a55b

2. Configuration File (traceback.toml)

traceback also loads settings from traceback.toml (searching ./traceback.toml, the Python executable parent directory, and ~/.config/traceback/traceback.toml on Linux/macOS or %APPDATA%/traceback/traceback.toml on Windows):

api_key = "nebius_api_key_here"
base_url = "https://api.tokenfactory.nebius.com/v1"

[models]
fast_tier = "nebius/nvidia/Nemotron-3_5-Lightning"
heavy_tier = "nebius/nvidia/Nemotron-3-Ultra-550b-a55b"


Additional runtime parameters supported by config.py:

max_hypotheses: Maximum candidate patches generated per failure (default: 3)

adversarial_fuzzing: Enable adversarial edge-case consideration during patching (default: true)

timeout_seconds: Subprocess execution timeout per test run (default: 30)

Usage & Quick Test

Prefix any command with traceback:

traceback <command> [args...]


Run with Included Test Fixtures

The repository includes fixtures/broken_math.py and fixtures/test_broken_math.py to test autonomous bug repair out of the box:

# Run pytest wrapped by traceback on the broken fixture suite
traceback pytest fixtures/test_broken_math.py


Or wrap any Python script directly:

traceback python my_failing_script.py


Repository Structure

abhishek-x86/traceback
├── LICENSE                  # MIT License
├── README.md                # Project documentation & setup guide
├── pyproject.toml           # Hatchling build config & CLI entrypoint
├── traceback.toml           # Nebius Token Factory endpoint & Nemotron model config
├── test.py                  # Quick smoke script
├── fixtures/                # Broken code fixtures for end-to-end healing tests
│   ├── broken_math.py
│   └── test_broken_math.py
└── traceback/               # Core Python package (zero external runtime dependencies)
    ├── __init__.py
    ├── cli.py               # CLI entrypoint (`traceback <command> [args...]`)
    ├── runner.py            # Subprocess runner with environment sanitization
    ├── parser.py            # Traceback regex parser & local source frame extractor
    ├── config.py            # TOML & environment variable loader
    ├── client.py            # Zero-dependency urllib REST client for Nebius Token Factory
    ├── agent.py             # Two-tier Nemotron triage & hypothesis diff generator
    └── git_engine.py        # Git checkpoint, speculative branching, merge & rollback engine


License

Distributed under the MIT License. See LICENSE for full license text.
