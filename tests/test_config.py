"""Unit tests for configuration manager."""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from reachy_mini_elevenlabs.config import Config


class TestConfig:
    """Tests for the Config class."""

    def test_loads_agent_id_from_environment(self) -> None:
        """Test that ELEVENLABS_AGENT_ID is loaded from environment."""
        with patch.dict(os.environ, {"ELEVENLABS_AGENT_ID": "test-agent-123"}, clear=False):
            config = Config()
            assert config.ELEVENLABS_AGENT_ID == "test-agent-123"

    def test_loads_api_key_from_environment(self) -> None:
        """Test that ELEVENLABS_API_KEY is loaded from environment."""
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": "sk-test-key-456"}, clear=False):
            config = Config()
            assert config.ELEVENLABS_API_KEY == "sk-test-key-456"

    def test_loads_both_values_from_environment(self) -> None:
        """Test that both config values are loaded from environment."""
        env_vars = {
            "ELEVENLABS_AGENT_ID": "agent-abc",
            "ELEVENLABS_API_KEY": "key-xyz",
        }
        with patch.dict(os.environ, env_vars, clear=False):
            config = Config()
            assert config.ELEVENLABS_AGENT_ID == "agent-abc"
            assert config.ELEVENLABS_API_KEY == "key-xyz"

    def test_missing_agent_id_returns_none(self) -> None:
        """Test that missing ELEVENLABS_AGENT_ID results in None."""
        # Remove the env var if it exists
        env_copy = os.environ.copy()
        env_copy.pop("ELEVENLABS_AGENT_ID", None)
        with patch.dict(os.environ, env_copy, clear=True):
            config = Config()
            assert config.ELEVENLABS_AGENT_ID is None

    def test_missing_api_key_returns_none(self) -> None:
        """Test that missing ELEVENLABS_API_KEY results in None."""
        env_copy = os.environ.copy()
        env_copy.pop("ELEVENLABS_API_KEY", None)
        with patch.dict(os.environ, env_copy, clear=True):
            config = Config()
            assert config.ELEVENLABS_API_KEY is None

    def test_empty_string_agent_id_treated_as_none(self) -> None:
        """Test that empty string ELEVENLABS_AGENT_ID is treated as None."""
        with patch.dict(os.environ, {"ELEVENLABS_AGENT_ID": ""}, clear=False):
            config = Config()
            assert config.ELEVENLABS_AGENT_ID is None

    def test_empty_string_api_key_treated_as_none(self) -> None:
        """Test that empty string ELEVENLABS_API_KEY is treated as None."""
        with patch.dict(os.environ, {"ELEVENLABS_API_KEY": ""}, clear=False):
            config = Config()
            assert config.ELEVENLABS_API_KEY is None


class TestConfigValidate:
    """Tests for the Config.validate() method."""

    def test_validate_returns_empty_list_when_agent_id_present(self) -> None:
        """Test that validate() returns empty list when agent ID is set."""
        with patch.dict(os.environ, {"ELEVENLABS_AGENT_ID": "test-agent"}, clear=False):
            config = Config()
            errors = config.validate()
            assert errors == []

    def test_validate_returns_agent_id_when_missing(self) -> None:
        """Test that validate() returns ELEVENLABS_AGENT_ID when missing."""
        env_copy = os.environ.copy()
        env_copy.pop("ELEVENLABS_AGENT_ID", None)
        with patch.dict(os.environ, env_copy, clear=True):
            config = Config()
            errors = config.validate()
            assert "ELEVENLABS_AGENT_ID" in errors

    def test_validate_returns_agent_id_when_empty(self) -> None:
        """Test that validate() returns ELEVENLABS_AGENT_ID when empty string."""
        with patch.dict(os.environ, {"ELEVENLABS_AGENT_ID": ""}, clear=False):
            config = Config()
            errors = config.validate()
            assert "ELEVENLABS_AGENT_ID" in errors

    def test_validate_does_not_require_api_key(self) -> None:
        """Test that validate() does not require API key (it's optional)."""
        env_vars = {"ELEVENLABS_AGENT_ID": "test-agent"}
        env_copy = {k: v for k, v in os.environ.items() if k != "ELEVENLABS_API_KEY"}
        env_copy.update(env_vars)
        with patch.dict(os.environ, env_copy, clear=True):
            config = Config()
            errors = config.validate()
            assert "ELEVENLABS_API_KEY" not in errors


class TestConfigReload:
    """Tests for the Config.reload() method."""

    def test_reload_updates_values_from_environment(self) -> None:
        """Test that reload() updates values from environment."""
        # Start with initial values
        with patch.dict(os.environ, {"ELEVENLABS_AGENT_ID": "initial-agent"}, clear=False):
            config = Config()
            assert config.ELEVENLABS_AGENT_ID == "initial-agent"

            # Update environment and reload
            with patch.dict(os.environ, {"ELEVENLABS_AGENT_ID": "updated-agent"}, clear=False):
                config.reload()
                assert config.ELEVENLABS_AGENT_ID == "updated-agent"


# Property-based tests using hypothesis
from hypothesis import given, settings, strategies as st


# Strategy for valid environment variable values (no null characters)
# Environment variables cannot contain null characters on any OS
valid_env_value = st.text(alphabet=st.characters(blacklist_characters="\x00"))


class TestConfigPropertyBased:
    """Property-based tests for configuration loading.

    Feature: elevenlabs-integration, Property 1: Configuration Loading from Environment
    **Validates: Requirements 2.1, 2.2**
    """

    @settings(max_examples=100)
    @given(api_key=valid_env_value, agent_id=valid_env_value)
    def test_config_loading_from_environment(self, api_key: str, agent_id: str) -> None:
        """Property 1: Configuration Loading from Environment.

        For any environment variable setting of ELEVENLABS_API_KEY or
        ELEVENLABS_AGENT_ID, the Config object should reflect those exact
        values after loading.

        **Validates: Requirements 2.1, 2.2**
        """
        # Set environment variables with the generated values
        env_vars = {
            "ELEVENLABS_API_KEY": api_key,
            "ELEVENLABS_AGENT_ID": agent_id,
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = Config()

            # Property: Config should reflect exact values from environment
            # Note: Empty strings are normalized to None by the Config class
            expected_api_key = api_key if api_key else None
            expected_agent_id = agent_id if agent_id else None

            assert config.ELEVENLABS_API_KEY == expected_api_key, (
                f"API key mismatch: expected {expected_api_key!r}, got {config.ELEVENLABS_API_KEY!r}"
            )
            assert config.ELEVENLABS_AGENT_ID == expected_agent_id, (
                f"Agent ID mismatch: expected {expected_agent_id!r}, got {config.ELEVENLABS_AGENT_ID!r}"
            )

    @settings(max_examples=100)
    @given(
        api_key=st.text(min_size=1, alphabet=st.characters(blacklist_characters="\x00")),
        agent_id=st.text(min_size=1, alphabet=st.characters(blacklist_characters="\x00")),
    )
    def test_config_loading_non_empty_values(self, api_key: str, agent_id: str) -> None:
        """Property 1 (non-empty variant): Non-empty values are preserved exactly.

        For any non-empty environment variable values, the Config object
        should reflect those exact values without modification.

        **Validates: Requirements 2.1, 2.2**
        """
        env_vars = {
            "ELEVENLABS_API_KEY": api_key,
            "ELEVENLABS_AGENT_ID": agent_id,
        }

        with patch.dict(os.environ, env_vars, clear=False):
            config = Config()

            # Property: Non-empty values should be preserved exactly
            assert config.ELEVENLABS_API_KEY == api_key, (
                f"API key not preserved: expected {api_key!r}, got {config.ELEVENLABS_API_KEY!r}"
            )
            assert config.ELEVENLABS_AGENT_ID == agent_id, (
                f"Agent ID not preserved: expected {agent_id!r}, got {config.ELEVENLABS_AGENT_ID!r}"
            )
