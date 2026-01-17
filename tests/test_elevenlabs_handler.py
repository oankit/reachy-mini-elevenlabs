"""Unit tests for ElevenLabsHandler.

Tests the ElevenLabs conversation handler that manages the conversation
lifecycle and coordinates with audio interface, HeadWobbler, and tools.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch, call

import pytest

from reachy_mini_elevenlabs.elevenlabs_handler import (
    ElevenLabsHandler,
    DEFAULT_MAX_RECONNECT_ATTEMPTS,
    DEFAULT_INITIAL_BACKOFF_SECONDS,
    DEFAULT_MAX_BACKOFF_SECONDS,
    DEFAULT_BACKOFF_MULTIPLIER,
)
from reachy_mini_elevenlabs.tools.core_tools import ToolDependencies


class MockHeadWobbler:
    """Mock HeadWobbler for testing."""

    def __init__(self) -> None:
        self.feed_calls: list[str] = []
        self.reset_calls: int = 0

    def feed(self, delta_b64: str) -> None:
        """Record feed calls."""
        self.feed_calls.append(delta_b64)

    def reset(self) -> None:
        """Record reset calls."""
        self.reset_calls += 1


class MockMedia:
    """Mock robot media interface for testing."""

    def __init__(self) -> None:
        self.recording = False
        self.audio = MockAudio()

    def start_recording(self) -> None:
        """Start recording."""
        self.recording = True

    def stop_recording(self) -> None:
        """Stop recording."""
        self.recording = False

    def get_audio_sample(self) -> None:
        """Get audio sample (returns None for testing)."""
        return None

    def push_audio_sample(self, audio: Any) -> None:
        """Push audio sample."""
        pass


class MockAudio:
    """Mock audio buffer interface."""

    def __init__(self) -> None:
        self.buffer_cleared = False

    def clear_output_buffer(self) -> None:
        """Record buffer clear."""
        self.buffer_cleared = True


class MockRobot:
    """Mock ReachyMini robot for testing."""

    def __init__(self) -> None:
        self.media = MockMedia()


class MockMovementManager:
    """Mock MovementManager for testing."""

    async def play_dance(self, dance_name: str) -> None:
        """Mock dance playback."""
        pass

    async def play_emotion(self, emotion: str) -> None:
        """Mock emotion playback."""
        pass


class MockConversation:
    """Mock ElevenLabs Conversation for testing."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.session_started = False
        self.session_ended = False
        self._conversation_id = "test-conversation-id"

    def start_session(self) -> None:
        """Start the conversation session."""
        self.session_started = True

    def end_session(self) -> None:
        """End the conversation session."""
        self.session_ended = True

    def wait_for_session_end(self) -> str:
        """Wait for session to end and return conversation ID."""
        return self._conversation_id


class MockElevenLabsClient:
    """Mock ElevenLabs client for testing."""

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key


def create_test_deps() -> ToolDependencies:
    """Create test dependencies."""
    return ToolDependencies(
        reachy_mini=MockRobot(),
        movement_manager=MockMovementManager(),
        camera_worker=None,
        head_wobbler=MockHeadWobbler(),
    )


class TestElevenLabsHandlerInit:
    """Tests for ElevenLabsHandler initialization."""

    def test_initializes_with_deps(self) -> None:
        """Test that handler initializes with dependencies."""
        deps = create_test_deps()

        handler = ElevenLabsHandler(deps)

        assert handler.deps is deps
        assert handler.instance_path is None
        assert handler.client is None
        assert handler.conversation is None
        assert handler.audio_interface is None

    def test_initializes_with_instance_path(self) -> None:
        """Test that handler accepts instance_path."""
        deps = create_test_deps()

        handler = ElevenLabsHandler(deps, instance_path="/path/to/instance")

        assert handler.instance_path == "/path/to/instance"


class TestElevenLabsHandlerStart:
    """Tests for the start() method."""

    def test_start_raises_without_agent_id(self) -> None:
        """Test that start() raises ValueError without ELEVENLABS_AGENT_ID."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        # Ensure no agent ID is set
        with patch.dict(os.environ, {}, clear=True):
            # Reload config to pick up cleared env
            from reachy_mini_elevenlabs.config import config
            config.ELEVENLABS_AGENT_ID = None
            config.ELEVENLABS_API_KEY = None

            with pytest.raises(ValueError, match="Missing required configuration"):
                handler.start()

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_start_creates_client(self) -> None:
        """Test that start() creates ElevenLabs client."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        # Set required config
        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        try:
            handler.start()

            assert handler.client is not None
            assert isinstance(handler.client, MockElevenLabsClient)
            assert handler.client.api_key == "test-api-key"
        finally:
            handler.stop()

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_start_creates_audio_interface(self) -> None:
        """Test that start() creates ReachyAudioInterface."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        try:
            handler.start()

            assert handler.audio_interface is not None
            assert handler.audio_interface.robot is deps.reachy_mini
            assert handler.audio_interface.head_wobbler is deps.head_wobbler
        finally:
            handler.stop()

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_start_creates_conversation(self) -> None:
        """Test that start() creates Conversation with correct parameters."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        try:
            handler.start()

            assert handler.conversation is not None
            assert isinstance(handler.conversation, MockConversation)
            # Verify conversation was created with correct parameters
            assert handler.conversation.kwargs["agent_id"] == "test-agent-id"
            assert handler.conversation.kwargs["requires_auth"] is True
        finally:
            handler.stop()

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_start_calls_start_session(self) -> None:
        """Test that start() calls conversation.start_session()."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        try:
            handler.start()

            assert handler.conversation.session_started is True
        finally:
            handler.stop()

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_start_with_no_api_key_sets_requires_auth_false(self) -> None:
        """Test that requires_auth is False when no API key is provided."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = None  # No API key

        try:
            handler.start()

            assert handler.conversation.kwargs["requires_auth"] is False
        finally:
            handler.stop()


class TestElevenLabsHandlerStop:
    """Tests for the stop() method."""

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_stop_ends_session(self) -> None:
        """Test that stop() calls conversation.end_session()."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        handler.start()
        handler.stop()

        assert handler.conversation.session_ended is True

    def test_stop_without_start_is_safe(self) -> None:
        """Test that stop() can be called without start()."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        # Should not raise
        handler.stop()

        assert handler.conversation is None


class TestElevenLabsHandlerWaitForEnd:
    """Tests for the wait_for_end() method."""

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_wait_for_end_returns_conversation_id(self) -> None:
        """Test that wait_for_end() returns conversation ID."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        handler.start()
        # Disable auto-restart so wait_for_end returns immediately
        handler.disable_auto_restart()
        conversation_id = handler.wait_for_end()

        assert conversation_id == "test-conversation-id"

    def test_wait_for_end_without_conversation_returns_empty(self) -> None:
        """Test that wait_for_end() returns empty string without conversation."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        conversation_id = handler.wait_for_end()

        assert conversation_id == ""


class TestElevenLabsHandlerCallbacks:
    """Tests for callback methods."""

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_callbacks_are_registered(self) -> None:
        """Test that callbacks are registered with Conversation."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        try:
            handler.start()

            # Verify callbacks were passed to Conversation
            assert "callback_agent_response" in handler.conversation.kwargs
            assert "callback_user_transcript" in handler.conversation.kwargs
            assert handler.conversation.kwargs["callback_agent_response"] is not None
            assert handler.conversation.kwargs["callback_user_transcript"] is not None
        finally:
            handler.stop()

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_on_agent_response_logs_response(self) -> None:
        """Test that _on_agent_response logs the response."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        try:
            handler.start()

            # Call the callback directly
            with patch("reachy_mini_elevenlabs.elevenlabs_handler.logger") as mock_logger:
                handler._on_agent_response("Hello, I am the agent!")
                mock_logger.info.assert_called_with("Agent: Hello, I am the agent!")
        finally:
            handler.stop()

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_on_user_transcript_logs_transcript(self) -> None:
        """Test that _on_user_transcript logs the transcript."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        try:
            handler.start()

            # Call the callback directly
            with patch("reachy_mini_elevenlabs.elevenlabs_handler.logger") as mock_logger:
                handler._on_user_transcript("Hello, robot!")
                mock_logger.info.assert_called_with("User: Hello, robot!")
        finally:
            handler.stop()


class TestElevenLabsHandlerClientTools:
    """Tests for client tools creation."""

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_client_tools_are_created(self) -> None:
        """Test that client tools are created and passed to Conversation."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        try:
            handler.start()

            # Verify client_tools was passed to Conversation
            assert "client_tools" in handler.conversation.kwargs
            assert handler.conversation.kwargs["client_tools"] is not None
        finally:
            handler.stop()


# =============================================================================
# Property-Based Tests
# =============================================================================

from hypothesis import given, settings, strategies as st


class TestAuthRequirementProperty:
    """Property-based tests for authentication requirement.

    Feature: elevenlabs-integration, Property 2: Authentication Requirement Matches API Key Presence

    **Validates: Requirements 3.6**

    Property Definition:
    *For any* configuration state, the `requires_auth` parameter passed to the
    Conversation should be `True` if and only if `ELEVENLABS_API_KEY` is set
    and non-empty.
    """

    @settings(max_examples=100)
    @given(api_key=st.one_of(st.none(), st.text()))
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_requires_auth_matches_api_key_presence(self, api_key: str | None) -> None:
        """Test that requires_auth matches API key presence.

        **Validates: Requirements 3.6**

        For any configuration state, the `requires_auth` parameter passed to
        the Conversation should be `True` if and only if `ELEVENLABS_API_KEY`
        is set and non-empty.

        Args:
            api_key: Generated API key value (None or any text string).
        """
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        # Set up configuration
        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"  # Required for start()
        config.ELEVENLABS_API_KEY = api_key

        try:
            handler.start()

            # Calculate expected requires_auth value
            # Should be True if and only if api_key is set and non-empty (after stripping)
            expected_requires_auth = bool(api_key and api_key.strip())

            # Verify the requires_auth parameter passed to Conversation
            actual_requires_auth = handler.conversation.kwargs["requires_auth"]

            assert actual_requires_auth == expected_requires_auth, (
                f"requires_auth mismatch: expected {expected_requires_auth} "
                f"for api_key={api_key!r}, got {actual_requires_auth}"
            )
        finally:
            handler.stop()


# =============================================================================
# Error Handling Tests (Task 10.1)
# =============================================================================


class MockConversationWithFailure:
    """Mock Conversation that can simulate failures."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.session_started = False
        self.session_ended = False
        self._conversation_id = "test-conversation-id"
        self._start_fail_count = 0
        self._max_start_failures = 0
        self._wait_fail_count = 0
        self._max_wait_failures = 0

    def configure_start_failures(self, count: int) -> None:
        """Configure how many times start_session should fail."""
        self._max_start_failures = count
        self._start_fail_count = 0

    def configure_wait_failures(self, count: int) -> None:
        """Configure how many times wait_for_session_end should fail."""
        self._max_wait_failures = count
        self._wait_fail_count = 0

    def start_session(self) -> None:
        """Start the conversation session, possibly failing."""
        if self._start_fail_count < self._max_start_failures:
            self._start_fail_count += 1
            raise ConnectionError("WebSocket connection failed")
        self.session_started = True

    def end_session(self) -> None:
        """End the conversation session."""
        self.session_ended = True

    def wait_for_session_end(self) -> str:
        """Wait for session to end and return conversation ID."""
        if self._wait_fail_count < self._max_wait_failures:
            self._wait_fail_count += 1
            raise ConnectionError("Session ended unexpectedly")
        return self._conversation_id


class TestElevenLabsHandlerErrorHandling:
    """Tests for error handling in ElevenLabsHandler.

    **Validates: Requirements 8.1, 8.2, 8.4, 8.5**
    """

    def test_start_logs_clear_error_for_missing_config(self) -> None:
        """Test that start() logs clear error message for missing configuration.

        **Validates: Requirement 8.1**
        """
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        # Clear configuration
        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = None
        config.ELEVENLABS_API_KEY = None

        with patch("reachy_mini_elevenlabs.elevenlabs_handler.logger") as mock_logger:
            with pytest.raises(ValueError, match="Missing required configuration"):
                handler.start()

            # Verify clear error messages were logged
            error_calls = [c for c in mock_logger.error.call_args_list]
            assert len(error_calls) >= 2  # At least the main error and instructions

            # Check that the error message mentions the missing config
            error_messages = [str(c) for c in error_calls]
            assert any("ELEVENLABS_AGENT_ID" in msg for msg in error_messages)

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.time.sleep")
    def test_start_retries_on_websocket_failure(self, mock_sleep: MagicMock) -> None:
        """Test that start() retries on WebSocket connection failure.

        **Validates: Requirement 8.2**
        """
        deps = create_test_deps()
        # Use minimal backoff for faster tests
        handler = ElevenLabsHandler(
            deps,
            max_reconnect_attempts=3,
            initial_backoff=0.1,
        )

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        # Create a mock conversation that fails twice then succeeds
        mock_conv = MockConversationWithFailure()
        mock_conv.configure_start_failures(2)

        with patch(
            "reachy_mini_elevenlabs.elevenlabs_handler.Conversation",
            return_value=mock_conv,
        ):
            handler.start()

            # Verify session eventually started
            assert mock_conv.session_started is True
            # Verify sleep was called for backoff (2 failures = 2 sleeps)
            assert mock_sleep.call_count == 2

        handler.stop()

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.time.sleep")
    def test_start_raises_after_max_retries(self, mock_sleep: MagicMock) -> None:
        """Test that start() raises ConnectionError after max retries.

        **Validates: Requirement 8.2**
        """
        deps = create_test_deps()
        handler = ElevenLabsHandler(
            deps,
            max_reconnect_attempts=3,
            initial_backoff=0.1,
        )

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        # Create a mock conversation that always fails
        mock_conv = MockConversationWithFailure()
        mock_conv.configure_start_failures(10)  # More than max attempts

        with patch(
            "reachy_mini_elevenlabs.elevenlabs_handler.Conversation",
            return_value=mock_conv,
        ):
            with pytest.raises(ConnectionError, match="Failed to start"):
                handler.start()

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.time.sleep")
    def test_start_logs_connection_error_details(self, mock_sleep: MagicMock) -> None:
        """Test that start() logs detailed error information on failure.

        **Validates: Requirement 8.2**
        """
        deps = create_test_deps()
        handler = ElevenLabsHandler(
            deps,
            max_reconnect_attempts=2,
            initial_backoff=0.1,
        )

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        mock_conv = MockConversationWithFailure()
        mock_conv.configure_start_failures(10)

        with patch(
            "reachy_mini_elevenlabs.elevenlabs_handler.Conversation",
            return_value=mock_conv,
        ):
            with patch("reachy_mini_elevenlabs.elevenlabs_handler.logger") as mock_logger:
                with pytest.raises(ConnectionError):
                    handler.start()

                # Verify error details were logged
                error_calls = [str(c) for c in mock_logger.error.call_args_list]
                assert any("WebSocket connection failure" in msg for msg in error_calls)
                assert any("Error type" in msg for msg in error_calls)
                assert any("Error details" in msg for msg in error_calls)

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_stop_sets_stop_requested_flag(self) -> None:
        """Test that stop() sets the _stop_requested flag."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        handler.start()
        assert handler._stop_requested is False

        handler.stop()
        assert handler._stop_requested is True

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_stop_disables_auto_restart(self) -> None:
        """Test that stop() disables automatic session restart."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        handler.start()
        assert handler._should_restart is True

        handler.stop()
        assert handler._should_restart is False


class TestElevenLabsHandlerSessionRestart:
    """Tests for session restart functionality.

    **Validates: Requirements 8.4, 8.5**
    """

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_wait_for_end_does_not_restart_after_stop(self) -> None:
        """Test that wait_for_end() does not restart after explicit stop().

        **Validates: Requirement 8.5**
        """
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        handler.start()
        handler.stop()  # Explicit stop

        # wait_for_end should return immediately without restart attempt
        conversation_id = handler.wait_for_end()
        assert conversation_id == "test-conversation-id"

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_disable_auto_restart(self) -> None:
        """Test that disable_auto_restart() prevents automatic restart."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        handler.start()
        handler.disable_auto_restart()

        assert handler._should_restart is False

        handler.stop()

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.Conversation", MockConversation)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    def test_enable_auto_restart(self) -> None:
        """Test that enable_auto_restart() re-enables automatic restart."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        handler.start()
        handler.disable_auto_restart()
        handler.enable_auto_restart()

        assert handler._should_restart is True

        handler.stop()

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.time.sleep")
    def test_wait_for_end_logs_unexpected_end(self, mock_sleep: MagicMock) -> None:
        """Test that wait_for_end() logs when session ends unexpectedly.

        **Validates: Requirement 8.5**
        """
        deps = create_test_deps()
        handler = ElevenLabsHandler(
            deps,
            max_reconnect_attempts=1,  # Fail fast for test
            initial_backoff=0.1,
        )

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        # Create mock that succeeds on start but we'll disable restart
        mock_conv = MockConversation()

        with patch(
            "reachy_mini_elevenlabs.elevenlabs_handler.Conversation",
            return_value=mock_conv,
        ):
            handler.start()
            # Disable restart so we can test the logging
            handler.disable_auto_restart()

            with patch("reachy_mini_elevenlabs.elevenlabs_handler.logger") as mock_logger:
                handler.wait_for_end()

                # Verify conversation ID was logged
                info_calls = [str(c) for c in mock_logger.info.call_args_list]
                assert any("test-conversation-id" in msg for msg in info_calls)


class TestElevenLabsHandlerReconnectionConfig:
    """Tests for reconnection configuration."""

    def test_default_reconnection_config(self) -> None:
        """Test that default reconnection configuration is set."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(deps)

        assert handler.max_reconnect_attempts == DEFAULT_MAX_RECONNECT_ATTEMPTS
        assert handler.initial_backoff == DEFAULT_INITIAL_BACKOFF_SECONDS
        assert handler.max_backoff == DEFAULT_MAX_BACKOFF_SECONDS
        assert handler.backoff_multiplier == DEFAULT_BACKOFF_MULTIPLIER

    def test_custom_reconnection_config(self) -> None:
        """Test that custom reconnection configuration is accepted."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(
            deps,
            max_reconnect_attempts=10,
            initial_backoff=2.0,
            max_backoff=60.0,
            backoff_multiplier=3.0,
        )

        assert handler.max_reconnect_attempts == 10
        assert handler.initial_backoff == 2.0
        assert handler.max_backoff == 60.0
        assert handler.backoff_multiplier == 3.0

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.time.sleep")
    def test_exponential_backoff_calculation(self, mock_sleep: MagicMock) -> None:
        """Test that exponential backoff is calculated correctly."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(
            deps,
            max_reconnect_attempts=4,
            initial_backoff=1.0,
            max_backoff=10.0,
            backoff_multiplier=2.0,
        )

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        mock_conv = MockConversationWithFailure()
        mock_conv.configure_start_failures(10)  # Always fail

        with patch(
            "reachy_mini_elevenlabs.elevenlabs_handler.Conversation",
            return_value=mock_conv,
        ):
            with pytest.raises(ConnectionError):
                handler.start()

            # Verify backoff values: 1.0, 2.0, 4.0 (3 sleeps for 4 attempts)
            assert mock_sleep.call_count == 3
            sleep_values = [c[0][0] for c in mock_sleep.call_args_list]
            assert sleep_values[0] == 1.0
            assert sleep_values[1] == 2.0
            assert sleep_values[2] == 4.0

    @patch("reachy_mini_elevenlabs.elevenlabs_handler.ElevenLabs", MockElevenLabsClient)
    @patch("reachy_mini_elevenlabs.elevenlabs_handler.time.sleep")
    def test_backoff_respects_max_limit(self, mock_sleep: MagicMock) -> None:
        """Test that backoff does not exceed max_backoff."""
        deps = create_test_deps()
        handler = ElevenLabsHandler(
            deps,
            max_reconnect_attempts=5,
            initial_backoff=1.0,
            max_backoff=3.0,  # Low max to test capping
            backoff_multiplier=2.0,
        )

        from reachy_mini_elevenlabs.config import config
        config.ELEVENLABS_AGENT_ID = "test-agent-id"
        config.ELEVENLABS_API_KEY = "test-api-key"

        mock_conv = MockConversationWithFailure()
        mock_conv.configure_start_failures(10)

        with patch(
            "reachy_mini_elevenlabs.elevenlabs_handler.Conversation",
            return_value=mock_conv,
        ):
            with pytest.raises(ConnectionError):
                handler.start()

            # Verify backoff is capped: 1.0, 2.0, 3.0, 3.0 (4 sleeps for 5 attempts)
            sleep_values = [c[0][0] for c in mock_sleep.call_args_list]
            assert all(v <= 3.0 for v in sleep_values)
