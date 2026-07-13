"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from src.settings.manager import LLMGenerationSettings


class BaseLLMClient(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, generation_settings: Optional[LLMGenerationSettings] = None):
        """Initialize with optional generation parameter overrides.

        Args:
            generation_settings: Advanced LLM parameters (temperature, top_p, etc.)
        """
        self._gen = generation_settings or LLMGenerationSettings()
        self._cancelled = False

    def _get_gen_params(self) -> dict[str, Any]:
        """Extract generation parameters as a dict for API calls."""
        return self._gen.to_dict()

    def cancel(self) -> None:
        """Cancel the current generation."""
        self._cancelled = True

    def cancelled(self) -> bool:
        """Check if the current operation has been cancelled."""
        return self._cancelled

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str = "",
    ) -> Optional[str]:
        """Generate a response from the LLM.

        Args:
            prompt: The user prompt
            system_prompt: Optional system/instruction prompt

        Returns:
            Generated text, or None if generation failed
        """
        ...

    async def generate_chat(
        self,
        messages: list[dict[str, str]],
    ) -> Optional[str]:
        """Generate a response using a chat message list.

        Default implementation delegates to generate(). Providers that
        natively support chat (e.g. Ollama /api/chat) can override.

        Args:
            messages: List of {"role": ..., "content": ...} dicts

        Returns:
            Generated text, or None if generation failed
        """
        system_prompt = ""
        prompt = ""
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                system_prompt = content
            elif role == "user":
                prompt = content
        return await self.generate(prompt=prompt, system_prompt=system_prompt)

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the LLM provider is available and configured."""
        ...
