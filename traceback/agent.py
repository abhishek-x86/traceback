import json
import re
from dataclasses import dataclass
from pathlib import Path
from traceback.client import LLMClient
from traceback.config import Config, load_config
from traceback.parser import ErrorContext


@dataclass
class Hypothesis:
    index: int
    title: str
    diff: str
    target_file: str

def _clean_diff_output(raw_text: str) -> str:
    text = re.sub(r"^```(?:diff)?\n", "", raw_text.strip(), flags=re.MULTILINE)
    text = re.sub(r"\n```$", "", text, flags=re.MULTILINE)
    return text.strip() + "\n"

def _extract_relative_path(file_path: Path, repo_root: Path) -> str:
    try:
        return str(file_path.relative_to(repo_root)).replace("\\", "/")
    except ValueError:
        return file_path.name

class DebugAgent:
    def __init__(self, config: Config | None = None, repo_root: Path | None = None) -> None:
        self.cfg = config or load_config()
        self.client = LLMClient(self.cfg)
        self.root = (repo_root or Path.cwd()).resolve()

    def triage_failure(self, error: ErrorContext) -> str:
        prompt = (
            "You are an automated debugger triage module. Given the following error trace and snippet, "
            "provide a single, precise sentence explaining the root cause failure invariant.\n\n"
            f"Error Type: {error.error_type}\n"
            f"Message: {error.error_message}\n"
            f"Trace:\n{error.compacted_trace}\n"
        )
        if error.source_snippet:
            prompt += f"\nSnippet:\n{error.source_snippet}\n"

        return self.client.complete(
            model=self.cfg.fast_tier,
            messages=[
                {"role": "system", "content": "You are a concise debugging invariant analyzer. Respond in one sentence only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        ).strip()

    def generate_hypotheses(self, error: ErrorContext, diagnosis: str, count: int = 3) -> list[Hypothesis]:
        if not error.target_file or not error.target_file.is_file():
            return []

        rel_path = _extract_relative_path(error.target_file, self.root)
        try:
            full_source = error.target_file.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return []

        prompt = (
            f"We are fixing a bug in `{rel_path}`.\n"
            f"Triage Diagnosis: {diagnosis}\n"
            f"Error Details: {error.error_type}: {error.error_message}\n\n"
            f"Full content of `{rel_path}`:\n"
            f"```\n{full_source}\n```\n\n"
            f"Generate exactly {count} distinct, competing fix hypotheses as a JSON array.\n"
            "Each item must have:\n"
            "- 'title': brief strategy description\n"
            "- 'diff': a valid unified diff (starting with --- a/path and +++ b/path) applicable with `git apply`\n"
            "Do not include conversational text. Format strictly as: {\"hypotheses\": [{\"title\": \"...\", \"diff\": \"...\"}]}"
        )

        response = self.client.complete(
            model=self.cfg.heavy_tier,
            messages=[
                {"role": "system", "content": "You synthesize strict, minimal unified diffs that resolve code bugs without breaking contracts."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            json_mode=True,
        )

        results: list[Hypothesis] = []
        try:
            parsed = json.loads(response)
            items = parsed.get("hypotheses", [])
            for idx, item in enumerate(items[:count], start=1):
                clean_diff = _clean_diff_output(item.get("diff", ""))
                if clean_diff and "---" in clean_diff and "+++" in clean_diff:
                    results.append(
                        Hypothesis(
                            index=idx,
                            title=item.get("title", f"Hypothesis {idx}"),
                            diff=clean_diff,
                            target_file=rel_path,
                        )
                    )
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        return results

    def synthesize_fuzzer(self, error: ErrorContext, source_code: str) -> str | None:
        if not self.cfg.adversarial_fuzzing or not error.target_file:
            return None

        prompt = (
            f"Create a single, standalone Python test function using pytest that acts as an adversarial check "
            f"for this bug fix. Do not explain anything; output ONLY the Python code block.\n\n"
            f"Error Was: {error.error_type}: {error.error_message}\n"
            f"Code:\n```python\n{source_code}\n```"
        )

        raw = self.client.complete(
            model=self.cfg.fast_tier,
            messages=[
                {"role": "system", "content": "You write minimal, adversarial edge-case test functions."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        return _clean_diff_output(raw)