from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from pathlib import Path
from traceback.client import LLMClient
from traceback.config import Config, load_config
from traceback.parser import ErrorContext
from traceback.tavily import search_error_context


@dataclass
class Hypothesis:
    index: int
    title: str
    diff: str
    target_file: str
    fixed_code: str = ""


def _extract_code(raw: str) -> str:
    clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
    matches = re.findall(r"```(?:python|py)?\s*\n(.*?)```", clean, flags=re.DOTALL)
    if matches:
        return matches[-1].strip() + "\n"
    lines = clean.splitlines()
    if lines and lines[0].startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].startswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip() + "\n"


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
            "Given the error trace and code snippet, state the root cause bug in ONE short sentence.\n\n"
            f"Error: {error.error_type}: {error.error_message}\n"
            f"Trace:\n{error.compacted_trace}\n"
            f"Snippet:\n{error.source_snippet or ''}\n"
        )
        raw = self.client.complete(
            model=self.cfg.fast_tier,
            messages=[
                {"role": "system", "content": "Respond in one concise sentence only. Do not overthink."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )
        clean = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        lines = [line.strip() for line in clean.splitlines() if line.strip()]
        return lines[-1] if lines else "Boundary condition error in target function."

    def generate_hypotheses(
        self,
        error: ErrorContext,
        diagnosis: str,
        count: int = 1,
    ) -> list[Hypothesis]:
        if not error.target_file or not error.target_file.is_file():
            return []

        rel_path = _extract_relative_path(error.target_file, self.root)
        full_source = error.target_file.read_text(encoding="utf-8", errors="replace")

        test_context = ""
        for tf in error.target_file.parent.glob("test_*.py"):
            try:
                test_context += f"\nTest file `{tf.name}`:\n```python\n{tf.read_text(encoding='utf-8')}\n```\n"
            except OSError:
                pass

        prompt = (
            f"Fix the bug in `{rel_path}` so all tests pass.\n"
            f"Diagnosis: {diagnosis}\n"
            f"Current `{rel_path}`:\n```python\n{full_source}\n```\n"
            f"{test_context}\n"
            "Output the COMPLETE fixed Python file for `{rel_path}` inside a ```python ... ``` block. Do not omit any functions or imports."
        )

        response = self.client.complete(
            model=self.cfg.heavy_tier,
            messages=[
                {"role": "system", "content": "You are an automated code repair agent. Return only the complete fixed file inside a ```python block."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,
        )

        fixed_code = _extract_code(response)
        if not fixed_code or fixed_code.strip() == full_source.strip():
            return []

        diff_lines = list(
            difflib.unified_diff(
                full_source.splitlines(keepends=True),
                fixed_code.splitlines(keepends=True),
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
            )
        )
        unified_diff = "".join(diff_lines)
        if not unified_diff.strip():
            return []

        return [
            Hypothesis(
                index=1,
                title=f"Fix {error.error_type} in {Path(rel_path).name}",
                diff=unified_diff,
                target_file=rel_path,
                fixed_code=fixed_code,
            )
        ]
