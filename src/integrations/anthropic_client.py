"""Thin wrapper around the Anthropic SDK so the router can call it uniformly."""
from __future__ import annotations

import os
from typing import Any

from anthropic import Anthropic


class AnthropicClient:
    def __init__(self) -> None:
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")
        self._client = Anthropic(api_key=api_key)

    def complete(
        self,
        *,
        model: str,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        response = self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        # Concatenate all text blocks (messages API returns a list of content blocks).
        parts: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if text:
                parts.append(text)
        return "".join(parts).strip()
