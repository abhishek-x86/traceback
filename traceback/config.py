import contextlib
import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    api_key: str = ""
    base_url: str = ""
    fast_tier: str = ""
    heavy_tier: str = ""
    max_hypotheses: int = 3
    adversarial_fuzzing: bool = True
    timeout_seconds: int = 30

def _find_config_file() -> Path | None:
    search_dirs = [Path.cwd()]
    if getattr(sys, "frozen", False):
        search_dirs.append(Path(sys.executable).resolve().parent)
    if sys.platform == "win32":
        if appdata := os.environ.get("APPDATA"):
            search_dirs.append(Path(appdata) / "traceback")
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        cfg_dir = Path(xdg) / "traceback" if xdg else Path.home() / ".config" / "traceback"
        search_dirs.append(cfg_dir)

    for directory in search_dirs:
        for filename in ("traceback.toml", ".traceback.toml", "config.toml"):
            candidate = directory / filename
            if candidate.is_file():
                return candidate
    return None

def load_config() -> Config:
    cfg = Config()
    if target := _find_config_file():
        with contextlib.suppress(tomllib.TOMLDecodeError, OSError):
            with open(target, "rb") as f:
                data = tomllib.load(f)
            cfg.api_key = data.get("api_key", "")
            cfg.base_url = data.get("base_url", "")
            if models := data.get("models"):
                cfg.fast_tier = models.get("fast_tier", "")
                cfg.heavy_tier = models.get("heavy_tier", "")
            if engine := data.get("engine"):
                cfg.max_hypotheses = engine.get("max_hypotheses", cfg.max_hypotheses)
                cfg.adversarial_fuzzing = engine.get("adversarial_fuzzing", cfg.adversarial_fuzzing)
                cfg.timeout_seconds = engine.get("timeout_seconds", cfg.timeout_seconds)

    # Generic env overrides with fallbacks across standard naming conventions
    cfg.api_key = (
        os.environ.get("TRACEBACK_API_KEY")
        or os.environ.get("LLM_API_KEY")
        or os.environ.get("NEBIUS_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or cfg.api_key
    )
    cfg.base_url = (
        os.environ.get("TRACEBACK_BASE_URL")
        or os.environ.get("LLM_BASE_URL")
        or os.environ.get("NEBIUS_BASE_URL")
        or os.environ.get("OPENAI_BASE_URL")
        or cfg.base_url
        or "https://api.tokenfactory.nebius.com/v1"
    )
    cfg.fast_tier = (
        os.environ.get("TRACEBACK_FAST_MODEL")
        or cfg.fast_tier
        or "nebius/nvidia/Nemotron-3_5-Lightning"
    )
    cfg.heavy_tier = (
        os.environ.get("TRACEBACK_HEAVY_MODEL")
        or cfg.heavy_tier
        or "nebius/nvidia/Nemotron-3-Ultra-550b-a55b"
    )
    return cfg