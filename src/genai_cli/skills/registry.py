"""Skill discovery and registry."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from genai_cli.config import ConfigManager
from genai_cli.skills.loader import SkillLoader, SkillMetadata


class SkillRegistry:
    """Discover and index available skills from 3 locations.

    Priority (highest first):
      1. Project: .genai-cli/skills/
      2. User: ~/.genai-cli/skills/
      3. Bundled: <package>/skills/
    """

    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self._loader = SkillLoader()
        self._skills: dict[str, SkillMetadata] = {}
        self._discover()

    def _discover(self) -> None:
        """Scan all skill directories."""
        locations = self._get_skill_dirs()
        # Process in reverse priority order so higher priority overwrites
        for location in reversed(locations):
            if not location.is_dir():
                continue
            for skill_dir in sorted(location.iterdir()):
                skill_file = skill_dir / "SKILL.md"
                if skill_file.is_file():
                    meta = self._loader.load_metadata(skill_file)
                    if meta:
                        self._skills[meta.name] = meta

    def _get_skill_dirs(self) -> list[Path]:
        """Return skill directories in priority order (highest first)."""
        dirs: list[Path] = []

        # 1. Project skills
        project = Path.cwd() / ".genai-cli" / "skills"
        dirs.append(project)

        # 2. User skills
        user = Path.home() / ".genai-cli" / "skills"
        dirs.append(user)

        # 3. Bundled skills
        bundled = Path(__file__).resolve().parent.parent.parent.parent / "skills"
        dirs.append(bundled)

        return dirs

    def get_skill(self, name: str) -> SkillMetadata | None:
        """Get a skill by name."""
        return self._skills.get(name)

    def list_skills(self) -> list[SkillMetadata]:
        """List all discovered skills."""
        return sorted(self._skills.values(), key=lambda s: s.name)

    def find_agents_md(self, start_dir: Path | None = None) -> str | None:
        """Walk up directory tree to find nearest agents.md."""
        current = start_dir or Path.cwd()
        current = current.resolve()
        root = Path(current.anchor)

        while current != root:
            agents_file = current / "agents.md"
            if agents_file.is_file():
                return agents_file.read_text()
            agents_file = current / "AGENTS.md"
            if agents_file.is_file():
                return agents_file.read_text()
            current = current.parent

        return None
