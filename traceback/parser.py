import re
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ErrorContext:
    target_file: Path | None
    line_number: int | None
    error_type: str
    error_message: str
    compacted_trace: str
    source_snippet: str | None = None

FRAME_PATTERNS = [
    re.compile(r'File\s+["\'](?P<file>[^"\']+)["\'],\s+line\s+(?P<line>\d+)'),
    re.compile(r'(?:^|\s)(?P<file>[a-zA-Z0-9_\-./]+\.py):(?P<line>\d+):'),
    re.compile(r'(?:^|\n)(?P<file>[a-zA-Z0-9_\-./]+\.[a-zA-Z0-9]+):(?P<line>\d+):'),
]

EXCEPTION_PATTERN = re.compile(
    r'^(?P<type>[a-zA-Z0-9_.]*(?:Error|Exception|Failure|Panic)):?\s*(?P<msg>.*)$',
    re.MULTILINE,
)

def _read_source_window(file_path: Path, line: int, window: int = 10) -> str:
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""

    start = max(0, line - window - 1)
    end = min(len(lines), line + window)

    snippet: list[str] = []
    for idx in range(start, end):
        current_num = idx + 1
        marker = ">> " if current_num == line else "   "
        snippet.append(f"{marker}{current_num:4d} | {lines[idx]}")
    return "\n".join(snippet)

def _extract_target(text: str, repo_root: Path) -> tuple[Path | None, int | None]:
    for pattern in FRAME_PATTERNS:
        matches = list(pattern.finditer(text))
        for m in reversed(matches):
            raw_path = m.group("file")
            line_str = m.group("line")
            if not raw_path or not line_str:
                continue

            path = Path(raw_path)
            resolved = path if path.is_absolute() else (repo_root / path).resolve()
            path_str = str(resolved).lower()

            if any(p in path_str for p in ("site-packages", "/lib/python", "\\lib\\python")):
                continue

            if resolved.is_file():
                return resolved, int(line_str)
    return None, None

def _compact_trace(text: str, max_lines: int = 35) -> str:
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text.strip()
    return "\n".join(lines[:5] + ["\n[... truncated intermediate output ...]\n"] + lines[-30:]).strip()

def parse_trace(stderr: str, stdout: str = "", repo_root: Path | None = None) -> ErrorContext:
    root = (repo_root or Path.cwd()).resolve()
    full_output = f"{stdout}\n{stderr}".strip()

    err_type, err_msg = "CommandError", "Execution failed"
    if matches := list(EXCEPTION_PATTERN.finditer(full_output)):
        last = matches[-1]
        err_type = last.group("type") or err_type
        err_msg = (last.group("msg") or "").strip()

    target_file, line_num = _extract_target(full_output, root)
    snippet = _read_source_window(target_file, line_num) if target_file and line_num else None

    return ErrorContext(
        target_file=target_file,
        line_number=line_num,
        error_type=err_type,
        error_message=err_msg,
        compacted_trace=_compact_trace(full_output),
        source_snippet=snippet,
    )