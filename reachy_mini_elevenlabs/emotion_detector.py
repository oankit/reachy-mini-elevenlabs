"""Emotion detection from text for triggering robot expressions.

This module analyzes agent text responses to detect emotional content
and map it to appropriate robot movements and expressions.

ATTRIBUTION NOTICE:
Emotion triggering approach inspired by reachy_mini_conversation_app
Original work Copyright (c) Pollen Robotics
Licensed under the Apache License, Version 2.0
Source: https://github.com/pollen-robotics/reachy_mini_conversation_app
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from reachy_mini_elevenlabs.tools.core_tools import ToolDependencies


logger = logging.getLogger(__name__)


# Initialize emotion library
try:
    from reachy_mini.motion.recorded_move import RecordedMoves
    from reachy_mini_elevenlabs.dance_emotion_moves import EmotionQueueMove, GotoQueueMove
    from reachy_mini.utils import create_head_pose

    # Note: huggingface_hub automatically reads HF_TOKEN from environment variables
    RECORDED_MOVES = RecordedMoves("pollen-robotics/reachy-mini-emotions-library")
    EMOTION_AVAILABLE = True
    logger.info("Emotion library loaded successfully")
except ImportError as e:
    logger.warning(f"Emotion library not available: {e}")
    RECORDED_MOVES = None
    EMOTION_AVAILABLE = False
    EmotionQueueMove = None  # type: ignore
    GotoQueueMove = None  # type: ignore


# Emotion keywords and patterns mapped to robot actions
# Available emotions from the library: cheerful1, sad1, sad2, confused1, surprised1, surprised2, welcoming1, welcoming2, etc.
EMOTION_PATTERNS = {
    "happy": {
        "keywords": [
            "happy", "glad", "great", "wonderful", "excellent", "fantastic",
            "excited", "thrilled", "delighted", "pleased", "joy", "cheerful",
            "awesome", "amazing", "perfect", "love", "yay", "hooray"
        ],
        "patterns": [
            r"!+",  # Exclamation marks
            r":\)",  # Smiley emoticons
            r"😊|😄|😃|🎉|✨",  # Happy emojis
        ],
        "action": "play_emotion",
        "action_param": "cheerful1",  # Using actual emotion from library
    },
    "sad": {
        "keywords": [
            "sad", "sorry", "unfortunately", "regret", "apologize", "disappointed",
            "unhappy", "upset", "down", "blue", "gloomy", "melancholy"
        ],
        "patterns": [
            r":\(",  # Sad emoticons
            r"😢|😞|😔|😟",  # Sad emojis
        ],
        "action": "play_emotion",
        "action_param": "sad1",  # Using actual emotion from library
    },
    "thinking": {
        "keywords": [
            "hmm", "let me think", "considering", "analyzing", "processing",
            "evaluating", "pondering", "wondering", "curious", "interesting"
        ],
        "patterns": [
            r"\.{3,}",  # Ellipsis (thinking pause)
            r"🤔",  # Thinking emoji
        ],
        "action": "play_emotion",
        "action_param": "thoughtful1",  # Using actual emotion from library
    },
    "confused": {
        "keywords": [
            "confused", "unclear", "not sure", "don't understand", "puzzled",
            "perplexed", "baffled", "uncertain", "unsure"
        ],
        "patterns": [
            r"\?{2,}",  # Multiple question marks
            r"😕|🤷",  # Confused emojis
        ],
        "action": "play_emotion",
        "action_param": "confused1",  # Using actual emotion from library
    },
    "surprised": {
        "keywords": [
            "wow", "oh", "really", "surprising", "unexpected", "amazing",
            "incredible", "unbelievable", "astonishing", "shocking"
        ],
        "patterns": [
            r"!{2,}",  # Multiple exclamation marks
            r"😮|😲|🤯",  # Surprised emojis
        ],
        "action": "play_emotion",
        "action_param": "surprised1",  # Using actual emotion from library
    },
    "greeting": {
        "keywords": [
            "hello", "hi", "hey", "greetings", "good morning", "good afternoon",
            "good evening", "welcome", "howdy"
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "welcoming1",  # Using actual emotion from library
    },
}


class EmotionDetector:
    """Detects emotions from text and triggers robot expressions.

    This class analyzes agent text responses for emotional content using
    keyword matching and pattern recognition, then triggers appropriate
    robot movements and expressions.

    Attributes:
        deps: Tool dependencies containing movement_manager reference.
        enabled: Whether emotion detection is currently enabled.
        min_confidence: Minimum confidence threshold (0-1) for triggering actions.
        cooldown_seconds: Minimum time between emotion-triggered actions.
    """

    def __init__(
        self,
        deps: ToolDependencies,
        enabled: bool = True,
        min_confidence: float = 0.3,
        cooldown_seconds: float = 3.0,
    ) -> None:
        """Initialize the emotion detector.

        Args:
            deps: Tool dependencies containing movement_manager reference.
            enabled: Whether emotion detection is enabled by default.
            min_confidence: Minimum confidence (0-1) to trigger an action.
            cooldown_seconds: Minimum seconds between emotion actions.
        """
        self.deps = deps
        self.enabled = enabled
        self.min_confidence = min_confidence
        self.cooldown_seconds = cooldown_seconds
        self._last_action_time: float = 0.0

    def analyze_and_act(self, text: str) -> dict[str, any]:
        """Analyze text for emotions and trigger robot actions.

        Args:
            text: The agent's text response to analyze.

        Returns:
            Dictionary with analysis results:
            - detected_emotion: The emotion detected (or None)
            - confidence: Confidence score (0-1)
            - action_triggered: Whether an action was triggered
            - action_type: Type of action (play_emotion, move_head, etc.)
        """
        if not self.enabled:
            return {
                "detected_emotion": None,
                "confidence": 0.0,
                "action_triggered": False,
                "action_type": None,
            }

        # Detect emotion with confidence score
        emotion, confidence = self._detect_emotion(text)

        result = {
            "detected_emotion": emotion,
            "confidence": confidence,
            "action_triggered": False,
            "action_type": None,
        }

        # Check if we should trigger an action
        if emotion and confidence >= self.min_confidence:
            # Check cooldown
            import time
            current_time = time.time()
            if current_time - self._last_action_time >= self.cooldown_seconds:
                # Trigger the action
                action_triggered = self._trigger_action(emotion)
                if action_triggered:
                    result["action_triggered"] = True
                    result["action_type"] = EMOTION_PATTERNS[emotion]["action"]
                    self._last_action_time = current_time
                    logger.info(
                        f"Emotion detected: {emotion} (confidence: {confidence:.2f}) "
                        f"-> Action: {result['action_type']}"
                    )
            else:
                logger.debug(
                    f"Emotion {emotion} detected but in cooldown period "
                    f"({current_time - self._last_action_time:.1f}s < {self.cooldown_seconds}s)"
                )

        return result

    def _detect_emotion(self, text: str) -> tuple[str | None, float]:
        """Detect emotion from text with confidence score.

        Args:
            text: The text to analyze.

        Returns:
            Tuple of (emotion_name, confidence_score) or (None, 0.0).
        """
        text_lower = text.lower()
        best_emotion = None
        best_confidence = 0.0

        for emotion_name, emotion_data in EMOTION_PATTERNS.items():
            confidence = 0.0
            matches = 0

            # Check keywords
            for keyword in emotion_data["keywords"]:
                if keyword in text_lower:
                    matches += 1
                    # Weight by keyword length (longer = more specific)
                    confidence += len(keyword) / 20.0

            # Check patterns
            for pattern in emotion_data["patterns"]:
                if re.search(pattern, text):
                    matches += 1
                    confidence += 0.5

            # Normalize confidence (cap at 1.0)
            if matches > 0:
                confidence = min(confidence / matches, 1.0)

                # Update best match
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_emotion = emotion_name

        return best_emotion, best_confidence

    def _trigger_action(self, emotion: str) -> bool:
        """Trigger robot action for detected emotion.

        Args:
            emotion: The emotion name to act on.

        Returns:
            True if action was successfully triggered, False otherwise.
        """
        if not EMOTION_AVAILABLE:
            logger.warning("Emotion system not available, cannot trigger actions")
            return False

        if emotion not in EMOTION_PATTERNS:
            logger.warning(f"Unknown emotion: {emotion}")
            return False

        emotion_data = EMOTION_PATTERNS[emotion]
        action_type = emotion_data["action"]
        action_param = emotion_data["action_param"]

        try:
            if action_type == "play_emotion":
                # Check if emotion exists in library
                emotion_names = RECORDED_MOVES.list_moves()
                if action_param not in emotion_names:
                    logger.warning(f"Emotion '{action_param}' not found in library. Available: {emotion_names}")
                    return False

                # Create emotion move and queue it
                emotion_move = EmotionQueueMove(action_param, RECORDED_MOVES)
                self.deps.movement_manager.queue_move(emotion_move)
                logger.debug(f"✨ Emotion queued: {action_param}")
                return True

            elif action_type == "move_head":
                # Create a simple head movement
                # Map action_param to head pose
                head_poses = {
                    "up": create_head_pose(0, 0, 0, 0, 20, 0, degrees=True),
                    "down": create_head_pose(0, 0, 0, 0, -10, 0, degrees=True),
                    "left": create_head_pose(0, 0, 0, 0, 0, 20, degrees=True),
                    "right": create_head_pose(0, 0, 0, 0, 0, -20, degrees=True),
                    "front": create_head_pose(0, 0, 0, 0, 0, 0, degrees=True),
                }

                target_pose = head_poses.get(action_param)
                if target_pose is None:
                    logger.warning(f"Unknown head pose: {action_param}")
                    return False

                # Queue head movement
                goto_move = GotoQueueMove(
                    target_head_pose=target_pose,
                    duration=0.5,  # Quick movement
                )
                self.deps.movement_manager.queue_move(goto_move)
                logger.debug(f"Queued head movement: {action_param}")
                return True

            elif action_type == "dance":
                # Queue dance (if dance support is added later)
                logger.debug(f"Dance action not yet implemented: {action_param}")
                return False

            else:
                logger.warning(f"Unknown action type: {action_type}")
                return False

        except Exception as e:
            logger.error(f"Error triggering action for emotion {emotion}: {e}")
            return False

    def enable(self) -> None:
        """Enable emotion detection."""
        self.enabled = True
        logger.info("Emotion detection enabled")

    def disable(self) -> None:
        """Disable emotion detection."""
        self.enabled = False
        logger.info("Emotion detection disabled")

    def set_confidence_threshold(self, threshold: float) -> None:
        """Set minimum confidence threshold for triggering actions.

        Args:
            threshold: Confidence threshold (0.0 to 1.0).
        """
        self.min_confidence = max(0.0, min(1.0, threshold))
        logger.info(f"Emotion confidence threshold set to {self.min_confidence:.2f}")

    def set_cooldown(self, seconds: float) -> None:
        """Set cooldown period between emotion actions.

        Args:
            seconds: Cooldown period in seconds.
        """
        self.cooldown_seconds = max(0.0, seconds)
        logger.info(f"Emotion cooldown set to {self.cooldown_seconds:.1f}s")
