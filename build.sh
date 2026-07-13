#!/usr/bin/env bash
# build.sh — Build a distributable Meeting Recorder app
#
# Usage:
#   ./build.sh              # Build for current platform
#   ./build.sh --macos      # Build macOS universal binary
#   ./build.sh --clean      # Clean build directory first
#
# Output:
#   dist/Meeting Recorder.app   (macOS)
#   dist/meeting-recorder       (Linux)
#   dist/meeting-recorder.exe   (Windows)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

CLEAN=false
PLATFORM=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=true
            shift
            ;;
        --macos)
            PLATFORM="macos"
            shift
            ;;
        --help)
            echo "Usage: $0 [--clean] [--macos]"
            echo ""
            echo "Options:"
            echo "  --clean    Remove build/ and dist/ before building"
            echo "  --macos    Build macOS universal binary"
            echo "  --help     Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Check prerequisites
# ---------------------------------------------------------------------------

echo "=== Meeting Recorder Builder ==="
echo ""

# Python 3.12
if ! command -v python3.12 &>/dev/null; then
    echo "ERROR: Python 3.12 is required."
    echo "Install with: brew install python@3.12"
    exit 1
fi

# Virtual environment
VENV_DIR="${HOME}/.local/share/meeting-recorder/venv"
if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment…"
    mkdir -p "$(dirname "$VENV_DIR")"
    python3.12 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Install build dependencies
echo "Installing build dependencies…"
pip install -q PyInstaller

# ---------------------------------------------------------------------------
# Clean if requested
# ---------------------------------------------------------------------------

if [[ "$CLEAN" == "true" ]]; then
    echo "Cleaning build artifacts…"
    rm -rf build/ dist/
fi

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

echo ""
echo "Building Meeting Recorder…"
echo ""

if [[ "$PLATFORM" == "macos" ]]; then
    # macOS universal binary (Apple Silicon + Intel)
    echo "Building macOS universal binary…"
    pyinstaller \
        --clean \
        --name="Meeting Recorder" \
        --windowed \
        --icon="icons/meeting-recorder-icon.png" \
        --add-data "whisper-diarization:whisper-diarization" \
        --hidden-import PySide6.QtCore \
        --hidden-import PySide6.QtGui \
        --hidden-import PySide6.QtWidgets \
        --hidden-import pyaudio \
        --hidden-import openai \
        --hidden-import anthropic \
        --hidden-import numpy \
        --hidden-import mlx_whisper \
        --hidden-import pyannote.audio \
        --hidden-import torch \
        --hidden-import torchaudio \
        --hidden-import omegaconf \
        --exclude-module tkinter \
        --exclude-module unittest \
        --exclude-module jinja2 \
        src/main.py

    echo ""
    echo "✓ Build complete: dist/Meeting Recorder.app"
    echo ""
    echo "To run:"
    echo "  open dist/Meeting\ Recorder.app"
    echo ""
    echo "To sign (for notarization):"
    echo "  codesign --force --deep --sign \"Developer ID Application: Your Name\" dist/Meeting\ Recorder.app"
    echo "  xcrun notarytool submit dist/Meeting\ Recorder.app --keychain-profile \"notaryprofile\""

elif [[ "$(uname)" == "Linux" ]]; then
    echo "Building Linux executable…"
    pyinstaller \
        --clean \
        --name="meeting-recorder" \
        --onefile \
        --add-data "whisper-diarization:whisper-diarization" \
        --hidden-import PySide6.QtCore \
        --hidden-import PySide6.QtGui \
        --hidden-import PySide6.QtWidgets \
        --hidden-import pyaudio \
        --hidden-import openai \
        --hidden-import anthropic \
        --hidden-import numpy \
        --hidden-import mlx_whisper \
        --hidden-import pyannote.audio \
        --hidden-import torch \
        --hidden-import torchaudio \
        --hidden-import omegaconf \
        --exclude-module tkinter \
        --exclude-module unittest \
        src/main.py

    echo ""
    echo "✓ Build complete: dist/meeting-recorder"
    echo ""
    echo "To run:"
    echo "  ./dist/meeting-recorder"

else
    echo "Building for current platform…"
    pyinstaller \
        --clean \
        --name="meeting-recorder" \
        --windowed \
        --add-data "whisper-diarization:whisper-diarization" \
        --hidden-import PySide6.QtCore \
        --hidden-import PySide6.QtGui \
        --hidden-import PySide6.QtWidgets \
        --hidden-import pyaudio \
        --hidden-import openai \
        --hidden-import anthropic \
        --hidden-import numpy \
        --hidden-import mlx_whisper \
        --hidden-import pyannote.audio \
        --hidden-import torch \
        --hidden-import torchaudio \
        --hidden-import omegaconf \
        --exclude-module tkinter \
        --exclude-module unittest \
        src/main.py

    echo ""
    echo "✓ Build complete: dist/"
fi

# ---------------------------------------------------------------------------
# Post-build: add uninstaller
# ---------------------------------------------------------------------------

echo ""
echo "Creating uninstaller…"

cat > dist/uninstall.sh << 'UNINSTALL'
#!/usr/bin/env bash
echo "Uninstalling Meeting Recorder…"
read -p "This will remove all data. Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Remove app bundle
if [[ -d "Meeting Recorder.app" ]]; then
    rm -rf "Meeting Recorder.app"
    echo "  Removed Meeting Recorder.app"
fi

# Remove user data
rm -rf "$HOME/Documents/MeetingRecorder"
echo "  Removed ~/Documents/MeetingRecorder"

rm -rf "$HOME/.config/meeting-recorder"
echo "  Removed ~/.config/meeting-recorder"

rm -rf "$HOME/.local/share/meeting-recorder"
echo "  Removed ~/.local/share/meeting-recorder/venv"

rm -f "$HOME/.local/bin/meeting-recorder"
rm -f "$HOME/.local/bin/whisper-setup"
echo "  Removed launcher scripts"

echo ""
echo "Uninstall complete."
UNINSTALL

chmod +x dist/uninstall.sh

echo "  Created dist/uninstall.sh"
echo ""
echo "=========================================="
echo "  Build complete!"
echo "=========================================="
