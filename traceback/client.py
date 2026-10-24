import json
import os
import urllib.error
import urllib.request
from traceback.config import Config, load_config
from typing import Any


class ClientError(Exception):
    pass

class LLMClient:
    def __init__(self, config: Config | None = None) -> None:
        cfg = config or load_config()
        self.api_key = cfg.api_key or os.environ.get("NEBIUS_API_KEY", "") or os.environ.get("LLM_API_KEY", "")
        self.base_url = (cfg.base_url or os.environ.get("LLM_BASE_URL", "")).rstrip("/")
        self.timeout = float(cfg.timeout_seconds)

        if not self.base_url:
            self.base_url = "https://api.tokenfactory.nebius.com/v1"

    def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> str:
        if not self.api_key:
            raise ClientError("API key missing. Set NEBIUS_API_KEY, LLM_API_KEY, or add 'api_key' in traceback.toml")

        endpoint = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "User-Agent": "TraceBack-Engine/0.1.0",
        }

        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(endpoint, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise ClientError(f"HTTP {exc.code} from {endpoint}: {err_body}") from None
        except urllib.error.URLError as exc:
            raise ClientError(f"Network failure connecting to {endpoint}: {exc.reason}") from None
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise ClientError(f"Malformed response from {endpoint}: {exc}") from None