"""Skill execution: assemble prompt and run through agent loop."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from genai_cli.agent import AgentLoop, AgentResult
from genai_cli.auth import AuthManager
from genai_cli.client import GenAIClient
from genai_cli.config import ConfigManager
from genai_cli.display import Display
from genai_cli.session import SessionManager
from genai_cli.skills.loader import SkillLoader
from genai_cli.skills.registry import SkillRegistry
from genai_cli.token_tracker import TokenTracker


class SkillExecutor:
    """Execute a skill by assembling prompt and running agent."""

    def __init__(
        self,
        config: ConfigManager,
        display: Display,
        registry: SkillRegistry,
    ) -> None:
        self._config = config
        self._display = display
        self._registry = registry
        self._loader = SkillLoader()

    def execute(
        self,
        skill_name: str,
        message: str = "",
        files: list[str] | None = None,
        model: str | None = None,
        auto_apply: bool = False,
        dry_run: bool = False,
        max_rounds: int = 5,
    ) -> AgentResult | None:
        """Execute a skill by name."""
        # Find skill
        meta = self._registry.get_skill(skill_name)
        if meta is None:
            self._display.print_error(f"Skill not found: {skill_name}")
            return None

        if meta.source_path is None:
            self._display.print_error(f"Skill has no source: {skill_name}")
            return None

        # Load full skill content
        content = self._loader.load_full(meta.source_path)
        if content is None:
            self._display.print_error(f"Failed to load skill: {skill_name}")
            return None

        self._display.print_info(f"Invoking skill: {meta.name}")
        self._display.print_info(f"  {meta.description[:80]}")

        # Build prompt components
        system_prompt = self._config.get_system_prompt()
        agents_md = self._registry.find_agents_md()
        skill_prompt = content.body

        # Include references in skill prompt if any
        if content.references:
            ref_texts = []
            for ref_name, ref_content in content.references.items():
                ref_texts.append(f"\n## Reference: {ref_name}\n{ref_content}")
            skill_prompt += "\n".join(ref_texts)

        # Use auto_apply from skill metadata if not overridden
        effective_auto_apply = auto_apply or meta.auto_apply

        # Set up agent
        model_name = model or self._config.settings.default_model
        auth = AuthManager()
        client = GenAIClient(self._config, auth)
        tracker = TokenTracker(self._config)
        session_mgr = SessionManager(self._config)
        session = session_mgr.create_session(model_name)

        # Build full system context
        full_system = system_prompt
        if agents_md:
            full_system += f"\n\n{agents_md}"

        agent = AgentLoop(
            self._config,
            client,
            self._display,
            tracker,
            session,
            auto_apply=effective_auto_apply,
            dry_run=dry_run,
            max_rounds=max_rounds,
        )

        # User message defaults to skill name if not provided
        user_message = message or f"Execute the {skill_name} skill on the provided files."

        result = agent.run(
            user_message,
            model_name,
            files=files,
            system_prompt=full_system,
            skill_prompt=skill_prompt,
        )

        client.close()
        return result
