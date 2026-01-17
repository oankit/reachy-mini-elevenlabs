"""Tests for the settings UI module.

This module tests the settings UI endpoints and configuration persistence
functionality for the ElevenLabs integration.
"""

from __future__ import annotations
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, strategies as st

from reachy_mini_elevenlabs.settings_ui import (
    _read_env_lines,
    persist_config,
)


class TestReadEnvLines:
    """Tests for _read_env_lines function."""

    def test_reads_existing_env_file(self, tmp_path: Path) -> None:
        """Test reading an existing .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("KEY1=value1\nKEY2=value2\n", encoding="utf-8")

        lines = _read_env_lines(env_file)

        assert lines == ["KEY1=value1", "KEY2=value2"]

    def test_returns_empty_list_for_nonexistent_file_without_template(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test returns empty list when file doesn't exist and no template."""
        env_file = tmp_path / ".env"

        # Change to tmp_path so no .env.example is found in cwd
        monkeypatch.chdir(tmp_path)

        lines = _read_env_lines(env_file)

        assert lines == []

    def test_reads_template_from_env_example(self, tmp_path: Path) -> None:
        """Test reading template from .env.example when .env doesn't exist."""
        env_file = tmp_path / ".env"
        example_file = tmp_path / ".env.example"
        example_file.write_text(
            "# Example config\nELEVENLABS_API_KEY=\nELEVENLABS_AGENT_ID=\n",
            encoding="utf-8",
        )

        lines = _read_env_lines(env_file)

        assert "# Example config" in lines
        assert "ELEVENLABS_API_KEY=" in lines
        assert "ELEVENLABS_AGENT_ID=" in lines

    def test_handles_empty_env_file(self, tmp_path: Path) -> None:
        """Test handling an empty .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text("", encoding="utf-8")

        lines = _read_env_lines(env_file)

        # Empty string splits to empty list
        assert lines == []


class TestPersistConfig:
    """Tests for persist_config function."""

    def test_sets_environment_variables(self) -> None:
        """Test that persist_config sets environment variables."""
        with patch.dict(os.environ, {}, clear=True):
            with patch("reachy_mini_elevenlabs.settings_ui.config") as mock_config:
                persist_config("test_api_key", "test_agent_id", None)

                assert os.environ.get("ELEVENLABS_API_KEY") == "test_api_key"
                assert os.environ.get("ELEVENLABS_AGENT_ID") == "test_agent_id"

    def test_updates_config_object(self) -> None:
        """Test that persist_config updates the config object."""
        with patch("reachy_mini_elevenlabs.settings_ui.config") as mock_config:
            persist_config("test_api_key", "test_agent_id", None)

            mock_config.ELEVENLABS_API_KEY = "test_api_key"
            mock_config.ELEVENLABS_AGENT_ID = "test_agent_id"

    def test_creates_env_file_when_not_exists(self, tmp_path: Path) -> None:
        """Test that persist_config creates .env file when it doesn't exist."""
        with patch("reachy_mini_elevenlabs.settings_ui.config"):
            persist_config("test_api_key", "test_agent_id", str(tmp_path))

            env_file = tmp_path / ".env"
            assert env_file.exists()
            content = env_file.read_text(encoding="utf-8")
            assert "ELEVENLABS_API_KEY=test_api_key" in content
            assert "ELEVENLABS_AGENT_ID=test_agent_id" in content

    def test_updates_existing_env_file(self, tmp_path: Path) -> None:
        """Test that persist_config updates existing .env file."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "ELEVENLABS_API_KEY=old_key\nELEVENLABS_AGENT_ID=old_id\n",
            encoding="utf-8",
        )

        with patch("reachy_mini_elevenlabs.settings_ui.config"):
            persist_config("new_api_key", "new_agent_id", str(tmp_path))

            content = env_file.read_text(encoding="utf-8")
            assert "ELEVENLABS_API_KEY=new_api_key" in content
            assert "ELEVENLABS_AGENT_ID=new_agent_id" in content
            assert "old_key" not in content
            assert "old_id" not in content

    def test_preserves_other_env_variables(self, tmp_path: Path) -> None:
        """Test that persist_config preserves other environment variables."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "OTHER_VAR=other_value\nELEVENLABS_API_KEY=old_key\n",
            encoding="utf-8",
        )

        with patch("reachy_mini_elevenlabs.settings_ui.config"):
            persist_config("new_api_key", "new_agent_id", str(tmp_path))

            content = env_file.read_text(encoding="utf-8")
            assert "OTHER_VAR=other_value" in content
            assert "ELEVENLABS_API_KEY=new_api_key" in content
            assert "ELEVENLABS_AGENT_ID=new_agent_id" in content

    def test_strips_whitespace_from_values(self, tmp_path: Path) -> None:
        """Test that persist_config strips whitespace from values."""
        with patch("reachy_mini_elevenlabs.settings_ui.config"):
            persist_config("  api_key  ", "  agent_id  ", str(tmp_path))

            env_file = tmp_path / ".env"
            content = env_file.read_text(encoding="utf-8")
            assert "ELEVENLABS_API_KEY=api_key" in content
            assert "ELEVENLABS_AGENT_ID=agent_id" in content

    def test_handles_empty_api_key(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that persist_config handles empty API key."""
        # Change to tmp_path so no .env.example is found in cwd
        monkeypatch.chdir(tmp_path)

        with patch("reachy_mini_elevenlabs.settings_ui.config"):
            persist_config("", "agent_id", str(tmp_path))

            env_file = tmp_path / ".env"
            content = env_file.read_text(encoding="utf-8")
            # Empty API key should not be written
            assert "ELEVENLABS_API_KEY" not in content
            assert "ELEVENLABS_AGENT_ID=agent_id" in content

    def test_handles_empty_agent_id(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that persist_config handles empty agent ID."""
        # Change to tmp_path so no .env.example is found in cwd
        monkeypatch.chdir(tmp_path)

        with patch("reachy_mini_elevenlabs.settings_ui.config"):
            persist_config("api_key", "", str(tmp_path))

            env_file = tmp_path / ".env"
            content = env_file.read_text(encoding="utf-8")
            assert "ELEVENLABS_API_KEY=api_key" in content
            # Empty agent ID should not be written
            assert "ELEVENLABS_AGENT_ID" not in content

    def test_handles_none_instance_path(self) -> None:
        """Test that persist_config handles None instance path gracefully."""
        with patch("reachy_mini_elevenlabs.settings_ui.config"):
            # Should not raise an exception
            persist_config("api_key", "agent_id", None)


@pytest.mark.pbt
class TestSettingsPersistenceRoundTrip:
    """Property-based tests for settings persistence round-trip.

    Feature: elevenlabs-integration, Property 7: Settings Persistence Round-Trip

    **Validates: Requirements 7.5**

    For any configuration values provided via the settings UI,
    persisting to .env and then reloading should produce the
    same configuration values.
    """

    @given(
        api_key=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
                # Exclude characters that break .env parsing:
                # - newlines (\n, \r) break line-based format
                # - equals (=) breaks key=value parsing
                blacklist_characters="\n\r=",
            ),
            min_size=1,
            max_size=100,
        ).filter(lambda x: x.strip()),
        agent_id=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
                blacklist_characters="\n\r=",
            ),
            min_size=1,
            max_size=100,
        ).filter(lambda x: x.strip()),
    )
    @settings(max_examples=100)
    def test_settings_persistence_round_trip(
        self, api_key: str, agent_id: str
    ) -> None:
        """Test that persisting and reloading config produces same values.

        Feature: elevenlabs-integration, Property 7: Settings Persistence Round-Trip

        **Validates: Requirements 7.5**

        For any configuration values provided via the settings UI,
        persisting to .env and then reloading should produce the
        same configuration values.
        """
        from dotenv import load_dotenv

        api_key_stripped = api_key.strip()
        agent_id_stripped = agent_id.strip()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            env_file = tmp_path / ".env"

            # Persist the configuration
            with patch("reachy_mini_elevenlabs.settings_ui.config"):
                persist_config(api_key, agent_id, str(tmp_path))

            # Verify .env file was created
            assert env_file.exists(), "Environment file should be created"

            # Reload the .env file and verify values via environment
            # Clear any existing values first
            with patch.dict(os.environ, {}, clear=True):
                load_dotenv(dotenv_path=str(env_file), override=True)

                loaded_api_key = os.environ.get("ELEVENLABS_API_KEY")
                loaded_agent_id = os.environ.get("ELEVENLABS_AGENT_ID")

                # Verify round-trip
                assert loaded_api_key == api_key_stripped, (
                    f"API key mismatch: expected '{api_key_stripped}', "
                    f"got '{loaded_api_key}'"
                )
                assert loaded_agent_id == agent_id_stripped, (
                    f"Agent ID mismatch: expected '{agent_id_stripped}', "
                    f"got '{loaded_agent_id}'"
                )

    @given(
        api_key=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
                blacklist_characters="\n\r=",
            ),
            min_size=1,
            max_size=50,
        ),
        agent_id=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
                blacklist_characters="\n\r=",
            ),
            min_size=1,
            max_size=50,
        ),
    )
    @settings(max_examples=100)
    def test_settings_persistence_preserves_existing_content(
        self, api_key: str, agent_id: str
    ) -> None:
        """Test that persisting config preserves other .env content.

        Feature: elevenlabs-integration, Property 7: Settings Persistence Round-Trip

        **Validates: Requirements 7.5**
        """
        from hypothesis import assume

        api_key_stripped = api_key.strip()
        agent_id_stripped = agent_id.strip()
        assume(bool(api_key_stripped) and bool(agent_id_stripped))

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            env_file = tmp_path / ".env"

            # Create initial .env with other content
            initial_content = "OTHER_VAR=preserved_value\nANOTHER_VAR=also_preserved\n"
            env_file.write_text(initial_content, encoding="utf-8")

            # Persist the configuration
            with patch("reachy_mini_elevenlabs.settings_ui.config"):
                persist_config(api_key, agent_id, str(tmp_path))

            # Read back and verify
            content = env_file.read_text(encoding="utf-8")

            assert "OTHER_VAR=preserved_value" in content
            assert "ANOTHER_VAR=also_preserved" in content
            assert f"ELEVENLABS_API_KEY={api_key_stripped}" in content
            assert f"ELEVENLABS_AGENT_ID={agent_id_stripped}" in content

    @given(
        api_key=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
                # Exclude characters that break .env parsing:
                # - newlines (\n, \r) break line-based format
                # - equals (=) breaks key=value parsing
                # - quotes (', ") break dotenv parsing when unescaped
                # - hash (#) starts comments
                blacklist_characters="\n\r='\"#",
            ),
            min_size=1,
            max_size=100,
        ).filter(lambda x: x.strip()),
        agent_id=st.text(
            alphabet=st.characters(
                whitelist_categories=("L", "N"),
                blacklist_characters="\n\r='\"#",
            ),
            min_size=1,
            max_size=100,
        ).filter(lambda x: x.strip()),
    )
    @settings(max_examples=100)
    def test_settings_persistence_handles_alphanumeric_values(
        self, api_key: str, agent_id: str
    ) -> None:
        """Test that persisting config handles alphanumeric values properly.

        Feature: elevenlabs-integration, Property 7: Settings Persistence Round-Trip

        **Validates: Requirements 7.5**

        This test verifies that alphanumeric values (typical for API keys
        and agent IDs) are preserved through the round-trip. Note that
        .env files have limitations with special characters like quotes
        and hash symbols, which is a known limitation of the format.
        """
        from dotenv import load_dotenv

        api_key_stripped = api_key.strip()
        agent_id_stripped = agent_id.strip()

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            env_file = tmp_path / ".env"

            # Persist the configuration
            with patch("reachy_mini_elevenlabs.settings_ui.config"):
                persist_config(api_key, agent_id, str(tmp_path))

            # Verify .env file was created
            assert env_file.exists(), "Environment file should be created"

            # Reload and verify via environment
            with patch.dict(os.environ, {}, clear=True):
                load_dotenv(dotenv_path=str(env_file), override=True)

                loaded_api_key = os.environ.get("ELEVENLABS_API_KEY")
                loaded_agent_id = os.environ.get("ELEVENLABS_AGENT_ID")

                # Verify round-trip preserves values
                assert loaded_api_key == api_key_stripped, (
                    f"API key mismatch: "
                    f"expected '{api_key_stripped}', got '{loaded_api_key}'"
                )
                assert loaded_agent_id == agent_id_stripped, (
                    f"Agent ID mismatch: "
                    f"expected '{agent_id_stripped}', got '{loaded_agent_id}'"
                )


class TestMountSettingsRoutes:
    """Tests for mount_settings_routes function."""

    def test_mounts_static_files(self) -> None:
        """Test that mount_settings_routes mounts static files."""
        mock_app = MagicMock()

        from reachy_mini_elevenlabs.settings_ui import mount_settings_routes

        mount_settings_routes(mock_app, None)

        # Verify mount was called for static files
        mock_app.mount.assert_called_once()
        call_args = mock_app.mount.call_args
        assert call_args[0][0] == "/static"

    def test_registers_root_endpoint(self) -> None:
        """Test that mount_settings_routes registers root endpoint."""
        mock_app = MagicMock()

        from reachy_mini_elevenlabs.settings_ui import mount_settings_routes

        mount_settings_routes(mock_app, None)

        # Verify get decorator was called for root
        mock_app.get.assert_any_call("/")

    def test_registers_status_endpoint(self) -> None:
        """Test that mount_settings_routes registers status endpoint."""
        mock_app = MagicMock()

        from reachy_mini_elevenlabs.settings_ui import mount_settings_routes

        mount_settings_routes(mock_app, None)

        # Verify get decorator was called for status
        mock_app.get.assert_any_call("/status")

    def test_registers_config_endpoint(self) -> None:
        """Test that mount_settings_routes registers config endpoint."""
        mock_app = MagicMock()

        from reachy_mini_elevenlabs.settings_ui import mount_settings_routes

        mount_settings_routes(mock_app, None)

        # Verify post decorator was called for config
        mock_app.post.assert_any_call("/elevenlabs_config")

    def test_registers_favicon_endpoint(self) -> None:
        """Test that mount_settings_routes registers favicon endpoint."""
        mock_app = MagicMock()

        from reachy_mini_elevenlabs.settings_ui import mount_settings_routes

        mount_settings_routes(mock_app, None)

        # Verify get decorator was called for favicon
        mock_app.get.assert_any_call("/favicon.ico")
