"""Tests for config module."""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from genai_cli.config import ConfigManager, _deep_merge, _load_yaml
from genai_cli.models import ModelInfo


class TestLoadYaml:
    def test_load_existing_file(self, tmp_path: Path) -> None:
        f = tmp_path / "test.yaml"
        f.write_text("key: value\nnested:\n  a: 1\n")
        result = _load_yaml(f)
        assert result == {"key": "value", "nested": {"a": 1}}

    def test_load_missing_file(self, tmp_path: Path) -> None:
        result = _load_yaml(tmp_path / "missing.yaml")
        assert result == {}

    def test_load_empty_file(self, tmp_path: Path) -> None:
        f = tmp_path / "empty.yaml"
        f.write_text("")
        result = _load_yaml(f)
        assert result == {}


class TestDeepMerge:
    def test_simple_merge(self) -> None:
        result = _deep_merge({"a": 1}, {"b": 2})
        assert result == {"a": 1, "b": 2}

    def test_override(self) -> None:
        result = _deep_merge({"a": 1}, {"a": 2})
        assert result == {"a": 2}

    def test_nested_merge(self) -> None:
        base = {"nested": {"a": 1, "b": 2}}
        override = {"nested": {"b": 3, "c": 4}}
        result = _deep_merge(base, override)
        assert result == {"nested": {"a": 1, "b": 3, "c": 4}}


class TestConfigManager:
    def test_loads_defaults(self, mock_config: ConfigManager) -> None:
        settings = mock_config.settings
        assert settings.agent_name == "test-agent"
        assert settings.api_base_url == "https://api-genai.test.com"

    def test_get_model(self, mock_config: ConfigManager) -> None:
        model = mock_config.get_model("gpt-5-chat-global")
        assert model is not None
        assert model.display_name == "GPT-5"
        assert model.context_window == 128000

    def test_get_default_model(self, mock_config: ConfigManager) -> None:
        model = mock_config.get_model()
        assert model is not None
        assert model.name == "gpt-5-chat-global"

    def test_get_nonexistent_model(self, mock_config: ConfigManager) -> None:
        model = mock_config.get_model("nonexistent")
        assert model is None

    def test_get_all_models(self, mock_config: ConfigManager) -> None:
        models = mock_config.get_all_models()
        assert len(models) == 11
        assert "gpt-5-chat-global" in models
        assert "claude-sonnet-4-5-global" in models
        assert "gemini-2.5-pro-global" in models

    def test_get_headers(self, mock_config: ConfigManager) -> None:
        headers = mock_config.get_headers()
        assert headers["accept"] == "*/*"
        assert headers["ngrok-skip-browser-warning"] == "true"
        assert headers["origin"] == "https://genai.test.com"
        assert headers["referer"] == "https://genai.test.com/"

    def test_get_system_prompt(self, mock_config: ConfigManager) -> None:
        prompt = mock_config.get_system_prompt()
        assert "test-agent" not in prompt or "Never mention" in prompt
        assert "{agent_name}" not in prompt
        assert "AI coding assistant" in prompt

    def test_system_prompt_substitution(self, mock_config: ConfigManager) -> None:
        prompt = mock_config.get_system_prompt()
        # {agent_name} should be replaced with the configured name
        assert "{agent_name}" not in prompt

    def test_file_type_config(self, mock_config: ConfigManager) -> None:
        settings = mock_config.settings
        assert "code" in settings.file_types
        assert ".py" in settings.file_types["code"].extensions
        assert "scripts" in settings.file_types
        assert "Makefile" in settings.file_types["scripts"].include_names

    def test_env_override(self, tmp_path: Path) -> None:
        settings_path = tmp_path / "s.yaml"
        settings_path.write_text(yaml.dump({"default_model": "original"}))
        with patch.dict(os.environ, {"GENAI_MODEL": "overridden"}):
            cfg = ConfigManager(config_path=str(settings_path))
            assert cfg.settings.default_model == "overridden"

    def test_cli_override(self, tmp_path: Path) -> None:
        settings_path = tmp_path / "s.yaml"
        settings_path.write_text(yaml.dump({"default_model": "original"}))
        cfg = ConfigManager(
            config_path=str(settings_path),
            cli_overrides={"default_model": "cli-model"},
        )
        assert cfg.settings.default_model == "cli-model"

    def test_set_override(self, mock_config: ConfigManager) -> None:
        mock_config.set_override("auto_apply", True)
        assert mock_config.settings.auto_apply is True

    def test_raw_config(self, mock_config: ConfigManager) -> None:
        raw = mock_config.raw
        assert isinstance(raw, dict)
        assert "api_base_url" in raw

    def test_exclude_patterns_loaded(self, mock_config: ConfigManager) -> None:
        settings = mock_config.settings
        assert len(settings.exclude_patterns) > 0
        assert "**/__pycache__/**" in settings.exclude_patterns
