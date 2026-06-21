"""Qwen Cloud (DashScope) + local-Qwen clients, OpenAI-compatible.

Two backends, one interface:
- ``QwenCloudClient`` -> Alibaba Cloud Model Studio / DashScope (Qwen-Plus): the
  planner brain. This is the file that demonstrates use of Alibaba Cloud APIs.
- ``LocalQwenClient`` -> a small Qwen served locally via Ollama's OpenAI-compatible
  endpoint: the cheap triage/recall worker.

Everything degrades gracefully: if no key / SDK / server is present, ``available``
is False and callers fall back to the deterministic rule-based path so tests and
the offline demo always run.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

try:  # optional dependency
    from openai import OpenAI

    _HAVE_OPENAI = True
except Exception:  # pragma: no cover
    OpenAI = None  # type: ignore
    _HAVE_OPENAI = False

# DashScope international (Singapore) compatible-mode endpoint by default.
DEFAULT_DASHSCOPE_BASE = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"


@dataclass
class ChatResult:
    text: str
    tokens: int
    backend: str


class QwenCloudClient:
    """Qwen-Plus on Alibaba Cloud DashScope via the OpenAI-compatible API."""

    def __init__(
        self,
        model: str = "qwen-plus",
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self.model = model
        self.backend_label = "dashscope"
        self.api_key = api_key or os.environ.get("DASHSCOPE_API_KEY")
        self.base_url = (
            base_url
            or os.environ.get("DASHSCOPE_BASE_URL")
            or DEFAULT_DASHSCOPE_BASE
        )
        self._client = (
            OpenAI(api_key=self.api_key, base_url=self.base_url)
            if (_HAVE_OPENAI and self.api_key)
            else None
        )

    @property
    def available(self) -> bool:
        return self._client is not None

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        response_format: dict | None = None,
    ) -> ChatResult:
        if not self.available:
            raise RuntimeError("QwenCloudClient unavailable (no DASHSCOPE_API_KEY)")
        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        resp = self._client.chat.completions.create(**kwargs)
        text = resp.choices[0].message.content or ""
        tokens = int(getattr(resp.usage, "total_tokens", 0) or 0)
        return ChatResult(text=text, tokens=tokens,
                          backend=f"{self.backend_label}:{self.model}")


class LocalQwenClient(QwenCloudClient):
    """A small model served locally (Ollama OpenAI-compatible). The triage worker.

    Zero-cost: runs entirely on local hardware. The model is configurable via
    ``OLLAMA_MODEL`` so you can use whatever you already have pulled (a vanilla
    small Qwen, MiniCPM, your own fine-tune, etc.) — no GPU bill, no API spend.
    """

    def __init__(self, model: str | None = None) -> None:
        base = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        # Ollama ignores the key but the SDK requires a non-empty one.
        super().__init__(
            model=model or os.environ.get("OLLAMA_MODEL", "qwen3:1.7b"),
            api_key=os.environ.get("OLLAMA_API_KEY", "ollama"),
            base_url=base,
        )
        self.backend_label = "local"
        self._enabled = os.environ.get("WBM_USE_LOCAL_QWEN") == "1"

    @property
    def available(self) -> bool:
        return self._enabled and super().available
