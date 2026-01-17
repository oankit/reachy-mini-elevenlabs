# Running Locally

This guide explains how to run the `reachy_mini_elevenlabs` app locally for development and testing.

## Prerequisites

### System Requirements

- **Operating System**: Windows 10/11, Linux, or macOS
- **Python**: 3.10 or higher
- **Hardware**: Reachy Mini robot (or simulator for testing)

### Required Software

1. **Python 3.10+**
   - Windows: Download from [python.org](https://www.python.org/downloads/)
   - Linux: `sudo apt install python3.10 python3.10-venv`
   - macOS: `brew install python@3.10`

2. **uv** (recommended) or pip
   - Install uv: `pip install uv`
   - Or use pip that comes with Python

## Installation

### 1. Clone or Navigate to Repository

```bash
cd reachy_mini_elevenlabs
```

### 2. Create Virtual Environment

Using uv (recommended):
```bash
uv venv
```

Using standard Python:
```bash
python -m venv .venv
```

### 3. Activate Virtual Environment

**Windows (PowerShell):**
```powershell
.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
.venv\Scripts\activate.bat
```

**Linux/macOS:**
```bash
source .venv/bin/activate
```

### 4. Install Dependencies

Using uv:
```bash
uv pip install -e .
```

Using pip:
```bash
pip install -e .
```

For development (includes testing tools):
```bash
uv pip install -e ".[dev]"
# or
pip install -e ".[dev]"
```

## Configuration

### 1. Create Environment File

Copy the example environment file:

```bash
cp .env.example .env
```

### 2. Configure ElevenLabs Credentials

Edit `.env` and add your credentials:

```env
ELEVENLABS_API_KEY=your_api_key_here
ELEVENLABS_AGENT_ID=your_agent_id_here
```

**Getting Your Credentials:**

1. **API Key** (for private agents):
   - Go to [ElevenLabs Dashboard](https://elevenlabs.io/app/settings/api-keys)
   - Create or copy your API key
   - Note: Public agents don't require an API key

2. **Agent ID**:
   - Go to [ElevenLabs Conversational AI](https://elevenlabs.io/app/conversational-ai)
   - Select or create an agent
   - Copy the Agent ID from the agent settings

### 3. Configure Robot Connection (Optional)

If connecting to a specific robot by name:

```env
ROBOT_NAME=my_reachy_mini
```

## Running the App

### Standard Run

```bash
reachy-mini-elevenlabs
```

### With Debug Logging

```bash
reachy-mini-elevenlabs --debug
```

### Specify Robot Name

```bash
reachy-mini-elevenlabs --robot-name my_reachy_mini
```

### Disable Camera

```bash
reachy-mini-elevenlabs --no-camera
```

### All Options

```bash
reachy-mini-elevenlabs --help
```

## Running on Windows

### PowerShell Execution Policy

If you encounter execution policy errors when activating the virtual environment:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Windows-Specific Notes

1. **Audio Drivers**: Ensure your audio drivers are up to date
2. **Firewall**: Allow Python through Windows Firewall for WebSocket connections
3. **Antivirus**: Some antivirus software may block WebSocket connections

### Troubleshooting Windows Issues

**Issue: "python not found"**
```powershell
# Add Python to PATH or use full path
C:\Users\YourName\AppData\Local\Programs\Python\Python310\python.exe -m venv .venv
```

**Issue: WebSocket connection fails**
- Check Windows Firewall settings
- Verify internet connectivity
- Try disabling VPN temporarily

## Development Workflow

### Running Tests

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=reachy_mini_elevenlabs --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_audio_interface.py
```

Run with verbose output:
```bash
pytest -v
```

### Code Quality

Format code:
```bash
ruff format .
```

Lint code:
```bash
ruff check .
```

Fix linting issues automatically:
```bash
ruff check --fix .
```

Type checking:
```bash
mypy src/reachy_mini_elevenlabs
```

### Hot Reload Development

For rapid development, you can run the app with auto-reload on code changes:

```bash
# Install watchdog
pip install watchdog

# Run with auto-reload (custom script needed)
python -m watchdog.watchmedo auto-restart --patterns="*.py" --recursive -- reachy-mini-elevenlabs
```

## Troubleshooting

### Connection Issues

**Problem: "Failed to connect to Reachy Mini daemon"**

Solutions:
1. Verify robot is powered on and connected to network
2. Check robot IP address: `ping <robot-ip>`
3. Verify robot daemon is running on the robot
4. Try specifying robot name: `--robot-name <name>`

**Problem: "WebSocket connection failed"**

Solutions:
1. Check internet connectivity
2. Verify ElevenLabs API key is valid
3. Check firewall settings
4. Verify agent ID is correct

### Configuration Issues

**Problem: "Missing required configuration"**

Solutions:
1. Verify `.env` file exists in the correct location
2. Check that `ELEVENLABS_AGENT_ID` is set
3. For private agents, ensure `ELEVENLABS_API_KEY` is set
4. Reload environment: `source .env` (Linux/macOS) or restart terminal

### Audio Issues

**Problem: No audio input/output**

Solutions:
1. Check robot microphone and speaker are working
2. Verify audio permissions on your system
3. Test with `--debug` flag to see audio-related logs
4. Check robot media system status

### Import Errors

**Problem: "ModuleNotFoundError"**

Solutions:
1. Ensure virtual environment is activated
2. Reinstall package: `pip install -e .`
3. Check Python version: `python --version` (must be 3.10+)
4. Clear Python cache: `find . -type d -name __pycache__ -exec rm -r {} +`

## Performance Tips

1. **Reduce Latency**: Use wired network connection for robot
2. **Optimize Audio**: Ensure robot is on same network segment
3. **Debug Mode**: Only use `--debug` when troubleshooting (increases logging overhead)
4. **Camera**: Use `--no-camera` if camera tools aren't needed

## Logs and Debugging

### Log Locations

Logs are printed to console. To save logs to file:

```bash
reachy-mini-elevenlabs --debug 2>&1 | tee app.log
```

### Debug Mode

Enable verbose logging:

```bash
reachy-mini-elevenlabs --debug
```

This shows:
- WebSocket connection details
- Audio chunk processing
- Tool invocations
- HeadWobbler state changes
- Configuration loading

### Common Log Messages

| Message | Meaning | Action |
|---------|---------|--------|
| "Starting Reachy Mini ElevenLabs App" | App starting | Normal |
| "Missing configuration" | Config not set | Check `.env` file |
| "WebSocket connection failure" | Can't reach ElevenLabs | Check network/credentials |
| "Conversation ended with ID" | Session ended normally | Normal |
| "Attempting session restart" | Reconnecting after error | Wait for reconnection |

## Next Steps

- See [INTEGRATE_WITH_HOST.md](INTEGRATE_WITH_HOST.md) for deploying to Reachy Mini Control
- See [ARCHITECTURE.md](ARCHITECTURE.md) for understanding the system design
- See [REPO_MAP.md](REPO_MAP.md) for navigating the codebase
