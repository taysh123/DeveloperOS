"""Pluggable provider abstractions (AI, and later embeddings/git/etc.)."""
from devos.providers.ai import AIProvider, AIResult, MockAIProvider, get_provider
from devos.providers.ollama import OllamaProvider  # registers "ollama" on import

__all__ = ["AIProvider", "AIResult", "MockAIProvider", "OllamaProvider", "get_provider"]
