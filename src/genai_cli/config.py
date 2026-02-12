"""Configuration manager with 5-level precedence merging."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from genai_cli.mapper import ResponseMapper
from genai_cli.models import AppSettings, FileTypeConfig, ModelInfo


def _package_config_dir() -> Path:
    """Return the config/ directory shipped with the package."""
    return Path(__file__).resolve().parent.parent.parent / "config"


def _user_config_dir() -> Path:
    """Return ~/.genai-cli/."""
    return Path.home() / ".genai-cli"


def _project_config_dir() -> Path:
    """Return .genai-cli/ in the current working directory."""
    return Path.cwd() / ".genai-cli"


def _load_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML file, returning empty dict if not found."""
    if path.is_file():
        with open(path) as f:
            data = yaml.safe_load(f)
            return data if isinstance(data, dict) else {}
    return {}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge override into base."""
    result = dict(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class ConfigManager:
    """Loads and merges configuration from multiple sources.

    Precedence (highest first):
      1. CLI overrides (set via set_override)
      2. Environment variables (GENAI_*)
      3. Project config: .genai-cli/settings.yaml
      4. User config: ~/.genai-cli/settings.yaml
      5. Package defaults: config/settings.yaml
    """

    def __init__(
        self,
        *,
        config_path: str | None = None,
        cli_overrides: dict[str, Any] | None = None,
    ) -> None:
        self._cli_overrides = cli_overrides or {}
        self._config_path = Path(config_path) if config_path else None
        self._merged: dict[str, Any] = {}
        self._models: dict[str, ModelInfo] = {}
        self._headers: dict[str, str] = {}
        self._system_prompt: str = ""
        self._active_prompt_name: str = "default"
        self._active_prompt_body: str | None = None
        self._api_format: dict[str, Any] = {}
        self._mapper: ResponseMapper | None = None
        self._load()

    def _load(self) -> None:
        """Load and merge all config sources."""
        pkg_dir = _package_config_dir()

        # Level 5: Package defaults
        merged = _load_yaml(pkg_dir / "settings.yaml")

        # Level 4: User config
        merged = _deep_merge(merged, _load_yaml(_user_config_dir() / "settings.yaml"))

        # Level 3: Project config
        merged = _deep_merge(
            merged, _load_yaml(_project_config_dir() / "settings.yaml")
        )

        # Level 3b: Custom config path
        if self._config_path:
            merged = _deep_merge(merged, _load_yaml(self._config_path))

        # Level 2: Environment variables
        env_map: dict[str, str] = {
            "GENAI_API_BASE_URL": "api_base_url",
            "GENAI_MODEL": "default_model",
            "GENAI_AUTO_APPLY": "auto_apply",
            "GENAI_VERBOSE": "verbose",
        }
        for env_key, config_key in env_map.items():
            val = os.environ.get(env_key)
            if val is not None:
                if val.lower() in ("true", "false"):
                    merged[config_key] = val.lower() == "true"
                else:
                    merged[config_key] = val

        # Level 1: CLI overrides
        merged = _deep_merge(merged, self._cli_overrides)

        self._merged = merged

        # Load models
        models_data = _load_yaml(pkg_dir / "models.yaml")
        self._models = {}
        for name, info in models_data.get("models", {}).items():
            self._models[name] = ModelInfo(
                name=name,
                display_name=info.get("display_name", name),
                provider=info.get("provider", ""),
                tier=info.get("tier", ""),
                context_window=info.get("context_window", 128000),
                max_output_tokens=info.get("max_output_tokens", 4096),
                cost_per_1k_input=info.get("cost_per_1k_input", 0.0),
                cost_per_1k_output=info.get("cost_per_1k_output", 0.0),
                supports_streaming=info.get("supports_streaming", True),
                supports_file_upload=info.get("supports_file_upload", True),
                premium=info.get("premium", False),
            )

        # Load headers
        headers_data = _load_yaml(pkg_dir / "headers.yaml")
        self._headers = dict(headers_data.get("headers", {}))

        # Load system prompt
        prompt_data = _load_yaml(pkg_dir / "system_prompt.yaml")
        raw_prompt = prompt_data.get("system_prompt", "")
        agent_name = self._merged.get("agent_name", "ai-assistant")
        self._system_prompt = raw_prompt.replace("{agent_name}", agent_name)

        # Load API format mapping (same 3-level merge: package → user → project)
        api_fmt = _load_yaml(pkg_dir / "api_format.yaml").get("api_format", {})
        api_fmt = _deep_merge(
            api_fmt,
            _load_yaml(_user_config_dir() / "api_format.yaml").get("api_format", {}),
        )
        api_fmt = _deep_merge(
            api_fmt,
            _load_yaml(_project_config_dir() / "api_format.yaml").get("api_format", {}),
        )
        self._api_format = api_fmt
        self._mapper = None  # reset cached mapper

    @property
    def mapper(self) -> ResponseMapper:
        """Return the ResponseMapper for API field translation."""
        if self._mapper is None:
            self._mapper = ResponseMapper(self._api_format)
        return self._mapper

    def set_override(self, key: str, value: Any) -> None:
        """Set a CLI-level override."""
        self._cli_overrides[key] = value
        self._load()

    @property
    def settings(self) -> AppSettings:
        """Build AppSettings from merged config."""
        ft_raw = self._merged.get("file_types", {})
        file_types: dict[str, FileTypeConfig] = {}
        for ft_name, ft_data in ft_raw.items():
            if isinstance(ft_data, dict):
                file_types[ft_name] = FileTypeConfig(
                    extensions=ft_data.get("extensions", []),
                    include_names=ft_data.get("include_names", []),
                    max_file_size_kb=ft_data.get("max_file_size_kb", 500),
                )

        return AppSettings(
            agent_name=self._merged.get("agent_name", "ai-assistant"),
            api_base_url=self._merged.get("api_base_url", ""),
            web_ui_url=self._merged.get("web_ui_url", ""),
            default_model=self._merged.get("default_model", "gpt-5-chat-global"),
            auto_apply=bool(self._merged.get("auto_apply", False)),
            streaming=bool(self._merged.get("streaming", True)),
            max_agent_rounds=int(self._merged.get("max_agent_rounds", 5)),
            create_backups=bool(self._merged.get("create_backups", True)),
            token_warning_threshold=float(
                self._merged.get("token_warning_threshold", 0.80)
            ),
            token_critical_threshold=float(
                self._merged.get("token_critical_threshold", 0.95)
            ),
            session_dir=str(self._merged.get("session_dir", "~/.genai-cli/sessions")),
            session_db=str(self._merged.get("session_db", "~/.genai-cli/sessions.db")),
            session_backend=str(self._merged.get("session_backend", "both")),
            max_saved_sessions=int(self._merged.get("max_saved_sessions", 50)),
            show_token_count=bool(self._merged.get("show_token_count", True)),
            show_cost=bool(self._merged.get("show_cost", True)),
            markdown_rendering=bool(self._merged.get("markdown_rendering", True)),
            color_theme=str(self._merged.get("color_theme", "auto")),
            allowed_write_paths=self._merged.get("allowed_write_paths", ["."]),
            blocked_write_patterns=self._merged.get("blocked_write_patterns", []),
            file_types=file_types,
            exclude_patterns=self._merged.get("exclude_patterns", []),
        )

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value by key."""
        return self._merged.get(key, default)

    def get_model(self, name: str | None = None) -> ModelInfo | None:
        """Get model info by name or the default model."""
        model_name = name or self._merged.get("default_model", "")
        return self._models.get(model_name)

    def get_all_models(self) -> dict[str, ModelInfo]:
        """Return all registered models."""
        return dict(self._models)

    def get_headers(self) -> dict[str, str]:
        """Return default HTTP headers, with origin/referer derived from web_ui_url."""
        headers = dict(self._headers)
        web_ui = self._merged.get("web_ui_url", "")
        if web_ui:
            headers["origin"] = web_ui
            headers["referer"] = web_ui + "/"
        return headers

    def get_system_prompt(self) -> str:
        """Return the active prompt body, or the default system prompt."""
        if self._active_prompt_body is not None:
            return self._active_prompt_body
        return self._system_prompt

    @property
    def active_prompt_name(self) -> str:
        """Return the name of the active prompt profile."""
        return self._active_prompt_name

    def set_active_prompt(self, name: str, body: str) -> None:
        """Switch the active system prompt."""
        self._active_prompt_name = name
        self._active_prompt_body = body

    def clear_active_prompt(self) -> None:
        """Reset to the default system prompt from config/system_prompt.yaml."""
        self._active_prompt_name = "default"
        self._active_prompt_body = None

    @property
    def raw(self) -> dict[str, Any]:
        """Return the raw merged config dict."""
        return dict(self._merged)
