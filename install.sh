#!/usr/bin/env bash
# install.sh — Install Meeting Recorder on macOS
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/your-org/meeting-recorder/main/install.sh | bash
#   # or locally:
#   ./install.sh

set -euo pipefail

echo "=== Meeting Recorder Installer ==="
echo ""

# ---------------------------------------------------------------------------
# 1. Check prerequisites
# ---------------------------------------------------------------------------

# Python 3.12
if ! command -v python3.12 &>/dev/null; then
    echo "ERROR: Python 3.12 is required but not found."
    echo "Install it from https://www.python.org/downloads/"
    echo "Or via Homebrew:"
    echo "  brew install python@3.12"
    exit 1
fi

echo "✓ Python 3.12 found: $(python3.12 --version)"

# ffmpeg
if ! command -v ffmpeg &>/dev/null; then
    echo "⚠  ffmpeg not found. Whisper needs ffmpeg for audio transcoding."
    echo "   Install with: brew install ffmpeg"
    read -p "   Continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    echo "✓ ffmpeg found: $(ffmpeg -version | head -1)"
fi

# ---------------------------------------------------------------------------
# 1.5. Install system dependencies (PortAudio for PyAudio)
# ---------------------------------------------------------------------------

if ! command -v brew &>/dev/null; then
    echo "ERROR: Homebrew is required but not found."
    echo "Install it from https://brew.sh/"
    exit 1
fi

if ! brew list portaudio &>/dev/null; then
    echo "Installing PortAudio (required by PyAudio)…"
    brew install portaudio
    echo "✓ PortAudio installed"
else
    echo "✓ PortAudio already installed"
fi

# ---------------------------------------------------------------------------
# 2. Create virtual environment
# ---------------------------------------------------------------------------

VENV_DIR="${HOME}/.local/share/meeting-recorder/venv"

if [[ -d "$VENV_DIR" ]]; then
    echo "ℹ  Virtual environment already exists at $VENV_DIR"
    read -p "   Recreate? [y/N] " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
    else
        echo "Skipping venv creation."
    fi
fi

if [[ ! -d "$VENV_DIR" ]]; then
    echo ""
    echo "Creating virtual environment…"
    python3.12 -m venv "$VENV_DIR"
    echo "✓ Virtual environment created at $VENV_DIR"
fi

# Activate
source "$VENV_DIR/bin/activate"

# ---------------------------------------------------------------------------
# 3. Install the application
# ---------------------------------------------------------------------------

echo ""
echo "Installing Meeting Recorder…"

# If running from a cloned repo, install from local; otherwise pip install
if [[ -f "pyproject.toml" ]]; then
    pip install -e ".[dev]"
    echo "✓ Installed from local source (editable)"
else
    pip install meeting-recorder
    echo "✓ Installed from PyPI"
fi

# ---------------------------------------------------------------------------
# 4. Install Whisper-diarization dependencies
# ---------------------------------------------------------------------------

echo ""
echo "Installing Whisper-diarization dependencies (mlx-whisper, pyannote.audio)…"
echo "This will download ~3.4 GB of models on first use."
read -p "   Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation incomplete. Run 'pip install mlx-whisper pyannote.audio torch torchaudio' later."
    deactivate
    exit 0
fi

pip install mlx-whisper pyannote.audio torch torchaudio omegaconf

# ---------------------------------------------------------------------------
# 5. Create launcher scripts
# ---------------------------------------------------------------------------

BIN_DIR="${HOME}/.local/bin"
mkdir -p "$BIN_DIR"

# meeting-recorder script
cat > "$BIN_DIR/meeting-recorder" << 'SCRIPT'
#!/usr/bin/env bash
VENV="${HOME}/.local/share/meeting-recorder/venv"
if [[ -f "$VENV/bin/activate" ]]; then
    source "$VENV/bin/activate"
    python -m src.main "$@"
else
    echo "Error: Meeting Recorder not installed. Run install.sh first."
    exit 1
fi
SCRIPT
chmod +x "$BIN_DIR/meeting-recorder"

# whisper-setup script (one-time HF model download)
cat > "$BIN_DIR/whisper-setup" << 'SCRIPT'
#!/usr/bin/env bash
VENV="${HOME}/.local/share/meeting-recorder/venv"
if [[ -f "$VENV/bin/activate" ]]; then
    source "$VENV/bin/activate"
    echo "Downloading Whisper and pyannote models (~3.4 GB)…"
    python -c "import mlx_whisper; import torch; from pyannote.audio import Pipeline; print('Models cached.')"
else
    echo "Error: Virtual environment not found."
    exit 1
fi
SCRIPT
chmod +x "$BIN_DIR/whisper-setup"

echo ""
echo "✓ Launcher scripts created in $BIN_DIR"

# ---------------------------------------------------------------------------
# 6. Add to PATH if needed
# ---------------------------------------------------------------------------

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "Adding $BIN_DIR to your PATH…"
    if [[ -f "$HOME/.zshrc" ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.zshrc"
        echo "  Added to ~/.zshrc"
    elif [[ -f "$HOME/.bashrc" ]]; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
        echo "  Added to ~/.bashrc"
    fi
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
echo "=========================================="
echo "  Installation complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Restart your terminal (or run: source ~/.zshrc)"
echo "  2. Configure your Hugging Face token:"
echo "     meeting-recorder  →  File → Settings → Whisper tab"
echo "     (You need access to pyannote/speaker-diarization-3.1)"
echo "  3. Run: meeting-recorder"
echo ""
echo "To uninstall:"
echo "  ./uninstall.sh"
echo ""
