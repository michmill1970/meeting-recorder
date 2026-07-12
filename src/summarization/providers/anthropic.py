"""Anthropic LLM provider."""

from __future__ import annotations

import logging
from typing import Optional

import anthropic

from src.settings.manager import LLMGenerationSettings
from src.summarization.providers.base import BaseLLMClient

logger = logging.getLogger(__name__)


class AnthropicProvider(BaseLLMClient):
    """Anthropic Claude provider."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-20250514",
        generation_settings: Optional[LLMGenerationSettings] = None,
    ):
        super().__init__(generation_settings=generation_settings)
        self._api_key = api_key
        self._model = model
        self._client: Optional[anthropic.Anthropic] = None

    def _init_client(self) -> anthropic.Anthropic:
        """Initialize the Anthropic client."""
        return anthropic.Anthropic(api_key=self._api_key)

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
    ) -> Optional[str]:
        """Generate response using Anthropic API."""
        try:
            if self._client is None:
                self._client = self._init_client()

            messages = [{"role": "user", "content": prompt}]

            kwargs: dict = {
                "model": self._model,
                "messages": messages,
                **self._get_gen_params(),
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            response = await self._client.messages.create(**kwargs)

            content = response.content[0].text
            logger.info("Anthropic generation complete: %d characters", len(content or ""))
            return content

        except Exception as e:
            logger.error("Anthropic generation failed: %s", e)
            return None

    async def is_available(self) -> bool:
        """Check if provider is available."""
        if not self._api_key:
            return False
        try:
            if self._client is None:
                self._client = self._init_client()
            # Simple check - try listing models
            await self._client.models.list()
            return True
        except Exception:
            return False
