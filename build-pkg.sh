#!/usr/bin/env bash
# build-pkg.sh — Build a macOS installer package (.pkg) for Meeting Recorder
#
# Prerequisites:
#   - macOS 12+ with Xcode Command Line Tools installed
#   - Apple Developer account with signing certificate
#   - NotaryTool configured: xcrun notarytool store-credentials "notaryprofile"
#
# Usage:
#   ./build-pkg.sh              # Build .pkg (current macOS version)
#   ./build-pkg.sh --unsigned   # Build unsigned .pkg (for testing only)
#   ./build-pkg.sh --clean      # Remove build artifacts first
#
# Output:
#   dist/Meeting Recorder.pkg    — signed & notarized installer

set -euo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

DIST_DIR="dist"
BUILD_DIR="build/pkg"
APP_NAME="Meeting Recorder"
APP_BUNDLE="$DIST_DIR/$APP_NAME.app"
PKG_FILE="$DIST_DIR/$APP_NAME.pkg"

SIGNING_IDENTITY="${SIGNING_IDENTITY:-}"
NOTARY_PROFILE="${NOTARY_PROFILE:-notaryprofile}"

CLEAN=false
UNSIGNED=false

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------

while [[ $# -gt 0 ]]; do
    case $1 in
        --clean)
            CLEAN=true
            shift
            ;;
        --unsigned)
            UNSIGNED=true
            shift
            ;;
        --help)
            echo "Usage: $0 [--clean] [--unsigned]"
            echo ""
            echo "Options:"
            echo "  --clean    Remove build artifacts before building"
            echo "  --unsigned Build unsigned .pkg (for testing, not for distribution)"
            echo ""
            echo "Environment variables:"
            echo "  SIGNING_IDENTITY  — Codesign identity (default: auto-detect)"
            echo "  NOTARY_PROFILE    — Keychain profile name (default: notaryprofile)"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

log() {
    echo "=== [build-pkg] $1 ==="
}

error() {
    echo "ERROR: $1" >&2
    exit 1
}

check_command() {
    if ! command -v "$1" &>/dev/null; then
        error "'$1' not found. Install Xcode Command Line Tools: xcode-select --install"
    fi
}

# Auto-detect signing identity if not provided
detect_signing_identity() {
    if [[ -n "$SIGNING_IDENTITY" ]]; then
        echo "$SIGNING_IDENTITY"
        return
    fi

    local identity
    identity=$(security find-identity -v -p codesigning 2>/dev/null \
        | grep "Developer ID Application" \
        | head -1 \
        | sed 's/.*"\(.*\)".*/\1/')

    if [[ -z "$identity" ]]; then
        error "No 'Developer ID Application' certificate found.
  List available: security find-identity -v -p codesigning
  Set with: export SIGNING_IDENTITY=\"Your Name (TEAMID)\""
    fi

    echo "$identity"
}

# Check if notarization is supported (macOS 10.15+)
check_notarization() {
    if [[ "$UNSIGNED" == "true" ]]; then
        log "Skipping notarization (--unsigned)"
        return
    fi

    if ! command -v xcrun &>/dev/null; then
        error "xcrun not found. Run on macOS with Xcode installed."
    fi

    if ! xcrun notarytool --help &>/dev/null 2>&1; then
        error "notarytool not available. Requires Xcode 12+ and Apple Developer account.
  Set up: xcrun notarytool store-credentials \"$NOTARY_PROFILE\" --apple-id \"your@apple.com\" --team-id \"TEAMID\" --api-key-path \"key.p8\""
    fi
}

# ---------------------------------------------------------------------------
# Prerequisites
# ---------------------------------------------------------------------------

log "Checking prerequisites…"

check_command codesign
check_command pkgbuild
check_command productbuild

SIGNING_IDENTITY=$(detect_signing_identity)
log "Signing identity: $SIGNING_IDENTITY"

check_notarization

# ---------------------------------------------------------------------------
# Clean if requested
# ---------------------------------------------------------------------------

if [[ "$CLEAN" == "true" ]]; then
    log "Cleaning build artifacts…"
    rm -rf "$DIST_DIR" "$BUILD_DIR"
    # Also clean PyInstaller artifacts
    rm -rf build/ dist/
fi

# ---------------------------------------------------------------------------
# Step 1: Build .app bundle with PyInstaller
# ---------------------------------------------------------------------------

log "Step 1: Building .app bundle with PyInstaller…"

if ! command -v python3.12 &>/dev/null; then
    error "Python 3.12 not found. Install with: brew install python@3.12"
fi

VENV_DIR="${HOME}/.local/share/meeting-recorder/venv"
if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating virtual environment…"
    mkdir -p "$(dirname "$VENV_DIR")"
    python3.12 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"

# Install PyInstaller if needed
if ! python -c "import PyInstaller" &>/dev/null; then
    log "Installing PyInstaller…"
    pip install -q PyInstaller
fi

pyinstaller \
    --clean \
    --name="$APP_NAME" \
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

if [[ ! -f "$APP_BUNDLE" ]]; then
    error "PyInstaller build failed: $APP_BUNDLE not found"
fi

log "✓ .app bundle built: $APP_BUNDLE"

# ---------------------------------------------------------------------------
# Step 2: Sign the .app bundle
# ---------------------------------------------------------------------------

log "Step 2: Signing .app bundle…"

codesign \
    --force \
    --deep \
    --sign "$SIGNING_IDENTITY" \
    --timestamp \
    --options runtime \
    "$APP_BUNDLE"

log "✓ .app bundle signed"

# Verify signing
codesign -dvvv "$APP_BUNDLE" 2>&1 | head -3

# ---------------------------------------------------------------------------
# Step 3: Create .pkg
# ---------------------------------------------------------------------------

log "Step 3: Creating .pkg installer…"

mkdir -p "$BUILD_DIR"
mkdir -p "$DIST_DIR"

# Create payload directory (must contain the .app, not the .app itself)
PAYLOAD_DIR="$BUILD_DIR/payload"
rm -rf "$PAYLOAD_DIR"
mkdir -p "$PAYLOAD_DIR"
cp -a "$APP_BUNDLE" "$PAYLOAD_DIR/"

# Create the .pkg
# --root: directory containing the files to package
# --install-location: where files are placed (absolute path in /)
pkgbuild \
    --root "$PAYLOAD_DIR" \
    --identifier "com.yourdomain.$(echo "$APP_NAME" | tr ' ' '-')" \
    --version "1.0.0" \
    --install-location "/Applications" \
    --sign "$SIGNING_IDENTITY" \
    "$PKG_FILE"

log "✓ .pkg created: $PKG_FILE"

# Verify pkg contents
log "Verifying .pkg contents…"
pkgutil --expand "$PKG_FILE" "$BUILD_DIR/expanded" 2>/dev/null || true
if [[ -d "$BUILD_DIR/expanded" ]]; then
    log "  Payload:"
    ls -la "$BUILD_DIR/expanded/Payload" 2>/dev/null | head -5 || true
fi

# ---------------------------------------------------------------------------
# Step 4: Notarize (skip if --unsigned)
# ---------------------------------------------------------------------------

if [[ "$UNSIGNED" == "true" ]]; then
    log "Skipping notarization (--unsigned flag)"
    log ""
    log "To build a distributable .pkg:"
    log "  Remove --unsigned and ensure you have:"
    log "    1. Developer ID Application certificate"
    log "    2. NotaryTool configured:"
    log "       xcrun notarytool store-credentials \"$NOTARY_PROFILE\" \\"
    log "         --apple-id \"your@apple.com\" \\"
    log "         --team-id \"TEAMID\" \\"
    log "         --api-key-path \"key.p8\""
    log ""
    log "  Then re-run: ./build-pkg.sh"
else
    log "Step 4: Notarizing .pkg…"

    # Notarize
    log "  Submitting to Apple Notary Service…"
    xcrun notarytool submit "$PKG_FILE" \
        --keychain-profile "$NOTARY_PROFILE" \
        --wait \
        --timeout 10m

    log "  ✓ Notarization submitted and approved"

    # Staple ticket
    log "  Stealing notarization ticket…"
    xcrun stapler staple "$PKG_FILE"

    log "  ✓ Ticket stapled"
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

log "=========================================="
log "  Build complete!"
log "=========================================="
log ""
log "  Package: $PKG_FILE"
log "  Size:    $(du -h "$PKG_FILE" | cut -f1)"
log ""

if [[ "$UNSIGNED" != "true" ]]; then
    log "  Verify notarization:"
    log "    xcrun notarytool info \\"
    log "      --keychain-profile \"$NOTARY_PROFILE\" \\"
    log "      --date-start $(date -v-7d -u +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || echo '2024-01-01T00:00:00Z')"
    log ""
    log "  Distribute to users. The .pkg will open in Installer.app."
else
    log "  WARNING: This is an unsigned .pkg for testing only."
    log "  Users on macOS 10.15+ will see a security warning."
fi

# Clean up build artifacts
rm -rf "$BUILD_DIR"

# ---------------------------------------------------------------------------
# Post-build: add uninstaller to .app
# ---------------------------------------------------------------------------

log "Adding uninstaller to .app…"

mkdir -p "$APP_BUNDLE/Contents/Resources"
cat > "$APP_BUNDLE/Contents/Resources/uninstall.sh" << 'UNINSTALL'
#!/usr/bin/env bash
echo "Uninstalling Meeting Recorder…"
read -p "This will remove all data. Continue? [y/N] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Cancelled."
    exit 0
fi

# Remove app bundle
rm -rf "/Applications/Meeting Recorder.app"
echo "  Removed /Applications/Meeting Recorder.app"

# Remove user data
rm -rf "$HOME/Documents/MeetingRecorder"
echo "  Removed ~/Documents/MeetingRecorder"

rm -rf "$HOME/.config/meeting-recorder"
echo "  Removed ~/.config/meeting-recorder"

rm -rf "$HOME/.local/share/meeting-recorder"
echo "  Removed ~/.local/share/meeting-recorder/venv"

echo ""
echo "Uninstall complete."
UNINSTALL

chmod +x "$APP_BUNDLE/Contents/Resources/uninstall.sh"

log "  Created uninstaller inside app bundle"
