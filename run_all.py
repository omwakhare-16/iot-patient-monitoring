"""One command to run the whole system:  python run_all.py
Starts: MQTT broker, cloud backend, device simulator and the dashboard."""
import os
import subprocess
import sys
import time

PY = sys.executable
HERE = os.path.dirname(os.path.abspath(__file__))
USE_LOCAL_BROKER = os.getenv("MQTT_HOST", "127.0.0.1") in ("127.0.0.1", "localhost")

procs = []


def start(name, cmd):
    p = subprocess.Popen(cmd, cwd=HERE)
    procs.append((name, p))
    return p


try:
    if USE_LOCAL_BROKER:
        start("broker", [PY, "broker.py"])
        time.sleep(2)
    start("backend", [PY, "backend.py"])
    time.sleep(1)
    start("simulator", [PY, "simulator.py"])
    start("dashboard", [PY, "-m", "streamlit", "run", "dashboard.py",
                        "--server.headless", "true", "--browser.gatherUsageStats", "false"])
    print("\n  Dashboard: http://localhost:8501   (press Ctrl+C to stop everything)\n", flush=True)
    while True:
        time.sleep(1)
        for name, p in procs:
            if p.poll() is not None:
                print(f"[run_all] {name} exited with code {p.returncode}", flush=True)
                raise KeyboardInterrupt
except KeyboardInterrupt:
    pass
finally:
    for name, p in procs:
        if p.poll() is None:
            p.terminate()
    for name, p in procs:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()
    print("[run_all] stopped.")
