# External Audio Routing for Reachy Mini

Use external microphones and speakers with the Reachy Mini ElevenLabs
app — for conferences, demos, classrooms, or any situation where the
built-in respeaker mic/speaker isn't enough.

## Why This Exists

The Reachy Mini SDK hardcodes its audio device selection. It scans all
audio devices and grabs the first one whose name contains **"Reachy
Mini Audio"** or **"respeaker"**. You can't change this from the app
settings, and changing the system default audio device has no effect.

These scripts work around that by creating PulseAudio virtual devices
that impersonate "Reachy Mini Audio" while routing audio through your
external hardware. The real respeaker is temporarily hidden (suspended)
so there's no name conflict.

## What's In This Folder

| File | Purpose |
|------|---------|
| `setup.sh` | One-time setup — detects your hardware and creates a config file |
| `external-audio-on.sh` | Switch to external mic/speaker |
| `external-audio-off.sh` | Switch back to built-in respeaker |
| `audio-status.sh` | Show current routing and what the SDK sees |
| `README.md` | This file |

## Quick Start

### 1. Plug in your external audio device

Connect your USB microphone, USB speaker, USB conference speakerphone,
or whatever external audio hardware you want to use.

### 2. Run setup (once)

```bash
cd audio-routing
chmod +x *.sh
./setup.sh
```

This will:
- List all audio devices on the system
- Ask you to pick your external speaker and microphone
- Save your choices to `~/.config/reachy-audio/devices.conf`

You only need to run setup once per external device. If you swap
hardware, run it again.

### 3. Switch to external audio

```bash
./external-audio-on.sh
```

Then **restart the ElevenLabs app** (stop and start it from the Reachy
Mini dashboard, or restart the service).

### 4. Switch back to internal audio

```bash
./external-audio-off.sh
```

Then **restart the ElevenLabs app** again.

## When to Run These

| Scenario | What to do |
|----------|------------|
| Before a conference/demo with external audio | Run `external-audio-on.sh`, then restart the app |
| Going back to normal use | Run `external-audio-off.sh`, then restart the app |
| Just plugged in new hardware | Run `setup.sh` to reconfigure, then `external-audio-on.sh` |
| Something seems wrong | Run `audio-status.sh` to see what the SDK is picking up |
| Rebooted the robot | Everything resets to internal automatically — no action needed |

## Important Notes

### No virtual environment needed

These scripts are pure bash + `pactl` (a system tool). You do **not**
need to activate the Reachy Mini Control app's virtual environment to
run them. Just open a terminal and run them directly.

The `audio-status.sh` script has an optional `sounddevice` diagnostic
that shows what the SDK sees. It will automatically try to find the
Reachy Mini app's venv for this check. If it can't find `sounddevice`,
it prints a harmless notice — the audio routing still works fine.

### The app must be restarted after switching

The SDK reads audio devices at startup. Switching profiles while the
app is running won't take effect until you restart it.

### Order of operations

1. Make sure the Reachy Mini Control App is running (it manages the
   app lifecycle)
2. Stop the ElevenLabs app from the dashboard
3. Run `external-audio-on.sh` or `external-audio-off.sh`
4. Start the ElevenLabs app from the dashboard

### This is completely safe

The scripts use `pactl suspend-sink/source` which is a **soft,
temporary pause** at the PulseAudio layer. It does NOT:

- Disable the hardware or kernel driver
- Modify any system configuration files
- Persist across reboots
- Require root/sudo

If anything goes wrong, **just reboot**. Everything returns to factory
state. You can also recover instantly:

```bash
./external-audio-off.sh
```

### Multiple external devices

If you have different setups for different situations (e.g., a
conference speakerphone vs. a demo PA system), run `setup.sh` each
time you switch hardware. Your previous config is overwritten, but
that's fine — just run setup again when you switch back.

## Troubleshooting

### "pactl: command not found"

```bash
sudo apt install pulseaudio-utils
```

Or if using PipeWire:

```bash
sudo apt install pipewire-pulse
```

### External device not showing up

```bash
# Check USB is recognized
lsusb

# Check ALSA sees it
arecord -l
aplay -l

# Check PulseAudio sees it
pactl list short sinks
pactl list short sources
```

If the device shows in `lsusb` but not in PulseAudio, you may need
drivers for that specific USB audio device.

### App still uses the respeaker after switching

Run `audio-status.sh` and check the output. The respeaker should show
as SUSPENDED and only the virtual "Reachy Mini Audio" device should be
visible to sounddevice. If not, make sure you ran the script **before**
starting the app.

### No sound / no mic input

1. Check the external device works outside of Reachy: `aplay -D default /usr/share/sounds/alsa/Front_Center.wav`
2. Check volume levels: `alsamixer` or `pavucontrol`
3. Run `audio-status.sh` to verify routing
4. Make sure you restarted the app after switching
