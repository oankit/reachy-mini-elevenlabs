"""ElevenLabs conversation handler for Reachy Mini.

This module manages the ElevenLabs Conversation lifecycle and coordinates
with the audio interface, HeadWobbler, and tool registration.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from elevenlabs import ElevenLabs
from elevenlabs.conversational_ai.conversation import ClientTools, Conversation

from reachy_mini_elevenlabs.audio_interface import ReachyAudioInterface
from reachy_mini_elevenlabs.config import config
from reachy_mini_elevenlabs.tools.core_tools import ToolDependencies, register_tools

if TYPE_CHECKING:
    pass


logger = logging.getLogger(__name__)


# Constants for reconnection logic
DEFAULT_MAX_RECONNECT_ATTEMPTS = 5
DEFAULT_INITIAL_BACKOFF_SECONDS = 1.0
DEFAULT_MAX_BACKOFF_SECONDS = 30.0
DEFAULT_BACKOFF_MULTIPLIER = 2.0


class ElevenLabsHandler:
    """Manages ElevenLabs Conversation and coordinates components.

    This class is responsible for:
    - Creating and configuring the ElevenLabs client
    - Setting up the custom ReachyAudioInterface for robot audio I/O
    - Registering client tools that the agent can call
    - Managing the conversation session lifecycle (start/stop)
    - Handling callbacks for agent responses and user transcripts
    - Handling connection failures with exponential backoff
    - Restarting sessions on unexpected termination

    Attributes:
        deps: Tool dependencies containing robot and component references.
        instance_path: Optional path to instance directory for configuration.
        client: The ElevenLabs client instance.
        conversation: The active Conversation instance.
        audio_interface: The custom audio interface for robot audio.
        max_reconnect_attempts: Maximum number of reconnection attempts.
        initial_backoff: Initial backoff time in seconds.
        max_backoff: Maximum backoff time in seconds.
        backoff_multiplier: Multiplier for exponential backoff.
        _should_restart: Flag indicating if session should restart on end.
        _stop_requested: Flag indicating if stop was explicitly requested.
    """

    def __init__(
        self,
        deps: ToolDependencies,
        instance_path: str | None = None,
        max_reconnect_attempts: int = DEFAULT_MAX_RECONNECT_ATTEMPTS,
        initial_backoff: float = DEFAULT_INITIAL_BACKOFF_SECONDS,
        max_backoff: float = DEFAULT_MAX_BACKOFF_SECONDS,
        backoff_multiplier: float = DEFAULT_BACKOFF_MULTIPLIER,
    ) -> None:
        """Initialize the ElevenLabs handler.

        Args:
            deps: Tool dependencies containing reachy_mini, movement_manager,
                camera_worker, and head_wobbler references.
            instance_path: Optional path to instance directory for configuration
                persistence.
            max_reconnect_attempts: Maximum number of reconnection attempts on failure.
            initial_backoff: Initial backoff time in seconds for reconnection.
            max_backoff: Maximum backoff time in seconds for reconnection.
            backoff_multiplier: Multiplier for exponential backoff.
        """
        self.deps = deps
        self.instance_path = instance_path
        self.client: ElevenLabs | None = None
        self.conversation: Conversation | None = None
        self.audio_interface: ReachyAudioInterface | None = None

        # Reconnection configuration
        self.max_reconnect_attempts = max_reconnect_attempts
        self.initial_backoff = initial_backoff
        self.max_backoff = max_backoff
        self.backoff_multiplier = backoff_multiplier

        # Internal state
        self._should_restart = True
        self._stop_requested = False
        self._last_conversation_id: str = ""

    def start(self) -> None:
        """Initialize and start the conversation session.

        Creates the ElevenLabs client, audio interface, client tools,
        and conversation instance, then starts the session.

        Handles WebSocket connection failures with detailed logging.

        Raises:
            ValueError: If required configuration (ELEVENLABS_AGENT_ID) is missing.
            ConnectionError: If WebSocket connection fails after all retry attempts.
        """
        # Validate configuration
        missing = config.validate()
        if missing:
            error_msg = f"Missing required configuration: {', '.join(missing)}"
            logger.error(error_msg)
            logger.error(
                "Please set the following environment variables or provide them "
                "via the settings UI:"
            )
            for item in missing:
                logger.error(f"  - {item}")
            raise ValueError(error_msg)

        logger.info("Starting ElevenLabs conversation handler")
        self._stop_requested = False

        # Create ElevenLabs client
        # API key can be None for public agents
        self.client = ElevenLabs(api_key=config.ELEVENLABS_API_KEY)
        logger.debug("ElevenLabs client created")

        # Create custom audio interface
        self.audio_interface = ReachyAudioInterface(
            robot=self.deps.reachy_mini,
            head_wobbler=self.deps.head_wobbler,
        )
        logger.debug("Audio interface created")

        # Create client tools and register handlers
        client_tools = self._create_client_tools()
        logger.debug("Client tools registered")

        # Create conversation with all components
        # requires_auth is True if an API key is provided and non-empty (for private agents)
        api_key = config.ELEVENLABS_API_KEY
        requires_auth = bool(api_key and api_key.strip())

        self._create_conversation(client_tools, requires_auth)

        # Start the conversation session with retry logic
        self._start_session_with_retry()

    def stop(self) -> None:
        """End the conversation session.

        Gracefully ends the active conversation session if one exists.
        Sets the stop flag to prevent automatic session restart.
        """
        self._stop_requested = True
        self._should_restart = False

        if self.conversation:
            logger.info("Stopping ElevenLabs conversation session")
            try:
                self.conversation.end_session()
                logger.info("ElevenLabs conversation session ended")
            except Exception as e:
                logger.warning(f"Error while ending conversation session: {e}")

    def wait_for_end(self) -> str:
        """Block until conversation ends, return conversation ID.

        This method blocks the calling thread until the conversation
        session ends (either normally or due to an error).

        If the session ends unexpectedly (not due to explicit stop()),
        this method will attempt to restart the session automatically.

        Returns:
            The conversation ID string, or empty string if no conversation.
        """
        if not self.conversation:
            return ""

        while True:
            logger.debug("Waiting for conversation session to end")
            try:
                conversation_id = self.conversation.wait_for_session_end()
                self._last_conversation_id = conversation_id
                logger.info(f"Conversation ended with ID: {conversation_id}")

                # Check if we should restart the session
                if self._should_restart and not self._stop_requested:
                    logger.warning(
                        f"Conversation session ended unexpectedly "
                        f"(ID: {conversation_id}). Attempting to restart..."
                    )
                    if self._attempt_session_restart():
                        # Successfully restarted, continue waiting
                        continue
                    else:
                        logger.error(
                            "Failed to restart conversation session after "
                            "maximum retry attempts"
                        )

                return conversation_id

            except Exception as e:
                logger.error(f"Error while waiting for session end: {e}")
                if self._should_restart and not self._stop_requested:
                    if self._attempt_session_restart():
                        continue
                return self._last_conversation_id

    def _create_client_tools(self) -> ClientTools:
        """Create and register custom tools.

        Creates a ClientTools instance and registers all available tools
        (camera, dance, emotion) with their handlers.

        Returns:
            Configured ClientTools instance with all tools registered.
        """
        client_tools = ClientTools()
        register_tools(client_tools, self.deps)
        return client_tools

    def _on_agent_response(self, response: str) -> None:
        """Callback for agent text responses.

        Called when the agent produces a text response. Used for logging
        and potentially for displaying the response in a UI.

        Args:
            response: The text response from the agent.
        """
        logger.info(f"Agent: {response}")

    def _on_user_transcript(self, transcript: str) -> None:
        """Callback for user speech transcripts.

        Called when the user's speech is transcribed. Used for logging
        and potentially for displaying the transcript in a UI.

        Args:
            transcript: The transcribed text from the user's speech.
        """
        logger.info(f"User: {transcript}")

    def _create_conversation(
        self,
        client_tools: ClientTools,
        requires_auth: bool,
    ) -> None:
        """Create a new Conversation instance.

        Args:
            client_tools: The ClientTools instance with registered tools.
            requires_auth: Whether authentication is required.
        """
        self.conversation = Conversation(
            client=self.client,
            agent_id=config.ELEVENLABS_AGENT_ID,
            requires_auth=requires_auth,
            audio_interface=self.audio_interface,
            client_tools=client_tools,
            callback_agent_response=self._on_agent_response,
            callback_user_transcript=self._on_user_transcript,
        )
        logger.debug("Conversation instance created")

    def _start_session_with_retry(self) -> None:
        """Start the conversation session with exponential backoff retry.

        Attempts to start the session, retrying on WebSocket connection
        failures with exponential backoff.

        Raises:
            ConnectionError: If all retry attempts fail.
        """
        backoff = self.initial_backoff
        last_error: Exception | None = None

        for attempt in range(self.max_reconnect_attempts):
            try:
                self.conversation.start_session()
                logger.info("ElevenLabs conversation session started")
                return

            except Exception as e:
                last_error = e
                self._log_connection_error(e, attempt + 1)

                if attempt < self.max_reconnect_attempts - 1:
                    logger.info(
                        f"Retrying in {backoff:.1f} seconds... "
                        f"(attempt {attempt + 2}/{self.max_reconnect_attempts})"
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * self.backoff_multiplier, self.max_backoff)

        # All attempts failed
        error_msg = (
            f"Failed to start ElevenLabs conversation after "
            f"{self.max_reconnect_attempts} attempts"
        )
        logger.error(error_msg)
        raise ConnectionError(error_msg) from last_error

    def _attempt_session_restart(self) -> bool:
        """Attempt to restart the conversation session.

        Uses exponential backoff for retry attempts.

        Returns:
            True if session was successfully restarted, False otherwise.
        """
        backoff = self.initial_backoff

        for attempt in range(self.max_reconnect_attempts):
            try:
                logger.info(
                    f"Attempting session restart "
                    f"(attempt {attempt + 1}/{self.max_reconnect_attempts})"
                )

                # Recreate conversation components
                client_tools = self._create_client_tools()
                api_key = config.ELEVENLABS_API_KEY
                requires_auth = bool(api_key and api_key.strip())
                self._create_conversation(client_tools, requires_auth)

                # Start the new session
                self.conversation.start_session()
                logger.info("Session restart successful")
                return True

            except Exception as e:
                self._log_connection_error(e, attempt + 1, is_restart=True)

                if attempt < self.max_reconnect_attempts - 1:
                    logger.info(
                        f"Retrying restart in {backoff:.1f} seconds... "
                        f"(attempt {attempt + 2}/{self.max_reconnect_attempts})"
                    )
                    time.sleep(backoff)
                    backoff = min(backoff * self.backoff_multiplier, self.max_backoff)

        return False

    def _log_connection_error(
        self,
        error: Exception,
        attempt: int,
        is_restart: bool = False,
    ) -> None:
        """Log detailed information about a connection error.

        Args:
            error: The exception that occurred.
            attempt: The current attempt number.
            is_restart: Whether this is a restart attempt.
        """
        action = "restart" if is_restart else "start"
        error_type = type(error).__name__

        logger.error(
            f"WebSocket connection failure during session {action} "
            f"(attempt {attempt}/{self.max_reconnect_attempts})"
        )
        logger.error(f"  Error type: {error_type}")
        logger.error(f"  Error details: {error}")

        # Log additional context for common error types
        if "websocket" in str(error).lower() or "connection" in str(error).lower():
            logger.error("  Possible causes:")
            logger.error("    - Network connectivity issues")
            logger.error("    - ElevenLabs service unavailable")
            logger.error("    - Invalid agent ID or API key")
            logger.error("    - Firewall blocking WebSocket connections")

        if "auth" in str(error).lower() or "401" in str(error):
            logger.error("  Authentication error detected:")
            logger.error("    - Check that ELEVENLABS_API_KEY is valid")
            logger.error("    - Verify the agent requires authentication")

    def disable_auto_restart(self) -> None:
        """Disable automatic session restart on unexpected end.

        Call this method if you want the handler to not automatically
        restart sessions when they end unexpectedly.
        """
        self._should_restart = False

    def enable_auto_restart(self) -> None:
        """Enable automatic session restart on unexpected end.

        This is the default behavior. Call this method to re-enable
        auto-restart if it was previously disabled.
        """
        self._should_restart = True
