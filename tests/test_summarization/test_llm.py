"""Unit tests for LLM providers and summarization client."""

import asyncio
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
        """Test availability check with empty API key."""
        with patch("src.summarization.providers.openai.AsyncOpenAI") as mock_client_class:
            mock_client_class.side_effect = Exception("No API key")
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
        """Test availability check with empty API key."""
        with patch("anthropic.Anthropic") as mock_client_class:
            mock_client_class.side_effect = Exception("No API key")
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
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
            provider = OllamaProvider()
            result = await provider.is_available()
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
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
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
        with patch("requests.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")
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
        """Test that LLMClient returns False when no API key is configured."""
        with patch("src.summarization.providers.openai.AsyncOpenAI") as mock_client_class:
            mock_client_class.side_effect = Exception("No API key")
            settings = Settings()
            settings.llm.provider = LLMProvider.OPENAI
            settings.llm.api_key = ""
            client = LLMClient(settings)
            result = await client.is_available()
            assert result is False


class TestBaseLLMClientCancel:
    """Tests for BaseLLMClient cancellation support."""

    def test_cancelled_initially_false(self) -> None:
        """cancelled() should return False when not cancelled."""
        with patch("src.summarization.providers.openai.AsyncOpenAI"):
            provider = OpenAIProvider(api_key="test_key", model="gpt-4o")
            assert provider.cancelled() is False

    def test_cancel_sets_flag(self) -> None:
        """cancel() should set _cancelled to True."""
        with patch("src.summarization.providers.openai.AsyncOpenAI"):
            provider = OpenAIProvider(api_key="test_key", model="gpt-4o")
            provider.cancel()
            assert provider.cancelled() is True


class TestOllamaProviderCancel:
    """Tests for OllamaProvider cancellation."""

    @pytest.mark.asyncio
    async def test_generate_raises_cancelled_when_cancelled_before_request(self) -> None:
        """generate() should raise CancelledError if cancelled before API call."""
        provider = OllamaProvider()
        provider.cancel()
        with pytest.raises(asyncio.CancelledError) as exc_info:
            await provider.generate("test prompt")
        assert "cancelled" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_raises_cancelled_when_cancelled_after_response(self) -> None:
        """generate() should raise CancelledError if cancelled after API response."""
        mock_response = MagicMock()
        mock_response.json.return_value = {"response": "test content"}
        mock_response.raise_for_status = MagicMock()

        provider = OllamaProvider()
        with patch("requests.post", return_value=mock_response):
            provider.cancel()
            with pytest.raises(asyncio.CancelledError) as exc_info:
                await provider.generate("test prompt")
            assert "cancelled" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_generate_chat_raises_cancelled_before_request(self) -> None:
        """generate_chat() should raise CancelledError if cancelled before API call."""
        provider = OllamaProvider()
        provider.cancel()
        with pytest.raises(asyncio.CancelledError) as exc_info:
            await provider.generate_chat([{"role": "user", "content": "hello"}])
        assert "cancelled" in str(exc_info.value).lower()


class TestLMStudioProviderCancel:
    """Tests for LMStudioProvider cancellation."""

    @pytest.mark.asyncio
    async def test_generate_raises_cancelled_when_cancelled(self) -> None:
        """generate() should raise CancelledError if cancelled."""
        provider = LMStudioProvider()
        provider.cancel()
        with pytest.raises(asyncio.CancelledError) as exc_info:
            await provider.generate("test prompt")
        assert "cancelled" in str(exc_info.value).lower()


class TestVLLMProviderCancel:
    """Tests for VLLMProvider cancellation."""

    @pytest.mark.asyncio
    async def test_generate_raises_cancelled_when_cancelled(self) -> None:
        """generate() should raise CancelledError if cancelled."""
        provider = VLLMProvider()
        provider.cancel()
        with pytest.raises(asyncio.CancelledError) as exc_info:
            await provider.generate("test prompt")
        assert "cancelled" in str(exc_info.value).lower()


class TestLLMClientCancel:
    """Tests for LLMClient cancellation."""

    def test_cancel_no_provider(self) -> None:
        """cancel() should not crash when no provider is created."""
        settings = Settings()
        client = LLMClient(settings)
        # Should not raise
        client.cancel()

    def test_cancel_delegates_to_provider(self) -> None:
        """cancel() should delegate to the provider."""
        with patch("src.summarization.providers.openai.AsyncOpenAI"):
            settings = Settings()
            settings.llm.provider = LLMProvider.OPENAI
            settings.llm.api_key = "test_key"
            client = LLMClient(settings)
            # Force provider creation
            client._get_provider()
            # Now cancel
            client.cancel()
            assert client._provider.cancelled() is True
