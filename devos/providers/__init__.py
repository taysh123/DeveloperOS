"""Pluggable provider abstractions (AI, and later embeddings/git/etc.)."""
from devos.providers.ai import AIProvider, AIResult, MockAIProvider, get_provider

__all__ = ["AIProvider", "AIResult", "MockAIProvider", "get_provider"]
