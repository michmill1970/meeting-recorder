"""ZIP export utility for meeting recordings."""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def export_meeting_zip(
    meeting_dir: Path,
    output_dir: Optional[Path] = None,
) -> Optional[Path]:
    """Create a ZIP file containing the meeting audio, transcript, and summary.

    Args:
        meeting_dir: Directory containing meeting files
        output_dir: Directory to save ZIP file (defaults to meeting_dir)

    Returns:
        Path to the created ZIP file, or None if export failed
    """
    if not meeting_dir.exists():
        logger.error("Meeting directory does not exist: %s", meeting_dir)
        return None

    if output_dir is None:
        output_dir = meeting_dir

    output_dir.mkdir(parents=True, exist_ok=True)

    # Build file list
    files_to_archive = []
    # Find the audio file (any extension)
    audio_files = list(meeting_dir.glob("recording.*"))
    if audio_files:
        files_to_archive.extend(audio_files)
    for filename in ["transcript.txt", "summary.md"]:
        filepath = meeting_dir / filename
        if filepath.exists():
            files_to_archive.append(filepath)

    if not files_to_archive:
        logger.warning("No files to archive in %s", meeting_dir)
        return None

    # Create ZIP filename based on meeting directory name
    zip_filename = f"{meeting_dir.name}.zip"
    zip_path = output_dir / zip_filename

    try:
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for filepath in files_to_archive:
                arcname = filepath.name
                zf.write(filepath, arcname)
                logger.debug("Added %s to archive", arcname)

        logger.info("Meeting exported to %s (%d files)", zip_path, len(files_to_archive))
        return zip_path

    except OSError as e:
        logger.error("Failed to create ZIP: %s", e)
        return None
