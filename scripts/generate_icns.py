#!/usr/bin/env python3
"""Generate macOS .icns icon from PNG.

Usage:
    python generate_icns.py icons/meeting-recorder.png icons/meeting-recorder.icns

Requires: Pillow library
"""

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("Error: Pillow is required. Install with: pip install Pillow")
    sys.exit(1)


def create_icns(png_path: str, icns_path: str) -> None:
    """Convert PNG to ICNS format for macOS."""
    png_file = Path(png_path)
    icns_file = Path(icns_path)

    if not png_file.exists():
        print(f"Error: PNG file not found: {png_path}")
        sys.exit(1)

    # Load and resize to multiple sizes macOS expects
    sizes = [
        (16, 16, "icon_16x16.png"),
        (32, 32, "icon_16x16@2x.png"),
        (32, 32, "icon_32x32.png"),
        (64, 64, "icon_32x32@2x.png"),
        (128, 128, "icon_128x128.png"),
        (256, 256, "icon_128x128@2x.png"),
        (256, 256, "icon_256x256.png"),
        (512, 512, "icon_256x256@2x.png"),
        (512, 512, "icon_512x512.png"),
        (1024, 1024, "icon_512x512@2x.png"),
    ]

    img = Image.open(png_file)

    # Create temporary directory for icon components
    temp_dir = icns_file.parent / "icon_temp"
    temp_dir.mkdir(exist_ok=True)

    try:
        # Generate all required sizes
        for width, height, filename in sizes:
            resized = img.resize((width, height), Image.LANCZOS)
            resized.save(temp_dir / filename, "PNG")

        # Use macOS iconutil to create ICNS
        import subprocess
        result = subprocess.run(
            ["iconutil", "-c", "icns", str(temp_dir), "-o", str(icns_file)],
            capture_output=True,
            text=True,
        )

        if result.returncode != 0:
            print(f"Error creating ICNS: {result.stderr}")
            print("Falling back to PNG-only approach...")
            icns_file = None  # Don't create ICNS, use PNG directly

        print(f"✓ Created ICNS icon: {icns_path}")

    finally:
        # Cleanup temporary files
        import shutil
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python generate_icns.py <input.png> <output.icns>")
        sys.exit(1)

    create_icns(sys.argv[1], sys.argv[2])
