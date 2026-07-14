.PHONY: help install dev test test-cov lint clean build build-macos run

# Default target
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install for production (Python 3.12 required)
	@echo "Installing Meeting Recorder…"
	python3.12 -m venv .venv
	. .venv/bin/activate && pip install -e ".[dev]"
	@echo ""
	@echo "Next: pip install mlx-whisper pyannote.audio torch torchaudio"

dev: ## Install for development
	@echo "Setting up development environment…"
	python3.12 -m venv .venv
	. .venv/bin/activate && pip install -e ".[dev]"
	@echo ""
	@echo "Virtual environment created at .venv/"
	@echo "Activate it with: source .venv/bin/activate"

run: ## Run the application
	. .venv/bin/activate && python -m src.main

test: ## Run all tests
	. .venv/bin/activate && pytest tests/ -v

test-cov: ## Run tests with coverage report
	. .venv/bin/activate && pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

test-unit: ## Run only unit tests
	. .venv/bin/activate && pytest tests/test_models/ tests/test_settings/ tests/test_recording/ tests/test_transcription/ tests/test_summarization/ tests/test_ui/ tests/test_utils/ -v

test-system: ## Run system and integration tests
	. .venv/bin/activate && pytest tests/test_system/ -v --tb=short

lint: ## Run linter and type checker
	. .venv/bin/activate && ruff check src/ tests/
	. .venv/bin/activate && mypy src/

format: ## Format code
	. .venv/bin/activate && ruff format src/ tests/

clean: ## Clean build artifacts and caches
	rm -rf build/ dist/ *.egg-info .pytest_cache .mypy_cache
	rm -rf htmlcov/ .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaned."

build: ## Build distributable app (PyInstaller)
	@echo "Building Meeting Recorder…"
	. .venv/bin/activate && pyinstaller meeting-recorder.spec --clean

build-macos: ## Build macOS application bundle
	@echo "Building macOS app bundle…"
	. .venv/bin/activate && pyinstaller \
		--clean \
		--name="Meeting Recorder" \
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
		--exclude-module jinja2 \
		src/main.py
	@echo ""
	@echo "Build complete: dist/Meeting Recorder.app"
	@echo "Run with: open dist/Meeting\ Recorder.app"
