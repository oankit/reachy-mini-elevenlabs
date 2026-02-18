# External Audio Device Selection for Reachy Mini

This guide explains how to add interactive audio device selection to
the Reachy Mini SDK so you can choose which speaker and microphone to
use at startup — for conferences, demos, or any situation where the
built-in respeaker isn't ideal.

## The Problem

The Reachy Mini SDK (`reachy_mini.media.audio_sounddevice.SoundDeviceAudio`)
hardcodes its audio device selection. It scans `sounddevice.query_devices()`
for a device whose name contains "Reachy Mini Audio" or "respeaker" and
opens it by integer index directly via ALSA.

This means:
- Changing PulseAudio defaults has no effect (the SDK bypasses PulseAudio)
- ALSA `.asoundrc` config has no effect (the SDK opens by index, not by name)
- PulseAudio virtual devices have no effect (the SDK talks to ALSA directly)
- `pavucontrol` can't see or redirect the stream

The only way to change the audio device is to modify the SDK's device
selection code.

## The Solution

We modify three things in the SDK's `audio_sounddevice.py` file:
1. Interactive device selection at startup
2. Force 16 kHz output sample rate for external devices
3. Larger output buffers to prevent ALSA underruns

Plus a bonus fix in the ElevenLabs app's `audio_interface.py`.

## What to Modify

### File Location

Find the SDK file on your Reachy Mini (Lubuntu) machine:

```bash
find / -name "audio_sounddevice.py" -path "*/reachy_mini/*" 2>/dev/null
```

Typical path:
```
/home/<user>/reachy_mini_env/lib/python3.12/site-packages/reachy_mini/media/audio_sounddevice.py
```

### Change 1: Interactive Device Selection

Find the `_get_device_id` method. The original looks like this:

```python
def _get_device_id(
        self, names_contains: List[str], device_io_type: str = "output"
    ) -> int:
        devices = sd.query_devices()

        for idx, dev in enumerate(devices):
            for name_contains in names_contains:
                if (
                    name_contains.lower() in dev["name"].lower()
                    and dev[f"max_{device_io_type}_channels"] > 0
                ):
                    return idx
        self.logger.warning(
            f"No {device_io_type} device found containing '{names_contains}', using default."
        )
        return self._safe_query_device(device_io_type)
```

Replace the entire method with:

```python
def _get_device_id(
        self, names_contains: List[str], device_io_type: str = "output"
    ) -> int:
        devices = sd.query_devices()
        channel_key = f"max_{device_io_type}_channels"

        eligible = [
            (idx, dev) for idx, dev in enumerate(devices)
            if dev[channel_key] > 0
        ]

        if eligible:
            print(f"\n{'='*50}")
            print(f"  Select {device_io_type.upper()} device")
            print(f"{'='*50}")
            for i, (idx, dev) in enumerate(eligible):
                ch = dev[channel_key]
                marker = ""
                name_lower = dev["name"].lower()
                if "reachy" in name_lower or "respeaker" in name_lower:
                    marker = "  [default]"
                print(f"  [{i}] {dev['name']}  ({ch}ch){marker}")
            print()
            try:
                choice = input(f"  Enter number for {device_io_type} device: ").strip()
                if choice.isdigit() and 0 <= int(choice) < len(eligible):
                    chosen_idx, chosen_dev = eligible[int(choice)]
                    self.logger.info(
                        f"User selected {device_io_type} device [{chosen_idx}]: {chosen_dev['name']}"
                    )
                    print(f"  -> {chosen_dev['name']}\n")
                    return chosen_idx
                else:
                    print("  Invalid choice, falling back to auto-detect.\n")
            except (EOFError, KeyboardInterrupt):
                print("\n  Skipped, falling back to auto-detect.\n")

        # Fallback: original auto-detect behavior
        for idx, dev in enumerate(devices):
            for name_contains in names_contains:
                if (
                    name_contains.lower() in dev["name"].lower()
                    and dev[channel_key] > 0
                ):
                    self.logger.info(
                        f"Auto-selected {device_io_type} device [{idx}]: {dev['name']}"
                    )
                    return idx

        self.logger.warning(
            f"No {device_io_type} device found containing '{names_contains}', using default."
        )
        return self._safe_query_device(device_io_type)
```

### Change 2: Force 16 kHz Output Sample Rate

When using an external output device (e.g. the 3.5 mm jack on the HDA
Intel card), the device reports its native rate — typically 44100 or
48000 Hz. But the audio pipeline produces 16 kHz data. If the SDK opens
the output stream at 44100 Hz and writes 16 kHz data into it, playback
runs at roughly 10× speed.

Find the `get_output_audio_samplerate` method. The original:

```python
def get_output_audio_samplerate(self) -> int:
    return int(
        sd.query_devices(self._output_device_id, "output")["default_samplerate"]
    )
```

Replace it with:

```python
def get_output_audio_samplerate(self) -> int:
    """Get the output samplerate of the audio device.

    Note: When using an external output device, we force 16000 Hz
    because the audio pipeline produces 16000 Hz data.
    """
    device_rate = int(
        sd.query_devices(self._output_device_id, "output")["default_samplerate"]
    )
    if device_rate > 16000:
        self.logger.info(
            f"Output device reports {device_rate} Hz, using 16000 Hz to match audio pipeline."
        )
        return 16000
    return device_rate
```

This forces the output stream to open at 16 kHz whenever the device
reports a higher native rate, matching the actual audio data rate.

### Change 3: Prevent ALSA Underrun Stuttering

External audio cards (especially over HDA Intel) are more sensitive to
buffer underruns than the respeaker. The default `sd.OutputStream`
settings use small buffers that cause audible stuttering.

Find the `start_playing` method. Look for the line that creates the
`sd.OutputStream`:

```python
self._output_stream = sd.OutputStream(
    samplerate=self.get_output_audio_samplerate(),
    device=self._output_device_id,
    callback=self._output_callback,
)
```

Add `blocksize=2048` and `latency="high"`:

```python
self._output_stream = sd.OutputStream(
    samplerate=self.get_output_audio_samplerate(),
    device=self._output_device_id,
    callback=self._output_callback,
    blocksize=2048,
    latency="high",
)
```

This gives ALSA a larger buffer to work with, eliminating underrun
stuttering. The added latency is negligible for conversational audio.

### Bonus Fix: ZeroDivisionError in audio_interface.py

When using an external input device, occasional empty audio chunks can
arrive during resampling, causing a `ZeroDivisionError` in
`scipy.signal.resample`.

This fix is in the ElevenLabs app code, not the SDK. Find
`audio_interface.py` in the `reachy_mini_elevenlabs` package, around
line 268 in the `_input_loop` method. Look for:

```python
if needs_resampling:
    from scipy.signal import resample
    target_length = int(len(audio_data) * INPUT_SAMPLE_RATE / robot_sample_rate)
    audio_data = resample(audio_data, target_length).astype(np.int16)
```

Add a guard before the resample call:

```python
if needs_resampling:
    from scipy.signal import resample
    target_length = int(len(audio_data) * INPUT_SAMPLE_RATE / robot_sample_rate)
    if target_length < 1:
        continue
    audio_data = resample(audio_data, target_length).astype(np.int16)
```

This skips empty chunks instead of crashing.

## Reverting

To restore the original SDK file, reinstall the package:

```bash
pip install --force-reinstall reachy_mini
```

Or if you're using a virtual environment:

```bash
source ~/reachy_mini_env/bin/activate
pip install --force-reinstall reachy_mini
```

## Caveats

- **SDK updates overwrite the patch.** Any `pip install --upgrade
  reachy_mini` or `pip install --force-reinstall reachy_mini` will
  replace `audio_sounddevice.py` with the stock version. You'll need
  to re-apply the changes after updating.

- **The device prompt blocks startup.** The app will wait for you to
  type a device number before continuing. If running headless or via
  systemd, press Enter or Ctrl+C to fall back to auto-detect
  (respeaker).

- **The prompt appears twice.** Once when Reachy Mini Control starts
  (it initializes the SDK), and again when the ElevenLabs app starts
  (it creates its own SDK instance). This is expected — you pick
  devices for each.

- **Sample rate forcing is output-only.** Input resampling is handled
  by the ElevenLabs app's `audio_interface.py`, not by this SDK patch.
  The SDK reads input at whatever rate the device reports.
