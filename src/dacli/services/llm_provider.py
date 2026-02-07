"""LLM provider abstraction for the experimental ask feature.

Supports two providers:
- Claude Code CLI (subprocess): uses the `claude` binary
- Anthropic API (SDK): uses the `anthropic` Python package

Auto-detection tries Claude Code first, then Anthropic API.
"""

import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Lazy import for anthropic SDK
anthropic = None


def _ensure_anthropic():
    """Lazy-import the anthropic SDK."""
    global anthropic
    if anthropic is None:
        try:
            import anthropic as _anthropic

            anthropic = _anthropic
        except ImportError:
            raise RuntimeError(
                "The 'anthropic' package is required for the Anthropic API provider. "
                "Install it with: uv add anthropic  or  pip install anthropic"
            )
    return anthropic


@dataclass
class LLMResponse:
    """Response from an LLM provider."""

    text: str
    provider: str
    model: str | None = None


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name identifier."""

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available for use."""

    @abstractmethod
    def ask(self, system_prompt: str, user_message: str) -> LLMResponse:
        """Send a question to the LLM and return the response.

        Args:
            system_prompt: System instructions for the LLM.
            user_message: The user's question with context.

        Returns:
            LLMResponse with the answer text.

        Raises:
            RuntimeError: If the provider call fails.
        """


class ClaudeCodeProvider(LLMProvider):
    """LLM provider using Claude Code CLI (subprocess)."""

    @property
    def name(self) -> str:
        return "claude-code"

    def is_available(self) -> bool:
        return shutil.which("claude") is not None

    def ask(self, system_prompt: str, user_message: str) -> LLMResponse:
        prompt = f"{system_prompt}\n\n{user_message}"
        try:
            result = subprocess.run(
                ["claude", "-p", prompt, "--output-format", "text"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Claude Code CLI failed (exit {result.returncode}): {result.stderr}"
                )
            return LLMResponse(
                text=result.stdout.strip(),
                provider=self.name,
                model=None,
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("Claude Code CLI timed out after 120 seconds")
        except FileNotFoundError:
            raise RuntimeError("Claude Code CLI binary not found")


class AnthropicAPIProvider(LLMProvider):
    """LLM provider using the Anthropic Python SDK."""

    @property
    def name(self) -> str:
        return "anthropic-api"

    def is_available(self) -> bool:
        return bool(os.environ.get("ANTHROPIC_API_KEY"))

    def ask(self, system_prompt: str, user_message: str) -> LLMResponse:
        _ensure_anthropic()
        client = anthropic.Anthropic()
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1024,
            system=system_prompt,
            messages=[{"role": "user", "content": user_message}],
        )
        return LLMResponse(
            text=message.content[0].text,
            provider=self.name,
            model=message.model,
        )


_PROVIDERS = {
    "claude-code": ClaudeCodeProvider,
    "anthropic-api": AnthropicAPIProvider,
}

_AUTO_DETECT_ORDER = ["claude-code", "anthropic-api"]


def get_provider(preferred: str | None = None) -> LLMProvider:
    """Get an LLM provider, either by name or auto-detection.

    Args:
        preferred: Provider name to use. If None, auto-detects.

    Returns:
        An available LLMProvider instance.

    Raises:
        RuntimeError: If the requested or any provider is not available.
    """
    if preferred is not None:
        cls = _PROVIDERS.get(preferred)
        if cls is None:
            available = ", ".join(_PROVIDERS.keys())
            raise RuntimeError(
                f"Unknown provider '{preferred}'. Available: {available}"
            )
        provider = cls()
        if not provider.is_available():
            raise RuntimeError(f"Provider '{preferred}' is not available")
        return provider

    # Auto-detect
    for name in _AUTO_DETECT_ORDER:
        provider = _PROVIDERS[name]()
        if provider.is_available():
            return provider

    raise RuntimeError(
        "No LLM provider available. Install Claude Code CLI or set ANTHROPIC_API_KEY."
    )
