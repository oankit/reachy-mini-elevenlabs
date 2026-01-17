"""Core tool dependencies and registration for ElevenLabs integration."""

from __future__ import annotations

import base64
import functools
import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, TypeVar

import cv2
from elevenlabs.conversational_ai.conversation import ClientTools

if TYPE_CHECKING:
    from reachy_mini import ReachyMini
    from reachy_mini_elevenlabs.audio.head_wobbler import HeadWobbler

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class ToolDependencies:
    """Dependencies shared across tools.

    This dataclass holds references to the robot and its components
    that tools need to perform actions like capturing images,
    triggering dances, or playing emotions.
    """

    reachy_mini: "ReachyMini"
    """The Reachy Mini robot instance for hardware access."""

    movement_manager: Any
    """MovementManager for coordinating robot movements and animations."""

    camera_worker: Any | None
    """CameraWorker for frame capture, or None if camera is unavailable."""

    head_wobbler: "HeadWobbler"
    """HeadWobbler for audio-reactive head movements (lip-sync)."""


def safe_sync_tool_handler(handler: Callable[[dict], dict]) -> Callable[[dict], dict]:
    """Wrap a synchronous tool handler to catch exceptions and return error dicts.

    This decorator ensures that any exception raised by a tool handler is caught
    and converted to an error result dictionary, preventing the exception from
    propagating and crashing the conversation.

    Args:
        handler: The synchronous tool handler function to wrap.

    Returns:
        A wrapped handler that catches exceptions and returns error dicts.
    """

    @functools.wraps(handler)
    def wrapper(params: dict) -> dict:
        try:
            return handler(params)
        except Exception as e:
            logger.exception(f"Tool handler error: {e}")
            return {"error": str(e)}

    return wrapper


def safe_async_tool_handler(
    handler: Callable[[dict], Any]
) -> Callable[[dict], Any]:
    """Wrap an async tool handler to catch exceptions and return error dicts.

    This decorator ensures that any exception raised by an async tool handler
    is caught and converted to an error result dictionary, preventing the
    exception from propagating and crashing the conversation.

    Args:
        handler: The async tool handler function to wrap.

    Returns:
        A wrapped async handler that catches exceptions and returns error dicts.
    """

    @functools.wraps(handler)
    async def wrapper(params: dict) -> dict:
        try:
            return await handler(params)
        except Exception as e:
            logger.exception(f"Tool handler error: {e}")
            return {"error": str(e)}

    return wrapper


def camera_tool(deps: ToolDependencies) -> dict:
    """Capture image from robot camera.

    Args:
        deps: Tool dependencies containing camera_worker.

    Returns:
        Dictionary with base64-encoded JPEG image or error message.
    """
    if deps.camera_worker is None:
        return {"error": "Camera not available"}
    frame = deps.camera_worker.get_latest_frame()
    if frame is None:
        return {"error": "No frame available"}
    # Encode as base64 JPEG
    _, buffer = cv2.imencode(".jpg", frame)
    b64_image = base64.b64encode(buffer).decode("utf-8")
    return {"image": b64_image}


async def dance_tool(deps: ToolDependencies, params: dict) -> dict:
    """Trigger a dance animation.

    Args:
        deps: Tool dependencies containing movement_manager.
        params: Parameters dict with optional "dance_name" key.

    Returns:
        Dictionary with status and dance name.
    """
    dance_name = params.get("dance_name", "default")
    await deps.movement_manager.play_dance(dance_name)
    return {"status": "dancing", "dance": dance_name}


async def emotion_tool(deps: ToolDependencies, params: dict) -> dict:
    """Play an emotion animation.

    Args:
        deps: Tool dependencies containing movement_manager.
        params: Parameters dict with optional "emotion" key.

    Returns:
        Dictionary with status and emotion name.
    """
    emotion = params.get("emotion", "happy")
    await deps.movement_manager.play_emotion(emotion)
    return {"status": "playing", "emotion": emotion}


def register_tools(client_tools: ClientTools, deps: ToolDependencies) -> None:
    """Register all available tools with ClientTools.

    This function registers the camera, dance, and emotion tools with the
    ElevenLabs ClientTools instance. Each tool is wrapped to inject the
    dependencies and to catch any exceptions, returning error dicts instead
    of propagating exceptions.

    Args:
        client_tools: The ElevenLabs ClientTools instance to register with.
        deps: Tool dependencies to inject into each tool handler.
    """

    def _camera_handler(params: dict) -> dict:
        """Wrapper for camera_tool that injects dependencies."""
        return camera_tool(deps)

    async def _dance_handler(params: dict) -> dict:
        """Wrapper for dance_tool that injects dependencies."""
        return await dance_tool(deps, params)

    async def _emotion_handler(params: dict) -> dict:
        """Wrapper for emotion_tool that injects dependencies."""
        return await emotion_tool(deps, params)

    # Wrap handlers with error handling to catch exceptions and return error dicts
    client_tools.register("camera", safe_sync_tool_handler(_camera_handler), is_async=False)
    client_tools.register("dance", safe_async_tool_handler(_dance_handler), is_async=True)
    client_tools.register("emotion", safe_async_tool_handler(_emotion_handler), is_async=True)
