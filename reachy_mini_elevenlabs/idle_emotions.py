"""Idle emotion system for continuous subtle expressions.

ATTRIBUTION NOTICE:
Idle emotion concept inspired by reachy_mini_conversation_app breathing system
Original work Copyright (c) Pollen Robotics
Licensed under the Apache License, Version 2.0
Source: https://github.com/pollen-robotics/reachy_mini_conversation_app

This module implements continuous idle emotions instead of just breathing.
"""

from __future__ import annotations

import logging
import random
import time
import threading
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reachy_mini_elevenlabs.tools.core_tools import ToolDependencies

logger = logging.getLogger(__name__)

# Initialize emotion library
try:
    from reachy_mini.motion.recorded_move import RecordedMoves
    from reachy_mini_elevenlabs.dance_emotion_moves import EmotionQueueMove

    RECORDED_MOVES = RecordedMoves("pollen-robotics/reachy-mini-emotions-library")
    EMOTION_AVAILABLE = True
except ImportError as e:
    logger.warning(f"Emotion library not available for idle emotions: {e}")
    RECORDED_MOVES = None
    EMOTION_AVAILABLE = False
    EmotionQueueMove = None  # type: ignore


# Idle emotions - subtle, contemplative, attentive expressions
IDLE_EMOTIONS = [
    "understanding1",
    "understanding2",
    "indifferent1",
    "curious1",
    "attentive1",
    "attentive2",
    "shy1",
    "serenity1",
    "proud1",
    "proud2",
    "proud3",
    "thoughtful1",
    "thoughtful2",
]


class IdleEmotionManager:
    """Manages continuous idle emotions for the robot.

    This system ensures the robot is always expressing something subtle
    when not actively responding or performing other actions.

    Attributes:
        deps: Tool dependencies containing movement_manager reference.
        enabled: Whether idle emotions are currently enabled.
        min_delay: Minimum seconds between idle emotions.
        max_delay: Maximum seconds between idle emotions.
    """

    def __init__(
        self,
        deps: ToolDependencies,
        enabled: bool = True,
        min_delay: float = 3.0,
        max_delay: float = 8.0,
    ) -> None:
        """Initialize the idle emotion manager.

        Args:
            deps: Tool dependencies containing movement_manager reference.
            enabled: Whether idle emotions are enabled by default.
            min_delay: Minimum seconds between idle emotions.
            max_delay: Maximum seconds between idle emotions.
        """
        self.deps = deps
        self.enabled = enabled
        self.min_delay = min_delay
        self.max_delay = max_delay

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_idle_time = time.time()

        # Verify emotions are available
        if EMOTION_AVAILABLE:
            available_emotions = RECORDED_MOVES.list_moves()
            self.available_idle_emotions = [e for e in IDLE_EMOTIONS if e in available_emotions]
            if not self.available_idle_emotions:
                logger.warning("No idle emotions found in library!")
                self.enabled = False
            else:
                logger.info(f"Idle emotion system initialized with {len(self.available_idle_emotions)} emotions")
        else:
            logger.warning("Emotion library not available, idle emotions disabled")
            self.enabled = False
            self.available_idle_emotions = []

    def start(self) -> None:
        """Start the idle emotion background thread."""
        if not self.enabled or not EMOTION_AVAILABLE:
            logger.info("Idle emotions not started (disabled or unavailable)")
            return

        if self._thread is not None and self._thread.is_alive():
            logger.warning("Idle emotion thread already running")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._idle_loop,
            daemon=True,
            name="IdleEmotionManager",
        )
        self._thread.start()
        logger.info("Idle emotion system started")

    def stop(self) -> None:
        """Stop the idle emotion background thread."""
        if self._thread is None:
            return

        logger.info("Stopping idle emotion system")
        self._stop_event.set()

        if self._thread.is_alive():
            self._thread.join(timeout=2.0)

        self._thread = None
        logger.info("Idle emotion system stopped")

    def _idle_loop(self) -> None:
        """Background loop that continuously queues idle emotions."""
        logger.debug("Idle emotion loop started")

        while not self._stop_event.is_set():
            try:
                # Check if we should queue a new idle emotion
                if self._should_queue_idle_emotion():
                    self._queue_random_idle_emotion()

                # Sleep briefly before checking again
                time.sleep(0.5)

            except Exception as e:
                logger.error(f"Error in idle emotion loop: {e}", exc_info=True)
                time.sleep(1.0)  # Back off on error

        logger.debug("Idle emotion loop stopped")

    def _should_queue_idle_emotion(self) -> bool:
        """Check if we should queue a new idle emotion.

        Returns:
            True if enough time has passed and the robot is truly idle
            (no move playing AND no moves queued).
        """
        if not self.enabled:
            return False

        # Check if enough time has passed since last idle emotion
        current_time = time.time()
        time_since_last = current_time - self._last_idle_time

        # Random delay between min and max
        target_delay = random.uniform(self.min_delay, self.max_delay)

        if time_since_last < target_delay:
            return False

        # Check if movement manager is truly idle:
        # - No move currently playing
        # - No moves waiting in the queue
        try:
            mm = self.deps.movement_manager
            # Check if a move is currently playing
            if hasattr(mm, 'state') and mm.state.current_move is not None:
                from reachy_mini_elevenlabs.moves import BreathingMove
                # Breathing is idle behaviour, don't block on it
                if not isinstance(mm.state.current_move, BreathingMove):
                    return False
            # Check if moves are queued
            if hasattr(mm, 'move_queue') and len(mm.move_queue) > 0:
                return False
        except Exception as e:
            logger.debug(f"Could not check movement state: {e}")

        return True

    def _queue_random_idle_emotion(self) -> None:
        """Queue a random idle emotion."""
        if not self.available_idle_emotions:
            return

        try:
            # Select random idle emotion
            emotion_name = random.choice(self.available_idle_emotions)

            # Create and queue the emotion move
            emotion_move = EmotionQueueMove(emotion_name, RECORDED_MOVES)
            self.deps.movement_manager.queue_move(emotion_move)

            self._last_idle_time = time.time()
            logger.info(f"🌙 Idle emotion queued: {emotion_name}")

        except Exception as e:
            logger.error(f"Failed to queue idle emotion: {e}")

    def enable(self) -> None:
        """Enable idle emotions."""
        self.enabled = True
        logger.info("Idle emotions enabled")

    def disable(self) -> None:
        """Disable idle emotions."""
        self.enabled = False
        logger.info("Idle emotions disabled")

    def set_delay_range(self, min_delay: float, max_delay: float) -> None:
        """Set the delay range between idle emotions.

        Args:
            min_delay: Minimum seconds between idle emotions.
            max_delay: Maximum seconds between idle emotions.
        """
        self.min_delay = max(0.0, min_delay)
        self.max_delay = max(self.min_delay, max_delay)
        logger.info(f"Idle emotion delay range set to {self.min_delay:.1f}s - {self.max_delay:.1f}s")
