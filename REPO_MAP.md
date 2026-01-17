# Repository Map

This document describes the directory structure and file purposes for the `reachy_mini_elevenlabs` package.

## Overview

`reachy_mini_elevenlabs` is a Reachy Mini app that integrates ElevenLabs Conversational AI for interactive voice conversations. The package uses the `src/` layout with source code in `src/reachy_mini_elevenlabs/`.

## Directory Structure

```
reachy_mini_elevenlabs/
├── pyproject.toml              # Package configuration and dependencies
├── README.md                   # Package documentation
├── .env.example                # Example environment variables template
├── REPO_MAP.md                 # This file - repository structure documentation
│
├── src/
│   └── reachy_mini_elevenlabs/
│       ├── __init__.py         # Package init with version info
│       ├── config.py           # Configuration manager (env vars, .env files)
│       ├── main.py             # Main entry point and ReachyMiniElevenLabsApp
│       ├── utils.py            # Argument parsing and logging utilities
│       ├── audio_interface.py  # ReachyAudioInterface for robot audio I/O
│       ├── elevenlabs_handler.py # ElevenLabsHandler conversation manager
│       ├── settings_ui.py      # Settings UI endpoints for headless mode
│       │
│       ├── audio/              # Audio processing components
│       │   ├── __init__.py     # Audio module exports
│       │   ├── head_wobbler.py # HeadWobbler for lip-sync animation
│       │   ├── speech_tapper.py # SwayRollRT audio-to-movement converter
│       │   └── utils.py        # Audio conversion and resampling utilities
│       │
│       ├── tools/              # ElevenLabs agent tools
│       │   ├── __init__.py     # Tools module exports
│       │   └── core_tools.py   # Tool dependencies and handlers (camera, dance, emotion)
│       │
│       └── static/             # Settings UI frontend assets
│           ├── index.html      # Settings page HTML
│           ├── main.js         # Settings page JavaScript
│           └── style.css       # Settings page styles
│
└── tests/                      # Test suite
    ├── __init__.py             # Test package init
    ├── test_config.py          # Configuration manager tests
    ├── test_utils.py           # Utility function tests
    ├── test_audio_interface.py # ReachyAudioInterface tests
    ├── test_audio_utils.py     # Audio utility tests
    ├── test_elevenlabs_handler.py # ElevenLabsHandler tests
    ├── test_core_tools.py      # Tool registration and handler tests
    └── test_settings_ui.py     # Settings UI endpoint tests
```

## File Descriptions

### Root Files

| File | Purpose |
|------|---------|
| `pyproject.toml` | Package configuration including dependencies (`elevenlabs`, `python-dotenv`, `reachy_mini`), entry points (`reachy-mini-elevenlabs` console script, `reachy_mini_apps` plugin), and development tools configuration (ruff, mypy, pytest). |
| `README.md` | Package documentation with installation and usage instructions. |
| `.env.example` | Template for environment variables (`ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID`). |

### Source Files (`src/reachy_mini_elevenlabs/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Package initialization with version string (`__version__`). |
| `config.py` | `Config` class that loads `ELEVENLABS_API_KEY` and `ELEVENLABS_AGENT_ID` from environment variables and `.env` files using python-dotenv. Provides validation and reload functionality. |
| `main.py` | Main entry point containing `main()` console script function, `run()` orchestration function, and `ReachyMiniElevenLabsApp` class that extends `ReachyMiniApp` for host integration. Initializes robot, HeadWobbler, MovementManager, and ElevenLabsHandler. |
| `utils.py` | Utility functions: `parse_args()` for command-line argument parsing, `setup_logger()` for logging configuration, and `log_connection_troubleshooting()` for connection error guidance. |
| `audio_interface.py` | `ReachyAudioInterface` class extending ElevenLabs `AudioInterface`. Routes audio through robot microphone/speaker and feeds audio to HeadWobbler for lip-sync. Implements `start()`, `stop()`, `output()`, and `interrupt()` methods. |
| `elevenlabs_handler.py` | `ElevenLabsHandler` class managing the ElevenLabs Conversation lifecycle. Creates client, audio interface, and tools. Handles session start/stop, callbacks, connection failures with exponential backoff, and automatic session restart. |
| `settings_ui.py` | Settings UI for headless mode. Provides FastAPI routes (`/status`, `/elevenlabs_config`) for checking and setting ElevenLabs credentials. Persists configuration to instance `.env` file. |

### Audio Module (`src/reachy_mini_elevenlabs/audio/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Module exports for audio utilities and constants. |
| `head_wobbler.py` | `HeadWobbler` class that converts base64-encoded audio chunks into head movement offsets for lip-sync animation. Runs in a background thread and coordinates with `SwayRollRT`. |
| `speech_tapper.py` | `SwayRollRT` class implementing real-time audio analysis. Converts PCM audio to head sway/roll movements using VAD (Voice Activity Detection), loudness tracking, and oscillator-based motion generation. |
| `utils.py` | Audio utility functions: `audio_to_float32()` for PCM conversion, `to_float32_mono()` for multi-channel handling, `resample_audio()` for sample rate conversion, and convenience wrappers for common conversions. |

### Tools Module (`src/reachy_mini_elevenlabs/tools/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Module exports for tool dependencies and handlers. |
| `core_tools.py` | `ToolDependencies` dataclass holding robot component references. Tool handlers: `camera_tool()` captures images, `dance_tool()` triggers dances, `emotion_tool()` plays emotions. `register_tools()` registers all tools with ElevenLabs `ClientTools`. Includes error-handling wrappers. |

### Static Assets (`src/reachy_mini_elevenlabs/static/`)

| File | Purpose |
|------|---------|
| `index.html` | Settings UI HTML page with form for entering ElevenLabs API key and Agent ID. |
| `main.js` | Settings UI JavaScript handling form submission, status polling, and API communication. |
| `style.css` | Settings UI styles for the configuration form. |

### Tests (`tests/`)

| File | Purpose |
|------|---------|
| `__init__.py` | Test package initialization. |
| `test_config.py` | Tests for `Config` class including environment loading, validation, and property-based tests for configuration round-trips. |
| `test_utils.py` | Tests for argument parsing and logging setup utilities. |
| `test_audio_interface.py` | Tests for `ReachyAudioInterface` including audio output to HeadWobbler and interrupt behavior. |
| `test_audio_utils.py` | Tests for audio conversion and resampling functions. |
| `test_elevenlabs_handler.py` | Tests for `ElevenLabsHandler` including authentication requirement logic. |
| `test_core_tools.py` | Tests for tool registration, execution, and error handling. |
| `test_settings_ui.py` | Tests for settings UI endpoints and configuration persistence. |

## Entry Points

The package provides two entry points defined in `pyproject.toml`:

1. **Console Script**: `reachy-mini-elevenlabs`
   - Maps to `reachy_mini_elevenlabs.main:main`
   - Allows running the app directly from command line

2. **Reachy Mini Apps Plugin**: `reachy_mini_elevenlabs`
   - Maps to `reachy_mini_elevenlabs.main:ReachyMiniElevenLabsApp`
   - Enables discovery and launch by the Reachy Mini host system

## Dependencies

Key dependencies (from `pyproject.toml`):
- `elevenlabs>=1.0.0` - ElevenLabs Conversational AI SDK
- `python-dotenv` - Environment variable management
- `reachy_mini>=1.2.7` - Reachy Mini robot SDK
- `reachy_mini_dances_library` - Dance animations
- `reachy_mini_toolbox` - Robot utilities
- `opencv-python>=4.12.0.88` - Image processing for camera tool
- `numpy` - Audio and numerical processing

Development dependencies:
- `pytest`, `pytest-asyncio` - Testing framework
- `hypothesis` - Property-based testing
- `ruff` - Linting and formatting
- `mypy` - Type checking
