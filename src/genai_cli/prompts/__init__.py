"""Prompt system: loader, registry."""

from genai_cli.prompts.loader import PromptLoader, PromptMetadata, PromptContent
from genai_cli.prompts.registry import PromptRegistry

__all__ = ["PromptLoader", "PromptMetadata", "PromptContent", "PromptRegistry"]
