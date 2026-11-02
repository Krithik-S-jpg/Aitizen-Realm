"""Real isolated backend process restart, never connects to the live backend."""
import os
import socket
import subprocess
import sys
import time
from pathlib import Path
import httpx
from app.infrastructure.repositories.local_recovery import LocalRecovery
from tests.test_local_recovery import snapshot


def test_process_restart_restores_same_paused_clock(tmp_path):
    path = tmp_path / "isolated-recovery.gz"
    LocalRecovery(path).write_payload(snapshot(123).model_dump_json())
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    environment = dict(os.environ, LOCAL_RECOVERY_ENABLED="true", LOCAL_RECOVERY_PATH=str(path))
    for _ in range(2):
        process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)], cwd=Path(__file__).resolve().parents[1], env=environment, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic()+30
            state = None
            with httpx.Client(trust_env=False, timeout=2) as client:
                while time.monotonic() < deadline:
                    assert process.poll() is None, "Isolated backend exited during startup"
                    try:
                        response = client.get(f"http://127.0.0.1:{port}/api/v1/simulation/state")
                        if response.status_code == 200:
                            state = response.json()
                            break
                    except httpx.TransportError:
                        pass
                    time.sleep(.1)
            assert state is not None, "Isolated backend startup timed out"
            assert state["current_tick"] == 123
            assert state["state"].upper() == "PAUSED"
            assert state["recovery"]["restored_tick"] == 123
        finally:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
