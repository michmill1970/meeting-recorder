"""Unit tests for LLM providers and summarization client."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.models.schemas import LLMProvider, RecordingSession
from src.settings.manager import Settings
from src.summarization.llm_client import LLMClient
from src.summarization.providers.anthropic import AnthropicProvider
from src.summarization.providers.base import BaseLLMClient
from src.summarization.providers.lm_studio import LMStudioProvider
from src.summarization.providers.ollama import OllamaProvider
from src.summarization.providers.openai import OpenAIProvider
from src.summarization.providers.vllm import VLLMProvider


class TestBaseLLMClient:
    """Tests for BaseLLMClient abstract class."""

    def test_is_abstract(self) -> None:
        """BaseLLMClient should not be instantiable directly."""
        with pytest.raises(TypeError):
            BaseLLMClient()  # type: ignore[abstract]


class TestOpenAIProvider:
    """Tests for OpenAIProvider."""

    def test_initialization(self) -> None:
        provider = OpenAIProvider(api_key="test_key", model="gpt-4o")
        assert provider._api_key == "test_key"
        assert provider._model == "gpt-4o"
        assert provider._base_url == ""

    def test_initialization_with_base_url(self) -> None:
        provider = OpenAIProvider(
            api_key="test_key",
            base_url="http://localhost:1234/v1",
            model="llama3",
        )
        assert provider._base_url == "http://localhost:1234/v1"

    @pytest.mark.asyncio
    async def test_is_available_no_key(self) -> None:
        provider = OpenAIProvider(api_key="")
        assert await provider.is_available() is False

    @pytest.mark.asyncio
    async def test_is_available_with_key(self) -> None:
        """Test availability check with mocked client."""
        with patch("src.summarization.providers.openai.AsyncOpenAI") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client

            provider = OpenAIProvider(api_key="test_key")
            result = await provider.is_available()
            assert result is True


class TestAnthropicProvider:
    """Tests for AnthropicProvider."""

    def test_initialization(self) -> None:
        provider = AnthropicProvider(api_key="test_key", model="claude-sonnet-4-20250514")
        assert provider._api_key == "test_key"
        assert provider._model == "claude-sonnet-4-20250514"

    @pytest.mark.asyncio
    async def test_is_available_no_key(self) -> None:
        provider = AnthropicProvider(api_key="")
        assert await provider.is_available() is False


class TestOllamaProvider:
    """Tests for OllamaProvider."""

    def test_initialization(self) -> None:
        provider = OllamaProvider()
        assert provider._base_url == "http://localhost:11434"
        assert provider._model == "llama3"

    def test_initialization_custom_url(self) -> None:
        provider = OllamaProvider(
            base_url="http://custom:11434",
            model="mistral",
        )
        assert provider._base_url == "http://custom:11434"
        assert provider._model == "mistral"

    @pytest.mark.asyncio
    async def test_is_available_offline(self) -> None:
        """Test availability when Ollama is not running."""
        provider = OllamaProvider()
        result = await provider.is_available()
        # Should return False if Ollama is not running
        assert result is False


class TestLMStudioProvider:
    """Tests for LMStudioProvider."""

    def test_initialization(self) -> None:
        provider = LMStudioProvider()
        assert provider._base_url == "http://localhost:1234/v1"

    def test_initialization_custom_model(self) -> None:
        provider = LMStudioProvider(model="custom-model")
        assert provider._model == "custom-model"

    @pytest.mark.asyncio
    async def test_is_available_offline(self) -> None:
        """Test availability when LM Studio is not running."""
        provider = LMStudioProvider()
        result = await provider.is_available()
        assert result is False


class TestVLLMProvider:
    """Tests for VLLMProvider."""

    def test_initialization(self) -> None:
        provider = VLLMProvider()
        assert provider._base_url == "http://localhost:8000/v1"

    @pytest.mark.asyncio
    async def test_is_available_offline(self) -> None:
        """Test availability when vLLM is not running."""
        provider = VLLMProvider()
        result = await provider.is_available()
        assert result is False


class TestLLMClient:
    """Tests for high-level LLMClient."""

    def test_initialization(self) -> None:
        settings = Settings()
        client = LLMClient(settings)
        assert client._settings == settings
        assert client._provider is None

    def test_get_provider_openai(self) -> None:
        settings = Settings()
        settings.llm.provider = LLMProvider.OPENAI
        settings.llm.api_key = "test_key"
        client = LLMClient(settings)
        provider = client._get_provider()
        assert isinstance(provider, OpenAIProvider)

    def test_get_provider_ollama(self) -> None:
        settings = Settings()
        settings.llm.provider = LLMProvider.OLLAMA
        client = LLMClient(settings)
        provider = client._get_provider()
        assert isinstance(provider, OllamaProvider)

    def test_get_provider_anthropic(self) -> None:
        settings = Settings()
        settings.llm.provider = LLMProvider.ANTHROPIC
        settings.llm.api_key = "test_key"
        client = LLMClient(settings)
        provider = client._get_provider()
        assert isinstance(provider, AnthropicProvider)

    def test_get_provider_lm_studio(self) -> None:
        settings = Settings()
        settings.llm.provider = LLMProvider.LM_STUDIO
        client = LLMClient(settings)
        provider = client._get_provider()
        assert isinstance(provider, LMStudioProvider)

    def test_get_provider_vllm(self) -> None:
        settings = Settings()
        settings.llm.provider = LLMProvider.VLLM
        client = LLMClient(settings)
        provider = client._get_provider()
        assert isinstance(provider, VLLMProvider)

    def test_get_provider_caches_instance(self) -> None:
        """Provider should be cached after first creation."""
        settings = Settings()
        settings.llm.provider = LLMProvider.OPENAI
        settings.llm.api_key = "test_key"
        client = LLMClient(settings)
        provider1 = client._get_provider()
        provider2 = client._get_provider()
        assert provider1 is provider2

    def test_system_prompt_exists(self) -> None:
        """System prompt should be defined."""
        assert LLMClient._DEFAULT_USER_INSTRUCTIONS != ""
        assert "Summary" in LLMClient._DEFAULT_USER_INSTRUCTIONS
        assert "Action Items" in LLMClient._DEFAULT_USER_INSTRUCTIONS

    @pytest.mark.asyncio
    async def test_is_available_false_when_no_key(self) -> None:
        settings = Settings()
        settings.llm.provider = LLMProvider.OPENAI
        settings.llm.api_key = ""
        client = LLMClient(settings)
        result = await client.is_available()
        assert result is False
