"""Settings UI for ElevenLabs configuration.

This module provides a minimal settings UI for configuring ElevenLabs
API key and Agent ID when running in headless mode. The UI is served
via the Reachy Mini Apps settings server.

The settings UI allows non-technical users to enter their ElevenLabs
credentials without needing to edit environment files directly.
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


def mount_settings_routes(
    app: "FastAPI",
    instance_path: str | None = None,
) -> None:
    """Mount settings UI routes on the FastAPI app.

    This function adds the following routes:
    - GET / : Serves the settings UI index.html
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

    # GET / -> index.html
    @app.get("/")
    def _root() -> FileResponse:
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
        return JSONResponse({
            "has_api_key": has_api_key,
            "has_agent_id": has_agent_id,
        })

    # POST /elevenlabs_config -> set API key and Agent ID
    @app.post("/elevenlabs_config")
    def _set_config(payload: ElevenLabsConfigPayload) -> JSONResponse:
        api_key = (payload.elevenlabs_api_key or "").strip()
        agent_id = (payload.elevenlabs_agent_id or "").strip()

        # Agent ID is required
        if not agent_id:
            return JSONResponse(
                {"ok": False, "error": "empty_agent_id"},
                status_code=400,
            )

        # API key is optional (only needed for private agents)
        persist_config(api_key, agent_id, instance_path)
        return JSONResponse({"ok": True})

    logger.info("Settings UI routes mounted")
