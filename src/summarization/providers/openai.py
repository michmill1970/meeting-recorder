"""OpenAI-compatible LLM provider.

Works with OpenAI API, LM Studio, and vLLM (all use OpenAI-compatible endpoints).
"""

from __future__ import annotations

import logging
import asyncio
from typing import Optional

from openai import AsyncOpenAI

from src.settings.manager import LLMGenerationSettings
from src.summarization.providers.base import BaseLLMClient

logger = logging.getLogger(__name__)


class OpenAIProvider(BaseLLMClient):
    """OpenAI-compatible LLM provider."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "",
        model: str = "gpt-4o",
        generation_settings: Optional[LLMGenerationSettings] = None,
    ):
        super().__init__(generation_settings=generation_settings)
        self._api_key = api_key
        self._base_url = base_url
        self._model = model
        self._client: Optional[AsyncOpenAI] = None

    def _init_client(self) -> AsyncOpenAI:
        """Initialize the OpenAI client."""
        kwargs = {
            "api_key": self._api_key or "sk-no-key-required",
        }
        if self._base_url:
            kwargs["base_url"] = self._base_url
        return AsyncOpenAI(**kwargs)

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
    ) -> Optional[str]:
        """Generate response using OpenAI-compatible API."""
        try:
            if self.cancelled():
                raise asyncio.CancelledError("Summarization cancelled by user")

            if self._client is None:
                self._client = self._init_client()

            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            gen_params = self._get_gen_params()
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                **gen_params,
            )

            if self.cancelled():
                raise asyncio.CancelledError("Summarization cancelled by user")

            content = response.choices[0].message.content
            logger.info("OpenAI generation complete: %d characters", len(content or ""))
            return content

        except Exception as e:
            logger.error("OpenAI generation failed: %s", e)
            return None

    async def is_available(self) -> bool:
        """Check if provider is available."""
        try:
            if self._client is None:
                self._client = self._init_client()
            await self._client.models.list()
            return True
        except Exception:
            return False
