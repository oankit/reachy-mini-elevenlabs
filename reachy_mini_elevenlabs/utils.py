"""Utility functions for the Reachy Mini ElevenLabs app.

This module provides command-line argument parsing, logging configuration,
and other utility functions used throughout the application.
"""

from __future__ import annotations

import logging
import argparse
import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


def parse_args() -> tuple[argparse.Namespace, list[str]]:
    """Parse command line arguments.

    Returns
    -------
        Tuple of (parsed arguments, remaining arguments).

    """
    parser = argparse.ArgumentParser("Reachy Mini ElevenLabs App")
    parser.add_argument(
        "--debug",
        default=False,
        action="store_true",
        help="Enable debug logging",
    )
    parser.add_argument(
        "--robot-name",
        type=str,
        default=None,
        help=(
            "[Optional] Robot name/prefix for Zenoh topics "
            "(must match daemon's --robot-name). "
            "Only needed for development with multiple robots."
        ),
    )
    parser.add_argument(
        "--no-camera",
        default=False,
        action="store_true",
        help="Disable camera usage",
    )
    parser.add_argument(
        "--gradio",
        default=False,
        action="store_true",
        help="Open Gradio settings interface",
    )
    return parser.parse_known_args()


def setup_logger(debug: bool) -> logging.Logger:
    """Set up the logger with appropriate log level.

    Args:
        debug: If True, enable debug logging.

    Returns
    -------
        Configured logger instance.

    """
    log_level = "DEBUG" if debug else "INFO"
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s:%(lineno)d | %(message)s",
    )
    logger = logging.getLogger(__name__)

    # Suppress WebRTC warnings
    warnings.filterwarnings("ignore", message=".*AVCaptureDeviceTypeExternal.*")
    warnings.filterwarnings("ignore", category=UserWarning, module="aiortc")

    # Tame third-party noise (looser in DEBUG)
    if log_level == "DEBUG":
        logging.getLogger("elevenlabs").setLevel(logging.INFO)
        logging.getLogger("websockets").setLevel(logging.INFO)
    else:
        logging.getLogger("elevenlabs").setLevel(logging.WARNING)
        logging.getLogger("websockets").setLevel(logging.WARNING)

    return logger


def log_connection_troubleshooting(logger: logging.Logger, robot_name: str | None) -> None:
    """Log troubleshooting steps for connection issues.

    Args:
        logger: Logger instance to use.
        robot_name: Optional robot name that was used for connection.

    """
    logger.error("Troubleshooting steps:")
    logger.error("  1. Verify reachy-mini-daemon is running")

    if robot_name is not None:
        logger.error(
            f"  2. Daemon must be started with: --robot-name '{robot_name}'"
        )
    else:
        logger.error(
            "  2. If daemon uses --robot-name, add the same flag here: "
            "--robot-name <name>"
        )

    logger.error("  3. For wireless: check network connectivity")
    logger.error("  4. Review daemon logs")
    logger.error("  5. Restart the daemon")
