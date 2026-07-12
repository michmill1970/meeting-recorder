"""LLM summarization client.

Factory pattern for creating provider-specific clients based on settings.
"""

from __future__ import annotations

import logging
from typing import Optional

from src.models.schemas import LLMProvider, SummarizationStyle
from src.settings.manager import LLMSettings, Settings
from src.summarization.providers.anthropic import AnthropicProvider
from src.summarization.providers.base import BaseLLMClient
from src.summarization.providers.lm_studio import LMStudioProvider
from src.summarization.providers.ollama import OllamaProvider
from src.summarization.providers.openai import OpenAIProvider
from src.summarization.providers.vllm import VLLMProvider

logger = logging.getLogger(__name__)


class LLMClient:
    """High-level LLM client that delegates to provider-specific implementations."""

    # Style-specific system prompts
    _STYLE_PROMPTS = {
        SummarizationStyle.CONCISE: (
            "You are a meeting assistant. Produce a brief, high-level summary of this meeting."
            " Include only the most important points, decisions, and action items."
            " Keep it under 200 words. Use bullet points."
        ),
        SummarizationStyle.NORMAL: (
            "You are a professional meeting assistant. Analyze this transcript and produce a"
            " clear, structured summary with the sections below. Be thorough but concise."
        ),
        SummarizationStyle.DETAILED: (
            "You are a professional meeting assistant. Analyze this transcript thoroughly and"
            " produce a comprehensive, well-structured summary. Capture every discussion topic,"
            " decision, and point of consensus or disagreement. For each topic, include the key"
            " arguments made, the outcome or status, and any relevant details. Do not omit"
            " substantive content — prioritize completeness and accuracy."
        ),
    }

    def __init__(self, settings: Settings):
        self._settings = settings
        self._provider: Optional[BaseLLMClient] = None

    def _get_provider(self) -> BaseLLMClient:
        """Get or create the provider instance."""
        if self._provider is not None:
            return self._provider

        cfg = self._settings.llm
        gen = cfg.generation
        provider_map = {
            LLMProvider.OPENAI: lambda: OpenAIProvider(
                api_key=cfg.api_key,
                base_url=cfg.base_url,
                model=cfg.model,
                generation_settings=gen,
            ),
            LLMProvider.ANTHROPIC: lambda: AnthropicProvider(
                api_key=cfg.api_key,
                model=cfg.model,
                generation_settings=gen,
            ),
            LLMProvider.OLLAMA: lambda: OllamaProvider(
                base_url=cfg.base_url or "http://localhost:11434",
                model=cfg.model,
                generation_settings=gen,
            ),
            LLMProvider.LM_STUDIO: lambda: LMStudioProvider(
                base_url=cfg.base_url or "http://localhost:1234/v1",
                model=cfg.model,
                generation_settings=gen,
            ),
            LLMProvider.VLLM: lambda: VLLMProvider(
                base_url=cfg.base_url or "http://localhost:8000/v1",
                model=cfg.model,
                generation_settings=gen,
            ),
        }

        factory = provider_map.get(cfg.provider)
        if factory is None:
            raise ValueError(f"Unknown LLM provider: {cfg.provider}")

        self._provider = factory()  # type: ignore[assignment]
        assert self._provider is not None
        return self._provider

    _DEFAULT_USER_INSTRUCTIONS = (
        "Provide your response in markdown format with these sections:\n"
        "1. **Summary** — Overview of key discussion points and decisions\n"
        "2. **Action Items** — Specific tasks assigned during the meeting\n"
        "3. **Assignments** — Who is responsible for what\n"
        "4. **Follow-up Dates** — Any dates, deadlines, or scheduling mentioned"
    )

    async def summarize(
        self,
        transcript: str,
    ) -> Optional[str]:
        """Summarize a meeting transcript.

        Args:
            transcript: The full meeting transcript text

        Returns:
            Markdown summary text, or None if summarization failed
        """
        provider = self._get_provider()
        cfg = self._settings.llm
        style = cfg.summarization_style

        if style == SummarizationStyle.CUSTOM and cfg.custom_prompt:
            # Custom prompt: the entire prompt is user-defined
            if cfg.use_chat_api:
                system_msg = cfg.custom_prompt.replace("{transcript}", transcript)
                messages = [{"role": "system", "content": system_msg}]
                return await provider.generate_chat(messages)
            else:
                user_prompt = cfg.custom_prompt.replace("{transcript}", transcript)
                return await provider.generate(prompt=user_prompt)
        else:
            # Built-in style
            system_prompt = self._STYLE_PROMPTS.get(style, self._STYLE_PROMPTS[SummarizationStyle.NORMAL])
            user_prompt = f"""Please analyze the following meeting transcript and provide a summary.

{self._DEFAULT_USER_INSTRUCTIONS}

MEETING TRANSCRIPT:
{transcript}"""
            if cfg.use_chat_api:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ]
                return await provider.generate_chat(messages)
            else:
                return await provider.generate(
                    prompt=user_prompt,
                    system_prompt=system_prompt,
                )

    async def is_available(self) -> bool:
        """Check if the configured LLM provider is available."""
        try:
            provider = self._get_provider()
            return await provider.is_available()
        except Exception as e:
            logger.warning("LLM availability check failed: %s", e)
            return False
