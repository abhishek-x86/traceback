"""HTTP client for Nebius Token Factory inference API using urllib."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from traceback.config import Config


class ClientError(Exception):
    """Raised when the LLM inference endpoint returns an error."""


class LLMClient:
    def __init__(self, config: Config) -> None:
        self.cfg = config
        self.base_url = config.base_url.rstrip("/")
        self.endpoint = f"{self.base_url}/chat/completions"
        self.api_key = config.api_key

        # Allow environment override, otherwise use config, fallback to 180s
        env_timeout = os.environ.get("TRACEBACK_TIMEOUT")
        if env_timeout:
            self.timeout = float(env_timeout)
        elif hasattr(self.cfg, "timeout_seconds") and self.cfg.timeout_seconds:
            self.timeout = float(self.cfg.timeout_seconds)
        else:
            self.timeout = 180.0

    def complete(
        self,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
        json_mode: bool = False,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }

        if json_mode:
            payload["response_format"] = {"type": "json_object"}

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as exc:
            err_body = exc.read().decode("utf-8", errors="replace")
            raise ClientError(f"HTTP {exc.code} from {self.endpoint}: {err_body}") from None
        except TimeoutError:
            raise ClientError(
                f"Request to {self.endpoint} timed out after {self.timeout}s while waiting for {model}."
            ) from None
