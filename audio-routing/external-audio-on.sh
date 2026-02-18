#!/bin/bash
# =============================================================================
# Reachy Mini Audio Routing — Switch to External Audio
#
# Creates virtual "Reachy Mini Audio" devices that route through your
# external hardware, and suspends the real respeaker so the SDK only
# sees the virtual device.
#
# Run setup.sh first to configure your external devices.
#
# Usage:
#   ./external-audio-on.sh
#
# After running this, restart the ElevenLabs app from the dashboard.
# =============================================================================

set -euo pipefail

CONFIG_DIR="$HOME/.config/reachy-audio"
CONFIG_FILE="$CONFIG_DIR/devices.conf"
STATE_FILE="$CONFIG_DIR/suspended.state"
VIRTUAL_NAME="Reachy_Mini_Audio"

# ---- Load configuration ----
if [ ! -f "$CONFIG_FILE" ]; then
    echo "ERROR: No configuration found."
    echo "Run setup.sh first to select your external audio devices."
    exit 1
fi

source "$CONFIG_FILE"

if [ -z "${EXTERNAL_SINK:-}" ] || [ -z "${EXTERNAL_SOURCE:-}" ]; then
    echo "ERROR: Configuration is incomplete."
    echo "Run setup.sh again to reconfigure."
    exit 1
fi

echo "============================================"
echo "  Switching to External Audio"
echo "============================================"
echo ""
echo "  Speaker : ${EXTERNAL_SINK_DESC:-$EXTERNAL_SINK}"
echo "  Mic     : ${EXTERNAL_SOURCE_DESC:-$EXTERNAL_SOURCE}"
echo ""

# ---- Verify external devices exist ----
if ! pactl list short sinks 2>/dev/null | grep -q "$EXTERNAL_SINK"; then
    echo "ERROR: External speaker not found: $EXTERNAL_SINK"
    echo ""
    echo "Is the device plugged in? Available sinks:"
    pactl list short sinks
    echo ""
    echo "Run setup.sh to reconfigure if you changed hardware."
    exit 1
fi

if ! pactl list short sources 2>/dev/null | grep -q "$EXTERNAL_SOURCE"; then
    echo "ERROR: External microphone not found: $EXTERNAL_SOURCE"
    echo ""
    echo "Is the device plugged in? Available sources:"
    pactl list short sources | grep -v monitor
    echo ""
    echo "Run setup.sh to reconfigure if you changed hardware."
    exit 1
fi

# ---- Clean up any previous virtual devices ----
echo "[1/4] Cleaning up previous virtual devices..."
for mod_id in $(pactl list short modules 2>/dev/null | grep "$VIRTUAL_NAME" | cut -f1); do
    pactl unload-module "$mod_id" 2>/dev/null || true
done
for mod_id in $(pactl list short modules 2>/dev/null | grep "module-loopback" | cut -f1); do
    pactl unload-module "$mod_id" 2>/dev/null || true
done

# ---- Suspend the real respeaker ----
echo "[2/4] Suspending built-in respeaker..."

respeaker_sink=$(pactl list short sinks 2>/dev/null | grep -i "respeaker" | head -1 | cut -f2 || true)
respeaker_source=$(pactl list short sources 2>/dev/null | grep -iv "monitor" | grep -i "respeaker" | head -1 | cut -f2 || true)

# Save what we suspended so external-audio-off.sh can restore it
mkdir -p "$CONFIG_DIR"
echo "# Suspended devices — auto-generated, do not edit" > "$STATE_FILE"

if [ -n "$respeaker_sink" ]; then
    pactl suspend-sink "$respeaker_sink" 1 2>/dev/null || true
    echo "  Suspended sink: $respeaker_sink"
    echo "SUSPENDED_SINK=\"$respeaker_sink\"" >> "$STATE_FILE"
else
    echo "  No respeaker sink found (may already be suspended)"
    echo "SUSPENDED_SINK=\"\"" >> "$STATE_FILE"
fi

if [ -n "$respeaker_source" ]; then
    pactl suspend-source "$respeaker_source" 1 2>/dev/null || true
    echo "  Suspended source: $respeaker_source"
    echo "SUSPENDED_SOURCE=\"$respeaker_source\"" >> "$STATE_FILE"
else
    echo "  No respeaker source found (may already be suspended)"
    echo "SUSPENDED_SOURCE=\"\"" >> "$STATE_FILE"
fi

# ---- Create virtual output (speaker) ----
echo "[3/4] Creating virtual speaker -> ${EXTERNAL_SINK_DESC:-$EXTERNAL_SINK}..."

pactl load-module module-null-sink \
    sink_name="${VIRTUAL_NAME}_sink" \
    sink_properties=device.description="Reachy\ Mini\ Audio" \
    rate=44100 channels=2 >/dev/null

pactl load-module module-loopback \
    source="${VIRTUAL_NAME}_sink.monitor" \
    sink="$EXTERNAL_SINK" \
    latency_msec=30 >/dev/null

# ---- Create virtual input (microphone) ----
echo "[4/4] Creating virtual microphone <- ${EXTERNAL_SOURCE_DESC:-$EXTERNAL_SOURCE}..."

pactl load-module module-remap-source \
    source_name="${VIRTUAL_NAME}_source" \
    master="$EXTERNAL_SOURCE" \
    source_properties=device.description="Reachy\ Mini\ Audio" >/dev/null

echo ""
echo "============================================"
echo "  External audio is ON"
echo "============================================"
echo ""
echo "  The SDK will now use your external devices."
echo ""
echo "  NEXT: Restart the ElevenLabs app from the"
echo "        Reachy Mini dashboard for changes to"
echo "        take effect."
echo ""
echo "  To switch back: ./external-audio-off.sh"
echo ""
