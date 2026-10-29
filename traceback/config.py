"""Configuration loader for traceback CLI."""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    api_key: str
    base_url: str
    fast_tier: str
    heavy_tier: str
    max_hypotheses: int = 2
    adversarial_fuzzing: bool = True
    timeout_seconds: int = 180


def _find_config_file() -> Path | None:
    cwd_cfg = Path.cwd() / "traceback.toml"
    if cwd_cfg.is_file():
        return cwd_cfg

    exe_cfg = Path(sys.executable).resolve().parent / "traceback.toml"
    if exe_cfg.is_file():
        return exe_cfg

    user_cfg = Path.home() / ".config" / "traceback" / "traceback.toml"
    if user_cfg.is_file():
        return user_cfg

    return None


def load_config() -> Config:
    cfg_data: dict = {}
    cfg_path = _find_config_file()
    if cfg_path:
        try:
            with open(cfg_path, "rb") as f:
                cfg_data = tomllib.load(f)
        except Exception:
            pass

    # Resolve API Key
    api_key = (
        os.environ.get("TRACEBACK_API_KEY")
        or os.environ.get("NEBIUS_API_KEY")
        or os.environ.get("LLM_API_KEY")
        or os.environ.get("OPENAI_API_KEY")
        or cfg_data.get("api_key", "")
    )

    # Resolve Base URL
    base_url = (
        os.environ.get("TRACEBACK_BASE_URL")
        or os.environ.get("NEBIUS_BASE_URL")
        or cfg_data.get("base_url", "https://api.tokenfactory.nebius.com/v1")
    )

    models_cfg = cfg_data.get("models", {})
    fast_tier = (
        os.environ.get("TRACEBACK_FAST_MODEL")
        or models_cfg.get("fast_tier", "nvidia/Nemotron-3_5-Lightning")
    )
    heavy_tier = (
        os.environ.get("TRACEBACK_HEAVY_MODEL")
        or models_cfg.get("heavy_tier", "nvidia/Nemotron-3_5-Lightning")
    )

    timeout = int(
        os.environ.get("TRACEBACK_TIMEOUT")
        or cfg_data.get("timeout_seconds", 180)
    )

    max_hypotheses = int(
        os.environ.get("TRACEBACK_MAX_HYPOTHESES")
        or cfg_data.get("max_hypotheses", 2)
    )

    return Config(
        api_key=api_key,
        base_url=base_url,
        fast_tier=fast_tier,
        heavy_tier=heavy_tier,
        max_hypotheses=max_hypotheses,
        adversarial_fuzzing=cfg_data.get("adversarial_fuzzing", True),
        timeout_seconds=timeout,
    )
