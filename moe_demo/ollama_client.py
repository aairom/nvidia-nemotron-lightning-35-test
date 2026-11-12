"""Thin, dependency-light client for the local Ollama REST API.

Only the endpoints the demo needs are wrapped:
  GET  /api/version   - connection check
  GET  /api/tags      - installed models
  GET  /api/ps        - models currently loaded in memory (model loading status)
  POST /api/generate  - empty prompt = preload; keep_alive=0 = unload
  POST /api/chat      - streaming chat (NDJSON), including the optional `thinking` channel
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Iterator

import requests


class OllamaError(Exception):
    """Base class for all client errors (message is safe to show to the user)."""


class OllamaConnectionError(OllamaError):
    """Ollama is not reachable (not running, wrong URL, network)."""


class OllamaModelNotFound(OllamaError):
    """The requested model is not installed."""


class OllamaTimeout(OllamaError):
    """Ollama did not answer in time."""


@dataclass
class StreamEvent:
    """One piece of a streamed answer.

    kind: "thinking" (reasoning trace), "content" (answer text) or "done" (final stats).
    """

    kind: str
    text: str = ""
    stats: dict[str, Any] = field(default_factory=dict)


class OllamaClient:
    def __init__(self, base_url: str, timeout: float = 600.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()

    # ------------------------------------------------------------------ helpers
    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def _request(self, method: str, path: str, *, timeout: float, **kwargs: Any) -> requests.Response:
        try:
            return self._session.request(method, self._url(path), timeout=timeout, **kwargs)
        except requests.ConnectionError as exc:
            raise OllamaConnectionError(
                f"Cannot reach Ollama at {self.base_url}. Start it with `ollama serve` "
                "(or open the Ollama app) and check OLLAMA_BASE_URL."
            ) from exc
        except requests.Timeout as exc:
            raise OllamaTimeout(f"Ollama did not answer within {timeout:.0f}s.") from exc
        except requests.RequestException as exc:  # pragma: no cover - defensive
            raise OllamaError(f"Unexpected HTTP error: {exc}") from exc

    @staticmethod
    def _raise_for_status(resp: requests.Response, model: str | None = None) -> None:
        if resp.status_code < 400:
            return
        try:
            detail = resp.json().get("error", resp.text)
        except ValueError:
            detail = resp.text
        if resp.status_code == 404 or "not found" in str(detail).lower():
            raise OllamaModelNotFound(
                f"Model '{model}' is not installed. Run: ollama pull {model}" if model else str(detail)
            )
        raise OllamaError(f"Ollama returned HTTP {resp.status_code}: {detail}")

    # ------------------------------------------------------------------ status
    def version(self) -> str:
        resp = self._request("GET", "/api/version", timeout=3)
        self._raise_for_status(resp)
        return str(resp.json().get("version", "unknown"))

    def is_alive(self) -> bool:
        try:
            self.version()
            return True
        except OllamaError:
            return False

    def list_models(self) -> list[str]:
        resp = self._request("GET", "/api/tags", timeout=5)
        self._raise_for_status(resp)
        return [m["name"] for m in resp.json().get("models", [])]

    def running_models(self) -> list[dict[str, Any]]:
        resp = self._request("GET", "/api/ps", timeout=5)
        self._raise_for_status(resp)
        return list(resp.json().get("models", []))

    def loaded_info(self, model: str) -> dict[str, Any] | None:
        """Return the /api/ps entry for `model` when it is resident in memory, else None."""
        for entry in self.running_models():
            if model in (entry.get("name"), entry.get("model")):
                return entry
        return None

    def preload(self, model: str, keep_alive: str = "15m") -> None:
        """Load the model into memory without generating anything."""
        resp = self._request(
            "POST", "/api/generate", timeout=self.timeout,
            json={"model": model, "keep_alive": keep_alive},
        )
        self._raise_for_status(resp, model)

    def unload(self, model: str) -> None:
        resp = self._request(
            "POST", "/api/generate", timeout=30, json={"model": model, "keep_alive": 0}
        )
        self._raise_for_status(resp, model)

    # ------------------------------------------------------------------ chat
    def chat_stream(
        self,
        model: str,
        messages: list[dict[str, str]],
        options: dict[str, Any] | None = None,
        think: bool | str | None = None,
        keep_alive: str = "15m",
    ) -> Iterator[StreamEvent]:
        """Stream a chat completion. Raises OllamaError subclasses on failure."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": True,
            "options": options or {},
            "keep_alive": keep_alive,
        }
        if think is not None:
            payload["think"] = think

        # (connect timeout, read timeout): the read timeout must cover cold model loads.
        resp = self._request("POST", "/api/chat", timeout=(5, self.timeout), json=payload, stream=True)
        try:
            self._raise_for_status(resp, model)
            for line in resp.iter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if "error" in data:
                    raise OllamaError(str(data["error"]))
                msg = data.get("message") or {}
                if msg.get("thinking"):
                    yield StreamEvent("thinking", msg["thinking"])
                if msg.get("content"):
                    yield StreamEvent("content", msg["content"])
                if data.get("done"):
                    yield StreamEvent("done", stats=data)
        except requests.Timeout as exc:
            raise OllamaTimeout("Ollama stopped responding while streaming the answer.") from exc
        except requests.RequestException as exc:
            raise OllamaConnectionError(f"Connection to Ollama was lost: {exc}") from exc
        except json.JSONDecodeError as exc:
            raise OllamaError("Received malformed data from Ollama.") from exc
        finally:
            resp.close()
