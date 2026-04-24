""" Control Plane (MCP) layer.

The router reads ``config/mcp.yaml``, exposes a single ``generate`` entry
point, and transparently falls back from the primary model to the secondary
on failure. Every call records what happened (provider, model, fallback path,
latency, error if any) so the workflow can surface it in the agent trace and
in LangSmith.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from .anthropic_client import AnthropicClient
from .openai_client import OpenAIClient

# Optional LangSmith tracing — silently no-op when the key is unset.
try:
    from langsmith import traceable  # type: ignore
except Exception:  # pragma: no cover - optional dep
    def traceable(*args: Any, **kwargs: Any):  # type: ignore
        def _decorator(fn):
            return fn

        return _decorator


CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "mcp.yaml"


@dataclass
class LLMResult:
    """Outcome of a single ``LLMRouter.generate`` call."""

    text: str
    model_used: str
    provider_used: str
    fell_back: bool
    latency_ms: int
    attempts: list[dict[str, Any]] = field(default_factory=list)


class LLMRouter:
    """Routes generation requests to a primary model with secondary fallback."""

    def __init__(self, config_path: Path | str = CONFIG_PATH) -> None:
        with open(config_path, "r") as fh:
            self._config: dict[str, Any] = yaml.safe_load(fh)
        # Lazy provider clients — only instantiated when first needed so a
        # single missing key does not crash the whole app at import time.
        self._clients: dict[str, Any] = {}

    # ------------------------------------------------------------------
    # Configuration helpers
    # ------------------------------------------------------------------
    def _resolved_specs(self, agent_name: str | None) -> tuple[dict, dict]:
        """Return (primary_spec, fallback_spec) merging defaults with overrides."""
        primary = dict(self._config["primary"])
        fallback = dict(self._config["fallback"])
        agent_overrides = (self._config.get("agents") or {}).get(agent_name or "", {})
        if "primary" in agent_overrides:
            primary.update(agent_overrides["primary"])
        if "fallback" in agent_overrides:
            fallback.update(agent_overrides["fallback"])
        return primary, fallback

    def _client_for(self, provider: str) -> Any:
        if provider not in self._clients:
            if provider == "anthropic":
                self._clients[provider] = AnthropicClient()
            elif provider == "openai":
                self._clients[provider] = OpenAIClient()
            else:
                raise ValueError(f"Unknown provider: {provider}")
        return self._clients[provider]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @traceable(run_type="llm", name="LLMRouter.generate")
    def generate(
        self,
        *,
        system: str,
        user: str,
        agent_name: str | None = None,
    ) -> LLMResult:
        """Generate text, falling back from primary to secondary on failure."""
        primary_spec, fallback_spec = self._resolved_specs(agent_name)
        attempts: list[dict[str, Any]] = []
        started = time.perf_counter()

        for idx, spec in enumerate((primary_spec, fallback_spec)):
            text, error = self._try_call(spec, system=system, user=user)
            attempts.append(
                {
                    "provider": spec["provider"],
                    "model": spec["model"],
                    "ok": error is None,
                    "error": error,
                }
            )
            if text and error is None:
                return LLMResult(
                    text=text,
                    model_used=spec["model"],
                    provider_used=spec["provider"],
                    fell_back=idx > 0,
                    latency_ms=int((time.perf_counter() - started) * 1000),
                    attempts=attempts,
                )

        raise RuntimeError(
            f"Both primary and fallback models failed. Attempts: {attempts}"
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _try_call(
        self,
        spec: dict[str, Any],
        *,
        system: str,
        user: str,
    ) -> tuple[str | None, str | None]:
        """Attempt one provider call. Returns (text, error_str)."""
        try:
            client = self._client_for(spec["provider"])
            text = client.complete(
                model=spec["model"],
                system=system,
                user=user,
                max_tokens=int(spec.get("max_tokens", 1500)),
                temperature=float(spec.get("temperature", 0.6)),
            )
            if not text or not text.strip():
                return None, "empty_output"
            return text, None
        except Exception as exc:  # noqa: BLE001 - we want to catch & fall back
            return None, f"{type(exc).__name__}: {exc}"


# ---------------------------------------------------------------------------
# Module-level singleton — most call sites just want the default config.
# ---------------------------------------------------------------------------
_default_router: LLMRouter | None = None


def get_router() -> LLMRouter:
    global _default_router
    if _default_router is None:
        _default_router = LLMRouter()
    return _default_router
