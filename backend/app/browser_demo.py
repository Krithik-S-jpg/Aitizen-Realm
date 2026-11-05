"""Opt-in same-origin browser demo; expose only through an authenticated tunnel.

Run from backend: python -m uvicorn app.browser_demo:app --host 127.0.0.1 --port 8000
The normal app.main entry point remains unchanged.
"""

from pathlib import Path

from starlette.staticfiles import StaticFiles

from app.main import app

BUILD_DIRECTORY = Path(__file__).resolve().parents[2] / ".local-build" / "web"
if not (BUILD_DIRECTORY / "index.html").is_file():
    raise RuntimeError("Export the Godot Web preset before starting the browser demo.")

app.mount("/game", StaticFiles(directory=BUILD_DIRECTORY, html=True), name="browser-game")
