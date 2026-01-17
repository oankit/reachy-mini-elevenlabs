"""Tests for the utils module.

This module tests the command-line argument parsing and logging configuration
utilities used by the Reachy Mini ElevenLabs app.
"""

from __future__ import annotations

import logging
import argparse
from unittest.mock import patch, MagicMock

import pytest

from reachy_mini_elevenlabs.utils import (
    parse_args,
    setup_logger,
    log_connection_troubleshooting,
)


class TestParseArgs:
    """Tests for parse_args function."""

    def test_returns_namespace_and_remaining_args(self) -> None:
        """Test that parse_args returns a tuple of namespace and remaining args."""
        with patch("sys.argv", ["test"]):
            args, remaining = parse_args()
            assert isinstance(args, argparse.Namespace)
            assert isinstance(remaining, list)

    def test_debug_flag_defaults_to_false(self) -> None:
        """Test that --debug flag defaults to False."""
        with patch("sys.argv", ["test"]):
            args, _ = parse_args()
            assert args.debug is False

    def test_debug_flag_can_be_enabled(self) -> None:
        """Test that --debug flag can be enabled."""
        with patch("sys.argv", ["test", "--debug"]):
            args, _ = parse_args()
            assert args.debug is True

    def test_robot_name_defaults_to_none(self) -> None:
        """Test that --robot-name defaults to None."""
        with patch("sys.argv", ["test"]):
            args, _ = parse_args()
            assert args.robot_name is None

    def test_robot_name_can_be_set(self) -> None:
        """Test that --robot-name can be set."""
        with patch("sys.argv", ["test", "--robot-name", "my-robot"]):
            args, _ = parse_args()
            assert args.robot_name == "my-robot"

    def test_no_camera_flag_defaults_to_false(self) -> None:
        """Test that --no-camera flag defaults to False."""
        with patch("sys.argv", ["test"]):
            args, _ = parse_args()
            assert args.no_camera is False

    def test_no_camera_flag_can_be_enabled(self) -> None:
        """Test that --no-camera flag can be enabled."""
        with patch("sys.argv", ["test", "--no-camera"]):
            args, _ = parse_args()
            assert args.no_camera is True

    def test_unknown_args_are_returned_in_remaining(self) -> None:
        """Test that unknown arguments are returned in remaining list."""
        with patch("sys.argv", ["test", "--unknown-arg", "value"]):
            args, remaining = parse_args()
            assert "--unknown-arg" in remaining
            assert "value" in remaining


class TestSetupLogger:
    """Tests for setup_logger function."""

    def test_returns_logger_instance(self) -> None:
        """Test that setup_logger returns a Logger instance."""
        logger = setup_logger(debug=False)
        assert isinstance(logger, logging.Logger)

    def test_debug_mode_sets_debug_level(self) -> None:
        """Test that debug=True sets DEBUG log level."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        logger = setup_logger(debug=True)
        assert root_logger.level == logging.DEBUG

    def test_non_debug_mode_sets_info_level(self) -> None:
        """Test that debug=False sets INFO log level."""
        # Clear any existing handlers
        root_logger = logging.getLogger()
        root_logger.handlers.clear()
        
        logger = setup_logger(debug=False)
        assert root_logger.level == logging.INFO

    def test_elevenlabs_logger_level_in_debug_mode(self) -> None:
        """Test that elevenlabs logger is set to INFO in debug mode."""
        setup_logger(debug=True)
        elevenlabs_logger = logging.getLogger("elevenlabs")
        assert elevenlabs_logger.level == logging.INFO

    def test_elevenlabs_logger_level_in_non_debug_mode(self) -> None:
        """Test that elevenlabs logger is set to WARNING in non-debug mode."""
        setup_logger(debug=False)
        elevenlabs_logger = logging.getLogger("elevenlabs")
        assert elevenlabs_logger.level == logging.WARNING

    def test_websockets_logger_level_in_debug_mode(self) -> None:
        """Test that websockets logger is set to INFO in debug mode."""
        setup_logger(debug=True)
        websockets_logger = logging.getLogger("websockets")
        assert websockets_logger.level == logging.INFO

    def test_websockets_logger_level_in_non_debug_mode(self) -> None:
        """Test that websockets logger is set to WARNING in non-debug mode."""
        setup_logger(debug=False)
        websockets_logger = logging.getLogger("websockets")
        assert websockets_logger.level == logging.WARNING


class TestLogConnectionTroubleshooting:
    """Tests for log_connection_troubleshooting function."""

    def test_logs_troubleshooting_steps(self) -> None:
        """Test that troubleshooting steps are logged."""
        mock_logger = MagicMock(spec=logging.Logger)
        
        log_connection_troubleshooting(mock_logger, robot_name=None)
        
        # Should have logged multiple error messages
        assert mock_logger.error.call_count >= 5

    def test_logs_robot_name_when_provided(self) -> None:
        """Test that robot name is included in troubleshooting when provided."""
        mock_logger = MagicMock(spec=logging.Logger)
        
        log_connection_troubleshooting(mock_logger, robot_name="test-robot")
        
        # Check that one of the error calls mentions the robot name
        calls = [str(call) for call in mock_logger.error.call_args_list]
        assert any("test-robot" in call for call in calls)

    def test_logs_generic_message_when_no_robot_name(self) -> None:
        """Test that generic message is logged when no robot name provided."""
        mock_logger = MagicMock(spec=logging.Logger)
        
        log_connection_troubleshooting(mock_logger, robot_name=None)
        
        # Check that one of the error calls mentions adding the flag
        calls = [str(call) for call in mock_logger.error.call_args_list]
        assert any("--robot-name" in call for call in calls)
