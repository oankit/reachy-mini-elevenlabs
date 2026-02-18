"""Settings UI for ElevenLabs configuration.

This module provides a minimal settings UI for configuring ElevenLabs
API key and Agent ID when running in headless mode. The UI is served
via the Reachy Mini Apps settings server.

The settings UI allows non-technical users to enter their ElevenLabs
credentials without needing to edit environment files directly.

Get your ElevenLabs agent at: https://try.elevenlabs.io/reachy-mini-agents
"""

from __future__ import annotations
import os
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from reachy_mini_elevenlabs.config import config

if TYPE_CHECKING:
    from fastapi import FastAPI

try:
    # FastAPI is provided by the Reachy Mini Apps runtime
    from fastapi import Response
    from pydantic import BaseModel
    from fastapi.responses import FileResponse, JSONResponse
    from starlette.staticfiles import StaticFiles
except Exception:  # pragma: no cover - only loaded when settings_app is used
    Response = object  # type: ignore
    FileResponse = object  # type: ignore
    JSONResponse = object  # type: ignore
    StaticFiles = object  # type: ignore
    BaseModel = object  # type: ignore


logger = logging.getLogger(__name__)


class ElevenLabsConfigPayload(BaseModel):
    """Payload for ElevenLabs configuration endpoint."""

    elevenlabs_api_key: str
    elevenlabs_agent_id: str


class EmotionConfigPayload(BaseModel):
    """Payload for emotion detection configuration endpoint."""

    enable_emotion_detection: bool
    enable_idle_emotions: bool
    emotion_confidence_threshold: float
    emotion_cooldown_seconds: float
    idle_emotion_min_delay: float
    idle_emotion_max_delay: float


def _read_env_lines(env_path: Path) -> list[str]:
    """Load env file contents or a template as a list of lines.

    Args:
        env_path: Path to the .env file.

    Returns:
        List of lines from the .env file or template.

    """
    inst = env_path.parent
    try:
        if env_path.exists():
            try:
                return env_path.read_text(encoding="utf-8").splitlines()
            except Exception:
                return []

        # Try to find a template
        template_text = None

        # Check instance directory for .env.example
        ex = inst / ".env.example"
        if ex.exists():
            try:
                template_text = ex.read_text(encoding="utf-8")
            except Exception:
                template_text = None

        # Check current working directory
        if template_text is None:
            try:
                cwd_example = Path.cwd() / ".env.example"
                if cwd_example.exists():
                    template_text = cwd_example.read_text(encoding="utf-8")
            except Exception:
                template_text = None

        # Check packaged template
        if template_text is None:
            packaged = Path(__file__).parent / ".env.example"
            if packaged.exists():
                try:
                    template_text = packaged.read_text(encoding="utf-8")
                except Exception:
                    template_text = None

        return template_text.splitlines() if template_text else []
    except Exception:
        return []


def persist_config(
    api_key: str,
    agent_id: str,
    instance_path: str | None,
) -> None:
    """Persist ElevenLabs configuration to environment and instance .env file.

    This function:
    - Sets environment variables in the current process
    - Updates the in-memory config object
    - Writes/updates the instance .env file

    Args:
        api_key: The ElevenLabs API key.
        agent_id: The ElevenLabs Agent ID.
        instance_path: Path to the instance directory for .env file.

    """
    api_key = (api_key or "").strip()
    agent_id = (agent_id or "").strip()

    # Update live process env and config
    if api_key:
        try:
            os.environ["ELEVENLABS_API_KEY"] = api_key
        except Exception:
            pass
        try:
            config.ELEVENLABS_API_KEY = api_key
        except Exception:
            pass

    if agent_id:
        try:
            os.environ["ELEVENLABS_AGENT_ID"] = agent_id
        except Exception:
            pass
        try:
            config.ELEVENLABS_AGENT_ID = agent_id
        except Exception:
            pass

    if not instance_path:
        return

    try:
        inst = Path(instance_path)
        env_path = inst / ".env"
        lines = _read_env_lines(env_path)

        # Track which variables we've replaced
        replaced_api_key = False
        replaced_agent_id = False

        for i, ln in enumerate(lines):
            stripped = ln.strip()
            if stripped.startswith("ELEVENLABS_API_KEY=") and api_key:
                lines[i] = f"ELEVENLABS_API_KEY={api_key}"
                replaced_api_key = True
            elif stripped.startswith("ELEVENLABS_AGENT_ID=") and agent_id:
                lines[i] = f"ELEVENLABS_AGENT_ID={agent_id}"
                replaced_agent_id = True

        # Append any values that weren't replaced
        if api_key and not replaced_api_key:
            lines.append(f"ELEVENLABS_API_KEY={api_key}")
        if agent_id and not replaced_agent_id:
            lines.append(f"ELEVENLABS_AGENT_ID={agent_id}")

        final_text = "\n".join(lines) + "\n"
        env_path.write_text(final_text, encoding="utf-8")
        logger.info("Persisted ElevenLabs configuration to %s", env_path)

        # Reload the .env into this process
        try:
            from dotenv import load_dotenv

            load_dotenv(dotenv_path=str(env_path), override=True)
        except Exception:
            pass

    except Exception as e:
        logger.warning("Failed to persist ElevenLabs configuration: %s", e)


def persist_emotion_config(
    enable_emotion_detection: bool,
    enable_idle_emotions: bool,
    emotion_confidence_threshold: float,
    emotion_cooldown_seconds: float,
    idle_emotion_min_delay: float,
    idle_emotion_max_delay: float,
    instance_path: str | None,
) -> None:
    """Persist emotion detection configuration to environment and instance .env file.

    Args:
        enable_emotion_detection: Whether emotion detection is enabled.
        enable_idle_emotions: Whether idle emotions are enabled.
        emotion_confidence_threshold: Minimum confidence threshold (0-1).
        emotion_cooldown_seconds: Cooldown between emotion actions.
        idle_emotion_min_delay: Minimum delay between idle emotions.
        idle_emotion_max_delay: Maximum delay between idle emotions.
        instance_path: Path to the instance directory for .env file.

    """
    # Update live process env and config
    try:
        os.environ["ENABLE_EMOTION_DETECTION"] = str(enable_emotion_detection).lower()
        config.ENABLE_EMOTION_DETECTION = enable_emotion_detection
    except Exception:
        pass

    try:
        os.environ["ENABLE_IDLE_EMOTIONS"] = str(enable_idle_emotions).lower()
        config.ENABLE_IDLE_EMOTIONS = enable_idle_emotions
    except Exception:
        pass

    try:
        os.environ["EMOTION_CONFIDENCE_THRESHOLD"] = str(emotion_confidence_threshold)
        config.EMOTION_CONFIDENCE_THRESHOLD = emotion_confidence_threshold
    except Exception:
        pass

    try:
        os.environ["EMOTION_COOLDOWN_SECONDS"] = str(emotion_cooldown_seconds)
        config.EMOTION_COOLDOWN_SECONDS = emotion_cooldown_seconds
    except Exception:
        pass

    try:
        os.environ["IDLE_EMOTION_MIN_DELAY"] = str(idle_emotion_min_delay)
        config.IDLE_EMOTION_MIN_DELAY = idle_emotion_min_delay
    except Exception:
        pass

    try:
        os.environ["IDLE_EMOTION_MAX_DELAY"] = str(idle_emotion_max_delay)
        config.IDLE_EMOTION_MAX_DELAY = idle_emotion_max_delay
    except Exception:
        pass

    if not instance_path:
        return

    try:
        inst = Path(instance_path)
        env_path = inst / ".env"
        lines = _read_env_lines(env_path)

        # Track which variables we've replaced
        replaced = {
            "ENABLE_EMOTION_DETECTION": False,
            "ENABLE_IDLE_EMOTIONS": False,
            "EMOTION_CONFIDENCE_THRESHOLD": False,
            "EMOTION_COOLDOWN_SECONDS": False,
            "IDLE_EMOTION_MIN_DELAY": False,
            "IDLE_EMOTION_MAX_DELAY": False,
        }

        for i, ln in enumerate(lines):
            stripped = ln.strip()
            if stripped.startswith("ENABLE_EMOTION_DETECTION="):
                lines[i] = f"ENABLE_EMOTION_DETECTION={str(enable_emotion_detection).lower()}"
                replaced["ENABLE_EMOTION_DETECTION"] = True
            elif stripped.startswith("ENABLE_IDLE_EMOTIONS="):
                lines[i] = f"ENABLE_IDLE_EMOTIONS={str(enable_idle_emotions).lower()}"
                replaced["ENABLE_IDLE_EMOTIONS"] = True
            elif stripped.startswith("EMOTION_CONFIDENCE_THRESHOLD="):
                lines[i] = f"EMOTION_CONFIDENCE_THRESHOLD={emotion_confidence_threshold}"
                replaced["EMOTION_CONFIDENCE_THRESHOLD"] = True
            elif stripped.startswith("EMOTION_COOLDOWN_SECONDS="):
                lines[i] = f"EMOTION_COOLDOWN_SECONDS={emotion_cooldown_seconds}"
                replaced["EMOTION_COOLDOWN_SECONDS"] = True
            elif stripped.startswith("IDLE_EMOTION_MIN_DELAY="):
                lines[i] = f"IDLE_EMOTION_MIN_DELAY={idle_emotion_min_delay}"
                replaced["IDLE_EMOTION_MIN_DELAY"] = True
            elif stripped.startswith("IDLE_EMOTION_MAX_DELAY="):
                lines[i] = f"IDLE_EMOTION_MAX_DELAY={idle_emotion_max_delay}"
                replaced["IDLE_EMOTION_MAX_DELAY"] = True

        # Append any values that weren't replaced
        if not replaced["ENABLE_EMOTION_DETECTION"]:
            lines.append(f"ENABLE_EMOTION_DETECTION={str(enable_emotion_detection).lower()}")
        if not replaced["ENABLE_IDLE_EMOTIONS"]:
            lines.append(f"ENABLE_IDLE_EMOTIONS={str(enable_idle_emotions).lower()}")
        if not replaced["EMOTION_CONFIDENCE_THRESHOLD"]:
            lines.append(f"EMOTION_CONFIDENCE_THRESHOLD={emotion_confidence_threshold}")
        if not replaced["EMOTION_COOLDOWN_SECONDS"]:
            lines.append(f"EMOTION_COOLDOWN_SECONDS={emotion_cooldown_seconds}")
        if not replaced["IDLE_EMOTION_MIN_DELAY"]:
            lines.append(f"IDLE_EMOTION_MIN_DELAY={idle_emotion_min_delay}")
        if not replaced["IDLE_EMOTION_MAX_DELAY"]:
            lines.append(f"IDLE_EMOTION_MAX_DELAY={idle_emotion_max_delay}")

        final_text = "\n".join(lines) + "\n"
        env_path.write_text(final_text, encoding="utf-8")
        logger.info("Persisted emotion configuration to %s", env_path)

        # Reload the .env into this process
        try:
            from dotenv import load_dotenv

            load_dotenv(dotenv_path=str(env_path), override=True)
        except Exception:
            pass

    except Exception as e:
        logger.warning("Failed to persist emotion configuration: %s", e)


def mount_settings_routes(
    app: "FastAPI",
    instance_path: str | None = None,
) -> None:
    """Mount settings UI routes on the FastAPI app.

    This function adds the following routes:
    - GET / : Serves the settings UI via Gradio (for Control App "Open" button)
    - GET /settings : Serves the settings UI index.html directly
    - GET /static/* : Serves static assets (CSS, JS)
    - GET /favicon.ico : Returns 204 to avoid 404 noise
    - GET /status : Returns configuration status
    - POST /elevenlabs_config : Sets API key and Agent ID

    Args:
        app: The FastAPI application to mount routes on.
        instance_path: Path to instance directory for .env persistence.

    """
    static_dir = Path(__file__).parent / "static"
    index_file = static_dir / "index.html"

    # Mount static files
    if hasattr(app, "mount"):
        try:
            app.mount(
                "/static",
                StaticFiles(directory=str(static_dir)),
                name="elevenlabs-static",
            )
        except Exception as e:
            logger.warning("Failed to mount static files: %s", e)

    # Create a minimal Gradio interface for Control App integration
    try:
        import gradio as gr
        from starlette.responses import RedirectResponse

        # Create a simple Gradio interface that redirects to settings
        with gr.Blocks(title="Reachy Mini ElevenLabs Settings") as gradio_ui:
            gr.Markdown("""
            # Reachy Mini ElevenLabs Settings
            
            Configure your ElevenLabs API credentials and emotion detection settings.
            
            **Get your ElevenLabs agent at:** [https://try.elevenlabs.io/reachy-mini-agents](https://try.elevenlabs.io/reachy-mini-agents)
            """)
            
            with gr.Row():
                gr.HTML("""
                <div style="text-align: center; padding: 20px;">
                    <a href="/settings" target="_blank" style="
                        display: inline-block;
                        padding: 12px 24px;
                        background: #000;
                        color: #fff;
                        text-decoration: none;
                        border-radius: 6px;
                        font-weight: 500;
                    ">Open Settings Panel →</a>
                </div>
                """)

        # Mount Gradio at /ui so FastAPI routes at /status and /elevenlabs_config
        # are not intercepted by Gradio's catch-all ASGI handler.
        gr.mount_gradio_app(app, gradio_ui, path="/ui")
        logger.info("Gradio interface mounted at /ui")

        # GET / -> redirect to /ui so the Control App "Open" button still works
        @app.get("/")
        def _root():  # type: ignore[return]
            return RedirectResponse(url="/ui")

    except ImportError:
        logger.warning("Gradio not available, using fallback HTML interface")

        # Fallback: GET / -> index.html
        @app.get("/")
        def _root() -> FileResponse:
            return FileResponse(str(index_file))

    # GET /settings -> index.html (direct access to settings UI)
    @app.get("/settings")
    def _settings() -> FileResponse:
        return FileResponse(str(index_file))

    # GET /favicon.ico -> 204 to avoid noisy 404s
    @app.get("/favicon.ico")
    def _favicon() -> Response:
        return Response(status_code=204)

    # GET /status -> configuration status
    @app.get("/status")
    def _status() -> JSONResponse:
        has_api_key = bool(
            config.ELEVENLABS_API_KEY and str(config.ELEVENLABS_API_KEY).strip()
        )
        has_agent_id = bool(
            config.ELEVENLABS_AGENT_ID and str(config.ELEVENLABS_AGENT_ID).strip()
        )
        
        # Return masked API key (last 5 chars) and full agent_id for display
        api_key_display = ""
        if has_api_key:
            full_key = str(config.ELEVENLABS_API_KEY).strip()
            if len(full_key) > 5:
                api_key_display = "..." + full_key[-5:]
            else:
                api_key_display = full_key
        
        agent_id_display = ""
        if has_agent_id:
            agent_id_display = str(config.ELEVENLABS_AGENT_ID).strip()
        
        return JSONResponse({
            "has_api_key": has_api_key,
            "has_agent_id": has_agent_id,
            "api_key_display": api_key_display,
            "agent_id_display": agent_id_display,
            "enable_emotion_detection": config.ENABLE_EMOTION_DETECTION,
            "enable_idle_emotions": config.ENABLE_IDLE_EMOTIONS,
            "emotion_confidence_threshold": config.EMOTION_CONFIDENCE_THRESHOLD,
            "emotion_cooldown_seconds": config.EMOTION_COOLDOWN_SECONDS,
            "idle_emotion_min_delay": config.IDLE_EMOTION_MIN_DELAY,
            "idle_emotion_max_delay": config.IDLE_EMOTION_MAX_DELAY,
        })

    # POST /elevenlabs_config -> set API key and Agent ID
    @app.post("/elevenlabs_config")
    def _set_config(payload: ElevenLabsConfigPayload) -> JSONResponse:
        api_key = (payload.elevenlabs_api_key or "").strip()
        agent_id = (payload.elevenlabs_agent_id or "").strip()

        # At least one field must be provided
        if not api_key and not agent_id:
            return JSONResponse(
                {"ok": False, "error": "no_fields_provided"},
                status_code=400,
            )

        # If only API key is provided, keep existing agent_id
        if api_key and not agent_id:
            agent_id = str(config.ELEVENLABS_AGENT_ID or "").strip()
            if not agent_id:
                return JSONResponse(
                    {"ok": False, "error": "agent_id_required_for_initial_setup"},
                    status_code=400,
                )

        # If only agent_id is provided, keep existing API key
        if agent_id and not api_key:
            api_key = str(config.ELEVENLABS_API_KEY or "").strip()

        # API key is optional (only needed for private agents)
        persist_config(api_key, agent_id, instance_path)
        return JSONResponse({"ok": True})

    # POST /emotion_config -> set emotion detection settings
    @app.post("/emotion_config")
    def _set_emotion_config(payload: EmotionConfigPayload) -> JSONResponse:
        # Validate ranges
        if not (0.0 <= payload.emotion_confidence_threshold <= 1.0):
            return JSONResponse(
                {"ok": False, "error": "confidence_threshold_out_of_range"},
                status_code=400,
            )
        if payload.emotion_cooldown_seconds < 0:
            return JSONResponse(
                {"ok": False, "error": "cooldown_negative"},
                status_code=400,
            )
        if payload.idle_emotion_min_delay < 0 or payload.idle_emotion_max_delay < 0:
            return JSONResponse(
                {"ok": False, "error": "idle_delay_negative"},
                status_code=400,
            )
        if payload.idle_emotion_min_delay > payload.idle_emotion_max_delay:
            return JSONResponse(
                {"ok": False, "error": "idle_delay_invalid_range"},
                status_code=400,
            )

        persist_emotion_config(
            payload.enable_emotion_detection,
            payload.enable_idle_emotions,
            payload.emotion_confidence_threshold,
            payload.emotion_cooldown_seconds,
            payload.idle_emotion_min_delay,
            payload.idle_emotion_max_delay,
            instance_path,
        )
        return JSONResponse({"ok": True})

    logger.info("Settings UI routes mounted")
