# Meeting Recorder

A desktop application for recording in-person meetings on macOS, with Whisper-based transcription and LLM-powered summarization.

![macOS](https://img.shields.io/badge/platform-macOS-blue)
![Python](https://img.shields.io/badge/python-3.12+-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## Built With

This entire project was **vibe coded** in a single session using [OpenCode](https://github.com/opencode-ai/opencode) with the Qwen3.6-35B-A3B model (UD-Q6_K quantization). Every line of code — architecture, UI, transcription pipeline, LLM integration, tests, build scripts, and documentation — was generated through natural language conversation.

As an IT professional with over 30 years in the industry, this project was as much about building a practical tool for recording, transcribing, and summarizing in-person meetings as it was about exploring what's possible when you run a capable local model on your own hardware. It was genuinely surprising to see how well a local model could handle the full scope of the project — from designing a polished UI to wiring up Whisper diarization and multi-provider LLM integration — all through conversation.

## Features

- **High-quality recording** — Configurable audio formats (WAV, FLAC, OPUS, MP3, OGG) with PyAudio
- **Automatic audio leveling** — RMS-based gain control with ambient noise calibration and dead air detection
- **Pause / Resume / Stop** — Full control over recording sessions
- **Speaker diarization** — Automatic speaker identification via MLX Whisper + pyannote
- **Speaker renaming** — Interactive dialog to label speakers before summarization
- **Multi-provider LLM** — OpenAI, Anthropic, Ollama, LM Studio, and vLLM
- **Summarization styles** — Concise, Normal, Detailed, or fully custom prompts
- **ZIP export** — Package audio, transcript, and summary into a single archive
- **Reprocess existing meetings** — Re-run transcription/summarization with updated settings
- **Modern dark UI** — Refined PySide6 interface with real-time audio metering

## Requirements

- **macOS** with Apple Silicon (M1 or newer)
- **Python 3.12** — Required by `mlx-whisper` and `pyannote.audio`
- **ffmpeg** — Audio transcoding (`brew install ffmpeg`)
- **Hugging Face token** — Required for diarization models

## Installation

### Quick Install (Recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/michmill1970/meeting-recorder/main/install.sh | bash
```

This will:
1. Create a Python 3.12 virtual environment at `~/.local/share/meeting-recorder/venv`
2. Install all Python dependencies
3. Install PortAudio via Homebrew (if not present)
4. Create launcher scripts (`meeting-recorder`, `whisper-setup`)
5. Add `~/.local/bin` to your PATH

### Manual Install

1. **Create a Python 3.12 virtual environment:**

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```

2. **Install dependencies:**

   ```bash
   pip install -e ".[dev]"
   ```

3. **Install whisper-diarization dependencies:**

   ```bash
   pip install mlx-whisper pyannote.audio torch torchaudio omegaconf
   ```

4. **Install PortAudio:**

   ```bash
   brew install portaudio
   ```

5. **Configure your Hugging Face token:**

   You need access to:
   - `pyannote/speaker-diarization-3.1`
   - `pyannote/segmentation-3.0`

   Set your token in the app's **Settings > Whisper** tab.

## Usage

```bash
python -m src.main
```

Or if installed via the install script:

```bash
meeting-recorder
```

### Workflow

1. **Select a microphone** from the dropdown
2. **Click Record** — the app calibrates ambient noise for 5 seconds
3. **Record your meeting** — use Pause/Stop as needed
4. **Stop recording** — the app automatically:
   - Runs Whisper transcription with speaker diarization
   - Shows the **Rename Speakers** dialog — label each speaker, then click **Apply & Continue**
   - Generates an LLM-powered summary
5. **Export** — click **File > Export Meeting** to create a ZIP archive

### Reprocessing Existing Meetings

The **Existing Recordings** tab scans your save directory for previous meetings. Select a meeting and click **Reprocess Selected** to re-run transcription and summarization with your current settings.

## Configuration

Settings are saved to `~/.config/meeting-recorder/settings.json`.

### Recording

| Setting | Default | Description |
|---|---|---|
| Microphone | System default | Input device, remembered between sessions |
| Save Directory | `~/Documents/MeetingRecorder/` | Where meeting archives are stored |
| Audio Format | WAV | WAV, FLAC, OPUS, MP3, or OGG |

### Audio Leveling

| Setting | Default | Description |
|---|---|---|
| Mode | Auto | Automatic or manual gain control |
| Noise Floor Offset | +10 dB | Target level relative to ambient noise |
| Dead Air Timeout | 60 s | Silence duration before gain boost |
| Max Gain | +12 dB | Maximum gain increase |

### Whisper

| Setting | Default | Description |
|---|---|---|
| HF Token | — | Hugging Face API token for diarization |
| Speaker Mode | Auto | Auto-detect, specific count, or min/max range |
| Ignore Flips | 2 | Brief backchannel turns absorbed as same speaker |

### LLM

| Setting | Description |
|---|---|
| Provider | OpenAI, Anthropic, Ollama, LM Studio, or vLLM |
| API Key | Required for OpenAI and Anthropic |
| Base URL | For local providers (Ollama: `http://localhost:11434`, etc.) |
| Model | Model name to use |
| Summarization Style | Concise, Normal, Detailed, or Custom |
| Custom Prompt | Full user-defined prompt with `{transcript}` placeholder |

### Advanced LLM Settings

Fine-tune generation parameters:

| Section | Parameters |
|---|---|
| Sampling | Temperature, Top-K, Top-P |
| Repetition | Repetition Penalty, Presence Penalty, Frequency Penalty |
| Diversity | Penalty Scope, Penalty Decay |

Preset profiles: **Focused** (coherent, conservative), **Balanced** (default), **Creative** (diverse, exploratory).

## Building a Distributable App

### Using the Build Script

```bash
./build.sh --macos   # macOS app bundle
./build.sh           # Linux executable
```

### Using Make

```bash
make build-macos    # macOS app bundle → dist/Meeting Recorder.app
make build          # Linux executable → dist/meeting-recorder
```

### PyInstaller Spec

The project uses `meeting-recorder.spec` with app icon and hidden imports configured.

## Running Tests

```bash
make test             # All tests
make test-unit        # Unit tests only
make test-system      # System + integration tests
make test-cov         # Tests with coverage report
```

## Project Structure

```
meeting-recorder/
├── whisper-diarization/          # Vendored transcription tool (MLX Whisper + pyannote)
├── src/
│   ├── main.py                   # Entry point
│   ├── models/                   # Data models & schemas
│   │   └── schemas.py            # Pydantic models for all settings
│   ├── recording/                # Audio recording engine
│   │   ├── engine.py             # PyAudio stream, format conversion via ffmpeg
│   │   └── level_manager.py      # RMS auto-leveling with dead air detection
│   ├── transcription/            # Whisper integration
│   │   └── whisper_client.py     # Subprocess wrapper with progress callbacks
│   ├── summarization/            # LLM summarization
│   │   ├── llm_client.py         # Multi-provider client with style prompts
│   │   └── providers/            # Provider implementations
│   │       ├── base.py           # Abstract base class
│   │       ├── openai.py         # OpenAI-compatible API
│   │       ├── anthropic.py      # Anthropic Claude
│   │       ├── ollama.py         # Ollama (OpenAI-compatible endpoint)
│   │       ├── lm_studio.py      # LM Studio
│   │       └── vllm.py           # vLLM
│   ├── settings/                 # Settings management
│   │   └── manager.py            # JSON persistence with Pydantic validation
│   ├── ui/                       # Qt UI components
│   │   ├── main_window.py        # Main application window, thread workers
│   │   ├── components/           # UI widgets
│   │   │   ├── recording_panel.py    # Record/pause/stop + meeting list
│   │   │   ├── transcript_panel.py   # Transcript display
│   │   │   ├── summary_panel.py      # Summary display
│   │   │   ├── audio_meter.py        # Real-time audio level meter
│   │   │   ├── settings_dialog.py    # Settings UI
│   │   │   ├── speaker_rename_dialog.py  # Speaker labeling
│   │   │   └── advanced_llm_dialog.py  # Advanced LLM params
│   │   └── styles/
│   │       └── dark_theme.py       # Modern dark theme stylesheet
│   └── utils/                    # Utilities
│       ├── export.py             # ZIP archive export
│       └── sleep_prevention.py   # macOS caffeinate wrapper
├── tests/                        # Test suite (pytest)
├── icons/                        # App icon assets
├── scripts/                      # Build helper scripts
├── install.sh                    # One-command installer
├── uninstall.sh                  # Complete removal script
├── build.sh                      # PyInstaller build script
├── meeting-recorder.spec         # PyInstaller spec file
├── pyproject.toml                # Project configuration
└── Makefile                      # Build/test/run commands
```

## Uninstall

```bash
./uninstall.sh
```

Removes the virtual environment, launcher scripts, config file, meeting recordings, and Hugging Face model cache.

## License

MIT — Vendored `whisper-diarization` is MIT (Concord Consortium)
