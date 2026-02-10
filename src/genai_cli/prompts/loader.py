"""PROMPT.md parser with tiered loading."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass
class PromptMetadata:
    """Tier 1: prompt metadata (~100 tokens)."""

    name: str
    description: str
    author: str = ""
    version: str = ""
    category: str = ""
    source_path: Path | None = None


@dataclass
class PromptContent:
    """Full prompt data (Tier 1 + Tier 2)."""

    metadata: PromptMetadata
    body: str = ""


class PromptLoader:
    """Parse PROMPT.md files with YAML frontmatter."""

    _FRONTMATTER_PATTERN = re.compile(
        r"^---\s*\n(.*?)\n---\s*\n(.*)",
        re.DOTALL,
    )

    def load_metadata(self, path: Path) -> PromptMetadata | None:
        """Tier 1: Load only frontmatter metadata (~100 tokens)."""
        if not path.is_file():
            return None

        text = path.read_text()
        match = self._FRONTMATTER_PATTERN.match(text)
        if not match:
            return None

        try:
            frontmatter = yaml.safe_load(match.group(1))
        except yaml.YAMLError:
            return None

        if not isinstance(frontmatter, dict):
            return None

        meta = frontmatter.get("metadata", {}) or {}

        return PromptMetadata(
            name=frontmatter.get("name", path.parent.name),
            description=frontmatter.get("description", ""),
            author=meta.get("author", ""),
            version=meta.get("version", ""),
            category=meta.get("category", ""),
            source_path=path,
        )

    def load_full(self, path: Path) -> PromptContent | None:
        """Tier 2: Load full prompt (frontmatter + body)."""
        metadata = self.load_metadata(path)
        if metadata is None:
            return None

        text = path.read_text()
        match = self._FRONTMATTER_PATTERN.match(text)
        if not match:
            return None

        body = match.group(2).strip()

        return PromptContent(
            metadata=metadata,
            body=body,
        )
