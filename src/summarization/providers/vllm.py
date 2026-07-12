"""vLLM LLM provider.

vLLM exposes an OpenAI-compatible API on localhost:8000 by default.
"""

from __future__ import annotations

import logging
from typing import Optional

import requests

from src.settings.manager import LLMGenerationSettings
from src.summarization.providers.base import BaseLLMClient

logger = logging.getLogger(__name__)


class VLLMProvider(BaseLLMClient):
    """vLLM local LLM provider."""

    def __init__(
        self,
        base_url: str = "http://localhost:8000/v1",
        model: str = "",
        generation_settings: Optional[LLMGenerationSettings] = None,
    ):
        super().__init__(generation_settings=generation_settings)
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
    ) -> Optional[str]:
        """Generate response using vLLM API (OpenAI-compatible)."""
        try:
            url = f"{self._base_url}/chat/completions"
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self._model,
                "messages": messages,
                **self._get_gen_params(),
            }

            response = requests.post(url, json=payload, timeout=300)
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.info("vLLM generation complete: %d characters", len(content or ""))
            return content

        except Exception as e:
            logger.error("vLLM generation failed: %s", e)
            return None

    async def is_available(self) -> bool:
        """Check if vLLM is available."""
        try:
            response = requests.get(f"{self._base_url}/models", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
