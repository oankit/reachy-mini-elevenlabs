"""Entrypoint for the Reachy Mini ElevenLabs conversation app.

This module provides the main entry point and app class for the ElevenLabs
integration with Reachy Mini. It follows the standard Reachy Mini app structure
for integration with the host system.
"""

from __future__ import annotations
import sys
import time
import asyncio
import argparse
import logging
import threading
from typing import TYPE_CHECKING

from reachy_mini import ReachyMini, ReachyMiniApp
from reachy_mini_elevenlabs.tools.core_tools import ToolDependencies
from reachy_mini_elevenlabs.audio.head_wobbler import HeadWobbler
from reachy_mini_elevenlabs.elevenlabs_handler import ElevenLabsHandler
from reachy_mini_elevenlabs.utils import (
    parse_args,
    setup_logger,
    log_connection_troubleshooting,
)


if TYPE_CHECKING:
    from fastapi import FastAPI


logger = logging.getLogger(__name__)


def main() -> None:
    """Console script entry point for reachy-mini-elevenlabs command."""
    args, _ = parse_args()
    run(args)


def run(
    args: argparse.Namespace,
    robot: ReachyMini | None = None,
    app_stop_event: threading.Event | None = None,
    settings_app: "FastAPI | None" = None,
    instance_path: str | None = None,
) -> None:
    """Run the Reachy Mini ElevenLabs conversation app.

    This function initializes all components and starts the ElevenLabs
    conversation session. It blocks until the conversation ends or
    the stop event is set.

    Args:
        args: Parsed command line arguments.
        robot: Optional pre-initialized ReachyMini instance.
        app_stop_event: Optional threading event to signal app shutdown.
        settings_app: Optional FastAPI app for settings UI.
        instance_path: Optional path to instance directory for configuration.

    """
    # Import MovementManager here to avoid slowing down dashboard loading
    from reachy_mini_elevenlabs.moves import MovementManager
    from reachy_mini_elevenlabs.camera_worker import CameraWorker
    from pathlib import Path
    from reachy_mini_elevenlabs.config import config

    app_logger = setup_logger(args.debug)
    
    # Log version information
    try:
        from importlib.metadata import version
        app_version = version("reachy_mini_elevenlabs")
        app_logger.info(f"Starting Reachy Mini ElevenLabs App v{app_version}")
    except Exception:
        app_logger.info("Starting Reachy Mini ElevenLabs App")

    # Try to load an existing instance .env first (covers subsequent runs)
    if instance_path:
        try:
            from dotenv import load_dotenv

            env_path = Path(instance_path) / ".env"
            if env_path.exists():
                load_dotenv(dotenv_path=str(env_path), override=True)
                # Reload config with newly loaded values
                config.reload()
        except Exception:
            pass

    # Mount settings UI if a settings app is available
    if settings_app is not None:
        try:
            from reachy_mini_elevenlabs.settings_ui import mount_settings_routes

            mount_settings_routes(settings_app, instance_path)
        except Exception as e:
            app_logger.warning(f"Failed to mount settings UI: {e}")

    # Check if configuration is missing and wait for it via settings UI
    missing_config = config.validate()
    if missing_config:
        if settings_app is not None:
            app_logger.info(
                f"Waiting for configuration: {', '.join(missing_config)}. "
                "Open the app settings page at the configured port to enter credentials."
            )
            # Poll until configuration becomes available (silently)
            try:
                while True:
                    # Check without logging errors
                    if not config.ELEVENLABS_AGENT_ID:
                        time.sleep(0.5)
                        # Reload config to pick up changes
                        config.reload()
                    else:
                        break
            except KeyboardInterrupt:
                app_logger.info("Interrupted while waiting for configuration.")
                return
        else:
            app_logger.error(
                f"Missing required configuration: {', '.join(missing_config)}. "
                "Please set environment variables or provide a .env file."
            )
            sys.exit(1)

    # Initialize robot if not provided
    if robot is None:
        try:
            robot_kwargs: dict[str, str] = {}
            if args.robot_name is not None:
                robot_kwargs["robot_name"] = args.robot_name

            app_logger.info("Initializing ReachyMini (SDK will auto-detect appropriate backend)")
            robot = ReachyMini(**robot_kwargs)

        except TimeoutError as e:
            app_logger.error(
                "Connection timeout: Failed to connect to Reachy Mini daemon. "
                f"Details: {e}"
            )
            log_connection_troubleshooting(app_logger, args.robot_name)
            sys.exit(1)

        except ConnectionError as e:
            app_logger.error(
                "Connection failed: Unable to establish connection to Reachy Mini. "
                f"Details: {e}"
            )
            log_connection_troubleshooting(app_logger, args.robot_name)
            sys.exit(1)

        except Exception as e:
            app_logger.error(
                f"Unexpected error during robot initialization: {type(e).__name__}: {e}"
            )
            app_logger.error("Please check your configuration and try again.")
            sys.exit(1)

    # Initialize camera worker if camera is enabled
    camera_worker: CameraWorker | None = None
    if not args.no_camera:
        camera_worker = CameraWorker(robot, head_tracker=None)

    # Initialize MovementManager for robot movements
    movement_manager = MovementManager(
        current_robot=robot,
        camera_worker=camera_worker,
    )

    # Initialize HeadWobbler for lip-sync animation
    head_wobbler = HeadWobbler(set_speech_offsets=movement_manager.set_speech_offsets)

    # Create tool dependencies
    deps = ToolDependencies(
        reachy_mini=robot,
        movement_manager=movement_manager,
        camera_worker=camera_worker,
        head_wobbler=head_wobbler,
    )

    # Initialize idle emotion manager
    from reachy_mini_elevenlabs.idle_emotions import IdleEmotionManager
    idle_emotion_manager = IdleEmotionManager(
        deps=deps,
        enabled=config.ENABLE_IDLE_EMOTIONS,
        min_delay=config.IDLE_EMOTION_MIN_DELAY,
        max_delay=config.IDLE_EMOTION_MAX_DELAY,
    )

    # Create ElevenLabs handler
    handler = ElevenLabsHandler(deps, instance_path=instance_path)

    # Start background threads
    movement_manager.start()
    head_wobbler.start()
    idle_emotion_manager.start()  # Start idle emotions
    if camera_worker:
        camera_worker.start()

    app_logger.info("Background threads started")

    # Set up stop event polling
    def poll_stop_event() -> None:
        """Poll the stop event to allow graceful shutdown."""
        if app_stop_event is not None:
            app_stop_event.wait()

        app_logger.info("App stop event detected, shutting down...")
        try:
            handler.stop()
        except Exception as e:
            app_logger.error(f"Error while stopping handler: {e}")

    if app_stop_event:
        threading.Thread(target=poll_stop_event, daemon=True).start()

    try:
        # Start the ElevenLabs conversation
        handler.start()
        app_logger.info("ElevenLabs conversation started")

        # Wait for the conversation to end (blocking)
        conversation_id = handler.wait_for_end()
        app_logger.info(f"Conversation ended with ID: {conversation_id}")

    except KeyboardInterrupt:
        app_logger.info("Keyboard interruption in main thread... shutting down.")
        handler.stop()
    except Exception as e:
        app_logger.error(f"Error during conversation: {e}")
        handler.stop()
    finally:
        # Clean shutdown of all components
        app_logger.info("Cleaning up...")

        movement_manager.stop()
        head_wobbler.stop()
        idle_emotion_manager.stop()  # Stop idle emotions
        if camera_worker:
            camera_worker.stop()

        # Ensure media is explicitly closed before disconnecting
        try:
            robot.media.close()
        except Exception as e:
            app_logger.debug(f"Error closing media during shutdown: {e}")

        # Prevent connection from keeping threads alive
        robot.client.disconnect()
        time.sleep(1)
        app_logger.info("Shutdown complete.")


class ReachyMiniElevenlabs(ReachyMiniApp):  # type: ignore[misc]
    """Reachy Mini Apps entry point for the ElevenLabs conversation app.

    This class extends ReachyMiniApp to integrate with the Reachy Mini
    host system's app discovery and launch mechanisms.

    Attributes:
        custom_app_url: URL where the app's web interface is served.
        dont_start_webserver: Whether to skip starting the web server.

    """

    description = "ElevenLabs Conversational AI Agents integration for Reachy Mini"
    custom_app_url = "http://0.0.0.0:7861/"
    dont_start_webserver = False

    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event) -> None:
        """Run the ElevenLabs conversation app.

        This method is called by the Reachy Mini host system to start
        the app. It sets up an asyncio event loop and delegates to
        the main run() function.

        Args:
            reachy_mini: The ReachyMini robot instance provided by the host.
            stop_event: Threading event to signal when the app should stop.

        """
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        args, _ = parse_args()

        instance_path = self._get_instance_path().parent
        run(
            args,
            robot=reachy_mini,
            app_stop_event=stop_event,
            settings_app=self.settings_app,
            instance_path=instance_path,
        )


if __name__ == "__main__":
    app = ReachyMiniElevenlabs()
    try:
        app.wrapped_run()
    except KeyboardInterrupt:
        app.stop()
