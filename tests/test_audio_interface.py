"""Unit tests for ReachyAudioInterface.

Tests the custom audio interface that bridges ElevenLabs SDK with
the Reachy Mini robot's audio hardware and HeadWobbler animation.
"""

from __future__ import annotations

import base64
import threading
import time
from typing import Any
from unittest.mock import MagicMock, call, patch

import numpy as np
import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

from reachy_mini_elevenlabs.audio_interface import ReachyAudioInterface


class MockHeadWobbler:
    """Mock HeadWobbler for testing."""

    def __init__(self) -> None:
        self.feed_calls: list[str] = []
        self.reset_calls: int = 0

    def feed(self, delta_b64: str) -> None:
        """Record feed calls."""
        self.feed_calls.append(delta_b64)

    def reset(self) -> None:
        """Record reset calls."""
        self.reset_calls += 1


class MockMedia:
    """Mock robot media interface for testing."""

    def __init__(self) -> None:
        self.recording = False
        self.audio_samples: list[np.ndarray] = []
        self.pushed_samples: list[np.ndarray] = []
        self.audio = MockAudio()
        self._sample_index = 0

    def start_recording(self) -> None:
        """Start recording."""
        self.recording = True

    def stop_recording(self) -> None:
        """Stop recording."""
        self.recording = False

    def get_audio_sample(self) -> np.ndarray | None:
        """Get next audio sample from queue."""
        if self._sample_index < len(self.audio_samples):
            sample = self.audio_samples[self._sample_index]
            self._sample_index += 1
            return sample
        return None

    def push_audio_sample(self, audio: np.ndarray) -> None:
        """Record pushed audio sample."""
        self.pushed_samples.append(audio)


class MockAudio:
    """Mock audio buffer interface."""

    def __init__(self) -> None:
        self.buffer_cleared = False

    def clear_output_buffer(self) -> None:
        """Record buffer clear."""
        self.buffer_cleared = True


class MockRobot:
    """Mock ReachyMini robot for testing."""

    def __init__(self) -> None:
        self.media = MockMedia()


class TestReachyAudioInterfaceInit:
    """Tests for ReachyAudioInterface initialization."""

    def test_initializes_with_robot_and_head_wobbler(self) -> None:
        """Test that interface initializes with required dependencies."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()

        interface = ReachyAudioInterface(robot, head_wobbler)

        assert interface.robot is robot
        assert interface.head_wobbler is head_wobbler
        assert interface._recording is False
        assert interface._input_callback is None

    def test_initial_state_is_not_recording(self) -> None:
        """Test that interface starts in non-recording state."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()

        interface = ReachyAudioInterface(robot, head_wobbler)

        assert interface._recording is False
        assert interface._input_thread is None


class TestReachyAudioInterfaceStart:
    """Tests for the start() method."""

    def test_start_begins_recording(self) -> None:
        """Test that start() begins microphone recording."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        callback = MagicMock()
        interface.start(callback)

        # Give thread time to start
        time.sleep(0.1)

        try:
            assert interface._recording is True
            assert robot.media.recording is True
            assert interface._input_callback is callback
            assert interface._input_thread is not None
            assert interface._input_thread.is_alive()
        finally:
            interface.stop()

    def test_start_stores_input_callback(self) -> None:
        """Test that start() stores the input callback."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        callback = MagicMock()
        interface.start(callback)

        try:
            assert interface._input_callback is callback
        finally:
            interface.stop()


class TestReachyAudioInterfaceStop:
    """Tests for the stop() method."""

    def test_stop_ends_recording(self) -> None:
        """Test that stop() ends microphone recording."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        callback = MagicMock()
        interface.start(callback)
        time.sleep(0.1)

        interface.stop()

        assert interface._recording is False
        assert robot.media.recording is False
        assert interface._input_callback is None

    def test_stop_joins_input_thread(self) -> None:
        """Test that stop() waits for input thread to finish."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        callback = MagicMock()
        interface.start(callback)
        time.sleep(0.1)

        interface.stop()

        # Thread should be cleaned up
        assert interface._input_thread is None

    def test_stop_without_start_is_safe(self) -> None:
        """Test that stop() can be called without start()."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        # Should not raise
        interface.stop()

        assert interface._recording is False


class TestReachyAudioInterfaceOutput:
    """Tests for the output() method."""

    def test_output_feeds_head_wobbler(self) -> None:
        """Test that output() feeds audio to HeadWobbler."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        # Create test audio (int16 PCM)
        audio_array = np.array([0, 1000, -1000, 2000], dtype=np.int16)
        audio_bytes = audio_array.tobytes()

        interface.output(audio_bytes)

        # HeadWobbler should receive base64-encoded audio
        assert len(head_wobbler.feed_calls) == 1
        received_b64 = head_wobbler.feed_calls[0]
        decoded = base64.b64decode(received_b64)
        assert decoded == audio_bytes

    def test_output_pushes_to_speaker(self) -> None:
        """Test that output() pushes audio to robot speaker."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        # Create test audio (int16 PCM)
        audio_array = np.array([0, 16384, -16384], dtype=np.int16)
        audio_bytes = audio_array.tobytes()

        interface.output(audio_bytes)

        # Robot should receive float32 audio
        assert len(robot.media.pushed_samples) == 1
        pushed = robot.media.pushed_samples[0]
        assert pushed.dtype == np.float32
        assert len(pushed) == 3

    def test_output_converts_to_float32(self) -> None:
        """Test that output() converts int16 to float32 correctly."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        # Create test audio with known values
        audio_array = np.array([0, 32767, -32768], dtype=np.int16)
        audio_bytes = audio_array.tobytes()

        interface.output(audio_bytes)

        pushed = robot.media.pushed_samples[0]
        # Zero should remain zero
        assert pushed[0] == pytest.approx(0.0, abs=1e-6)
        # Max int16 should be close to 1.0
        assert pushed[1] == pytest.approx(1.0, rel=1e-4)
        # Min int16 should be close to -1.0
        assert pushed[2] == pytest.approx(-1.0, rel=1e-4)

    def test_output_handles_empty_audio(self) -> None:
        """Test that output() handles empty audio gracefully."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        # Should not raise
        interface.output(b"")

        # Nothing should be pushed
        assert len(head_wobbler.feed_calls) == 0
        assert len(robot.media.pushed_samples) == 0


class TestReachyAudioInterfaceInterrupt:
    """Tests for the interrupt() method."""

    def test_interrupt_clears_audio_buffer(self) -> None:
        """Test that interrupt() clears the robot's audio buffer."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        interface.interrupt()

        assert robot.media.audio.buffer_cleared is True

    def test_interrupt_resets_head_wobbler(self) -> None:
        """Test that interrupt() resets the HeadWobbler."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        interface.interrupt()

        assert head_wobbler.reset_calls == 1

    def test_multiple_interrupts_reset_multiple_times(self) -> None:
        """Test that multiple interrupts call reset multiple times."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        interface.interrupt()
        interface.interrupt()
        interface.interrupt()

        assert head_wobbler.reset_calls == 3


class TestReachyAudioInterfaceInputLoop:
    """Tests for the audio input loop."""

    def test_input_loop_calls_callback_with_audio(self) -> None:
        """Test that input loop calls callback with audio data."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        # Pre-populate audio samples
        test_audio = np.array([100, 200, 300], dtype=np.int16)
        robot.media.audio_samples = [test_audio]

        received_audio: list[bytes] = []

        def callback(audio: bytes) -> None:
            received_audio.append(audio)

        interface.start(callback)
        # Give time for the loop to process
        time.sleep(0.3)
        interface.stop()

        # Should have received the audio
        assert len(received_audio) >= 1
        # First received should match our test audio
        received_array = np.frombuffer(received_audio[0], dtype=np.int16)
        np.testing.assert_array_equal(received_array, test_audio)

    def test_input_loop_converts_float32_to_int16(self) -> None:
        """Test that input loop converts float32 audio to int16."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        # Pre-populate with float32 audio
        test_audio = np.array([0.0, 0.5, -0.5], dtype=np.float32)
        robot.media.audio_samples = [test_audio]

        received_audio: list[bytes] = []

        def callback(audio: bytes) -> None:
            received_audio.append(audio)

        interface.start(callback)
        time.sleep(0.3)
        interface.stop()

        # Should have received int16 audio
        assert len(received_audio) >= 1
        received_array = np.frombuffer(received_audio[0], dtype=np.int16)
        assert received_array.dtype == np.int16
        # Check conversion: 0.5 * 32767 ≈ 16383
        assert received_array[1] == pytest.approx(16383, abs=1)


class TestReachyAudioInterfaceIntegration:
    """Integration tests for ReachyAudioInterface."""

    def test_full_conversation_lifecycle(self) -> None:
        """Test a full conversation lifecycle: start, output, interrupt, stop."""
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        callback = MagicMock()

        # Start conversation
        interface.start(callback)
        time.sleep(0.1)
        assert interface._recording is True

        # Output some audio
        audio = np.array([100, 200, 300], dtype=np.int16).tobytes()
        interface.output(audio)
        assert len(head_wobbler.feed_calls) == 1
        assert len(robot.media.pushed_samples) == 1

        # User interrupts
        interface.interrupt()
        assert head_wobbler.reset_calls == 1
        assert robot.media.audio.buffer_cleared is True

        # Output more audio after interrupt
        interface.output(audio)
        assert len(head_wobbler.feed_calls) == 2

        # Stop conversation
        interface.stop()
        assert interface._recording is False


# =============================================================================
# Property-Based Tests
# =============================================================================


# Strategy for generating even-length binary data (int16 requires 2 bytes per sample)
even_length_binary = st.integers(min_value=1, max_value=5000).flatmap(
    lambda n: st.binary(min_size=n * 2, max_size=n * 2)
)


class TestAudioOutputFeedsHeadWobblerProperty:
    """Property-based tests for audio output to HeadWobbler.

    Feature: elevenlabs-integration, Property 3: Audio Output Feeds HeadWobbler

    **Validates: Requirements 4.6, 5.2**

    Property Definition:
    *For any* audio bytes passed to `ReachyAudioInterface.output()`, the HeadWobbler
    should receive the same audio data (as base64) via its `feed()` method.
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(audio_bytes=even_length_binary)
    def test_audio_output_feeds_head_wobbler(self, audio_bytes: bytes) -> None:
        """Property test: HeadWobbler receives base64-encoded audio from output().

        Feature: elevenlabs-integration, Property 3: Audio Output Feeds HeadWobbler

        **Validates: Requirements 4.6, 5.2**

        For any valid audio bytes (even-length for int16 samples), when passed to
        ReachyAudioInterface.output(), the HeadWobbler.feed() method should receive
        the exact same audio data encoded as base64.
        """
        # Arrange
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        # Act
        interface.output(audio_bytes)

        # Assert
        # HeadWobbler should have received exactly one feed call
        assert len(head_wobbler.feed_calls) == 1, (
            f"Expected exactly 1 feed call, got {len(head_wobbler.feed_calls)}"
        )

        # The received base64 should decode to the original audio bytes
        received_b64 = head_wobbler.feed_calls[0]
        decoded_audio = base64.b64decode(received_b64)

        assert decoded_audio == audio_bytes, (
            f"HeadWobbler received different audio data. "
            f"Expected {len(audio_bytes)} bytes, got {len(decoded_audio)} bytes"
        )

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(audio_chunks=st.lists(even_length_binary, min_size=1, max_size=10))
    def test_multiple_audio_outputs_feed_head_wobbler_in_order(
        self, audio_chunks: list[bytes]
    ) -> None:
        """Property test: Multiple audio outputs feed HeadWobbler in order.

        Feature: elevenlabs-integration, Property 3: Audio Output Feeds HeadWobbler

        **Validates: Requirements 4.6, 5.2**

        For any sequence of audio chunks, each chunk should be fed to HeadWobbler
        in the same order they were output.
        """
        # Arrange
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        # Act
        for chunk in audio_chunks:
            interface.output(chunk)

        # Assert
        # HeadWobbler should have received exactly len(audio_chunks) feed calls
        assert len(head_wobbler.feed_calls) == len(audio_chunks), (
            f"Expected {len(audio_chunks)} feed calls, got {len(head_wobbler.feed_calls)}"
        )

        # Each feed call should contain the corresponding audio chunk as base64
        for i, (expected_chunk, received_b64) in enumerate(
            zip(audio_chunks, head_wobbler.feed_calls)
        ):
            decoded_audio = base64.b64decode(received_b64)
            assert decoded_audio == expected_chunk, (
                f"Chunk {i}: HeadWobbler received different audio data. "
                f"Expected {len(expected_chunk)} bytes, got {len(decoded_audio)} bytes"
            )


class TestInterruptResetsHeadWobblerProperty:
    """Property-based tests for interrupt behavior.

    Feature: elevenlabs-integration, Property 4: Interrupt Resets HeadWobbler

    **Validates: Requirements 5.4**

    Property Definition:
    *For any* call to `ReachyAudioInterface.interrupt()`, the HeadWobbler's
    `reset()` method should be called exactly once.
    """

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(interrupt_count=st.integers(min_value=1, max_value=10))
    def test_interrupt_resets_head_wobbler(self, interrupt_count: int) -> None:
        """Property test: Each interrupt() call triggers exactly one HeadWobbler reset().

        Feature: elevenlabs-integration, Property 4: Interrupt Resets HeadWobbler

        **Validates: Requirements 5.4**

        For any number of interrupt() calls (1 to 10), the HeadWobbler's reset()
        method should be called exactly that many times - once per interrupt.
        """
        # Arrange
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        # Act
        for _ in range(interrupt_count):
            interface.interrupt()

        # Assert
        assert head_wobbler.reset_calls == interrupt_count, (
            f"Expected {interrupt_count} reset calls, got {head_wobbler.reset_calls}. "
            f"Each interrupt() should trigger exactly one reset()."
        )

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(interrupt_count=st.integers(min_value=1, max_value=10))
    def test_interrupt_clears_audio_buffer_each_time(self, interrupt_count: int) -> None:
        """Property test: Each interrupt() call clears the audio buffer.

        Feature: elevenlabs-integration, Property 4: Interrupt Resets HeadWobbler

        **Validates: Requirements 5.4**

        For any number of interrupt() calls, the audio buffer should be cleared
        each time (buffer_cleared flag should be True after any interrupt).
        """
        # Arrange
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        # Act
        for i in range(interrupt_count):
            # Reset the flag before each interrupt to verify it gets set
            robot.media.audio.buffer_cleared = False
            interface.interrupt()

            # Assert after each interrupt
            assert robot.media.audio.buffer_cleared is True, (
                f"Interrupt {i + 1}: Audio buffer should be cleared after interrupt()"
            )

    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    @given(
        audio_chunks=st.lists(even_length_binary, min_size=0, max_size=5),
        interrupt_count=st.integers(min_value=1, max_value=5),
    )
    def test_interrupt_resets_head_wobbler_regardless_of_prior_output(
        self, audio_chunks: list[bytes], interrupt_count: int
    ) -> None:
        """Property test: Interrupt resets HeadWobbler regardless of prior audio output.

        Feature: elevenlabs-integration, Property 4: Interrupt Resets HeadWobbler

        **Validates: Requirements 5.4**

        For any sequence of audio outputs followed by any number of interrupts,
        the HeadWobbler's reset() should be called exactly once per interrupt,
        independent of how many audio chunks were output before.
        """
        # Arrange
        robot = MockRobot()
        head_wobbler = MockHeadWobbler()
        interface = ReachyAudioInterface(robot, head_wobbler)

        # Act - output some audio first
        for chunk in audio_chunks:
            interface.output(chunk)

        # Record feed calls before interrupts
        feed_calls_before = len(head_wobbler.feed_calls)

        # Now interrupt multiple times
        for _ in range(interrupt_count):
            interface.interrupt()

        # Assert
        # HeadWobbler should have received feed calls for each audio chunk
        assert len(head_wobbler.feed_calls) == feed_calls_before, (
            f"Feed calls should not change after interrupts. "
            f"Expected {feed_calls_before}, got {len(head_wobbler.feed_calls)}"
        )

        # HeadWobbler should have been reset exactly interrupt_count times
        assert head_wobbler.reset_calls == interrupt_count, (
            f"Expected {interrupt_count} reset calls after {len(audio_chunks)} audio outputs, "
            f"got {head_wobbler.reset_calls}. Prior audio output should not affect reset count."
        )
