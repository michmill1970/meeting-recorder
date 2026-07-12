#!/usr/bin/env bash
# uninstall.sh — Completely remove Meeting Recorder from your system
#
# Usage:
#   ./uninstall.sh
#
# This will remove:
#   - Virtual environment (~/.local/share/meeting-recorder/venv)
#   - Launcher scripts (~/.local/bin/meeting-recorder, whisper-setup)
#   - Configuration and logs (~/.config/meeting-recorder/)
#   - Meeting recordings (~/Documents/MeetingRecorder/)
#   - Hugging Face model cache for pyannote/whisper
#   - PATH additions to shell config files

set -euo pipefail

echo "=== Meeting Recorder Uninstaller ==="
echo ""

# ---------------------------------------------------------------------------
# 1. Confirm uninstallation
# ---------------------------------------------------------------------------

echo "This will remove ALL Meeting Recorder data:"
echo "  - Virtual environment (~/.local/share/meeting-recorder/venv)"
echo "  - Launcher scripts (~/.local/bin/meeting-recorder, whisper-setup)"
echo "  - Configuration and logs (~/.config/meeting-recorder/)"
echo "  - Meeting recordings (~/Documents/MeetingRecorder/)"
echo "  - Hugging Face model cache (~/.cache/huggingface/hub for pyannote/whisper)"
echo ""

read -p "Are you sure you want to continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

# ---------------------------------------------------------------------------
# 2. Remove virtual environment
# ---------------------------------------------------------------------------

VENV_DIR="${HOME}/.local/share/meeting-recorder"

if [[ -d "$VENV_DIR" ]]; then
    echo ""
    echo "Removing virtual environment…"
    rm -rf "$VENV_DIR"
    echo "✓ Removed $VENV_DIR"
else
    echo ""
    echo "ℹ Virtual environment not found at $VENV_DIR (skipping)"
fi

# ---------------------------------------------------------------------------
# 3. Remove launcher scripts
# ---------------------------------------------------------------------------

BIN_DIR="${HOME}/.local/bin"

echo ""
echo "Removing launcher scripts…"

if [[ -f "$BIN_DIR/meeting-recorder" ]]; then
    rm -f "$BIN_DIR/meeting-recorder"
    echo "✓ Removed $BIN_DIR/meeting-recorder"
else
    echo "ℹ $BIN_DIR/meeting-recorder not found (skipping)"
fi

if [[ -f "$BIN_DIR/whisper-setup" ]]; then
    rm -f "$BIN_DIR/whisper-setup"
    echo "✓ Removed $BIN_DIR/whisper-setup"
else
    echo "ℹ $BIN_DIR/whisper-setup not found (skipping)"
fi

# ---------------------------------------------------------------------------
# 4. Remove configuration and logs
# ---------------------------------------------------------------------------

CONFIG_DIR="${HOME}/.config/meeting-recorder"

if [[ -d "$CONFIG_DIR" ]]; then
    echo ""
    echo "Removing configuration and logs…"
    rm -rf "$CONFIG_DIR"
    echo "✓ Removed $CONFIG_DIR"
else
    echo ""
    echo "ℹ Configuration directory not found at $CONFIG_DIR (skipping)"
fi

# ---------------------------------------------------------------------------
# 5. Remove meeting recordings
# ---------------------------------------------------------------------------

MEETINGS_DIR="${HOME}/Documents/MeetingRecorder"

if [[ -d "$MEETINGS_DIR" ]]; then
    echo ""
    echo "Removing meeting recordings…"
    echo "⚠  This will delete all recorded meetings in $MEETINGS_DIR"
    read -p "   Continue? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$MEETINGS_DIR"
        echo "✓ Removed $MEETINGS_DIR"
    else
        echo "Keeping meeting recordings."
    fi
else
    echo ""
    echo "ℹ Meetings directory not found at $MEETINGS_DIR (skipping)"
fi

# ---------------------------------------------------------------------------
# 6. Remove Hugging Face model cache
# ---------------------------------------------------------------------------

HF_CACHE="${HOME}/.cache/huggingface/hub"

if [[ -d "$HF_CACHE" ]]; then
    # Check if any whisper/pyannote models exist
    if ls "$HF_CACHE"/*whisper* "$HF_CACHE"/*pyannote* 2>/dev/null | head -1 &>/dev/null; then
        echo ""
        echo "Removing Hugging Face model cache for Whisper and pyannote…"
        # Remove only whisper and pyannote related models
        for model_dir in "$HF_CACHE"/*whisper* "$HF_CACHE"/*pyannote*; do
            if [[ -d "$model_dir" ]]; then
                rm -rf "$model_dir"
                echo "✓ Removed $(basename "$model_dir")"
            fi
        done
    else
        echo ""
        echo "ℹ No Whisper or pyannote models found in HF cache (skipping)"
    fi
else
    echo ""
    echo "ℹ Hugging Face cache not found at $HF_CACHE (skipping)"
fi

# ---------------------------------------------------------------------------
# 7. Clean up shell PATH additions
# ---------------------------------------------------------------------------

echo ""
echo "Checking shell configuration files for PATH additions…"

for rc_file in "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile"; do
    if [[ -f "$rc_file" ]]; then
        if grep -q 'meeting-recorder\|\.local/bin' "$rc_file" 2>/dev/null; then
            echo "  Found PATH entry in $(basename "$rc_file")"
            echo "  ℹ  You may need to manually remove the line:"
            echo "     export PATH=\"\$HOME/.local/bin:\$PATH\""
            echo "  ℹ  Or run: source $rc_file"
        fi
    fi
done

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
echo "=========================================="
echo "  Uninstallation complete!"
echo "=========================================="
echo ""
echo "Note: If you customized the save directory in settings,"
echo "      check that location for any remaining meeting files."
echo ""
echo "To complete the cleanup, restart your terminal or run:"
echo "  source ~/.zshrc  # or source ~/.bashrc"
echo ""
