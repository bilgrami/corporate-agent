"""Token tracking for context window management."""

from __future__ import annotations

from typing import Any

from genai_cli.config import ConfigManager
from genai_cli.models import TokenUsage


class TokenTracker:
    """Tracks token consumption against model context window."""

    def __init__(self, config: ConfigManager) -> None:
        self._config = config
        self._consumed: int = 0
        self._estimated_cost: float = 0.0
        self._model_name: str = config.settings.default_model
        model = config.get_model(self._model_name)
        self._context_window: int = model.context_window if model else 128000

    def add_consumed(self, tokens: int, cost: float = 0.0) -> None:
        """Add consumed tokens."""
        self._consumed += tokens
        self._estimated_cost += cost

    @property
    def consumed(self) -> int:
        return self._consumed

    @property
    def context_window(self) -> int:
        return self._context_window

    @property
    def remaining(self) -> int:
        return max(0, self._context_window - self._consumed)

    @property
    def usage_ratio(self) -> float:
        if self._context_window == 0:
            return 0.0
        return self._consumed / self._context_window

    @property
    def status(self) -> str:
        """Return status: normal, warning, or critical."""
        settings = self._config.settings
        ratio = self.usage_ratio
        if ratio >= settings.token_critical_threshold:
            return "critical"
        if ratio >= settings.token_warning_threshold:
            return "warning"
        return "normal"

    def check_thresholds(self) -> str | None:
        """Return a warning message if thresholds exceeded, else None."""
        s = self.status
        if s == "critical":
            pct = self.usage_ratio * 100
            return (
                f"Context usage at {pct:.0f}%. "
                "Consider /clear or /compact to free context."
            )
        if s == "warning":
            pct = self.usage_ratio * 100
            return f"Context usage at {pct:.0f}%. Approaching limit."
        return None

    def switch_model(self, model_name: str) -> bool:
        """Switch to a new model, updating context window."""
        model = self._config.get_model(model_name)
        if model is None:
            return False
        self._model_name = model_name
        self._context_window = model.context_window
        return True

    def subtract_consumed(self, tokens: int, cost: float = 0.0) -> None:
        """Remove consumed tokens (e.g., when rewinding)."""
        self._consumed = max(0, self._consumed - tokens)
        self._estimated_cost = max(0.0, self._estimated_cost - cost)

    def reset(self) -> None:
        """Reset consumed tokens to 0."""
        self._consumed = 0
        self._estimated_cost = 0.0

    def to_usage(self) -> TokenUsage:
        """Return a TokenUsage snapshot."""
        return TokenUsage(
            consumed=self._consumed,
            context_window=self._context_window,
            estimated_cost=self._estimated_cost,
            model_name=self._model_name,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize for session persistence."""
        return {
            "consumed": self._consumed,
            "estimated_cost": self._estimated_cost,
            "model_name": self._model_name,
            "context_window": self._context_window,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], config: ConfigManager) -> TokenTracker:
        """Restore from serialized dict."""
        tracker = cls(config)
        tracker._consumed = data.get("consumed", 0)
        tracker._estimated_cost = data.get("estimated_cost", 0.0)
        tracker._model_name = data.get("model_name", config.settings.default_model)
        tracker._context_window = data.get("context_window", 128000)
        return tracker
