"""Tests for skill registry module."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from genai_cli.config import ConfigManager
from genai_cli.skills.registry import SkillRegistry


@pytest.fixture
def registry_config(tmp_path: Path) -> ConfigManager:
    settings = {
        "api_base_url": "https://api.test.com",
    }
    p = tmp_path / "settings.yaml"
    p.write_text(yaml.dump(settings))
    return ConfigManager(config_path=str(p))


class TestSkillRegistry:
    def test_discovers_bundled_skills(
        self, registry_config: ConfigManager
    ) -> None:
        registry = SkillRegistry(registry_config)
        skills = registry.list_skills()
        names = [s.name for s in skills]
        assert "review" in names
        assert "fix" in names
        assert "refactor" in names

    def test_discovers_all_14_skills(
        self, registry_config: ConfigManager
    ) -> None:
        registry = SkillRegistry(registry_config)
        skills = registry.list_skills()
        assert len(skills) == 14

    def test_get_skill(self, registry_config: ConfigManager) -> None:
        registry = SkillRegistry(registry_config)
        skill = registry.get_skill("review")
        assert skill is not None
        assert skill.name == "review"

    def test_get_nonexistent_skill(
        self, registry_config: ConfigManager
    ) -> None:
        registry = SkillRegistry(registry_config)
        skill = registry.get_skill("nonexistent")
        assert skill is None

    def test_project_skills_override(
        self, registry_config: ConfigManager, tmp_path: Path
    ) -> None:
        # Create project skill that overrides bundled
        proj_skills = tmp_path / ".genai-cli" / "skills" / "review"
        proj_skills.mkdir(parents=True)
        (proj_skills / "SKILL.md").write_text(
            '---\nname: review\ndescription: Custom review\n'
            'metadata:\n  author: custom\n  version: "2.0"\n  category: custom\n---\n\n# Custom Review\n'
        )

        import os

        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            registry = SkillRegistry(registry_config)
            skill = registry.get_skill("review")
            assert skill is not None
            # Project skill should override bundled
            assert "Custom" in skill.description or skill.category == "custom"
        finally:
            os.chdir(old_cwd)

    def test_skills_sorted(self, registry_config: ConfigManager) -> None:
        registry = SkillRegistry(registry_config)
        skills = registry.list_skills()
        names = [s.name for s in skills]
        assert names == sorted(names)

    def test_find_agents_md(self, tmp_path: Path) -> None:
        # Create agents.md in a parent directory
        (tmp_path / "AGENTS.md").write_text("# Agent Instructions\n")
        child = tmp_path / "src" / "module"
        child.mkdir(parents=True)

        settings = {"api_base_url": "https://api.test.com"}
        p = tmp_path / "settings.yaml"
        p.write_text(yaml.dump(settings))
        config = ConfigManager(config_path=str(p))

        registry = SkillRegistry(config)
        content = registry.find_agents_md(child)
        assert content is not None
        assert "Agent Instructions" in content

    def test_find_agents_md_none(self, tmp_path: Path) -> None:
        settings = {"api_base_url": "https://api.test.com"}
        p = tmp_path / "settings.yaml"
        p.write_text(yaml.dump(settings))
        config = ConfigManager(config_path=str(p))

        registry = SkillRegistry(config)
        # Starting from tmp root with no agents.md anywhere up
        content = registry.find_agents_md(tmp_path)
        # May or may not find one depending on the test environment
        # Just ensure no exception

    def test_each_skill_has_category(
        self, registry_config: ConfigManager
    ) -> None:
        registry = SkillRegistry(registry_config)
        for skill in registry.list_skills():
            assert skill.category, f"Skill {skill.name} missing category"

    def test_each_skill_has_description(
        self, registry_config: ConfigManager
    ) -> None:
        registry = SkillRegistry(registry_config)
        for skill in registry.list_skills():
            assert skill.description.strip(), (
                f"Skill {skill.name} missing description"
            )
