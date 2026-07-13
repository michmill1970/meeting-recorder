"""Ollama LLM provider."""

from __future__ import annotations

import logging
import asyncio
from typing import Optional

import requests

from src.settings.manager import LLMGenerationSettings
from src.summarization.providers.base import BaseLLMClient

logger = logging.getLogger(__name__)


class OllamaProvider(BaseLLMClient):
    """Ollama local LLM provider."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        generation_settings: Optional[LLMGenerationSettings] = None,
    ):
        super().__init__(generation_settings=generation_settings)
        self._base_url = base_url.rstrip("/")
        self._model = model

    def _get_gen_params(self, endpoint: str = "chat") -> dict:
        """Return generation params adapted for the specified Ollama endpoint.

        The native /api/generate endpoint supports: temperature, top_p, top_k,
        repeat_penalty, num_ctx, repeat_last_n.
        The /v1/chat/completions endpoint supports OpenAI-compatible params.
        """
        base = self._gen.to_dict()
        if endpoint == "generate":
            # Map OpenAI-style params to Ollama native params
            params = {"temperature": base.get("temperature", 0.3)}
            if base.get("top_p") is not None:
                params["top_p"] = base["top_p"]
            if base.get("top_k") is not None:
                params["top_k"] = base["top_k"]
            rep = base.get("repetition_penalty", 1.1)
            if rep != 1.0:
                params["repeat_penalty"] = rep
            # Ollama native endpoint does not support frequency/presence penalty
            return params
        return base

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
    ) -> Optional[str]:
        """Generate response using Ollama /api/generate endpoint."""
        try:
            if self.cancelled():
                raise asyncio.CancelledError("Summarization cancelled by user")

            url = f"{self._base_url}/api/generate"
            payload = {
                "model": self._model,
                "prompt": prompt,
                "stream": False,
                **self._get_gen_params(endpoint="generate"),
            }
            if system_prompt:
                payload["system"] = system_prompt

            response = requests.post(url, json=payload, timeout=300)

            if self.cancelled():
                raise asyncio.CancelledError("Summarization cancelled by user")

            response.raise_for_status()

            data = response.json()
            content = data.get("response", "")
            logger.info("Ollama generation complete: %d characters", len(content or ""))
            return content

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Ollama generation failed: %s", e)
            return None

    async def generate_chat(
        self,
        messages: list[dict[str, str]],
    ) -> Optional[str]:
        """Generate response using OpenAI-compatible /v1/chat/completions endpoint.

        Works with Ollama (v0.1.0+), llama.cpp server, and any OpenAI-compatible API.
        """
        try:
            if self.cancelled():
                raise asyncio.CancelledError("Summarization cancelled by user")

            url = f"{self._base_url}/v1/chat/completions"
            payload = {
                "model": self._model,
                "messages": messages,
                "stream": False,
                **self._get_gen_params(),
            }

            response = requests.post(url, json=payload, timeout=300)

            if self.cancelled():
                raise asyncio.CancelledError("Summarization cancelled by user")

            response.raise_for_status()

            data = response.json()
            content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            logger.info("OpenAI-compatible chat generation complete: %d characters", len(content or ""))
            return content

        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("OpenAI-compatible chat generation failed: %s", e)
            return None

    async def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            response = requests.get(f"{self._base_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
