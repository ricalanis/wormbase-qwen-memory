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

import json
import os
import re
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
        # triage worker is gated independently of the planner provider switch
        return self._enabled and super().available


OLLAMA_CLOUD_BASE = "https://ollama.com/v1"
OPENCODE_AUTH = os.path.expanduser("~/.local/share/opencode/auth.json")


def _ollama_cloud_key() -> str | None:
    """OLLAMA_API_KEY env, else the OpenCode auth store (provider 'ollama-cloud')."""
    k = os.environ.get("OLLAMA_API_KEY")
    if k:
        return k
    try:
        d = json.load(open(OPENCODE_AUTH))
        e = d.get("ollama-cloud") or {}
        return e.get("key") or e.get("apiKey")
    except Exception:
        return None


class OllamaCloudClient(QwenCloudClient):
    """A large Qwen model hosted on Ollama Cloud (https://ollama.com), driven
    through the local toolchain. Capable enough to author structured plans (the
    small local models can't). For DEV/DEMO; the hackathon's Alibaba-Cloud proof
    still uses ``QwenCloudClient`` (DashScope)."""

    def __init__(self, model: str | None = None) -> None:
        super().__init__(
            model=model or os.environ.get("OLLAMA_CLOUD_MODEL", "qwen3-coder:480b"),
            api_key=_ollama_cloud_key(),
            base_url=OLLAMA_CLOUD_BASE,
        )
        self.backend_label = "ollama-cloud"


def loads_lenient(text: str) -> Any:
    """Parse JSON from a model reply, tolerating prose around the object."""
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
        raise


def resolve_planner_client() -> QwenCloudClient | None:
    """Pick the planner backend from ``WBM_PROVIDER`` (one switch, identical code).

    dashscope|cloud|qwen -> Qwen-Plus on Alibaba Cloud (needs DASHSCOPE_API_KEY)
    rules                -> None (deterministic rule-based planner; reliable, $0)
    local                -> local model via Ollama (EXPERIMENTAL: small models are
                            unreliable at structured plan authoring; auto-falls back
                            to rules on malformed output)
    auto (default)       -> cloud if a key is present, else rules
    """
    provider = os.environ.get("WBM_PROVIDER", "auto").lower()
    model = os.environ.get("QWEN_PLANNER_MODEL", "qwen-plus")
    if provider == "rules":
        return None
    if provider in ("dashscope", "cloud", "qwen"):
        c = QwenCloudClient(model=model)
        return c if c.available else None
    if provider == "local":
        c = LocalQwenClient()
        return c if c._client is not None else None
    if provider in ("ollama_cloud", "ollama-cloud", "cloud-ollama"):
        c = OllamaCloudClient()
        return c if c.available else None
    # auto: cloud when a key exists, otherwise deterministic rules
    cloud = QwenCloudClient(model=model)
    return cloud if cloud.available else None
