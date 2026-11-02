"""End-to-end client transport check against an isolated backend instance."""
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import pytest
from app.infrastructure.repositories.local_recovery import LocalRecovery
from tests.test_local_recovery import snapshot


def test_godot_reconnects_after_real_backend_restart(tmp_path):
    godot = Path("H:/Godot_v4.7-stable_win64.exe/Godot_v4.7-stable_win64_console.exe")
    if not godot.exists():
        pytest.skip("Local Godot executable unavailable")
    backend = Path(__file__).resolve().parents[1]
    recovery = tmp_path / "test-world.gz"
    marker = tmp_path / "client-ready"
    log = tmp_path / "godot.log"
    LocalRecovery(recovery).write_payload(snapshot(123).model_dump_json())
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    env = dict(os.environ, LOCAL_RECOVERY_ENABLED="true", LOCAL_RECOVERY_PATH=str(recovery))
    def start():
        return subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)], cwd=backend, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    def stop(process):
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(5)
    server = start()
    client = None
    try:
        client = subprocess.Popen([str(godot), "--headless", "--log-file", str(log), "--path", str(backend.parent / "client"), "--script", "res://tools/TestLiveReconnect.gd", "--", f"http://127.0.0.1:{port}", str(marker)], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        deadline = time.monotonic()+35
        while not marker.exists() and time.monotonic() < deadline:
            assert client.poll() is None, "Client exited before initial connection"
            time.sleep(.1)
        if not marker.exists():
            stop(client)
            output, _ = client.communicate(timeout=5)
            pytest.fail("No initial Godot connection: " + output + (log.read_text(errors="replace") if log.exists() else ""))
        stop(server)
        time.sleep(4)
        server = start()
        output, _ = client.communicate(timeout=40)
        assert client.returncode == 0, output
        assert "PASS: actual Godot" in output
    finally:
        stop(client)
        stop(server)
