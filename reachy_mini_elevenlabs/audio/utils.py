"""Audio utility functions for Reachy Mini ElevenLabs integration.

This module provides public utility functions for audio conversion and resampling,
ensuring compatibility between ElevenLabs audio output and the robot's audio system.

Key sample rates:
- ElevenLabs output: 24000 Hz (PCM int16)
- Robot speaker input: Typically 16000 Hz or 24000 Hz (float32)
"""

from __future__ import annotations

from typing import Any

import numpy as np
from numpy.typing import NDArray


# Common sample rates
ELEVENLABS_SAMPLE_RATE = 24000  # ElevenLabs default output sample rate
ROBOT_SAMPLE_RATE = 16000  # Common robot audio sample rate


def audio_to_float32(
    audio: NDArray[Any] | bytes,
    dtype: str = "int16",
) -> NDArray[np.float32]:
    """Convert audio data to float32 format in range [-1.0, 1.0].

    This function converts PCM audio data (typically int16 from ElevenLabs)
    to float32 format suitable for the robot's speaker output.

    Args:
        audio: Audio data as numpy array or raw bytes.
            If bytes, will be interpreted using the specified dtype.
        dtype: Data type of the input bytes (default: "int16").
            Only used when audio is bytes.

    Returns:
        Float32 numpy array with values normalized to [-1.0, 1.0].

    Examples:
        >>> # Convert int16 PCM bytes from ElevenLabs
        >>> audio_bytes = b'\\x00\\x10\\x00\\x20'
        >>> float_audio = audio_to_float32(audio_bytes)

        >>> # Convert numpy int16 array
        >>> int_audio = np.array([0, 16384, -16384], dtype=np.int16)
        >>> float_audio = audio_to_float32(int_audio)
    """
    # Convert bytes to numpy array if needed
    if isinstance(audio, bytes):
        np_dtype = np.dtype(dtype)
        audio_array = np.frombuffer(audio, dtype=np_dtype)
    else:
        audio_array = np.asarray(audio)

    # Handle empty arrays
    if audio_array.size == 0:
        return np.zeros(0, dtype=np.float32)

    # If already floating point, just ensure float32
    if np.issubdtype(audio_array.dtype, np.floating):
        return audio_array.astype(np.float32, copy=False)

    # Convert integer PCM to float32 normalized to [-1.0, 1.0]
    info = np.iinfo(audio_array.dtype)
    scale = float(max(-info.min, info.max))
    if scale == 0.0:
        scale = 1.0

    return audio_array.astype(np.float32) / scale


def to_float32_mono(audio: NDArray[Any]) -> NDArray[np.float32]:
    """Convert arbitrary PCM array to float32 mono in [-1.0, 1.0].

    This is a public wrapper around the internal conversion function.
    Handles various input shapes and converts multi-channel audio to mono.

    Args:
        audio: Input audio array. Accepts shapes:
            - (N,): Mono audio with N samples
            - (1, N) or (N, 1): Mono audio in 2D format
            - (C, N) or (N, C): Multi-channel audio (averaged to mono)

    Returns:
        Float32 mono array with values in [-1.0, 1.0].

    Examples:
        >>> # Convert stereo int16 to mono float32
        >>> stereo = np.array([[100, 200], [-100, -200]], dtype=np.int16)
        >>> mono = to_float32_mono(stereo)
    """
    a = np.asarray(audio)

    # Handle empty or scalar arrays
    if a.ndim == 0:
        return np.zeros(0, dtype=np.float32)

    # If 2D, convert to mono by averaging channels
    if a.ndim == 2:
        # Determine which axis is channels (prefer small first dim)
        if a.shape[0] <= 8 and a.shape[0] <= a.shape[1]:
            # Shape is (channels, samples)
            a = np.mean(a, axis=0)
        else:
            # Shape is (samples, channels)
            a = np.mean(a, axis=1)
    elif a.ndim > 2:
        # Flatten higher dimensions
        a = np.mean(a.reshape(a.shape[0], -1), axis=0)

    # Now 1D, convert to float32
    if np.issubdtype(a.dtype, np.floating):
        return a.astype(np.float32, copy=False)

    # Integer PCM - normalize to [-1.0, 1.0]
    info = np.iinfo(a.dtype)
    scale = float(max(-info.min, info.max))
    if scale == 0.0:
        scale = 1.0

    return a.astype(np.float32) / scale


def resample_audio(
    audio: NDArray[np.float32],
    source_rate: int,
    target_rate: int,
) -> NDArray[np.float32]:
    """Resample audio from source sample rate to target sample rate.

    Uses linear interpolation for lightweight resampling suitable for
    real-time audio processing. For high-quality resampling, consider
    using scipy.signal.resample or librosa.

    Args:
        audio: Float32 audio array to resample.
        source_rate: Source sample rate in Hz (e.g., 24000).
        target_rate: Target sample rate in Hz (e.g., 16000).

    Returns:
        Resampled float32 audio array.

    Examples:
        >>> # Resample from ElevenLabs rate to robot rate
        >>> audio_24k = np.random.randn(24000).astype(np.float32)
        >>> audio_16k = resample_audio(audio_24k, 24000, 16000)
        >>> len(audio_16k)
        16000
    """
    # No resampling needed if rates match
    if source_rate == target_rate or audio.size == 0:
        return audio

    # Calculate output size
    n_out = int(round(audio.size * target_rate / source_rate))
    if n_out <= 1:
        return np.zeros(0, dtype=np.float32)

    # Linear interpolation resampling
    t_in = np.linspace(0.0, 1.0, num=audio.size, dtype=np.float32, endpoint=True)
    t_out = np.linspace(0.0, 1.0, num=n_out, dtype=np.float32, endpoint=True)

    return np.interp(t_out, t_in, audio).astype(np.float32, copy=False)


def resample_for_robot(
    audio: NDArray[np.float32],
    source_rate: int = ELEVENLABS_SAMPLE_RATE,
    target_rate: int = ROBOT_SAMPLE_RATE,
) -> NDArray[np.float32]:
    """Resample audio from ElevenLabs format to robot speaker format.

    Convenience function that uses common default sample rates for
    ElevenLabs output (24000 Hz) and robot input (16000 Hz).

    Args:
        audio: Float32 audio array from ElevenLabs.
        source_rate: Source sample rate (default: 24000 Hz).
        target_rate: Target sample rate for robot (default: 16000 Hz).

    Returns:
        Resampled float32 audio array suitable for robot speaker.

    Examples:
        >>> # Convert ElevenLabs audio for robot playback
        >>> elevenlabs_audio = np.random.randn(2400).astype(np.float32)
        >>> robot_audio = resample_for_robot(elevenlabs_audio)
    """
    return resample_audio(audio, source_rate, target_rate)


def convert_for_playback(
    audio: NDArray[Any] | bytes,
    source_rate: int = ELEVENLABS_SAMPLE_RATE,
    target_rate: int | None = None,
    dtype: str = "int16",
) -> NDArray[np.float32]:
    """Convert audio data for robot speaker playback.

    This is a convenience function that combines conversion to float32
    and optional resampling in a single call.

    Args:
        audio: Audio data as numpy array or raw bytes.
        source_rate: Source sample rate in Hz (default: 24000).
        target_rate: Target sample rate in Hz. If None, no resampling is done.
        dtype: Data type of input bytes (default: "int16").

    Returns:
        Float32 audio array ready for robot speaker playback.

    Examples:
        >>> # Convert ElevenLabs PCM bytes for robot playback
        >>> pcm_bytes = b'\\x00\\x10' * 1000
        >>> playback_audio = convert_for_playback(pcm_bytes, target_rate=16000)
    """
    # Convert to float32
    float_audio = audio_to_float32(audio, dtype=dtype)

    # Resample if target rate specified and different from source
    if target_rate is not None and target_rate != source_rate:
        float_audio = resample_audio(float_audio, source_rate, target_rate)

    return float_audio
