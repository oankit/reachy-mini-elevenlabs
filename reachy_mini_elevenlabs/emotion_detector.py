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
    from reachy_mini_elevenlabs.dance_emotion_moves import (
        DanceQueueMove,
        EmotionQueueMove,
        GotoQueueMove,
    )
    from reachy_mini.utils import create_head_pose

    # Note: huggingface_hub automatically reads HF_TOKEN from environment variables
    RECORDED_MOVES = RecordedMoves("pollen-robotics/reachy-mini-emotions-library")
    EMOTION_AVAILABLE = True
    logger.info("Emotion library loaded successfully")
except ImportError as e:
    logger.warning(f"Emotion library not available: {e}")
    RECORDED_MOVES = None
    EMOTION_AVAILABLE = False
    DanceQueueMove = None  # type: ignore
    EmotionQueueMove = None  # type: ignore
    GotoQueueMove = None  # type: ignore

try:
    from reachy_mini_dances_library.collection.dance import AVAILABLE_MOVES as DANCE_MOVES

    DANCE_AVAILABLE = True
except ImportError:
    DANCE_MOVES = {}
    DANCE_AVAILABLE = False


# Emotion keywords and patterns mapped to robot actions.
# Each entry maps a detected emotion category to keywords, regex patterns,
# an action type ("play_emotion", "move_head", or "dance"), and the
# parameter for that action.
EMOTION_PATTERNS = {
    # --- Positive emotions ---
    "happy": {
        "keywords": [
            "happy", "glad", "great", "wonderful", "excellent", "fantastic",
            "excited", "thrilled", "delighted", "pleased", "joy", "cheerful",
            "awesome", "amazing", "perfect", "love", "yay", "hooray",
        ],
        "patterns": [r":\)", r"😊|😄|😃|🎉|✨"],
        "action": "play_emotion",
        "action_param": "cheerful1",
    },
    "enthusiastic": {
        "keywords": [
            "incredible", "extraordinary", "celebrate", "congratulations",
            "victory", "triumph", "phenomenal", "outstanding",
        ],
        "patterns": [r"!{3,}"],
        "action": "play_emotion",
        "action_param": "enthusiastic1",
    },
    "proud": {
        "keywords": [
            "proud", "accomplished", "nailed it", "did it", "success",
            "achieved", "well done", "good job", "bravo",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "proud2",
    },
    "grateful": {
        "keywords": [
            "thank you", "thanks", "grateful", "appreciate", "gratitude",
            "thankful", "much appreciated",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "grateful1",
    },
    "admiration": {
        "keywords": [
            "admire", "impressive", "remarkable", "brilliant", "genius",
            "magnificent", "superb", "spectacular",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "admiration1",
    },
    "relief": {
        "keywords": [
            "relief", "relieved", "finally", "phew", "at last",
            "thank goodness", "that's over",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "relief1",
    },
    "laughing": {
        "keywords": [
            "haha", "hehe", "lol", "funny", "hilarious", "joke",
            "laugh", "laughing", "comedy", "crack up",
        ],
        "patterns": [r"😂|🤣|😆"],
        "action": "play_emotion",
        "action_param": "laughing1",
    },
    # --- Negative emotions ---
    "sad": {
        "keywords": [
            "sad", "sorry", "unfortunately", "regret", "apologize",
            "disappointed", "unhappy", "upset", "down", "blue",
            "gloomy", "melancholy", "heartbroken",
        ],
        "patterns": [r":\(", r"😢|😞|😔|😟"],
        "action": "play_emotion",
        "action_param": "sad1",
    },
    "discouraged": {
        "keywords": [
            "discouraged", "hopeless", "despair", "give up", "pointless",
            "no use", "what's the point", "can't do this",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "discouraged1",
    },
    "frustrated": {
        "keywords": [
            "frustrated", "frustrating", "can't figure", "stuck",
            "impossible", "no solution", "give up",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "frustrated1",
    },
    "angry": {
        "keywords": [
            "angry", "mad", "furious", "rage", "outraged", "livid",
            "infuriated", "irate",
        ],
        "patterns": [r"😠|😡"],
        "action": "play_emotion",
        "action_param": "furious1",
    },
    "irritated": {
        "keywords": [
            "irritated", "annoyed", "bothered", "bugged", "ugh",
            "come on", "seriously",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "irritated1",
    },
    "disapproving": {
        "keywords": [
            "disapprove", "careless", "disrespectful", "rude",
            "inappropriate", "unacceptable", "shame on",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "disapproving1",
    },
    "reprimand": {
        "keywords": [
            "stop it", "knock it off", "what's wrong with you",
            "ridiculous", "silly", "nonsense", "foolish",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "reprimand3",
    },
    "disgust": {
        "keywords": [
            "disgusting", "gross", "eww", "yuck", "nasty",
            "revolting", "awful",
        ],
        "patterns": [r"🤢|🤮"],
        "action": "play_emotion",
        "action_param": "disgust1",
    },
    # --- Cognitive / Neutral emotions ---
    "thinking": {
        "keywords": [
            "hmm", "let me think", "considering", "analyzing", "processing",
            "evaluating", "pondering", "wondering", "interesting",
        ],
        "patterns": [r"\.{3,}", r"🤔"],
        "action": "play_emotion",
        "action_param": "thoughtful1",
    },
    "curious": {
        "keywords": [
            "curious", "tell me more", "elaborate", "go on",
            "what do you mean", "how so", "why is that",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "inquiring1",
    },
    "confused": {
        "keywords": [
            "confused", "unclear", "not sure", "don't understand", "puzzled",
            "perplexed", "baffled", "uncertain", "unsure", "lost",
        ],
        "patterns": [r"\?{2,}", r"😕|🤷"],
        "action": "play_emotion",
        "action_param": "confused1",
    },
    "surprised": {
        "keywords": [
            "wow", "surprising", "unexpected", "astonishing",
            "shocking", "no way", "boo",
        ],
        "patterns": [r"!{2,}", r"😮|😲|🤯"],
        "action": "play_emotion",
        "action_param": "surprised1",
    },
    "scared": {
        "keywords": [
            "scared", "afraid", "terrified", "fear", "frightened",
            "creepy", "spooky", "horror",
        ],
        "patterns": [r"😨|😱"],
        "action": "play_emotion",
        "action_param": "afraid1",
    },
    "shy": {
        "keywords": [
            "shy", "embarrassed", "blushing", "awkward",
            "self-conscious", "bashful",
        ],
        "patterns": [r"😳"],
        "action": "play_emotion",
        "action_param": "shy1",
    },
    "impatient": {
        "keywords": [
            "hurry", "hurry up", "come on", "waiting", "impatient",
            "faster", "taking forever", "stalling",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "impatient1",
    },
    "oops": {
        "keywords": [
            "oops", "my bad", "mistake", "blunder", "whoops",
            "forgot", "slip up",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "oops1",
    },
    "disagreement": {
        "keywords": [
            "no", "nope", "disagree", "refuse", "won't",
            "absolutely not", "never", "no way",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "no1",
    },
    "agreement": {
        "keywords": [
            "yes", "yeah", "absolutely", "exactly", "correct",
            "right", "agreed", "indeed", "of course",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "yes1",
    },
    # --- Social emotions ---
    "greeting": {
        "keywords": [
            "hello", "hi", "hey", "greetings", "good morning", "good afternoon",
            "good evening", "welcome", "howdy",
        ],
        "patterns": [r"👋"],
        "action": "play_emotion",
        "action_param": "welcoming1",
    },
    "goodbye": {
        "keywords": [
            "goodbye", "bye", "see you", "farewell", "take care",
            "goodnight", "later", "see ya",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "loved1",
    },
    "indifferent": {
        "keywords": [
            "whatever", "meh", "oh well", "doesn't matter",
            "don't care", "shrug", "we'll see",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "indifferent1",
    },
    # --- Situational / Physical emotions ---
    "electric_shock": {
        "keywords": [
            "electric", "shock", "zap", "jolt", "electricity",
            "charged", "voltage", "spark", "plugged in",
        ],
        "patterns": [r"⚡"],
        "action": "play_emotion",
        "action_param": "electric_shock1",
    },
    "dying": {
        "keywords": [
            "dying", "dead", "shutting down", "low battery",
            "power off", "out of energy", "flatline",
        ],
        "patterns": [r"💀|☠️"],
        "action": "play_emotion",
        "action_param": "dying1",
    },
    "calming": {
        "keywords": [
            "calm down", "relax", "take it easy", "breathe",
            "chill", "settle down", "easy now", "soothing",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "calming1",
    },
    "come_closer": {
        "keywords": [
            "come closer", "come here", "lean in", "get closer",
            "whisper", "secret", "between us",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "come_closer1",
    },
    "exhausted": {
        "keywords": [
            "exhausted", "worn out", "drained", "burnt out",
            "so tired", "wiped out", "running on empty",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "exhausted1",
    },
    "tired": {
        "keywords": [
            "tired", "sleepy", "yawn", "drowsy", "nap",
            "bedtime", "need sleep",
        ],
        "patterns": [r"😴|🥱"],
        "action": "play_emotion",
        "action_param": "tired1",
    },
    "lonely": {
        "keywords": [
            "lonely", "alone", "isolated", "nobody", "all by myself",
            "no one here", "abandoned",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "lonely1",
    },
    "success": {
        "keywords": [
            "completed", "finished", "done it", "mission accomplished",
            "task complete", "crushed it", "smashed it",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "success1",
    },
    "incomprehension": {
        "keywords": [
            "what did you say", "say again", "repeat that",
            "didn't catch", "huh", "pardon", "excuse me",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "incomprehension1",
    },
    "resigned": {
        "keywords": [
            "fine", "I guess", "if you say so", "alright then",
            "suppose so", "grumpy ok", "reluctantly",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "resigned1",
    },
    "fear": {
        "keywords": [
            "dangerous", "threatening", "run", "watch out",
            "careful", "warning", "alert", "panic",
        ],
        "patterns": [r"🚨|⚠️"],
        "action": "play_emotion",
        "action_param": "fear1",
    },
    "attentive": {
        "keywords": [
            "listening", "go ahead", "I'm all ears", "continue",
            "keep going", "tell me", "paying attention",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "attentive1",
    },
    "bored": {
        "keywords": [
            "bored", "boring", "dull", "tedious", "snooze",
            "yawn", "uninteresting", "monotonous",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "boredom1",
    },
    "displeased": {
        "keywords": [
            "not happy", "displeased", "not satisfied", "let down",
            "not good enough", "subpar", "mediocre",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "displeased1",
    },
    "serenity": {
        "keywords": [
            "peaceful", "serene", "tranquil", "zen",
            "inner peace", "meditation", "mindful",
        ],
        "patterns": [r"🧘|☮️"],
        "action": "play_emotion",
        "action_param": "serenity1",
    },
    "rage": {
        "keywords": [
            "injustice", "unforgivable", "how dare", "why would you",
            "that's it", "last straw", "enough",
        ],
        "patterns": [],
        "action": "play_emotion",
        "action_param": "rage1",
    },
    # --- Dance triggers ---
    "dance_celebrate": {
        "keywords": [
            "dance", "dancing", "party", "celebrate", "groove",
            "music", "bust a move", "boogie",
        ],
        "patterns": [r"💃|🕺|🎶|🎵"],
        "action": "dance",
        "action_param": "groovy_sway_and_roll",
    },
    "dance_nod": {
        "keywords": [
            "nod", "nodding", "agree with that", "uh huh",
            "mm hmm", "totally",
        ],
        "patterns": [],
        "action": "dance",
        "action_param": "yeah_nod",
    },
}


# ---------------------------------------------------------------------------
# Personality weight profiles for DAMN-inspired weighted arbitration.
# Each profile maps emotion pattern names to multipliers.
# Unlisted emotions default to 1.0.  Set < 1.0 to suppress, > 1.0 to boost.
# ---------------------------------------------------------------------------
PERSONALITY_WEIGHTS: dict[str, dict[str, float]] = {
    "sarcastic": {
        # Boost sarcastic / mocking behaviours
        "reprimand": 1.5, "irritated": 1.3, "disapproving": 1.3,
        "laughing": 1.3, "surprised": 1.2, "impatient": 1.2,
        # Suppress overly positive behaviours
        "happy": 0.5, "enthusiastic": 0.4, "proud": 0.5,
        "dance_celebrate": 0.3, "admiration": 0.4,
    },
    "motivational": {
        # Boost celebratory / supportive behaviours
        "enthusiastic": 1.5, "proud": 1.4, "happy": 1.3,
        "dance_celebrate": 1.5, "admiration": 1.3, "success": 1.3,
        "grateful": 1.2,
        # Suppress negative behaviours
        "reprimand": 0.3, "disapproving": 0.3, "angry": 0.3,
        "irritated": 0.4, "sad": 0.5, "frustrated": 0.4,
        "disgust": 0.3,
    },
    "neutral": {
        # Suppress almost everything — robot should stay still
        "happy": 0.1, "enthusiastic": 0.1, "proud": 0.1,
        "sad": 0.1, "angry": 0.1, "irritated": 0.1,
        "reprimand": 0.1, "disapproving": 0.1, "laughing": 0.1,
        "dance_celebrate": 0.0, "dance_nod": 0.0,
        "surprised": 0.1, "scared": 0.1, "admiration": 0.1,
        "greeting": 0.8,  # Allow a single welcome
    },
    "drill_sergeant": {
        # Boost stern / authoritative behaviours
        "reprimand": 1.5, "disapproving": 1.5, "impatient": 1.4,
        "irritated": 1.3, "angry": 1.2, "displeased": 1.3,
        # Suppress celebratory behaviours
        "happy": 0.3, "enthusiastic": 0.2, "proud": 0.3,
        "dance_celebrate": 0.0, "dance_nod": 0.0,
        "laughing": 0.1, "admiration": 0.3,
    },
}


class EmotionDetector:
    """Detects emotions from text and triggers robot expressions.

    Implements a weighted arbitration architecture inspired by Rosenblatt
    and Payton's DAMN (1989).  Detected behaviours are grouped into
    independent channels (emotion, dance, head movement) and the best
    candidate in *each* channel is selected via personality-weighted
    confidence scores.  This allows multiple complementary behaviours to
    execute from a single text response — e.g. a reprimand emotion paired
    with a head shake.

    Attributes:
        deps: Tool dependencies containing movement_manager reference.
        enabled: Whether emotion detection is currently enabled.
        min_confidence: Minimum confidence threshold (0-1) for triggering actions.
        cooldown_seconds: Minimum time between emotion-triggered actions.
        personality: Active personality profile key (from PERSONALITY_WEIGHTS).
    """

    def __init__(
        self,
        deps: ToolDependencies,
        enabled: bool = True,
        min_confidence: float = 0.3,
        cooldown_seconds: float = 3.0,
        personality: str | None = None,
    ) -> None:
        """Initialize the emotion detector.

        Args:
            deps: Tool dependencies containing movement_manager reference.
            enabled: Whether emotion detection is enabled by default.
            min_confidence: Minimum confidence (0-1) to trigger an action.
            cooldown_seconds: Minimum seconds between emotion actions.
            personality: Personality key for weighted arbitration.
                         One of "sarcastic", "motivational", "neutral",
                         "drill_sergeant", or None (no weighting).
        """
        self.deps = deps
        self.enabled = enabled
        self.min_confidence = min_confidence
        self.cooldown_seconds = cooldown_seconds
        self.personality = personality
        self._last_action_time: float = 0.0
        # Per-category cooldown tracking
        self._last_action_time_by_category: dict[str, float] = {}

    def analyze_and_act(self, text: str) -> dict[str, any]:
        """Analyze text and trigger actions from each behaviour channel.

        Uses DAMN-inspired parallel category execution:
        1. Score ALL patterns against the text.
        2. Apply personality weights.
        3. Group candidates by action category (play_emotion, dance, move_head).
        4. Pick the best candidate per category.
        5. Execute the winner from each category (sequential queue).

        Args:
            text: The agent's text response to analyze.

        Returns:
            Dictionary with analysis results including all triggered actions.
        """
        if not self.enabled:
            return {
                "detected_emotions": [],
                "actions_triggered": [],
                "action_triggered": False,
            }

        import time
        current_time = time.time()

        # 1. Score all patterns
        all_scores = self._score_all_patterns(text)

        # 2. Apply personality weights
        weighted_scores = self._apply_personality_weights(all_scores)

        # 3. Group by category and pick best per category
        category_winners = self._select_per_category(weighted_scores)

        # 4. Execute winners
        actions_triggered: list[dict[str, str]] = []
        for category, (emotion_name, confidence) in category_winners.items():
            if confidence < self.min_confidence:
                continue

            # Per-category cooldown
            last_time = self._last_action_time_by_category.get(category, 0.0)
            if current_time - last_time < self.cooldown_seconds:
                logger.debug(
                    f"{emotion_name} ({category}) in cooldown "
                    f"({current_time - last_time:.1f}s < {self.cooldown_seconds}s)"
                )
                continue

            if self._trigger_action(emotion_name):
                self._last_action_time_by_category[category] = current_time
                self._last_action_time = current_time
                actions_triggered.append({
                    "emotion": emotion_name,
                    "category": category,
                    "confidence": confidence,
                    "action_type": EMOTION_PATTERNS[emotion_name]["action"],
                })
                logger.info(
                    f"Emotion detected: {emotion_name} (confidence: {confidence:.2f}, "
                    f"category: {category}) -> Action: {EMOTION_PATTERNS[emotion_name]['action']}"
                )

        # Backwards-compatible result dict
        first = actions_triggered[0] if actions_triggered else None
        return {
            "detected_emotion": first["emotion"] if first else None,
            "confidence": first["confidence"] if first else 0.0,
            "action_triggered": len(actions_triggered) > 0,
            "action_type": first["action_type"] if first else None,
            "detected_emotions": [a["emotion"] for a in actions_triggered],
            "actions_triggered": actions_triggered,
        }

    def _score_all_patterns(
        self, text: str,
    ) -> list[tuple[str, float]]:
        """Score every pattern against the text.

        Returns:
            List of (emotion_name, raw_confidence) for all patterns with
            at least one keyword/pattern match.
        """
        text_lower = text.lower()
        results: list[tuple[str, float]] = []

        for emotion_name, emotion_data in EMOTION_PATTERNS.items():
            confidence = 0.0
            matches = 0

            for keyword in emotion_data["keywords"]:
                if keyword in text_lower:
                    matches += 1
                    confidence += len(keyword) / 20.0

            for pattern in emotion_data["patterns"]:
                if re.search(pattern, text):
                    matches += 1
                    confidence += 0.5

            if matches > 0:
                confidence = min(confidence, 1.0)
                results.append((emotion_name, confidence))

        return results

    def _apply_personality_weights(
        self, scores: list[tuple[str, float]],
    ) -> list[tuple[str, float]]:
        """Multiply raw scores by personality-specific weights."""
        if not self.personality or self.personality not in PERSONALITY_WEIGHTS:
            return scores

        weights = PERSONALITY_WEIGHTS[self.personality]
        return [
            (name, conf * weights.get(name, 1.0))
            for name, conf in scores
        ]

    @staticmethod
    def _select_per_category(
        scores: list[tuple[str, float]],
    ) -> dict[str, tuple[str, float]]:
        """Group scores by action category and pick the best per category.

        Categories are derived from the 'action' field in EMOTION_PATTERNS
        (play_emotion, dance, move_head).
        """
        buckets: dict[str, list[tuple[str, float]]] = {}
        for emotion_name, confidence in scores:
            category = EMOTION_PATTERNS[emotion_name]["action"]
            buckets.setdefault(category, []).append((emotion_name, confidence))

        winners: dict[str, tuple[str, float]] = {}
        for category, candidates in buckets.items():
            best = max(candidates, key=lambda x: x[1])
            winners[category] = best

        return winners

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
                if not DANCE_AVAILABLE:
                    logger.warning("Dance library not available")
                    return False
                if action_param not in DANCE_MOVES:
                    logger.warning(f"Dance '{action_param}' not found. Available: {list(DANCE_MOVES.keys())}")
                    return False
                dance_move = DanceQueueMove(action_param)
                self.deps.movement_manager.queue_move(dance_move)
                logger.debug(f"💃 Dance queued: {action_param}")
                return True

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
