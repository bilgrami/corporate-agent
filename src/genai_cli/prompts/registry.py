"""Prompt discovery and registry."""

from __future__ import annotations

from pathlib import Path

from genai_cli.config import ConfigManager
from genai_cli.prompts.loader import PromptLoader, PromptMetadata


class PromptRegistry:
    """Discover and index available prompts from 3 locations.

    Priority (highest first):
      1. Project: .genai-cli/prompts/
      2. User: ~/.genai-cli/prompts/
      3. Bundled: <package>/prompts/
    """

    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self._loader = PromptLoader()
        self._prompts: dict[str, PromptMetadata] = {}
        self._discover()

    def _discover(self) -> None:
        """Scan all prompt directories."""
        locations = self._get_prompt_dirs()
        # Process in reverse priority order so higher priority overwrites
        for location in reversed(locations):
            if not location.is_dir():
                continue
            for prompt_dir in sorted(location.iterdir()):
                prompt_file = prompt_dir / "PROMPT.md"
                if prompt_file.is_file():
                    meta = self._loader.load_metadata(prompt_file)
                    if meta:
                        self._prompts[meta.name] = meta

    def _get_prompt_dirs(self) -> list[Path]:
        """Return prompt directories in priority order (highest first)."""
        dirs: list[Path] = []

        # 1. Project prompts
        project = Path.cwd() / ".genai-cli" / "prompts"
        dirs.append(project)

        # 2. User prompts
        user = Path.home() / ".genai-cli" / "prompts"
        dirs.append(user)

        # 3. Bundled prompts
        bundled = Path(__file__).resolve().parent.parent.parent.parent / "prompts"
        dirs.append(bundled)

        return dirs

    def get_prompt(self, name: str) -> PromptMetadata | None:
        """Get a prompt by name."""
        return self._prompts.get(name)

    def list_prompts(self) -> list[PromptMetadata]:
        """List all discovered prompts."""
        return sorted(self._prompts.values(), key=lambda p: p.name)

    def load_prompt_body(self, name: str, agent_name: str = "") -> str | None:
        """Load prompt body and substitute {agent_name}."""
        meta = self._prompts.get(name)
        if meta is None or meta.source_path is None:
            return None

        content = self._loader.load_full(meta.source_path)
        if content is None:
            return None

        body = content.body
        if agent_name:
            body = body.replace("{agent_name}", agent_name)
        return body
