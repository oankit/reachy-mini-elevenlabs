"""Tests for core tool handlers and registration."""

from __future__ import annotations

import asyncio
import base64
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
from hypothesis import given, settings, strategies as st

from reachy_mini_elevenlabs.tools.core_tools import (
    ToolDependencies,
    camera_tool,
    dance_tool,
    emotion_tool,
    register_tools,
)


@pytest.fixture
def mock_head_wobbler():
    """Create a mock HeadWobbler."""
    return MagicMock()


@pytest.fixture
def mock_movement_manager():
    """Create a mock MovementManager with async methods."""
    manager = MagicMock()
    manager.play_dance = AsyncMock()
    manager.play_emotion = AsyncMock()
    return manager


@pytest.fixture
def mock_camera_worker():
    """Create a mock CameraWorker."""
    worker = MagicMock()
    # Create a simple test image (10x10 RGB)
    test_frame = np.zeros((10, 10, 3), dtype=np.uint8)
    test_frame[5, 5] = [255, 0, 0]  # Red pixel in center
    worker.get_latest_frame.return_value = test_frame
    return worker


@pytest.fixture
def mock_reachy_mini():
    """Create a mock ReachyMini robot."""
    return MagicMock()


@pytest.fixture
def tool_deps(mock_reachy_mini, mock_movement_manager, mock_camera_worker, mock_head_wobbler):
    """Create ToolDependencies with all mocks."""
    return ToolDependencies(
        reachy_mini=mock_reachy_mini,
        movement_manager=mock_movement_manager,
        camera_worker=mock_camera_worker,
        head_wobbler=mock_head_wobbler,
    )


@pytest.fixture
def tool_deps_no_camera(mock_reachy_mini, mock_movement_manager, mock_head_wobbler):
    """Create ToolDependencies without camera."""
    return ToolDependencies(
        reachy_mini=mock_reachy_mini,
        movement_manager=mock_movement_manager,
        camera_worker=None,
        head_wobbler=mock_head_wobbler,
    )


class TestCameraTool:
    """Tests for camera_tool function."""

    def test_returns_error_when_camera_not_available(self, tool_deps_no_camera):
        """Camera tool returns error when camera_worker is None."""
        result = camera_tool(tool_deps_no_camera)
        assert result == {"error": "Camera not available"}

    def test_returns_error_when_no_frame_available(self, tool_deps):
        """Camera tool returns error when get_latest_frame returns None."""
        tool_deps.camera_worker.get_latest_frame.return_value = None
        result = camera_tool(tool_deps)
        assert result == {"error": "No frame available"}

    def test_returns_base64_encoded_image(self, tool_deps):
        """Camera tool returns base64-encoded JPEG image."""
        result = camera_tool(tool_deps)
        
        assert "image" in result
        assert "error" not in result
        
        # Verify it's valid base64
        decoded = base64.b64decode(result["image"])
        assert len(decoded) > 0
        
        # Verify it's a JPEG (starts with FFD8)
        assert decoded[:2] == b"\xff\xd8"

    def test_calls_get_latest_frame(self, tool_deps):
        """Camera tool calls get_latest_frame on camera_worker."""
        camera_tool(tool_deps)
        tool_deps.camera_worker.get_latest_frame.assert_called_once()


class TestDanceTool:
    """Tests for dance_tool function."""

    @pytest.mark.asyncio
    async def test_triggers_dance_with_default_name(self, tool_deps):
        """Dance tool uses 'default' when no dance_name provided."""
        result = await dance_tool(tool_deps, {})
        
        assert result == {"status": "dancing", "dance": "default"}
        tool_deps.movement_manager.play_dance.assert_called_once_with("default")

    @pytest.mark.asyncio
    async def test_triggers_dance_with_specified_name(self, tool_deps):
        """Dance tool uses provided dance_name."""
        result = await dance_tool(tool_deps, {"dance_name": "happy_dance"})
        
        assert result == {"status": "dancing", "dance": "happy_dance"}
        tool_deps.movement_manager.play_dance.assert_called_once_with("happy_dance")

    @pytest.mark.asyncio
    async def test_returns_status_and_dance_name(self, tool_deps):
        """Dance tool returns status and dance name in result."""
        result = await dance_tool(tool_deps, {"dance_name": "robot_shuffle"})
        
        assert "status" in result
        assert "dance" in result
        assert result["status"] == "dancing"
        assert result["dance"] == "robot_shuffle"


class TestEmotionTool:
    """Tests for emotion_tool function."""

    @pytest.mark.asyncio
    async def test_triggers_emotion_with_default(self, tool_deps):
        """Emotion tool uses 'happy' when no emotion provided."""
        result = await emotion_tool(tool_deps, {})
        
        assert result == {"status": "playing", "emotion": "happy"}
        tool_deps.movement_manager.play_emotion.assert_called_once_with("happy")

    @pytest.mark.asyncio
    async def test_triggers_emotion_with_specified_value(self, tool_deps):
        """Emotion tool uses provided emotion."""
        result = await emotion_tool(tool_deps, {"emotion": "sad"})
        
        assert result == {"status": "playing", "emotion": "sad"}
        tool_deps.movement_manager.play_emotion.assert_called_once_with("sad")

    @pytest.mark.asyncio
    async def test_returns_status_and_emotion(self, tool_deps):
        """Emotion tool returns status and emotion in result."""
        result = await emotion_tool(tool_deps, {"emotion": "surprised"})
        
        assert "status" in result
        assert "emotion" in result
        assert result["status"] == "playing"
        assert result["emotion"] == "surprised"


class TestRegisterTools:
    """Tests for register_tools function."""

    def test_registers_camera_tool(self, tool_deps):
        """register_tools registers camera tool as synchronous."""
        mock_client_tools = MagicMock()
        
        register_tools(mock_client_tools, tool_deps)
        
        # Find the camera registration call
        calls = mock_client_tools.register.call_args_list
        camera_call = next(c for c in calls if c[0][0] == "camera")
        
        assert camera_call[0][0] == "camera"
        assert camera_call[1]["is_async"] is False

    def test_registers_dance_tool(self, tool_deps):
        """register_tools registers dance tool as asynchronous."""
        mock_client_tools = MagicMock()
        
        register_tools(mock_client_tools, tool_deps)
        
        # Find the dance registration call
        calls = mock_client_tools.register.call_args_list
        dance_call = next(c for c in calls if c[0][0] == "dance")
        
        assert dance_call[0][0] == "dance"
        assert dance_call[1]["is_async"] is True

    def test_registers_emotion_tool(self, tool_deps):
        """register_tools registers emotion tool as asynchronous."""
        mock_client_tools = MagicMock()
        
        register_tools(mock_client_tools, tool_deps)
        
        # Find the emotion registration call
        calls = mock_client_tools.register.call_args_list
        emotion_call = next(c for c in calls if c[0][0] == "emotion")
        
        assert emotion_call[0][0] == "emotion"
        assert emotion_call[1]["is_async"] is True

    def test_registers_all_three_tools(self, tool_deps):
        """register_tools registers exactly three tools."""
        mock_client_tools = MagicMock()
        
        register_tools(mock_client_tools, tool_deps)
        
        assert mock_client_tools.register.call_count == 3

    def test_camera_handler_calls_camera_tool(self, tool_deps):
        """Registered camera handler invokes camera_tool with deps."""
        mock_client_tools = MagicMock()
        
        register_tools(mock_client_tools, tool_deps)
        
        # Get the registered handler
        calls = mock_client_tools.register.call_args_list
        camera_call = next(c for c in calls if c[0][0] == "camera")
        camera_handler = camera_call[0][1]
        
        # Call the handler
        result = camera_handler({})
        
        # Verify camera_worker was called
        tool_deps.camera_worker.get_latest_frame.assert_called_once()
        assert "image" in result

    @pytest.mark.asyncio
    async def test_dance_handler_calls_dance_tool(self, tool_deps):
        """Registered dance handler invokes dance_tool with deps and params."""
        mock_client_tools = MagicMock()
        
        register_tools(mock_client_tools, tool_deps)
        
        # Get the registered handler
        calls = mock_client_tools.register.call_args_list
        dance_call = next(c for c in calls if c[0][0] == "dance")
        dance_handler = dance_call[0][1]
        
        # Call the handler
        result = await dance_handler({"dance_name": "test_dance"})
        
        # Verify movement_manager was called
        tool_deps.movement_manager.play_dance.assert_called_once_with("test_dance")
        assert result["dance"] == "test_dance"

    @pytest.mark.asyncio
    async def test_emotion_handler_calls_emotion_tool(self, tool_deps):
        """Registered emotion handler invokes emotion_tool with deps and params."""
        mock_client_tools = MagicMock()
        
        register_tools(mock_client_tools, tool_deps)
        
        # Get the registered handler
        calls = mock_client_tools.register.call_args_list
        emotion_call = next(c for c in calls if c[0][0] == "emotion")
        emotion_handler = emotion_call[0][1]
        
        # Call the handler
        result = await emotion_handler({"emotion": "excited"})
        
        # Verify movement_manager was called
        tool_deps.movement_manager.play_emotion.assert_called_once_with("excited")
        assert result["emotion"] == "excited"


# =============================================================================
# Property-Based Tests
# =============================================================================


class TestToolExecutionProperty:
    """Property-based tests for tool execution.

    Feature: elevenlabs-integration, Property 5: Tool Calls Execute Handlers
    **Validates: Requirements 6.4**

    Property Definition: For any registered tool and valid parameters, calling
    the tool should invoke the corresponding handler function and return its result.
    """

    @staticmethod
    def _create_tool_deps_with_mocks():
        """Create ToolDependencies with fresh mocks for each test iteration."""
        mock_reachy_mini = MagicMock()
        mock_movement_manager = MagicMock()
        mock_movement_manager.play_dance = AsyncMock()
        mock_movement_manager.play_emotion = AsyncMock()
        mock_camera_worker = MagicMock()
        # Create a simple test image (10x10 RGB)
        test_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        test_frame[5, 5] = [255, 0, 0]  # Red pixel in center
        mock_camera_worker.get_latest_frame.return_value = test_frame
        mock_head_wobbler = MagicMock()

        return ToolDependencies(
            reachy_mini=mock_reachy_mini,
            movement_manager=mock_movement_manager,
            camera_worker=mock_camera_worker,
            head_wobbler=mock_head_wobbler,
        )

    @settings(max_examples=100)
    @given(
        tool_name=st.sampled_from(["camera", "dance", "emotion"]),
        params=st.fixed_dictionaries(
            {},
            optional={
                "dance_name": st.text(min_size=1, max_size=50),
                "emotion": st.text(min_size=1, max_size=50),
            },
        ),
    )
    def test_tool_calls_execute_handlers(self, tool_name: str, params: dict):
        """Property test: Tool calls execute their corresponding handlers.

        Feature: elevenlabs-integration, Property 5: Tool Calls Execute Handlers
        **Validates: Requirements 6.4**

        For any registered tool and valid parameters, calling the tool should
        invoke the corresponding handler function and return its result.
        """
        # Create fresh mocks for each iteration
        deps = self._create_tool_deps_with_mocks()
        mock_client_tools = MagicMock()

        # Register tools
        register_tools(mock_client_tools, deps)

        # Get the registered handler for the selected tool
        calls = mock_client_tools.register.call_args_list
        tool_call = next(c for c in calls if c[0][0] == tool_name)
        handler = tool_call[0][1]
        is_async = tool_call[1]["is_async"]

        # Execute the handler
        if is_async:
            # Run async handler in event loop
            result = asyncio.run(handler(params))
        else:
            result = handler(params)

        # Verify the result is a dictionary (all tools return dicts)
        assert isinstance(result, dict), f"Tool {tool_name} should return a dict"

        # Verify the corresponding handler was invoked based on tool type
        if tool_name == "camera":
            # Camera tool should call get_latest_frame
            deps.camera_worker.get_latest_frame.assert_called_once()
            # Result should have either 'image' or 'error' key
            assert "image" in result or "error" in result

        elif tool_name == "dance":
            # Dance tool should call play_dance with the dance name
            expected_dance = params.get("dance_name", "default")
            deps.movement_manager.play_dance.assert_called_once_with(expected_dance)
            # Result should have status and dance keys
            assert result["status"] == "dancing"
            assert result["dance"] == expected_dance

        elif tool_name == "emotion":
            # Emotion tool should call play_emotion with the emotion
            expected_emotion = params.get("emotion", "happy")
            deps.movement_manager.play_emotion.assert_called_once_with(expected_emotion)
            # Result should have status and emotion keys
            assert result["status"] == "playing"
            assert result["emotion"] == expected_emotion

    @settings(max_examples=100)
    @given(dance_name=st.text(min_size=0, max_size=100))
    def test_dance_tool_handler_invoked_with_any_name(self, dance_name: str):
        """Property test: Dance handler is invoked with any dance name parameter.

        Feature: elevenlabs-integration, Property 5: Tool Calls Execute Handlers
        **Validates: Requirements 6.4**

        For any dance_name string, the dance tool handler should be invoked
        and pass the name to the movement manager.
        """
        deps = self._create_tool_deps_with_mocks()
        mock_client_tools = MagicMock()

        register_tools(mock_client_tools, deps)

        # Get dance handler
        calls = mock_client_tools.register.call_args_list
        dance_call = next(c for c in calls if c[0][0] == "dance")
        handler = dance_call[0][1]

        # Execute with the generated dance name
        params = {"dance_name": dance_name} if dance_name else {}
        result = asyncio.run(handler(params))

        # Verify handler was called with correct name
        expected_name = dance_name if dance_name else "default"
        deps.movement_manager.play_dance.assert_called_once_with(expected_name)
        assert result["dance"] == expected_name

    @settings(max_examples=100)
    @given(emotion=st.text(min_size=0, max_size=100))
    def test_emotion_tool_handler_invoked_with_any_emotion(self, emotion: str):
        """Property test: Emotion handler is invoked with any emotion parameter.

        Feature: elevenlabs-integration, Property 5: Tool Calls Execute Handlers
        **Validates: Requirements 6.4**

        For any emotion string, the emotion tool handler should be invoked
        and pass the emotion to the movement manager.
        """
        deps = self._create_tool_deps_with_mocks()
        mock_client_tools = MagicMock()

        register_tools(mock_client_tools, deps)

        # Get emotion handler
        calls = mock_client_tools.register.call_args_list
        emotion_call = next(c for c in calls if c[0][0] == "emotion")
        handler = emotion_call[0][1]

        # Execute with the generated emotion
        params = {"emotion": emotion} if emotion else {}
        result = asyncio.run(handler(params))

        # Verify handler was called with correct emotion
        expected_emotion = emotion if emotion else "happy"
        deps.movement_manager.play_emotion.assert_called_once_with(expected_emotion)
        assert result["emotion"] == expected_emotion


class TestToolErrorHandlingProperty:
    """Property-based tests for tool error handling.

    Feature: elevenlabs-integration, Property 6: Tool Errors Return Error Result
    **Validates: Requirements 8.3**

    Property Definition: For any tool handler that raises an exception, the tool
    execution should catch the exception and return an error result dictionary
    without propagating the exception.
    """

    @staticmethod
    def _create_tool_deps_with_mocks():
        """Create ToolDependencies with fresh mocks for each test iteration."""
        mock_reachy_mini = MagicMock()
        mock_movement_manager = MagicMock()
        mock_movement_manager.play_dance = AsyncMock()
        mock_movement_manager.play_emotion = AsyncMock()
        mock_camera_worker = MagicMock()
        # Create a simple test image (10x10 RGB)
        test_frame = np.zeros((10, 10, 3), dtype=np.uint8)
        test_frame[5, 5] = [255, 0, 0]  # Red pixel in center
        mock_camera_worker.get_latest_frame.return_value = test_frame
        mock_head_wobbler = MagicMock()

        return ToolDependencies(
            reachy_mini=mock_reachy_mini,
            movement_manager=mock_movement_manager,
            camera_worker=mock_camera_worker,
            head_wobbler=mock_head_wobbler,
        )

    @settings(max_examples=100)
    @given(error_message=st.text(min_size=1, max_size=200))
    def test_sync_tool_errors_return_error_result(self, error_message: str):
        """Property test: Sync tool errors return error result dict.

        Feature: elevenlabs-integration, Property 6: Tool Errors Return Error Result
        **Validates: Requirements 8.3**

        For any synchronous tool handler that raises an exception, the tool
        execution should catch the exception and return an error result dictionary
        without propagating the exception.
        """
        from reachy_mini_elevenlabs.tools.core_tools import safe_sync_tool_handler

        # Create a handler that raises an exception with the generated message
        def failing_handler(params: dict) -> dict:
            raise RuntimeError(error_message)

        # Wrap with safe handler
        safe_handler = safe_sync_tool_handler(failing_handler)

        # Execute - should NOT raise an exception
        result = safe_handler({})

        # Verify result is an error dict containing the error message
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "error" in result, "Result should contain 'error' key"
        assert error_message in result["error"], "Error message should be in result"

    @settings(max_examples=100)
    @given(error_message=st.text(min_size=1, max_size=200))
    def test_async_tool_errors_return_error_result(self, error_message: str):
        """Property test: Async tool errors return error result dict.

        Feature: elevenlabs-integration, Property 6: Tool Errors Return Error Result
        **Validates: Requirements 8.3**

        For any asynchronous tool handler that raises an exception, the tool
        execution should catch the exception and return an error result dictionary
        without propagating the exception.
        """
        from reachy_mini_elevenlabs.tools.core_tools import safe_async_tool_handler

        # Create an async handler that raises an exception with the generated message
        async def failing_handler(params: dict) -> dict:
            raise RuntimeError(error_message)

        # Wrap with safe handler
        safe_handler = safe_async_tool_handler(failing_handler)

        # Execute - should NOT raise an exception
        result = asyncio.run(safe_handler({}))

        # Verify result is an error dict containing the error message
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "error" in result, "Result should contain 'error' key"
        assert error_message in result["error"], "Error message should be in result"

    @settings(max_examples=100)
    @given(
        tool_name=st.sampled_from(["camera", "dance", "emotion"]),
        error_message=st.text(min_size=1, max_size=200),
    )
    def test_registered_tool_errors_return_error_result(
        self, tool_name: str, error_message: str
    ):
        """Property test: Registered tools catch errors and return error dicts.

        Feature: elevenlabs-integration, Property 6: Tool Errors Return Error Result
        **Validates: Requirements 8.3**

        For any registered tool that raises an exception during execution,
        the error should be caught and returned as an error dictionary.
        """
        deps = self._create_tool_deps_with_mocks()
        mock_client_tools = MagicMock()

        # Configure mocks to raise exceptions
        deps.camera_worker.get_latest_frame.side_effect = RuntimeError(error_message)
        deps.movement_manager.play_dance.side_effect = RuntimeError(error_message)
        deps.movement_manager.play_emotion.side_effect = RuntimeError(error_message)

        # Register tools with error-handling wrappers
        register_tools(mock_client_tools, deps)

        # Get the registered handler for the selected tool
        calls = mock_client_tools.register.call_args_list
        tool_call = next(c for c in calls if c[0][0] == tool_name)
        handler = tool_call[0][1]
        is_async = tool_call[1]["is_async"]

        # Execute the handler - should NOT raise an exception
        if is_async:
            result = asyncio.run(handler({}))
        else:
            result = handler({})

        # Verify result is an error dict containing the error message
        assert isinstance(result, dict), f"Tool {tool_name} should return a dict"
        assert "error" in result, f"Tool {tool_name} should return error dict on exception"
        assert error_message in result["error"], "Error message should be preserved"

    @settings(max_examples=100)
    @given(
        exception_type=st.sampled_from([
            ValueError,
            TypeError,
            RuntimeError,
            KeyError,
            AttributeError,
            IOError,
        ]),
        error_message=st.text(min_size=1, max_size=100),
    )
    def test_various_exception_types_return_error_result(
        self, exception_type: type, error_message: str
    ):
        """Property test: Various exception types are caught and return error dicts.

        Feature: elevenlabs-integration, Property 6: Tool Errors Return Error Result
        **Validates: Requirements 8.3**

        For any type of exception raised by a tool handler, the exception should
        be caught and returned as an error dictionary.
        """
        from reachy_mini_elevenlabs.tools.core_tools import safe_sync_tool_handler

        # Create a handler that raises the specified exception type
        def failing_handler(params: dict) -> dict:
            raise exception_type(error_message)

        # Wrap with safe handler
        safe_handler = safe_sync_tool_handler(failing_handler)

        # Execute - should NOT raise an exception
        result = safe_handler({})

        # Verify result is an error dict
        assert isinstance(result, dict), "Result should be a dictionary"
        assert "error" in result, "Result should contain 'error' key"
        # The error message should be non-empty (str(exception) produces some output)
        # Note: KeyError wraps the message in quotes, so we just verify the error key exists
        # and contains a string representation of the exception
        assert isinstance(result["error"], str), "Error value should be a string"
        assert len(result["error"]) > 0 or error_message == "", "Error should have content"
