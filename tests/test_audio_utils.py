"""Unit tests for audio utility functions."""

from __future__ import annotations

import numpy as np
import pytest

from reachy_mini_elevenlabs.audio.utils import (
    ELEVENLABS_SAMPLE_RATE,
    ROBOT_SAMPLE_RATE,
    audio_to_float32,
    convert_for_playback,
    resample_audio,
    resample_for_robot,
    to_float32_mono,
)


class TestAudioToFloat32:
    """Tests for the audio_to_float32 function."""

    def test_converts_int16_array_to_float32(self) -> None:
        """Test conversion of int16 numpy array to float32."""
        int_audio = np.array([0, 16384, -16384, 32767, -32768], dtype=np.int16)
        float_audio = audio_to_float32(int_audio)

        assert float_audio.dtype == np.float32
        assert len(float_audio) == len(int_audio)
        # Check normalization: max int16 (32767) should be close to 1.0
        assert float_audio[3] == pytest.approx(1.0, rel=1e-4)
        # Min int16 (-32768) should be close to -1.0
        assert float_audio[4] == pytest.approx(-1.0, rel=1e-4)
        # Zero should remain zero
        assert float_audio[0] == 0.0

    def test_converts_bytes_to_float32(self) -> None:
        """Test conversion of raw PCM bytes to float32."""
        # Create int16 bytes: [0, 16384] in little-endian
        int_audio = np.array([0, 16384], dtype=np.int16)
        audio_bytes = int_audio.tobytes()

        float_audio = audio_to_float32(audio_bytes, dtype="int16")

        assert float_audio.dtype == np.float32
        assert len(float_audio) == 2
        assert float_audio[0] == 0.0
        assert float_audio[1] == pytest.approx(0.5, rel=1e-4)

    def test_handles_empty_array(self) -> None:
        """Test handling of empty input array."""
        empty_array = np.array([], dtype=np.int16)
        result = audio_to_float32(empty_array)

        assert result.dtype == np.float32
        assert len(result) == 0

    def test_handles_empty_bytes(self) -> None:
        """Test handling of empty bytes input."""
        result = audio_to_float32(b"", dtype="int16")

        assert result.dtype == np.float32
        assert len(result) == 0

    def test_preserves_float32_input(self) -> None:
        """Test that float32 input is preserved without modification."""
        float_audio = np.array([0.0, 0.5, -0.5, 1.0, -1.0], dtype=np.float32)
        result = audio_to_float32(float_audio)

        assert result.dtype == np.float32
        np.testing.assert_array_equal(result, float_audio)

    def test_converts_float64_to_float32(self) -> None:
        """Test conversion of float64 to float32."""
        float64_audio = np.array([0.0, 0.5, -0.5], dtype=np.float64)
        result = audio_to_float32(float64_audio)

        assert result.dtype == np.float32
        np.testing.assert_array_almost_equal(result, float64_audio.astype(np.float32))

    def test_converts_int32_to_float32(self) -> None:
        """Test conversion of int32 PCM to float32."""
        int32_audio = np.array([0, 1073741824, -1073741824], dtype=np.int32)
        result = audio_to_float32(int32_audio)

        assert result.dtype == np.float32
        assert result[0] == 0.0
        # int32 max is 2147483647, so 1073741824 is ~0.5
        assert result[1] == pytest.approx(0.5, rel=1e-4)


class TestToFloat32Mono:
    """Tests for the to_float32_mono function."""

    def test_converts_mono_int16_to_float32(self) -> None:
        """Test conversion of mono int16 array."""
        mono = np.array([0, 16384, -16384], dtype=np.int16)
        result = to_float32_mono(mono)

        assert result.dtype == np.float32
        assert result.ndim == 1
        assert len(result) == 3

    def test_converts_stereo_to_mono(self) -> None:
        """Test conversion of stereo (2, N) array to mono."""
        # Stereo with shape (2, 3): channels first
        stereo = np.array([[100, 200, 300], [100, 200, 300]], dtype=np.int16)
        result = to_float32_mono(stereo)

        assert result.dtype == np.float32
        assert result.ndim == 1
        assert len(result) == 3

    def test_converts_stereo_samples_first_to_mono(self) -> None:
        """Test conversion of stereo (N, 2) array to mono."""
        # Stereo with shape (3, 2): samples first
        stereo = np.array([[100, 100], [200, 200], [300, 300]], dtype=np.int16)
        result = to_float32_mono(stereo)

        assert result.dtype == np.float32
        assert result.ndim == 1
        # Should average across channels (axis=1)
        assert len(result) == 3

    def test_handles_empty_array(self) -> None:
        """Test handling of empty array."""
        empty = np.array([], dtype=np.int16)
        result = to_float32_mono(empty)

        assert result.dtype == np.float32
        assert len(result) == 0

    def test_handles_scalar_array(self) -> None:
        """Test handling of scalar (0-dimensional) array."""
        scalar = np.array(100, dtype=np.int16)
        result = to_float32_mono(scalar)

        assert result.dtype == np.float32
        assert len(result) == 0


class TestResampleAudio:
    """Tests for the resample_audio function."""

    def test_no_resampling_when_rates_match(self) -> None:
        """Test that no resampling occurs when rates match."""
        audio = np.array([0.0, 0.5, 1.0, 0.5, 0.0], dtype=np.float32)
        result = resample_audio(audio, 16000, 16000)

        np.testing.assert_array_equal(result, audio)

    def test_downsamples_correctly(self) -> None:
        """Test downsampling from 24000 to 16000 Hz."""
        # Create 24000 samples (1 second at 24kHz)
        audio = np.sin(2 * np.pi * 440 * np.arange(24000) / 24000).astype(np.float32)
        result = resample_audio(audio, 24000, 16000)

        # Should have 16000 samples (1 second at 16kHz)
        assert len(result) == 16000
        assert result.dtype == np.float32

    def test_upsamples_correctly(self) -> None:
        """Test upsampling from 16000 to 24000 Hz."""
        # Create 16000 samples (1 second at 16kHz)
        audio = np.sin(2 * np.pi * 440 * np.arange(16000) / 16000).astype(np.float32)
        result = resample_audio(audio, 16000, 24000)

        # Should have 24000 samples (1 second at 24kHz)
        assert len(result) == 24000
        assert result.dtype == np.float32

    def test_handles_empty_array(self) -> None:
        """Test handling of empty array."""
        empty = np.array([], dtype=np.float32)
        result = resample_audio(empty, 24000, 16000)

        assert len(result) == 0
        assert result.dtype == np.float32

    def test_handles_very_short_array(self) -> None:
        """Test handling of very short array that would result in <1 sample."""
        short = np.array([0.5], dtype=np.float32)
        result = resample_audio(short, 24000, 16000)

        # Result should be empty or single sample
        assert result.dtype == np.float32


class TestResampleForRobot:
    """Tests for the resample_for_robot convenience function."""

    def test_uses_default_sample_rates(self) -> None:
        """Test that default sample rates are ElevenLabs (24k) to robot (16k)."""
        # Create 2400 samples (0.1 second at 24kHz)
        audio = np.random.randn(2400).astype(np.float32)
        result = resample_for_robot(audio)

        # Should have 1600 samples (0.1 second at 16kHz)
        assert len(result) == 1600
        assert result.dtype == np.float32

    def test_accepts_custom_rates(self) -> None:
        """Test that custom sample rates can be specified."""
        audio = np.random.randn(4800).astype(np.float32)
        result = resample_for_robot(audio, source_rate=48000, target_rate=24000)

        # Should have 2400 samples
        assert len(result) == 2400


class TestConvertForPlayback:
    """Tests for the convert_for_playback convenience function."""

    def test_converts_bytes_without_resampling(self) -> None:
        """Test conversion of bytes without resampling."""
        int_audio = np.array([0, 16384, -16384], dtype=np.int16)
        audio_bytes = int_audio.tobytes()

        result = convert_for_playback(audio_bytes)

        assert result.dtype == np.float32
        assert len(result) == 3

    def test_converts_bytes_with_resampling(self) -> None:
        """Test conversion of bytes with resampling."""
        # Create 2400 int16 samples
        int_audio = np.random.randint(-32768, 32767, size=2400, dtype=np.int16)
        audio_bytes = int_audio.tobytes()

        result = convert_for_playback(audio_bytes, source_rate=24000, target_rate=16000)

        assert result.dtype == np.float32
        assert len(result) == 1600

    def test_converts_array_without_resampling(self) -> None:
        """Test conversion of numpy array without resampling."""
        int_audio = np.array([0, 16384, -16384], dtype=np.int16)

        result = convert_for_playback(int_audio)

        assert result.dtype == np.float32
        assert len(result) == 3

    def test_converts_array_with_resampling(self) -> None:
        """Test conversion of numpy array with resampling."""
        int_audio = np.random.randint(-32768, 32767, size=2400, dtype=np.int16)

        result = convert_for_playback(int_audio, source_rate=24000, target_rate=16000)

        assert result.dtype == np.float32
        assert len(result) == 1600


class TestSampleRateConstants:
    """Tests for sample rate constants."""

    def test_elevenlabs_sample_rate(self) -> None:
        """Test that ElevenLabs sample rate is 24000 Hz."""
        assert ELEVENLABS_SAMPLE_RATE == 24000

    def test_robot_sample_rate(self) -> None:
        """Test that robot sample rate is 16000 Hz."""
        assert ROBOT_SAMPLE_RATE == 16000
