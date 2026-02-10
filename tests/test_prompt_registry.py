"""Tests for prompt registry module."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
import yaml

from genai_cli.config import ConfigManager
from genai_cli.prompts.registry import PromptRegistry


@pytest.fixture
def registry_config(tmp_path: Path) -> ConfigManager:
    settings = {
        "api_base_url": "https://api.test.com",
        "agent_name": "test-agent",
    }
    p = tmp_path / "settings.yaml"
    p.write_text(yaml.dump(settings))
    return ConfigManager(config_path=str(p))


class TestPromptRegistry:
    def test_discovers_bundled_prompts(
        self, registry_config: ConfigManager
    ) -> None:
        registry = PromptRegistry(registry_config)
        prompts = registry.list_prompts()
        names = [p.name for p in prompts]
        assert "default" in names
        assert "code-changes" in names
        assert "reviewer" in names
        assert "planner" in names
        assert "minimal" in names

    def test_discovers_all_10_prompts(
        self, registry_config: ConfigManager
    ) -> None:
        registry = PromptRegistry(registry_config)
        prompts = registry.list_prompts()
        assert len(prompts) == 10

    def test_get_prompt(self, registry_config: ConfigManager) -> None:
        registry = PromptRegistry(registry_config)
        prompt = registry.get_prompt("default")
        assert prompt is not None
        assert prompt.name == "default"

    def test_get_nonexistent_prompt(
        self, registry_config: ConfigManager
    ) -> None:
        registry = PromptRegistry(registry_config)
        prompt = registry.get_prompt("nonexistent")
        assert prompt is None

    def test_project_prompts_override(
        self, registry_config: ConfigManager, tmp_path: Path
    ) -> None:
        # Create project prompt that overrides bundled
        proj_prompts = tmp_path / ".genai-cli" / "prompts" / "default"
        proj_prompts.mkdir(parents=True)
        (proj_prompts / "PROMPT.md").write_text(
            '---\nname: default\ndescription: Custom default\n'
            'metadata:\n  author: custom\n  version: "2.0"\n  category: custom\n---\n\n# Custom Default\n'
        )

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            registry = PromptRegistry(registry_config)
            prompt = registry.get_prompt("default")
            assert prompt is not None
            # Project prompt should override bundled
            assert "Custom" in prompt.description or prompt.category == "custom"
        finally:
            os.chdir(old_cwd)

    def test_prompts_sorted(self, registry_config: ConfigManager) -> None:
        registry = PromptRegistry(registry_config)
        prompts = registry.list_prompts()
        names = [p.name for p in prompts]
        assert names == sorted(names)

    def test_load_prompt_body(self, registry_config: ConfigManager) -> None:
        registry = PromptRegistry(registry_config)
        body = registry.load_prompt_body("default", "test-agent")
        assert body is not None
        assert "AI coding assistant" in body
        # {agent_name} should be substituted
        assert "{agent_name}" not in body
        assert "test-agent" in body

    def test_load_prompt_body_no_substitution(
        self, registry_config: ConfigManager
    ) -> None:
        registry = PromptRegistry(registry_config)
        body = registry.load_prompt_body("minimal", "")
        assert body is not None
        assert "AI coding assistant" in body

    def test_load_prompt_body_nonexistent(
        self, registry_config: ConfigManager
    ) -> None:
        registry = PromptRegistry(registry_config)
        body = registry.load_prompt_body("nonexistent", "test-agent")
        assert body is None

    def test_each_prompt_has_category(
        self, registry_config: ConfigManager
    ) -> None:
        registry = PromptRegistry(registry_config)
        for prompt in registry.list_prompts():
            assert prompt.category, f"Prompt {prompt.name} missing category"

    def test_each_prompt_has_description(
        self, registry_config: ConfigManager
    ) -> None:
        registry = PromptRegistry(registry_config)
        for prompt in registry.list_prompts():
            assert prompt.description.strip(), (
                f"Prompt {prompt.name} missing description"
            )
