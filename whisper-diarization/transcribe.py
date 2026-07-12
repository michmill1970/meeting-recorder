#!/usr/bin/env python3
"""Audio transcription with speaker diarization using faster-whisper and pyannote."""

import argparse
import logging
import os
import re
import subprocess
import sys
import tempfile
import warnings
from bisect import bisect_right
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning, module="pyannote")
warnings.filterwarnings("ignore", category=UserWarning, module="lightning")
warnings.filterwarnings("ignore", category=UserWarning, module="pytorch_lightning")
logging.getLogger("lightning").setLevel(logging.ERROR)
logging.getLogger("lightning.pytorch").setLevel(logging.ERROR)
logging.getLogger("pytorch_lightning").setLevel(logging.ERROR)

import mlx_whisper
import torch
from pyannote.audio import Pipeline

WHISPER_MODEL = "mlx-community/whisper-large-v3-mlx"
SPEAKER_PATTERN = re.compile(r"^SPEAKER_\d+$")


def parse_timestamp_str(s: str) -> float:
    """Parse '5', '5.3', '0:05', '1:23:45' into seconds."""
    s = s.strip()
    if ":" in s:
        parts = s.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        raise ValueError(f"Bad timestamp '{s}'")
    return float(s)


def parse_reference(s: str) -> tuple[str, float, float]:
    """Parse 'Alice@5-15' or 'Alice@0:05-0:15' into (name, start_sec, end_sec)."""
    if "@" not in s:
        raise argparse.ArgumentTypeError(
            f"Invalid reference '{s}'. Expected NAME@START-END (e.g. Alice@0:05-0:15)."
        )
    name, timerange = s.split("@", 1)
    name = name.strip()
    if not name:
        raise argparse.ArgumentTypeError(f"Reference name is empty in '{s}'.")
    if "-" not in timerange:
        raise argparse.ArgumentTypeError(
            f"Invalid time range '{timerange}'. Expected START-END."
        )
    start_str, end_str = timerange.rsplit("-", 1)
    start = parse_timestamp_str(start_str)
    end = parse_timestamp_str(end_str)
    if end <= start:
        raise argparse.ArgumentTypeError(
            f"Reference '{s}': end ({end}s) must be > start ({start}s)."
        )
    return name, start, end


def to_wav(audio_path: str) -> str:
    """Transcode any input to 16 kHz mono WAV in a temp file. Returns the path."""
    fd, out_path = tempfile.mkstemp(suffix=".wav")
    os.close(fd)
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", audio_path,
            "-ar", "16000", "-ac", "1",
            out_path,
        ],
        check=True,
    )
    return out_path


def get_audio_duration(audio_path: str) -> float:
    """Return audio file duration in seconds via ffprobe."""
    out = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(out.stdout.strip())


def diarize(
    audio_path: str,
    hf_token: str,
    num_speakers: int | None = None,
    min_speakers: int | None = None,
    max_speakers: int | None = None,
) -> list[dict]:
    from pyannote.audio.pipelines.utils.hook import ProgressHook

    pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1", token=hf_token
    )

    # Slightly tighten segmentation so brief pauses produce real turn boundaries
    # instead of getting merged into one long interval. Default min_duration_off
    # is ~0.58s; we lower to 0.3s for more granular utterance detection.
    try:
        current = pipeline.parameters(instantiated=True)
        current.setdefault("segmentation", {})
        current["segmentation"]["min_duration_off"] = 0.3
        pipeline.instantiate(current)
    except Exception as e:
        print(f"Note: skipped segmentation tuning ({e}); using pipeline defaults.")

    if torch.backends.mps.is_available():
        pipeline.to(torch.device("mps"))

    kwargs = {}
    if num_speakers is not None:
        kwargs["num_speakers"] = num_speakers
    else:
        if min_speakers is not None:
            kwargs["min_speakers"] = min_speakers
        if max_speakers is not None:
            kwargs["max_speakers"] = max_speakers

    with ProgressHook() as hook:
        diarization = pipeline(audio_path, hook=hook, **kwargs)
    annotation = getattr(diarization, "speaker_diarization", diarization)

    intervals = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        intervals.append({
            "start": turn.start,
            "end": turn.end,
            "speaker": speaker,
        })
    intervals.sort(key=lambda i: i["start"])
    return intervals


def relabel_with_references(
    intervals: list[dict],
    wav_path: str,
    references: list[tuple[str, float, float]],
    hf_token: str,
    audio_duration: float,
) -> list[dict]:
    """Replace pyannote speaker labels by matching each interval's voice
    embedding to the nearest reference embedding (cosine similarity).
    Pads short intervals with surrounding audio so the embedder has enough signal,
    and falls back to neighbor labels if embedding still fails."""
    import numpy as np
    from pyannote.audio import Inference, Model
    from pyannote.core import Segment

    MIN_EMBED_DURATION = 1.0  # seconds — pad short intervals up to at least this long
    PAD_EACH_SIDE = 0.4  # always extend a bit so the embedder has clean signal

    model = Model.from_pretrained("pyannote/embedding", token=hf_token)
    inference = Inference(model, window="whole")
    if torch.backends.mps.is_available():
        inference.to(torch.device("mps"))

    def embed(start: float, end: float) -> "np.ndarray":
        # Always pad a little; pad more if the interval is very short.
        needed = max(0.0, MIN_EMBED_DURATION - (end - start))
        pad_l = PAD_EACH_SIDE + needed / 2
        pad_r = PAD_EACH_SIDE + needed / 2
        s = max(0.0, start - pad_l)
        e = min(audio_duration, end + pad_r)
        emb = inference.crop({"audio": wav_path}, Segment(s, e))
        emb = np.asarray(emb, dtype=np.float64).flatten()
        norm = np.linalg.norm(emb)
        return emb / norm if norm > 0 else emb

    # Build (and average) reference embeddings per name.
    print("Computing reference embeddings...", flush=True)
    refs_by_name: dict[str, list] = {}
    for name, start, end in references:
        emb = embed(start, end)
        refs_by_name.setdefault(name, []).append(emb)
        print(f"  {name}: enrolled from {start:.1f}-{end:.1f}s", flush=True)
    ref_embeddings = {}
    for name, embs in refs_by_name.items():
        avg = np.mean(np.stack(embs), axis=0)
        norm = np.linalg.norm(avg)
        ref_embeddings[name] = avg / norm if norm > 0 else avg

    # Re-label each interval. Track which ones failed for the neighbor pass.
    from tqdm import tqdm

    print(f"Re-labeling {len(intervals)} intervals against references...", flush=True)
    relabeled: list[dict] = []
    failed_indices: list[int] = []
    for i, iv in enumerate(tqdm(intervals, desc="  re-labeling", unit="iv")):
        try:
            iv_emb = embed(iv["start"], iv["end"])
            if np.linalg.norm(iv_emb) == 0:
                raise ValueError("zero embedding")
            best_name = max(
                ref_embeddings,
                key=lambda n: float(np.dot(iv_emb, ref_embeddings[n])),
            )
            relabeled.append({**iv, "speaker": best_name})
        except Exception:
            relabeled.append(dict(iv))
            failed_indices.append(i)

    # Second pass: for intervals where embedding failed, inherit the label from
    # the nearest successfully-labeled neighbor (preferring previous over next).
    valid_names = set(ref_embeddings.keys())
    for i in failed_indices:
        # Look backward
        chosen = None
        for j in range(i - 1, -1, -1):
            if relabeled[j]["speaker"] in valid_names:
                chosen = relabeled[j]["speaker"]
                break
        # Then forward if no previous found
        if chosen is None:
            for j in range(i + 1, len(relabeled)):
                if relabeled[j]["speaker"] in valid_names:
                    chosen = relabeled[j]["speaker"]
                    break
        if chosen is not None:
            relabeled[i]["speaker"] = chosen

    if failed_indices:
        print(
            f"  ({len(failed_indices)} short intervals labeled by neighbor inheritance.)",
            flush=True,
        )
    return relabeled


def transcribe_full(audio_path: str) -> list[dict]:
    """Transcribe the entire file once with mlx-whisper. Returns words with timestamps."""
    print(
        f"Loading Whisper via MLX ({WHISPER_MODEL}; downloads ~3GB on first run)...",
        flush=True,
    )
    print("Transcribing full audio with Metal acceleration...", flush=True)

    result = mlx_whisper.transcribe(
        audio_path,
        path_or_hf_repo=WHISPER_MODEL,
        word_timestamps=True,
        verbose=False,
    )

    words = []
    for seg in result.get("segments", []):
        for w in seg.get("words", []) or []:
            text = (w.get("word") or "").strip()
            if not text:
                continue
            words.append({"start": w["start"], "end": w["end"], "text": text})

    print(f"Transcribed {len(words)} words.", flush=True)
    return words


def assign_speakers(words: list[dict], intervals: list[dict]) -> list[dict]:
    """Assign each word to the speaker whose interval contains the word's midpoint.
    Falls back to nearest interval if no overlap."""
    if not intervals:
        return [{**w, "speaker": "SPEAKER_00"} for w in words]

    starts = [iv["start"] for iv in intervals]
    out = []
    for w in words:
        mid = (w["start"] + w["end"]) / 2

        # bisect_right gives the index of the first interval starting AFTER mid.
        # The candidate containing mid is at idx-1.
        idx = bisect_right(starts, mid) - 1
        chosen = None
        if 0 <= idx < len(intervals) and intervals[idx]["end"] >= mid:
            chosen = intervals[idx]
        else:
            # No interval contains the midpoint; pick the nearest one by edge distance.
            best_dist = float("inf")
            for iv in intervals:
                if mid < iv["start"]:
                    dist = iv["start"] - mid
                elif mid > iv["end"]:
                    dist = mid - iv["end"]
                else:
                    dist = 0
                if dist < best_dist:
                    best_dist = dist
                    chosen = iv

        out.append({**w, "speaker": chosen["speaker"]})
    return out


def group_by_speaker(
    words: list[dict],
    max_words: int = 50,
    max_gap: float = 1.5,
) -> list[dict]:
    """Group words into output lines. Breaks a new line when the speaker changes,
    when a sentence ends (. ? !), when there's a pause longer than max_gap seconds,
    or when the current line reaches max_words tokens."""
    if not words:
        return []

    groups: list[dict] = []
    current: dict | None = None

    def flush():
        nonlocal current
        if current and current["tokens"]:
            groups.append({
                "start": current["start"],
                "speaker": current["speaker"],
                "text": " ".join(current["tokens"]),
            })
        current = None

    def start_new(w: dict):
        nonlocal current
        current = {
            "start": w["start"],
            "speaker": w["speaker"],
            "tokens": [w["text"]],
            "last_end": w["end"],
        }

    for w in words:
        if current is None:
            start_new(w)
            continue

        speaker_changed = w["speaker"] != current["speaker"]
        long_pause = w["start"] - current["last_end"] > max_gap
        sentence_ended = current["tokens"][-1].rstrip('"\')').endswith((".", "?", "!"))
        too_long = len(current["tokens"]) >= max_words

        if speaker_changed or long_pause or sentence_ended or too_long:
            flush()
            start_new(w)
        else:
            current["tokens"].append(w["text"])
            current["last_end"] = w["end"]

    flush()
    return groups


def print_diarization(intervals: list[dict]) -> None:
    """Print the raw diarization timeline for debugging."""
    print()
    print("=== Raw diarization timeline ===")
    prev_end = 0.0
    durations: dict[str, float] = {}
    for i, iv in enumerate(intervals, 1):
        gap = iv["start"] - prev_end
        gap_str = f"  (silence {gap:.2f}s)" if gap > 0.5 else ""
        duration = iv["end"] - iv["start"]
        print(
            f"  {i:3d}. [{format_timestamp(iv['start'])}-{format_timestamp(iv['end'])}] "
            f"{iv['speaker']:<12s} {duration:5.2f}s{gap_str}"
        )
        durations[iv["speaker"]] = durations.get(iv["speaker"], 0.0) + duration
        prev_end = iv["end"]
    print()
    print("Per-speaker total speech time:")
    for speaker, total in sorted(durations.items()):
        m, s = divmod(int(total), 60)
        print(f"  {speaker:<12s} {m:02d}:{s:02d}  ({total:.1f}s)")
    print("=== End diarization timeline ===")
    print()


def ignore_short_flips(groups: list[dict], max_words: int) -> list[dict]:
    """When a speaker turn of <= max_words words is sandwiched between two turns
    of the same other speaker, absorb its text into the surrounding speaker.
    Iterative — handles consecutive sandwich patterns."""
    if max_words <= 0 or len(groups) < 3:
        return list(groups)

    result: list[dict] = []
    i = 0
    while i < len(groups):
        result.append(dict(groups[i]))
        i += 1
        # Greedily absorb sandwich patterns into the most recently-appended group.
        while (
            i + 1 < len(groups)
            and groups[i]["speaker"] != result[-1]["speaker"]
            and groups[i + 1]["speaker"] == result[-1]["speaker"]
            and len(groups[i]["text"].split()) <= max_words
        ):
            result[-1]["text"] = (
                result[-1]["text"]
                + " " + groups[i]["text"]
                + " " + groups[i + 1]["text"]
            )
            i += 2
    return result


def format_timestamp(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def assign_speaker_labels(results: list[dict]) -> dict[str, str]:
    """Map raw labels to display labels. Pyannote-style 'SPEAKER_00' becomes
    'Speaker 1' etc.; reference-enrolled names like 'Alice' pass through unchanged."""
    seen = {}
    counter = 1
    for r in results:
        raw = r["speaker"]
        if raw in seen:
            continue
        if SPEAKER_PATTERN.match(raw):
            seen[raw] = f"Speaker {counter}"
            counter += 1
        else:
            seen[raw] = raw
    return seen


def format_output(results: list[dict]) -> str:
    labels = assign_speaker_labels(results)
    lines = []
    for r in results:
        ts = format_timestamp(r["start"])
        speaker = labels[r["speaker"]]
        lines.append(f"[{ts}] {speaker}: {r['text']}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio with speaker diarization."
    )
    parser.add_argument("audio", help="Path to the audio file")
    parser.add_argument(
        "--hf-token",
        default=os.environ.get("HF_TOKEN"),
        help="Hugging Face token (or set HF_TOKEN env var)",
    )
    parser.add_argument(
        "-o", "--output", help="Save transcript to this file path"
    )
    parser.add_argument(
        "--speakers", type=int, default=None,
        help="Exact number of speakers (recommended when known, e.g. 2 for an interview)",
    )
    parser.add_argument(
        "--min-speakers", type=int, default=None,
        help="Minimum number of speakers (use with --max-speakers when count is uncertain)",
    )
    parser.add_argument(
        "--max-speakers", type=int, default=None,
        help="Maximum number of speakers",
    )
    parser.add_argument(
        "--debug-diarization", action="store_true",
        help="Print the raw diarization timeline before transcribing.",
    )
    parser.add_argument(
        "--ignore-flips", type=int, default=0, metavar="N",
        help="When a speaker turn of N or fewer words is sandwiched between two "
             "turns of the same other speaker, absorb its text into the surrounding "
             "speaker's turn. Use to suppress brief backchannel interruptions "
             "('yeah', 'right') from breaking up a long monologue. "
             "Try N=1 or 2 for two-person interviews. Default 0 (off).",
    )
    parser.add_argument(
        "--reference", type=parse_reference, action="append", default=[],
        metavar="NAME@START-END",
        help="Reference clip for a known speaker. Anchors speaker identity to a "
             "real voice sample so labels stay stable across the recording. "
             "Times can be seconds, M:SS, or H:MM:SS. Repeat for multiple speakers. "
             "Example: --reference Alice@0:05-0:15 --reference Bob@0:30-0:42. "
             "Repeat with the same name to average multiple samples.",
    )
    args = parser.parse_args()

    if not args.hf_token:
        print("Error: Hugging Face token required. Use --hf-token or set HF_TOKEN.", file=sys.stderr)
        sys.exit(1)

    audio_path = args.audio
    if not Path(audio_path).is_file():
        print(f"Error: File not found: {audio_path}", file=sys.stderr)
        sys.exit(1)

    print("Transcoding to 16 kHz mono WAV...")
    wav_path = to_wav(audio_path)
    duration = get_audio_duration(wav_path)
    print(f"Audio duration: {format_timestamp(duration)} ({duration:.1f}s)")

    # Validate reference time ranges against actual file duration before doing
    # any heavy work, to catch typos like a 4-minute reference in a 2-minute file.
    for name, start, end in args.reference:
        if end > duration:
            print(
                f"Error: --reference {name}@{start:.1f}-{end:.1f} extends past the "
                f"end of the audio ({duration:.1f}s).",
                file=sys.stderr,
            )
            Path(wav_path).unlink(missing_ok=True)
            sys.exit(1)

    try:
        # If references are provided and --speakers wasn't set, infer count from refs.
        num_speakers = args.speakers
        if not num_speakers and args.reference:
            unique_names = {name for name, _, _ in args.reference}
            num_speakers = len(unique_names)
            print(
                f"Inferred --speakers={num_speakers} from references "
                f"({', '.join(sorted(unique_names))})."
            )

        if num_speakers:
            print(f"Running speaker diarization (expecting {num_speakers} speakers)...")
        else:
            print("Running speaker diarization...")
        intervals = diarize(
            wav_path,
            args.hf_token,
            num_speakers=num_speakers,
            min_speakers=args.min_speakers,
            max_speakers=args.max_speakers,
        )
        print(f"Found {len(intervals)} speaker intervals.")

        if args.reference:
            intervals = relabel_with_references(
                intervals, wav_path, args.reference, args.hf_token, duration
            )

        if args.debug_diarization:
            print_diarization(intervals)

        words = transcribe_full(wav_path)
        if not words:
            print("No speech detected.")
            sys.exit(0)

        labeled = assign_speakers(words, intervals)
        results = group_by_speaker(labeled)
        if args.ignore_flips > 0:
            before = len(results)
            results = ignore_short_flips(results, args.ignore_flips)
            print(
                f"Smoothing: absorbed {before - len(results)} brief sandwich turns "
                f"(<= {args.ignore_flips} words)."
            )
    finally:
        Path(wav_path).unlink(missing_ok=True)

    transcript = format_output(results)
    print()
    print(transcript)

    if args.output:
        Path(args.output).write_text(transcript + "\n")
        print(f"\nSaved to {args.output}")


if __name__ == "__main__":
    main()
