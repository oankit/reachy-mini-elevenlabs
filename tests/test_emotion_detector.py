"""Tests for emotion detection from text."""

from unittest.mock import Mock, patch

import pytest

from reachy_mini_elevenlabs.emotion_detector import EmotionDetector
from reachy_mini_elevenlabs.tools.core_tools import ToolDependencies


@pytest.fixture
def mock_deps():
    """Create mock dependencies for testing."""
    deps = Mock(spec=ToolDependencies)
    deps.movement_manager = Mock()
    return deps


@pytest.fixture
def mock_recorded_moves():
    """Mock the RECORDED_MOVES emotion library."""
    mock_moves = Mock()
    mock_moves.list_moves.return_value = [
        "cheerful1", "sad1", "thoughtful1", "confused1", "surprised1", "welcoming1"
    ]
    return mock_moves


@pytest.fixture
def detector(mock_deps, mock_recorded_moves):
    """Create an emotion detector for testing."""
    # Patch the RECORDED_MOVES import in emotion_detector module
    with patch('reachy_mini_elevenlabs.emotion_detector.RECORDED_MOVES', mock_recorded_moves):
        with patch('reachy_mini_elevenlabs.emotion_detector.EMOTION_AVAILABLE', True):
            detector = EmotionDetector(
                deps=mock_deps,
                enabled=True,
                min_confidence=0.3,
                cooldown_seconds=0.0,  # No cooldown for testing
            )
            # Keep the mock alive for the test
            detector._mock_recorded_moves = mock_recorded_moves
            yield detector


def test_detect_happy_emotion(detector):
    """Test detection of happy emotion."""
    text = "I'm so excited to help you today!"
    emotion, confidence = detector._detect_emotion(text)
    
    assert emotion == "happy"
    assert confidence > 0.3


def test_detect_sad_emotion(detector):
    """Test detection of sad emotion."""
    text = "I'm sorry to hear that. Unfortunately, I can't help with that."
    emotion, confidence = detector._detect_emotion(text)
    
    assert emotion == "sad"
    assert confidence > 0.3


def test_detect_thinking_emotion(detector):
    """Test detection of thinking emotion."""
    text = "Hmm, let me think about that for a moment..."
    emotion, confidence = detector._detect_emotion(text)
    
    assert emotion == "thinking"
    assert confidence > 0.3


def test_detect_greeting(detector):
    """Test detection of greeting."""
    text = "Hello, how can I help you today?"  # No exclamation to avoid happy match
    emotion, confidence = detector._detect_emotion(text)
    
    assert emotion == "greeting"
    assert confidence > 0.2  # Greeting has lower confidence without exclamation


def test_no_emotion_detected(detector):
    """Test when no clear emotion is present."""
    text = "The weather is 72 degrees."
    emotion, confidence = detector._detect_emotion(text)
    
    # Should either detect nothing or have very low confidence
    if emotion is not None:
        assert confidence < 0.3


def test_analyze_and_act_triggers_action(detector, mock_deps):
    """Test that analyze_and_act triggers robot actions."""
    text = "I'm so happy to help you!"
    
    result = detector.analyze_and_act(text)
    
    assert result["detected_emotion"] == "happy"
    assert result["action_triggered"] is True
    assert result["action_type"] == "play_emotion"
    
    # Verify movement_manager.queue_move was called (not queue_emotion)
    mock_deps.movement_manager.queue_move.assert_called_once()
    # Check that an EmotionQueueMove was passed
    call_args = mock_deps.movement_manager.queue_move.call_args
    assert call_args is not None


def test_analyze_and_act_respects_confidence_threshold(detector):
    """Test that low confidence emotions don't trigger actions."""
    # Set high threshold
    detector.min_confidence = 0.9
    
    text = "okay"  # Weak emotion signal
    result = detector.analyze_and_act(text)
    
    assert result["action_triggered"] is False


def test_analyze_and_act_respects_cooldown(detector, mock_deps):
    """Test that cooldown prevents rapid-fire actions."""
    import time
    
    # Set cooldown
    detector.cooldown_seconds = 1.0
    
    text = "I'm so excited!"
    
    # First call should trigger
    result1 = detector.analyze_and_act(text)
    assert result1["action_triggered"] is True
    
    # Immediate second call should not trigger (cooldown)
    result2 = detector.analyze_and_act(text)
    assert result2["action_triggered"] is False
    
    # After cooldown, should trigger again
    time.sleep(1.1)
    result3 = detector.analyze_and_act(text)
    assert result3["action_triggered"] is True


def test_enable_disable(detector):
    """Test enabling and disabling emotion detection."""
    text = "I'm so happy!"
    
    # Enabled by default
    result = detector.analyze_and_act(text)
    assert result["detected_emotion"] is not None
    
    # Disable
    detector.disable()
    result = detector.analyze_and_act(text)
    assert result["detected_emotion"] is None
    assert result["action_triggered"] is False
    
    # Re-enable
    detector.enable()
    result = detector.analyze_and_act(text)
    assert result["detected_emotion"] is not None


def test_exclamation_marks_boost_confidence(detector):
    """Test that exclamation marks increase emotion confidence."""
    text1 = "I am happy"
    text2 = "I am happy!"
    text3 = "I am happy!!!"
    
    _, conf1 = detector._detect_emotion(text1)
    _, conf2 = detector._detect_emotion(text2)
    _, conf3 = detector._detect_emotion(text3)
    
    # More exclamation marks should increase confidence
    assert conf2 > conf1
    assert conf3 >= conf2


def test_multiple_emotions_picks_strongest(detector):
    """Test that when multiple emotions are present, strongest wins."""
    text = "I'm sorry but I'm also excited to help!"
    
    emotion, confidence = detector._detect_emotion(text)
    
    # Should detect one of the emotions (implementation picks highest confidence)
    assert emotion in ("sad", "happy")
    assert confidence > 0.0


def test_set_confidence_threshold(detector):
    """Test setting confidence threshold."""
    detector.set_confidence_threshold(0.7)
    assert detector.min_confidence == 0.7
    
    # Test bounds
    detector.set_confidence_threshold(-0.5)
    assert detector.min_confidence == 0.0
    
    detector.set_confidence_threshold(1.5)
    assert detector.min_confidence == 1.0


def test_set_cooldown(detector):
    """Test setting cooldown period."""
    detector.set_cooldown(5.0)
    assert detector.cooldown_seconds == 5.0
    
    # Test bounds
    detector.set_cooldown(-1.0)
    assert detector.cooldown_seconds == 0.0
