"""Custom audio interface for Reachy Mini robot.

This module implements the ElevenLabs AudioInterface to route audio through
the robot's microphone and speaker while integrating with the HeadWobbler
for lip-sync animation.

The audio format expected by ElevenLabs:
- Input: 16-bit PCM mono at 16kHz
- Output: 16-bit PCM mono at 16kHz
"""

from __future__ import annotations

import base64
import logging
import threading
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

import numpy as np

from elevenlabs.conversational_ai.conversation import AudioInterface

from reachy_mini_elevenlabs.audio.utils import audio_to_float32

if TYPE_CHECKING:
    from reachy_mini import ReachyMini

    from reachy_mini_elevenlabs.audio.head_wobbler import HeadWobbler


logger = logging.getLogger(__name__)

# Audio configuration
INPUT_SAMPLE_RATE = 16000  # ElevenLabs expects 16kHz input
INPUT_CHUNK_SAMPLES = 4000  # 250ms chunks as recommended by ElevenLabs
INPUT_CHUNK_DURATION_S = INPUT_CHUNK_SAMPLES / INPUT_SAMPLE_RATE


class ReachyAudioInterface(AudioInterface):
    """Custom audio interface for Reachy Mini robot.

    This class bridges the ElevenLabs Conversation SDK with the robot's
    audio hardware and HeadWobbler animation system.

    The interface:
    - Captures audio from the robot's microphone and sends it to ElevenLabs
    - Receives synthesized speech from ElevenLabs and plays it through the speaker
    - Feeds audio to HeadWobbler for lip-sync animation
    - Handles interruptions by clearing audio buffers and resetting HeadWobbler

    Attributes:
        robot: The ReachyMini robot instance for audio I/O.
        head_wobbler: The HeadWobbler instance for lip-sync animation.
    """

    def __init__(self, robot: ReachyMini, head_wobbler: HeadWobbler) -> None:
        """Initialize the audio interface.

        Args:
            robot: The ReachyMini robot instance providing audio hardware access.
            head_wobbler: The HeadWobbler instance for lip-sync animation.
        """
        self.robot = robot
        self.head_wobbler = head_wobbler
        self._recording = False
        self._input_callback: Callable[[bytes], None] | None = None
        self._input_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        # Echo suppression: track when robot is speaking so we can mute mic input
        self._last_output_time: float = 0.0
        self._echo_suppression_tail_s: float = 0.3  # keep muting 300ms after last output

    def start(self, input_callback: Callable[[bytes], None]) -> None:
        """Start audio capture from robot microphone.

        Called once before the conversation starts. Begins capturing audio
        from the robot's microphone and calling the input_callback with
        audio chunks.

        Args:
            input_callback: Function to call with audio chunks (PCM bytes).
                The audio should be in 16-bit PCM mono format at 16kHz.
                Recommended chunk size is 4000 samples (250 milliseconds).
        """
        logger.debug("Starting audio interface")
        self._input_callback = input_callback
        self._recording = True
        self._stop_event.clear()

        # Start recording on the robot
        self.robot.media.start_recording()
        
        # Start playing on the robot (for output)
        self.robot.media.start_playing()
        
        # Give pipelines time to start
        time.sleep(1)

        # Start background thread to read from microphone
        self._input_thread = threading.Thread(
            target=self._input_loop,
            daemon=True,
            name="ReachyAudioInterface-Input",
        )
        self._input_thread.start()
        logger.info("Audio interface started")

    def stop(self) -> None:
        """Stop audio capture.

        Called once after the conversation ends. Stops the microphone
        capture and cleans up resources.
        """
        logger.debug("Stopping audio interface")
        self._recording = False
        self._stop_event.set()

        # Stop recording on the robot
        self.robot.media.stop_recording()
        
        # Stop playing on the robot
        self.robot.media.stop_playing()

        # Wait for input thread to finish
        if self._input_thread is not None:
            self._input_thread.join(timeout=2.0)
            self._input_thread = None

        self._input_callback = None
        logger.info("Audio interface stopped")

    def output(self, audio: bytes) -> None:
        """Play audio through robot speaker.

        Receives audio from ElevenLabs and:
        1. Feeds it to HeadWobbler for lip-sync animation
        2. Converts it to float32 format
        3. Pushes it to the robot's speaker

        This method should return quickly and not block the calling thread.

        Args:
            audio: PCM audio bytes to play (16-bit PCM mono at 16kHz).
        """
        if not audio:
            return

        # Mark that we're outputting audio (for echo suppression)
        self._last_output_time = time.monotonic()

        # Convert to numpy array for processing
        audio_array = np.frombuffer(audio, dtype=np.int16)

        # Feed to HeadWobbler for lip-sync animation
        # HeadWobbler expects base64-encoded audio
        audio_b64 = base64.b64encode(audio).decode("utf-8")
        self.head_wobbler.feed(audio_b64)

        # Convert to float32 and push to speaker
        audio_float = audio_to_float32(audio_array)
        self.robot.media.push_audio_sample(audio_float)

    def interrupt(self) -> None:
        """Handle user interruption - stop current playback.

        Called when the user interrupts the agent. Clears any buffered
        audio output and resets the HeadWobbler state.
        """
        logger.debug("Handling audio interruption")

        # Clear audio output buffer on the robot
        self.robot.media.audio.clear_output_buffer()

        # Reset HeadWobbler state
        self.head_wobbler.reset()

        logger.debug("Audio interruption handled")

    def _input_loop(self) -> None:
        """Background loop to read audio from microphone and send to callback.

        Reads audio chunks from the robot's microphone and calls the
        input_callback with the audio data. Runs in a separate thread.
        
        Strategy: Send audio chunks as they arrive (like conversation app does),
        with resampling if needed. Don't wait to accumulate large buffers since
        the robot returns None frequently, which would cause long delays.
        """
        logger.debug("Audio input loop started")
        
        # Get the robot's input sample rate
        robot_sample_rate = self.robot.media.get_input_audio_samplerate()
        logger.info(f"Robot microphone sample rate: {robot_sample_rate} Hz")
        logger.info(f"ElevenLabs expects: {INPUT_SAMPLE_RATE} Hz")
        
        needs_resampling = robot_sample_rate != INPUT_SAMPLE_RATE
        
        sample_count = 0
        none_count = 0
        chunks_sent = 0

        while self._recording and not self._stop_event.is_set():
            try:
                # Read audio chunk from robot microphone
                audio_data = self.robot.media.get_audio_sample()
                
                sample_count += 1
                
                if audio_data is None:
                    none_count += 1
                    # Sleep briefly to avoid busy-waiting
                    time.sleep(0.001)  # 1ms - shorter sleep for more responsive audio
                    continue

                if self._input_callback is not None:
                    # Convert to numpy array if needed
                    if not isinstance(audio_data, np.ndarray):
                        audio_data = np.frombuffer(audio_data, dtype=np.int16)
                    
                    # Log first successful sample with detailed info
                    if chunks_sent == 0:
                        logger.info(f"First audio sample received: {len(audio_data)} samples, dtype: {audio_data.dtype}, shape: {audio_data.shape}")
                        logger.info(f"First sample stats: min={audio_data.min():.6f}, max={audio_data.max():.6f}, mean={audio_data.mean():.6f}")
                    
                    # Handle stereo to mono conversion
                    if audio_data.ndim == 2 and audio_data.shape[1] == 2:
                        # Stereo audio - check which channel has data
                        if chunks_sent == 0:
                            ch0_level = np.abs(audio_data[:, 0]).mean()
                            ch1_level = np.abs(audio_data[:, 1]).mean()
                            logger.info(f"Stereo audio detected - Channel 0 level: {ch0_level:.6f}, Channel 1 level: {ch1_level:.6f}")
                        
                        # Check if only one channel has significant audio
                        ch0_max = np.abs(audio_data[:, 0]).max()
                        ch1_max = np.abs(audio_data[:, 1]).max()
                        
                        if ch0_max > ch1_max * 2:  # Channel 0 has significantly more audio
                            audio_data = audio_data[:, 0]
                            if chunks_sent == 0:
                                logger.info(f"Using channel 0 only (stronger signal)")
                        elif ch1_max > ch0_max * 2:  # Channel 1 has significantly more audio
                            audio_data = audio_data[:, 1]
                            if chunks_sent == 0:
                                logger.info(f"Using channel 1 only (stronger signal)")
                        else:  # Both channels have similar levels - average them
                            audio_data = audio_data.mean(axis=1)
                            if chunks_sent == 0:
                                logger.info(f"Averaging both channels (similar levels)")
                        
                        if chunks_sent == 0:
                            logger.info(f"Converted stereo to mono: new shape {audio_data.shape}")
                    elif audio_data.ndim == 2:
                        # Multi-channel but not stereo - take first channel
                        audio_data = audio_data[:, 0]
                        if chunks_sent == 0:
                            logger.info(f"Extracted first channel from multi-channel audio: new shape {audio_data.shape}")
                    
                    # Ensure correct format
                    if audio_data.dtype != np.int16:
                        if np.issubdtype(audio_data.dtype, np.floating):
                            # Convert float32 [-1, 1] to int16
                            if chunks_sent == 0:
                                logger.info(f"Converting float32 to int16")
                            audio_data = (audio_data * 32767).astype(np.int16)
                        else:
                            audio_data = audio_data.astype(np.int16)
                    
                    # Resample if needed (robot is 44.1kHz, ElevenLabs expects 16kHz)
                    if needs_resampling:
                        from scipy.signal import resample
                        target_length = int(len(audio_data) * INPUT_SAMPLE_RATE / robot_sample_rate)
                        if target_length < 1:
                            continue
                        audio_data = resample(audio_data, target_length).astype(np.int16)
                    
                    # Echo suppression: send silence while robot is speaking
                    time_since_output = time.monotonic() - self._last_output_time
                    if self._last_output_time > 0 and time_since_output < self._echo_suppression_tail_s:
                        audio_data = np.zeros_like(audio_data)

                    # Check audio levels to verify we're sending actual sound
                    audio_level = np.abs(audio_data).mean()
                    max_level = np.abs(audio_data).max()
                    
                    # Send immediately (don't buffer)
                    audio_bytes = audio_data.tobytes()
                    self._input_callback(audio_bytes)
                    chunks_sent += 1
                    
                    # Log audio levels only for first few chunks
                    if chunks_sent <= 5:  # Only log first 5 chunks
                        logger.info(f"Chunk {chunks_sent}: {len(audio_data)} samples, avg level: {audio_level:.0f}, max: {max_level:.0f}")
                    
                    if chunks_sent % 100 == 0:  # Log stats every 100 chunks
                        logger.debug(f"Sent {chunks_sent} audio chunks, {none_count}/{sample_count} samples were None ({100*none_count/sample_count:.1f}%)")

            except Exception as e:
                logger.error(f"Error reading audio input: {e}", exc_info=True)
                # Sleep briefly before retrying
                time.sleep(0.1)

        logger.info(f"Audio input loop stopped. Sent {chunks_sent} chunks, {none_count}/{sample_count} samples were None ({100*none_count/sample_count:.1f}%)")
