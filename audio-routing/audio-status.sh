#!/bin/bash
# =============================================================================
# Reachy Mini Audio Routing — Status Check
#
# Shows current audio routing state and what the SDK will see.
#
# Usage:
#   ./audio-status.sh
# =============================================================================

set -euo pipefail

CONFIG_DIR="$HOME/.config/reachy-audio"
CONFIG_FILE="$CONFIG_DIR/devices.conf"
STATE_FILE="$CONFIG_DIR/suspended.state"
VIRTUAL_NAME="Reachy_Mini_Audio"

echo "============================================"
echo "  Reachy Mini Audio Status"
echo "============================================"
echo ""

# ---- Current mode ----
virtual_modules=$(pactl list short modules 2>/dev/null | grep -c "$VIRTUAL_NAME" || true)

if [ "$virtual_modules" -gt 0 ]; then
    echo "  Mode: EXTERNAL (virtual devices active)"
else
    echo "  Mode: INTERNAL (using built-in respeaker)"
fi
echo ""

# ---- Saved configuration ----
echo "--- Saved Configuration ---"
if [ -f "$CONFIG_FILE" ]; then
    source "$CONFIG_FILE"
    echo "  External speaker : ${EXTERNAL_SINK_DESC:-${EXTERNAL_SINK:-not set}}"
    echo "  External mic     : ${EXTERNAL_SOURCE_DESC:-${EXTERNAL_SOURCE:-not set}}"
else
    echo "  (none — run setup.sh to configure)"
fi
echo ""

# ---- Suspended devices ----
echo "--- Suspended Devices ---"
if [ -f "$STATE_FILE" ]; then
    source "$STATE_FILE"
    echo "  Suspended sink   : ${SUSPENDED_SINK:-none}"
    echo "  Suspended source : ${SUSPENDED_SOURCE:-none}"
else
    echo "  (none suspended)"
fi
echo ""

# ---- PulseAudio sinks ----
echo "--- PulseAudio Sinks (speakers) ---"
while IFS=$'\t' read -r pa_idx name driver; do
    state=""
    # Check if suspended
    is_suspended=$(pactl list sinks 2>/dev/null | awk -v n="$name" '
        /Name:/ && $NF == n { found=1 }
        found && /State:/ { print $NF; exit }
    ')
    [ "$is_suspended" = "SUSPENDED" ] && state=" [SUSPENDED]"

    desc=$(pactl list sinks 2>/dev/null | awk -v n="$name" '
        /Name:/ && $NF == n { found=1 }
        found && /Description:/ { sub(/.*Description: /, ""); print; exit }
    ')
    echo "  [$pa_idx] ${desc:-$name}${state}"
    echo "       $name"
done < <(pactl list short sinks 2>/dev/null)
echo ""

# ---- PulseAudio sources ----
echo "--- PulseAudio Sources (microphones) ---"
while IFS=$'\t' read -r pa_idx name driver; do
    state=""
    is_suspended=$(pactl list sources 2>/dev/null | awk -v n="$name" '
        /Name:/ && $NF == n { found=1 }
        found && /State:/ { print $NF; exit }
    ')
    [ "$is_suspended" = "SUSPENDED" ] && state=" [SUSPENDED]"

    desc=$(pactl list sources 2>/dev/null | awk -v n="$name" '
        /Name:/ && $NF == n { found=1 }
        found && /Description:/ { sub(/.*Description: /, ""); print; exit }
    ')
    echo "  [$pa_idx] ${desc:-$name}${state}"
    echo "       $name"
done < <(pactl list short sources 2>/dev/null | grep -v '\.monitor')
echo ""

# ---- What sounddevice sees ----
echo "--- What the SDK Sees (sounddevice) ---"

# Try to find the Reachy Mini app venv for sounddevice access.
# The Control app installs community apps under ~/.local/share/reachy-mini/
# or similar paths. We search common locations for a venv with sounddevice.
PYTHON_CMD=""

# Common venv locations on Reachy Mini (Lubuntu)
VENV_SEARCH_PATHS=(
    "$HOME/.local/share/reachy-mini/apps/reachy-mini-elevenlabs/venv/bin/python3"
    "$HOME/.local/share/reachy-mini/venv/bin/python3"
    "$HOME/.local/share/reachy_mini/venv/bin/python3"
    "$HOME/reachy-mini/venv/bin/python3"
    "/opt/reachy-mini/venv/bin/python3"
)

for venv_python in "${VENV_SEARCH_PATHS[@]}"; do
    if [ -x "$venv_python" ] && "$venv_python" -c "import sounddevice" 2>/dev/null; then
        PYTHON_CMD="$venv_python"
        echo "  (using venv: $venv_python)"
        break
    fi
done

# Fall back to system python3
if [ -z "$PYTHON_CMD" ]; then
    if python3 -c "import sounddevice" 2>/dev/null; then
        PYTHON_CMD="python3"
    fi
fi

if [ -n "$PYTHON_CMD" ]; then
    $PYTHON_CMD -c "
import sounddevice as sd
devices = sd.query_devices()
for i, d in enumerate(devices):
    if d['max_input_channels'] == 0 and d['max_output_channels'] == 0:
        continue
    marker = ''
    name_lower = d['name'].lower()
    if 'reachy' in name_lower or 'respeaker' in name_lower or 'mini' in name_lower:
        marker = '  <-- SDK will use this'
    io = []
    if d['max_input_channels'] > 0:
        io.append(f\"in:{d['max_input_channels']}\")
    if d['max_output_channels'] > 0:
        io.append(f\"out:{d['max_output_channels']}\")
    print(f\"  [{i}] {d['name']}  ({', '.join(io)}){marker}\")
" 2>/dev/null || echo "  (sounddevice query failed)"
else
    echo "  (sounddevice not available — this is OK, audio routing still works)"
    echo "  (to enable this check, install sounddevice: pip3 install sounddevice)"
fi
echo ""
