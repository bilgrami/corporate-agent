"""Data classes for genai-cli. No business logic — just structured data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ModelInfo:
    """A model from the registry."""

    name: str
    display_name: str
    provider: str
    tier: str
    context_window: int
    max_output_tokens: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    supports_streaming: bool = True
    supports_file_upload: bool = True


@dataclass
class FileTypeConfig:
    """Configuration for a file type category."""

    extensions: list[str] = field(default_factory=list)
    include_names: list[str] = field(default_factory=list)
    max_file_size_kb: int = 500


@dataclass
class AppSettings:
    """Application settings loaded from YAML config."""

    agent_name: str = "ai-assistant"
    api_base_url: str = ""
    web_ui_url: str = ""
    default_model: str = "gpt-5-chat-global"
    auto_apply: bool = False
    streaming: bool = True
    max_agent_rounds: int = 5
    create_backups: bool = True
    token_warning_threshold: float = 0.80
    token_critical_threshold: float = 0.95
    session_dir: str = "~/.genai-cli/sessions"
    max_saved_sessions: int = 50
    show_token_count: bool = True
    show_cost: bool = True
    markdown_rendering: bool = True
    color_theme: str = "auto"
    allowed_write_paths: list[str] = field(default_factory=lambda: ["."])
    blocked_write_patterns: list[str] = field(default_factory=list)
    file_types: dict[str, FileTypeConfig] = field(default_factory=dict)
    exclude_patterns: list[str] = field(default_factory=list)


@dataclass
class AuthToken:
    """Bearer token with decoded metadata."""

    token: str
    email: str | None = None
    expires_at: datetime | None = None
    issued_at: datetime | None = None

    def __repr__(self) -> str:
        return f"AuthToken(email={self.email!r}, expires_at={self.expires_at!r})"


@dataclass
class ChatMessage:
    """A single message in a conversation."""

    session_id: str
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = ""
    model_name: str = ""
    display_name: str = ""
    tokens_consumed: int = 0
    token_cost: float = 0.0
    upload_content: str | None = None


@dataclass
class ChatSession:
    """A conversation session."""

    session_id: str
    messages: list[ChatMessage] = field(default_factory=list)
    model_name: str = ""
    created_at: str = ""
    total_tokens: int = 0
    total_cost: float = 0.0


@dataclass
class FileBundle:
    """A bundle of files ready for upload."""

    file_type: str  # code, docs, scripts, notebooks
    content: str
    file_count: int = 0
    file_paths: list[str] = field(default_factory=list)
    estimated_tokens: int = 0


@dataclass
class TokenUsage:
    """Token usage tracking for a session."""

    consumed: int = 0
    context_window: int = 128000
    estimated_cost: float = 0.0
    model_name: str = ""

    @property
    def remaining(self) -> int:
        return max(0, self.context_window - self.consumed)

    @property
    def usage_ratio(self) -> float:
        if self.context_window == 0:
            return 0.0
        return self.consumed / self.context_window
