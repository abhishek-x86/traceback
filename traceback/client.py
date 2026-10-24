import json
import urllib.error
import urllib.request
from traceback.config import Config, load_config
from typing import Any


class ClientError(Exception):
    pass

class LLMClient:
    def __init__(self, config: Config | None = None) -> None:
        self.cfg = config or load_config()
        self.api_key = self.cfg.api_key
        base = self.cfg.base_url.rstrip("/")
        self.endpoint = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
        self.timeout = float(self.cfg.timeout_seconds)

    def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> str:
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "TraceBack-Engine/0.1.0",
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        body: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        payload = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(self.endpoint, data=payload, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise ClientError(f"HTTP {exc.code} from {self.endpoint}: {err_body}") from None
        except urllib.error.URLError as exc:
            raise ClientError(f"Network error connecting to {self.endpoint}: {exc.reason}") from None
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise ClientError(f"Malformed response from {self.endpoint}: {exc}") from None