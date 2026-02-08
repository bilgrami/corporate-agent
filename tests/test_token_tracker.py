"""Tests for token tracker module."""

from __future__ import annotations

import pytest

from genai_cli.config import ConfigManager
from genai_cli.token_tracker import TokenTracker


class TestTokenTracker:
    def test_initial_state(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        assert tracker.consumed == 0
        assert tracker.context_window == 128000
        assert tracker.remaining == 128000
        assert tracker.usage_ratio == 0.0

    def test_add_consumed(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        tracker.add_consumed(5000, 0.01)
        assert tracker.consumed == 5000

    def test_accumulation(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        tracker.add_consumed(1000)
        tracker.add_consumed(2000)
        assert tracker.consumed == 3000

    def test_ratio(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        tracker.add_consumed(64000)
        assert tracker.usage_ratio == pytest.approx(0.5, abs=0.01)

    def test_remaining(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        tracker.add_consumed(100000)
        assert tracker.remaining == 28000

    def test_status_normal(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        tracker.add_consumed(50000)  # ~39%
        assert tracker.status == "normal"

    def test_status_warning(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        tracker.add_consumed(108000)  # ~84%
        assert tracker.status == "warning"

    def test_status_critical(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        tracker.add_consumed(124000)  # ~97%
        assert tracker.status == "critical"

    def test_check_thresholds_normal(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        tracker.add_consumed(50000)
        assert tracker.check_thresholds() is None

    def test_check_thresholds_warning(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        tracker.add_consumed(108000)
        msg = tracker.check_thresholds()
        assert msg is not None
        assert "Approaching" in msg

    def test_check_thresholds_critical(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        tracker.add_consumed(124000)
        msg = tracker.check_thresholds()
        assert msg is not None
        assert "/clear" in msg

    def test_switch_model(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        success = tracker.switch_model("claude-sonnet-4-5-global")
        assert success is True
        assert tracker.context_window == 200000

    def test_switch_model_invalid(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        success = tracker.switch_model("nonexistent")
        assert success is False

    def test_reset(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        tracker.add_consumed(50000, 0.05)
        tracker.reset()
        assert tracker.consumed == 0

    def test_to_usage(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        tracker.add_consumed(5000, 0.01)
        usage = tracker.to_usage()
        assert usage.consumed == 5000
        assert usage.context_window == 128000
        assert usage.estimated_cost == 0.01

    def test_serialization_roundtrip(self, mock_config: ConfigManager) -> None:
        tracker = TokenTracker(mock_config)
        tracker.add_consumed(12345, 0.05)
        data = tracker.to_dict()

        restored = TokenTracker.from_dict(data, mock_config)
        assert restored.consumed == 12345
        assert restored.context_window == 128000
