"""Configuration management for ElevenLabs integration.

This module handles loading and validating configuration from environment
variables and `.env` files using python-dotenv.

Get your ElevenLabs agent at: https://try.elevenlabs.io/reachy-mini-agents
"""

from __future__ import annotations
import os
import logging

from dotenv import load_dotenv


logger = logging.getLogger(__name__)


class Config:
    """Configuration for the ElevenLabs app.

    Loads configuration from environment variables and `.env` files.
    The ELEVENLABS_AGENT_ID is required for all operations.
    The ELEVENLABS_API_KEY is optional but required for private agents.
    """

    def __init__(self) -> None:
        """Initialize configuration by loading from environment."""
        # Load from .env file if present (does not override existing env vars)
        load_dotenv()

        # Required: Agent ID from ElevenLabs dashboard
        self.ELEVENLABS_AGENT_ID: str | None = os.getenv("ELEVENLABS_AGENT_ID") or None

        # Optional: API key (required for private agents)
        self.ELEVENLABS_API_KEY: str | None = os.getenv("ELEVENLABS_API_KEY") or None

        # Emotion detection settings
        self.ENABLE_EMOTION_DETECTION: bool = os.getenv("ENABLE_EMOTION_DETECTION", "true").lower() in ("true", "1", "yes")
        self.EMOTION_CONFIDENCE_THRESHOLD: float = float(os.getenv("EMOTION_CONFIDENCE_THRESHOLD", "0.3"))
        self.EMOTION_COOLDOWN_SECONDS: float = float(os.getenv("EMOTION_COOLDOWN_SECONDS", "3.0"))

        # Idle emotion settings
        self.ENABLE_IDLE_EMOTIONS: bool = os.getenv("ENABLE_IDLE_EMOTIONS", "true").lower() in ("true", "1", "yes")
        self.IDLE_EMOTION_MIN_DELAY: float = float(os.getenv("IDLE_EMOTION_MIN_DELAY", "3.0"))
        self.IDLE_EMOTION_MAX_DELAY: float = float(os.getenv("IDLE_EMOTION_MAX_DELAY", "8.0"))

    def validate(self, log_errors: bool = True) -> list[str]:
        """Return list of missing required configuration.

        Args:
            log_errors: Whether to log errors for missing configuration.

        Returns
        -------
            List of missing configuration variable names. Empty list if all
            required configuration is present.

        """
        errors: list[str] = []

        if not self.ELEVENLABS_AGENT_ID:
            errors.append("ELEVENLABS_AGENT_ID")
            if log_errors:
                logger.error("Missing required configuration: ELEVENLABS_AGENT_ID")

        return errors

    def log_missing_api_key_warning(self) -> None:
        """Log a warning if API key is missing.

        This should be called when attempting to connect to a private agent
        without an API key configured.
        """
        if not self.ELEVENLABS_API_KEY:
            logger.error(
                "Missing configuration: ELEVENLABS_API_KEY. "
                "This is required for private agents."
            )

    def reload(self) -> None:
        """Reload configuration from environment.

        Useful after updating the .env file programmatically.
        """
        # Force reload of .env file
        load_dotenv(override=True)

        # Re-read values
        self.ELEVENLABS_AGENT_ID = os.getenv("ELEVENLABS_AGENT_ID") or None
        self.ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY") or None
        self.ENABLE_EMOTION_DETECTION = os.getenv("ENABLE_EMOTION_DETECTION", "true").lower() in ("true", "1", "yes")
        self.EMOTION_CONFIDENCE_THRESHOLD = float(os.getenv("EMOTION_CONFIDENCE_THRESHOLD", "0.3"))
        self.EMOTION_COOLDOWN_SECONDS = float(os.getenv("EMOTION_COOLDOWN_SECONDS", "3.0"))
        self.ENABLE_IDLE_EMOTIONS = os.getenv("ENABLE_IDLE_EMOTIONS", "true").lower() in ("true", "1", "yes")
        self.IDLE_EMOTION_MIN_DELAY = float(os.getenv("IDLE_EMOTION_MIN_DELAY", "3.0"))
        self.IDLE_EMOTION_MAX_DELAY = float(os.getenv("IDLE_EMOTION_MAX_DELAY", "8.0"))


# Global configuration instance
config = Config()
