"""Thin wrapper around the OpenAI SDK so the router can call it uniformly."""
from __future__ import annotations

import os

from openai import OpenAI


class OpenAIClient:
    def __init__(self) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set")
        self._client = OpenAI(api_key=api_key)

    def complete(
        self,
        *,
        model: str,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float,
    ) -> str:
        response = self._client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (response.choices[0].message.content or "").strip()
