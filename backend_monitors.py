#!/usr/bin/env python3
import os
import time
import redis
import subprocess
from pathlib import Path

# -----------------------------
# Env Variables
# -----------------------------
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379")
DRAGONFLY_URL = os.getenv("DRAGONFLY_URL", "redis://127.0.0.1:6380")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 10))  # seconds
SERVICE_NAME = "notecli-monitor.service"
SERVICE_PATH = f"/etc/systemd/system/{SERVICE_NAME}"
SCRIPT_PATH = os.path.realpath(__file__)
SCRIPT_DIR = Path(__file__).parent.resolve()
REDCARPET_SCRIPT = SCRIPT_DIR / "redcarpet.py"
DOCKER_SERVICE = os.getenv("DOCKER_SERVICE", "docker.service")

print(f"[INFO] Monitoring script path: {SCRIPT_PATH}")
print(f"[INFO] RedCarpet path: {REDCARPET_SCRIPT}")

# -----------------------------
# Backend check
# -----------------------------
def check_backend(name, url):
    try:
        r = redis.from_url(url, decode_responses=True)
        r.ping()
        print(f"[OK] {name} reachable at {url}")
        return True
    except Exception as e:
        print(f"[FAIL] {name} at {url}: {e}")
        return False

# -----------------------------
# Check if Docker service exists
# -----------------------------
def docker_service_exists():
    try:
        subprocess.run(
            ["systemctl", "status", DOCKER_SERVICE],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False

# -----------------------------
# Restart systemd service
# -----------------------------
def systemctl_restart(service):
    if service == DOCKER_SERVICE and not docker_service_exists():
        print(f"[SYSTEMD] Docker service '{DOCKER_SERVICE}' not found, skipping restart")
        return
    try:
        subprocess.run(["sudo", "systemctl", "restart", service], check=True)
        print(f"[SYSTEMD] Restarted {service}")
    except subprocess.CalledProcessError as e:
        print(f"[SYSTEMD] Failed to restart {service}: {e}")

# -----------------------------
# Trigger RedCarpet Rollup
# -----------------------------
def trigger_redcarpet():
    try:
        if not REDCARPET_SCRIPT.exists():
            print(f"[RedCarpet] Script not found: {REDCARPET_SCRIPT}")
            return
        print(f"[RedCarpet] Executing: {REDCARPET_SCRIPT}")
        subprocess.run(["sudo", "python3", str(REDCARPET_SCRIPT)], check=True)
        print("[RedCarpet] Rollup complete ✅")
    except subprocess.CalledProcessError as e:
        print(f"[RedCarpet] Rollup failed: {e}")

# -----------------------------
# Setup persistent systemd service
# -----------------------------
def setup_systemd_service():
    if os.path.exists(SERVICE_PATH):
        print(f"[SYSTEMD] Service already exists: {SERVICE_PATH}")
        return

    unit_content = f"""
[Unit]
Description=NoteCLI Backend Monitor
After=network.target {DOCKER_SERVICE}
Wants={DOCKER_SERVICE}

[Service]
Type=simple
ExecStart=/usr/bin/python3 {SCRIPT_PATH}
Restart=always
RestartSec=5
Environment="REDIS_URL={REDIS_URL}"
Environment="DRAGONFLY_URL={DRAGONFLY_URL}"
Environment="DOCKER_SERVICE={DOCKER_SERVICE}"

[Install]
WantedBy=multi-user.target
"""
    try:
        tmp_path = "/tmp/" + SERVICE_NAME
        with open(tmp_path, "w") as f:
            f.write(unit_content)
        subprocess.run(["sudo", "mv", tmp_path, SERVICE_PATH], check=True)
        subprocess.run(["sudo", "systemctl", "daemon-reload"], check=True)
        subprocess.run(["sudo", "systemctl", "enable", SERVICE_NAME], check=True)
        subprocess.run(["sudo", "systemctl", "start", SERVICE_NAME], check=True)
        print(f"[SYSTEMD] Service installed and started: {SERVICE_NAME}")
    except Exception as e:
        print(f"[SYSTEMD] Failed to setup service: {e}")

# -----------------------------
# Main monitoring loop
# -----------------------------
def main():
    print("=== Backend Monitoring Script ===")
    # Ensure service is installed first run
    setup_systemd_service()

    while True:
        redis_ok = check_backend("Redis", REDIS_URL)
        dragonfly_ok = check_backend("Dragonfly", DRAGONFLY_URL)

        # Failover & action logic
        if not redis_ok and dragonfly_ok:
            print("[INFO] Redis down, using Dragonfly as primary")
            systemctl_restart(DOCKER_SERVICE)
        elif not dragonfly_ok and redis_ok:
            print("[INFO] Dragonfly down, using Redis as primary")
            systemctl_restart(DOCKER_SERVICE)
        elif not redis_ok and not dragonfly_ok:
            print("[ERROR] Both backends are down! Triggering RedCarpet Rollup...")
            systemctl_restart(DOCKER_SERVICE)
            trigger_redcarpet()

        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()
