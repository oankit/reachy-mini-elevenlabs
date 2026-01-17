# Architecture Documentation

This document describes the runtime architecture, host integration, threading model, and dataflow for the `reachy_mini_elevenlabs` package.

## Overview

`reachy_mini_elevenlabs` is a Reachy Mini app that integrates ElevenLabs Conversational AI for interactive voice conversations. The architecture bridges the ElevenLabs SDK with the robot's hardware through a custom `ReachyAudioInterface`, enabling:

1. **Voice Input**: Capture audio from the robot's microphone and stream to ElevenLabs
2. **Voice Output**: Play synthesized speech through the robot's speaker
3. **Lip-Sync Animation**: Convert audio to head movements for natural interaction
4. **Agent Tools**: Allow the AI agent to control robot actions (camera, dance, emotions)

## System Architecture

```mermaid
graph TB
    subgraph "Reachy Mini Robot Hardware"
        MIC[🎤 Microphone]
        SPK[🔊 Speaker]
        HEAD[🤖 Head Motors]
        CAM[📷 Camera]
    end
    
    subgraph "reachy_mini_elevenlabs App"
        subgraph "Entry Point"
            MAIN[main.py<br/>ReachyMiniElevenLabsApp]
        end
        
        subgraph "Configuration"
            CONFIG[config.py<br/>Config Manager]
            SETTINGS[settings_ui.py<br/>Settings UI]
        end
        
        subgraph "Core Components"
            HANDLER[elevenlabs_handler.py<br/>ElevenLabsHandler]
            AUDIO[audio_interface.py<br/>ReachyAudioInterface]
        end
        
        subgraph "Audio Processing"
            HW[head_wobbler.py<br/>HeadWobbler]
            ST[speech_tapper.py<br/>SwayRollRT]
        end
        
        subgraph "Tools"
            TOOLS[core_tools.py<br/>ClientTools]
        end
    end
    
    subgraph "External Dependencies"
        MM[MovementManager<br/>reachy_mini_conversation_app]
        CW[CameraWorker<br/>reachy_mini_conversation_app]
    end
    
    subgraph "ElevenLabs Cloud"
        CONV[Conversation<br/>WebSocket]
        AGENT[AI Agent<br/>STT + LLM + TTS]
    end
    
    %% Hardware connections
    MIC -->|PCM Audio| AUDIO
    AUDIO -->|Float32 Audio| SPK
    HW -->|Movement Offsets| MM
    MM -->|Motor Commands| HEAD
    CAM -->|Frames| CW
    
    %% Internal connections
    MAIN --> CONFIG
    MAIN --> HANDLER
    MAIN --> MM
    MAIN --> CW
    MAIN --> HW
    SETTINGS --> CONFIG
    
    HANDLER --> AUDIO
    HANDLER --> TOOLS
    AUDIO --> HW
    HW --> ST
    
    TOOLS --> CW
    TOOLS --> MM
    
    %% Cloud connections
    AUDIO <-->|Audio Chunks| CONV
    CONV <-->|WebSocket| AGENT
    TOOLS <-.->|Tool Calls| CONV
    
    classDef hardware fill:#e1f5fe,stroke:#01579b
    classDef core fill:#fff3e0,stroke:#e65100
    classDef cloud fill:#f3e5f5,stroke:#7b1fa2
    classDef external fill:#e8f5e9,stroke:#2e7d32
    
    class MIC,SPK,HEAD,CAM hardware
    class MAIN,HANDLER,AUDIO,HW,ST,TOOLS,CONFIG,SETTINGS core
    class CONV,AGENT cloud
    class MM,CW external
```

## Host Integration

The app integrates with the Reachy Mini host system through two entry points:

### Entry Points

```mermaid
graph LR
    subgraph "Host System"
        HOST[Reachy Mini Apps Host]
        DISC[Entry Point Discovery]
    end
    
    subgraph "reachy_mini_elevenlabs"
        EP1[Console Script<br/>reachy-mini-elevenlabs]
        EP2[Plugin Entry Point<br/>ReachyMiniElevenLabsApp]
        MAIN[main.py]
    end
    
    HOST --> DISC
    DISC -->|reachy_mini_apps| EP2
    EP2 --> MAIN
    
    EP1 -->|Direct CLI| MAIN
    
    classDef host fill:#e3f2fd,stroke:#1565c0
    classDef entry fill:#fff8e1,stroke:#f9a825
    
    class HOST,DISC host
    class EP1,EP2 entry
```

### ReachyMiniElevenLabsApp Class

The `ReachyMiniElevenLabsApp` class extends `ReachyMiniApp` to integrate with the host:

```python
class ReachyMiniElevenLabsApp(ReachyMiniApp):
    custom_app_url = "http://0.0.0.0:7860/"  # Settings UI URL
    dont_start_webserver = False              # Enable settings server
    
    def run(self, reachy_mini: ReachyMini, stop_event: threading.Event) -> None:
        # Host provides robot instance and stop signal
        # App delegates to main run() function
```

### Host Integration Flow

1. **Discovery**: Host discovers app via `reachy_mini_apps` entry point in `pyproject.toml`
2. **Initialization**: Host creates `ReachyMiniElevenLabsApp` instance
3. **Launch**: Host calls `run()` with robot instance and stop event
4. **Settings UI**: Host mounts settings routes on its FastAPI server
5. **Shutdown**: Host sets stop event, app performs graceful cleanup

## Threading Model

The app uses multiple threads for concurrent operations:

```mermaid
graph TB
    subgraph "Main Thread"
        MAIN_INIT[Initialize Components]
        MAIN_START[Start Background Threads]
        MAIN_CONV[Start Conversation<br/>handler.start]
        MAIN_WAIT[Wait for Session End<br/>handler.wait_for_end]
        MAIN_CLEANUP[Cleanup & Shutdown]
    end
    
    subgraph "Background Threads"
        MM_THREAD[MovementManager Thread<br/>Robot movement control]
        HW_THREAD[HeadWobbler Thread<br/>Lip-sync animation]
        CW_THREAD[CameraWorker Thread<br/>Frame capture]
        AUDIO_IN[Audio Input Thread<br/>Microphone capture]
        STOP_POLL[Stop Event Poller<br/>Graceful shutdown]
    end
    
    subgraph "ElevenLabs SDK Threads"
        WS_THREAD[WebSocket Thread<br/>Cloud communication]
        AUDIO_OUT[Audio Output<br/>Speaker playback]
    end
    
    MAIN_INIT --> MAIN_START
    MAIN_START --> MM_THREAD
    MAIN_START --> HW_THREAD
    MAIN_START --> CW_THREAD
    MAIN_START --> MAIN_CONV
    MAIN_CONV --> WS_THREAD
    MAIN_CONV --> AUDIO_IN
    MAIN_CONV --> MAIN_WAIT
    MAIN_WAIT --> MAIN_CLEANUP
    
    WS_THREAD -.->|Audio chunks| AUDIO_OUT
    AUDIO_OUT -.->|Feed audio| HW_THREAD
    HW_THREAD -.->|Movement offsets| MM_THREAD
    
    STOP_POLL -.->|Stop signal| MAIN_WAIT
    
    classDef main fill:#e3f2fd,stroke:#1565c0
    classDef background fill:#fff8e1,stroke:#f9a825
    classDef sdk fill:#f3e5f5,stroke:#7b1fa2
    
    class MAIN_INIT,MAIN_START,MAIN_CONV,MAIN_WAIT,MAIN_CLEANUP main
    class MM_THREAD,HW_THREAD,CW_THREAD,AUDIO_IN,STOP_POLL background
    class WS_THREAD,AUDIO_OUT sdk
```

### Thread Responsibilities

| Thread | Module | Purpose |
|--------|--------|---------|
| Main | `main.py` | Initialization, conversation lifecycle, cleanup |
| MovementManager | `reachy_mini_conversation_app` | Executes robot movements, applies speech offsets |
| HeadWobbler | `head_wobbler.py` | Converts audio to head movement offsets |
| CameraWorker | `reachy_mini_conversation_app` | Captures camera frames for agent tools |
| Audio Input | `audio_interface.py` | Reads microphone, sends to ElevenLabs |
| Stop Poller | `main.py` | Monitors host stop event for graceful shutdown |
| WebSocket | ElevenLabs SDK | Manages cloud communication |

### Thread Synchronization

The app uses several synchronization mechanisms:

1. **HeadWobbler Generation Counter**: Prevents stale audio from affecting movements after interruption
2. **State Locks**: Protect shared state in HeadWobbler (`_state_lock`, `_sway_lock`)
3. **Stop Events**: `threading.Event` for coordinated shutdown
4. **Queue**: Thread-safe audio queue between audio interface and HeadWobbler

## Audio Dataflow

The audio pipeline handles bidirectional audio streaming:

```mermaid
sequenceDiagram
    participant MIC as 🎤 Microphone
    participant AI as ReachyAudioInterface
    participant WS as WebSocket
    participant AGENT as ElevenLabs Agent
    participant HW as HeadWobbler
    participant ST as SwayRollRT
    participant MM as MovementManager
    participant SPK as 🔊 Speaker
    participant HEAD as 🤖 Head Motors
    
    Note over MIC,HEAD: Voice Input Flow
    MIC->>AI: PCM audio (16kHz, 16-bit)
    AI->>WS: Audio chunks (250ms)
    WS->>AGENT: Stream to cloud
    
    Note over MIC,HEAD: Voice Output Flow
    AGENT->>WS: TTS audio response
    WS->>AI: output(audio bytes)
    AI->>HW: Base64 encoded audio
    AI->>SPK: Float32 audio samples
    
    Note over MIC,HEAD: Lip-Sync Animation
    HW->>ST: PCM audio chunks
    ST->>ST: VAD + envelope detection
    ST->>HW: Movement offsets (50ms hops)
    HW->>MM: (x, y, z, roll, pitch, yaw)
    MM->>HEAD: Motor commands
    
    Note over MIC,HEAD: Interruption Handling
    AGENT-->>AI: interrupt()
    AI-->>SPK: Clear output buffer
    AI-->>HW: reset()
    HW-->>ST: reset()
```

### Audio Format Specifications

| Stage | Format | Sample Rate | Notes |
|-------|--------|-------------|-------|
| Microphone Input | 16-bit PCM mono | 16 kHz | Robot hardware format |
| ElevenLabs Input | 16-bit PCM mono | 16 kHz | 250ms chunks (4000 samples) |
| ElevenLabs Output | 16-bit PCM mono | 16 kHz | Variable chunk sizes |
| Speaker Output | Float32 mono | 16 kHz | Converted from int16 |
| HeadWobbler Input | 16-bit PCM mono | 24 kHz | Resampled internally |
| SwayRollRT Output | Movement dict | 50ms hops | Per-hop sway values |

### Lip-Sync Animation Pipeline

The `SwayRollRT` class converts audio to natural head movements:

1. **Preprocessing**: Convert input to float32 mono, resample to 16kHz
2. **VAD (Voice Activity Detection)**: Detect speech using RMS dB thresholds
   - Attack: 40ms above -35 dB to activate
   - Release: 250ms below -45 dB to deactivate
3. **Envelope Following**: Smooth transitions with attack/release curves
4. **Loudness Mapping**: Map dB to [0,1] with gamma correction
5. **Oscillator Generation**: Generate sinusoidal movements for each axis:
   - Pitch: 2.2 Hz, ±4.5°
   - Yaw: 0.6 Hz, ±7.5°
   - Roll: 1.3 Hz, ±2.25°
   - X/Y/Z translation: 0.25-0.45 Hz, ±2.25-4.5mm

## Tool System

The agent can invoke tools to control the robot:

```mermaid
graph LR
    subgraph "ElevenLabs Agent"
        LLM[LLM Decision]
    end
    
    subgraph "Tool Registration"
        CT[ClientTools]
        REG[register_tools]
    end
    
    subgraph "Tool Handlers"
        CAM_TOOL[take_picture<br/>Camera capture]
        DANCE_TOOL[dance<br/>Movement sequences]
        EMO_TOOL[set_emotion<br/>Facial expressions]
    end
    
    subgraph "Dependencies"
        DEPS[ToolDependencies]
        RM[ReachyMini]
        MM[MovementManager]
        CW[CameraWorker]
        HW[HeadWobbler]
    end
    
    LLM -->|Tool call| CT
    CT --> CAM_TOOL
    CT --> DANCE_TOOL
    CT --> EMO_TOOL
    
    REG --> CT
    DEPS --> REG
    
    RM --> DEPS
    MM --> DEPS
    CW --> DEPS
    HW --> DEPS
    
    CAM_TOOL --> CW
    DANCE_TOOL --> MM
    EMO_TOOL --> MM
    
    classDef agent fill:#f3e5f5,stroke:#7b1fa2
    classDef tools fill:#fff3e0,stroke:#e65100
    classDef deps fill:#e8f5e9,stroke:#2e7d32
    
    class LLM agent
    class CT,REG,CAM_TOOL,DANCE_TOOL,EMO_TOOL tools
    class DEPS,RM,MM,CW,HW deps
```

### Available Tools

| Tool | Description | Parameters |
|------|-------------|------------|
| `take_picture` | Capture image from robot camera | None |
| `dance` | Execute predefined dance sequence | `dance_name: str` |
| `set_emotion` | Set robot facial expression | `emotion: str` |

## Configuration System

Configuration is managed through environment variables and the settings UI:

```mermaid
graph TB
    subgraph "Configuration Sources"
        ENV[Environment Variables]
        DOTENV[.env File]
        UI[Settings UI]
    end
    
    subgraph "Config Manager"
        CONFIG[config.py<br/>Config singleton]
        VALIDATE[validate]
        RELOAD[reload]
    end
    
    subgraph "Configuration Values"
        API_KEY[ELEVENLABS_API_KEY]
        AGENT_ID[ELEVENLABS_AGENT_ID]
    end
    
    ENV --> CONFIG
    DOTENV --> CONFIG
    UI -->|Save| DOTENV
    UI -->|Trigger| RELOAD
    
    CONFIG --> VALIDATE
    CONFIG --> API_KEY
    CONFIG --> AGENT_ID
    
    classDef source fill:#e3f2fd,stroke:#1565c0
    classDef config fill:#fff8e1,stroke:#f9a825
    classDef value fill:#e8f5e9,stroke:#2e7d32
    
    class ENV,DOTENV,UI source
    class CONFIG,VALIDATE,RELOAD config
    class API_KEY,AGENT_ID value
```

### Required Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `ELEVENLABS_AGENT_ID` | Yes | The ElevenLabs agent ID to connect to |
| `ELEVENLABS_API_KEY` | No* | API key for private agents |

*API key is required only for private agents; public agents can be accessed without authentication.

## Error Handling & Reconnection

The handler implements robust error handling with exponential backoff:

```mermaid
stateDiagram-v2
    [*] --> Starting
    Starting --> Connected: Success
    Starting --> Retrying: Connection Failed
    
    Retrying --> Connected: Success
    Retrying --> Failed: Max Attempts
    
    Connected --> SessionEnded: Normal End
    Connected --> Reconnecting: Unexpected End
    
    Reconnecting --> Connected: Success
    Reconnecting --> Failed: Max Attempts
    
    SessionEnded --> [*]: stop() called
    SessionEnded --> Reconnecting: Auto-restart
    
    Failed --> [*]
```

### Reconnection Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `max_reconnect_attempts` | 5 | Maximum retry attempts |
| `initial_backoff` | 1.0s | Initial wait time |
| `max_backoff` | 30.0s | Maximum wait time |
| `backoff_multiplier` | 2.0 | Exponential multiplier |

## Shutdown Sequence

Graceful shutdown ensures all resources are properly released:

```mermaid
sequenceDiagram
    participant HOST as Host System
    participant MAIN as Main Thread
    participant HANDLER as ElevenLabsHandler
    participant MM as MovementManager
    participant HW as HeadWobbler
    participant CW as CameraWorker
    participant ROBOT as ReachyMini
    
    HOST->>MAIN: Set stop_event
    MAIN->>HANDLER: stop()
    HANDLER->>HANDLER: End session
    
    MAIN->>MM: stop()
    MAIN->>HW: stop()
    MAIN->>CW: stop()
    
    MAIN->>ROBOT: media.close()
    MAIN->>ROBOT: client.disconnect()
    
    Note over MAIN: Wait 1s for cleanup
    MAIN->>HOST: Shutdown complete
```

## File Structure

```
src/reachy_mini_elevenlabs/
├── __init__.py              # Package exports
├── main.py                  # Entry point, ReachyMiniElevenLabsApp
├── config.py                # Configuration management
├── elevenlabs_handler.py    # Conversation lifecycle
├── audio_interface.py       # ReachyAudioInterface
├── settings_ui.py           # FastAPI settings routes
├── utils.py                 # Logging, argument parsing
├── audio/
│   ├── __init__.py
│   ├── head_wobbler.py      # HeadWobbler thread
│   ├── speech_tapper.py     # SwayRollRT audio analysis
│   └── utils.py             # Audio format conversion
├── tools/
│   ├── __init__.py
│   └── core_tools.py        # Tool registration & handlers
└── static/
    ├── index.html           # Settings UI page
    ├── main.js              # Settings UI logic
    └── style.css            # Settings UI styles
```