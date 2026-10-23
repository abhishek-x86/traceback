import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path

@dataclass
class Config:
    api_key: str = ""
    base_url: str = "https://api.tokenfactory.nebius.com/v1"
    fast_tier: str = "nebius/nvidia/Nemotron-3_5-Lightning"
    heavy_tier: str = "nebius/nvidia/Nemotron-3-Ultra-550b-a55b"
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
        search_dirs.append(Path(xdg) / "traceback" if xdg else Path.home() / ".config" / "traceback")

    for directory in search_dirs:
        for filename in ("traceback.toml", ".traceback.toml", "config.toml"):
            candidate = directory / filename
            if candidate.is_file():
                return candidate
    return None

def load_config() -> Config:
    cfg = Config()
    
    if target := _find_config_file():
        try:
            with open(target, "rb") as f:
                data = tomllib.load(f)
            
            cfg.api_key = data.get("api_key", cfg.api_key)
            cfg.base_url = data.get("base_url", cfg.base_url)

            if models := data.get("models"):
                cfg.fast_tier = models.get("fast_tier", cfg.fast_tier)
                cfg.heavy_tier = models.get("heavy_tier", cfg.heavy_tier)

            if engine := data.get("engine"):
                cfg.max_hypotheses = engine.get("max_hypotheses", cfg.max_hypotheses)
                cfg.adversarial_fuzzing = engine.get("adversarial_fuzzing", cfg.adversarial_fuzzing)
                cfg.timeout_seconds = engine.get("timeout_seconds", cfg.timeout_seconds)
        except Exception:
            pass

    if env_key := os.environ.get("NEBIUS_API_KEY"):
        cfg.api_key = env_key
    if env_url := os.environ.get("NEBIUS_BASE_URL"):
        cfg.base_url = env_url

    return cfg