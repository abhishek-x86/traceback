# traceback

**Autonomous zero-dependency CLI debugging wrapper powered by Nebius Token Factory & NVIDIA Nemotron.**  
Built for the [Nebius x NVIDIA Global AI Hackathon](https://nebiusglobalaihackathon.devpost.com/) (*Coding and Agentic Engineering Track*).

`traceback` wraps any terminal command (e.g., `pytest` or `python script.py`), intercepts runtime crashes, diagnoses root causes via a two-tier **NVIDIA Nemotron** pipeline on **Nebius Token Factory**, verifies candidate diffs in isolated **Git branches**, and auto-merges the passing fix.

## How It Works

1. **Intercept (`runner.py`):** Runs `<command> [args...]` in a sanitized environment. Exits `0` immediately if the command succeeds.
2. **Parse (`parser.py`):** On crash, filters out stdlib/`site-packages` frames to extract the failing local file, line number, and `±10`-line code window.
3. **Checkpoint (`git_engine.py`):** Snapshots the current Git working tree before testing any patches.
4. **Two-Tier Nemotron Triage & Patching (`agent.py`, `client.py`):**
   - **Fast Tier (`nebius/nvidia/Nemotron-3_5-Lightning`):** Synthesizes a concise root-cause failure invariant from the stack trace.
   - **Heavy Tier (`nebius/nvidia/Nemotron-3-Ultra-550b-a55b`):** Generates up to `3` competing unified-diff patches in JSON mode using the failure invariant and full file context.
5. **Speculative Verification (`git_engine.py`, `cli.py`):** Forks an isolated Git branch per candidate patch, applies the diff, and re-runs the command. Merges the first passing branch (`exit_code == 0`) or rolls back cleanly if all fail.

## Nebius Token Factory & NVIDIA Models Used

- **Inference Endpoint:** `https://api.tokenfactory.nebius.com/v1/chat/completions` via a zero-dependency `urllib.request` client (`traceback/client.py`).
- **Models:** `nebius/nvidia/Nemotron-3_5-Lightning` (low-latency fault triage) + `nebius/nvidia/Nemotron-3-Ultra-550b-a55b` (structured multi-hypothesis diff generation).

## Quickstart

**Requirements:** Python `>=3.11`, `git`, and a [Nebius Token Factory](https://tokenfactory.nebius.com/) API key.

```bash
git clone https://github.com/abhishek-x86/traceback.git
cd traceback
pip install -e ".[dev]"
export NEBIUS_API_KEY="your-nebius-api-key"
```

## Usage

Prefix any failing test suite or script with `traceback`:

```bash
# Test autonomous healing on the included broken fixture
traceback pytest fixtures/test_broken_math.py

# Or wrap any Python script
traceback python script.py
```

## Configuration

Configure via environment variables or `traceback.toml`:

```toml
api_key = "nebius_api_key_here"
base_url = "https://api.tokenfactory.nebius.com/v1"

[models]
fast_tier = "nebius/nvidia/Nemotron-3_5-Lightning"
heavy_tier = "nebius/nvidia/Nemotron-3-Ultra-550b-a55b"
```

| Setting | Environment Variables | Default |
| :--- | :--- | :--- |
| **API Key** | `TRACEBACK_API_KEY`, `NEBIUS_API_KEY`, `LLM_API_KEY`, `OPENAI_API_KEY` | `traceback.toml` |
| **Base URL** | `TRACEBACK_BASE_URL`, `NEBIUS_BASE_URL`, `LLM_BASE_URL`, `OPENAI_BASE_URL` | `https://api.tokenfactory.nebius.com/v1` |
| **Fast Model** | `TRACEBACK_FAST_MODEL` | `nebius/nvidia/Nemotron-3_5-Lightning` |
| **Heavy Model** | `TRACEBACK_HEAVY_MODEL` | `nebius/nvidia/Nemotron-3-Ultra-550b-a55b` |

## License

MIT License — see [LICENSE](LICENSE).
