"""SKILL.md parser with tiered loading."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class SkillMetadata:
    """Tier 1: skill metadata (~100 tokens)."""

    name: str
    description: str
    author: str = ""
    version: str = ""
    category: str = ""
    auto_apply: bool = False
    source_path: Path | None = None


@dataclass
class SkillContent:
    """Full skill data (Tier 1 + Tier 2)."""

    metadata: SkillMetadata
    body: str = ""
    references: dict[str, str] = field(default_factory=dict)


class SkillLoader:
    """Parse SKILL.md files with YAML frontmatter."""

    _FRONTMATTER_PATTERN = re.compile(
        r"^---\s*\n(.*?)\n---\s*\n(.*)",
        re.DOTALL,
    )

    def load_metadata(self, path: Path) -> SkillMetadata | None:
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

        return SkillMetadata(
            name=frontmatter.get("name", path.parent.name),
            description=frontmatter.get("description", ""),
            author=meta.get("author", ""),
            version=meta.get("version", ""),
            category=meta.get("category", ""),
            auto_apply=frontmatter.get("auto_apply", False),
            source_path=path,
        )

    def load_full(self, path: Path) -> SkillContent | None:
        """Tier 2: Load full skill (frontmatter + body)."""
        metadata = self.load_metadata(path)
        if metadata is None:
            return None

        text = path.read_text()
        match = self._FRONTMATTER_PATTERN.match(text)
        if not match:
            return None

        body = match.group(2).strip()

        # Tier 3: Load references if present
        references: dict[str, str] = {}
        refs_dir = path.parent / "references"
        if refs_dir.is_dir():
            for ref_file in refs_dir.iterdir():
                if ref_file.is_file():
                    references[ref_file.name] = ref_file.read_text()

        return SkillContent(
            metadata=metadata,
            body=body,
            references=references,
        )
