#!/bin/bash
# =============================================================================
# Reachy Mini Audio Routing — Switch Back to Internal Audio
#
# Removes virtual devices and restores the built-in respeaker.
#
# Usage:
#   ./external-audio-off.sh
#
# After running this, restart the ElevenLabs app from the dashboard.
# =============================================================================

set -euo pipefail

CONFIG_DIR="$HOME/.config/reachy-audio"
STATE_FILE="$CONFIG_DIR/suspended.state"
VIRTUAL_NAME="Reachy_Mini_Audio"

echo "============================================"
echo "  Switching to Internal Audio (respeaker)"
echo "============================================"
echo ""

# ---- Remove virtual devices ----
echo "[1/2] Removing virtual devices..."

removed=0
for mod_id in $(pactl list short modules 2>/dev/null | grep "$VIRTUAL_NAME" | cut -f1); do
    pactl unload-module "$mod_id" 2>/dev/null || true
    removed=$((removed + 1))
done
for mod_id in $(pactl list short modules 2>/dev/null | grep "module-loopback" | cut -f1); do
    pactl unload-module "$mod_id" 2>/dev/null || true
    removed=$((removed + 1))
done

if [ $removed -gt 0 ]; then
    echo "  Removed $removed virtual device module(s)"
else
    echo "  No virtual devices found (already off)"
fi

# ---- Restore the real respeaker ----
echo "[2/2] Restoring built-in respeaker..."

if [ -f "$STATE_FILE" ]; then
    source "$STATE_FILE"

    if [ -n "${SUSPENDED_SINK:-}" ]; then
        pactl suspend-sink "$SUSPENDED_SINK" 0 2>/dev/null || true
        echo "  Restored sink: $SUSPENDED_SINK"
    fi

    if [ -n "${SUSPENDED_SOURCE:-}" ]; then
        pactl suspend-source "$SUSPENDED_SOURCE" 0 2>/dev/null || true
        echo "  Restored source: $SUSPENDED_SOURCE"
    fi

    rm -f "$STATE_FILE"
else
    # Best-effort: try to unsuspend anything with "respeaker" in the name
    echo "  No suspend state file found, attempting best-effort restore..."

    sink=$(pactl list short sinks 2>/dev/null | grep -i "respeaker" | head -1 | cut -f2 || true)
    source_dev=$(pactl list short sources 2>/dev/null | grep -iv "monitor" | grep -i "respeaker" | head -1 | cut -f2 || true)

    if [ -n "$sink" ]; then
        pactl suspend-sink "$sink" 0 2>/dev/null || true
        echo "  Restored sink: $sink"
    fi
    if [ -n "$source_dev" ]; then
        pactl suspend-source "$source_dev" 0 2>/dev/null || true
        echo "  Restored source: $source_dev"
    fi

    if [ -z "$sink" ] && [ -z "$source_dev" ]; then
        echo "  No respeaker devices found to restore (they may not have been suspended)"
    fi
fi

echo ""
echo "============================================"
echo "  Internal audio is restored"
echo "============================================"
echo ""
echo "  The SDK will now use the built-in respeaker."
echo ""
echo "  NEXT: Restart the ElevenLabs app from the"
echo "        Reachy Mini dashboard for changes to"
echo "        take effect."
echo ""
