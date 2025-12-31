#!/usr/bin/env python3
import subprocess
import os
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve()
SCRIPT_DIR = SCRIPT_PATH.parent

REDIS_CONTAINER = "local-redis"
DRAGONFLY_CONTAINER = "local-dragonfly"
DOCKER_CONTAINERS = [REDIS_CONTAINER, DRAGONFLY_CONTAINER]

LOG_DIRS = [
    "/var/log/redis",
    "/var/log/dragonfly",
    str(SCRIPT_DIR / "logs")
]

PLACEHOLDER_FILES = [
    str(SCRIPT_DIR / "redis_dummy.bin"),
    str(SCRIPT_DIR / "dragonfly_dummy.bin")
]

def run_cmd(cmd, check=False):
    """Run a shell command and print output."""
    try:
        print(f"[RUN] {' '.join(cmd)}")
        subprocess.run(cmd, check=check)
    except subprocess.CalledProcessError as e:
        print(f"[ERROR] Command failed: {e}")

# -----------------------------
# Stop and remove containers, images, volumes
# -----------------------------
def cleanup_docker():
    print("=== Cleaning Docker containers, images, and volumes ===")
    # Stop and remove containers
    for c in DOCKER_CONTAINERS:
        run_cmd(["docker", "rm", "-f", c], check=False)
    # Remove images if they exist
    run_cmd(["docker", "rmi", "-f", "redis:7"], check=False)
    run_cmd(["docker", "rmi", "-f", "dragonflydb/dragonfly:v1.27.1"], check=False)
    # Remove dangling volumes
    run_cmd(["docker", "volume", "prune", "-f"], check=False)

# -----------------------------
# Stop Docker service (if exists)
# -----------------------------
def stop_docker_service():
    print("=== Stopping Docker service ===")
    run_cmd(["sudo", "systemctl", "stop", "docker"], check=False)

# -----------------------------
# Wipe logs and temp files
# -----------------------------
def wipe_logs():
    print("=== Wiping logs and temp files ===")
    for d in LOG_DIRS:
        if os.path.exists(d):
            run_cmd(["sudo", "rm", "-rf", d], check=False)
            print(f"[INFO] Removed {d}")
        else:
            print(f"[INFO] Log directory not found: {d}")

# -----------------------------
# Zero out placeholder files
# -----------------------------
def zero_out_files():
    print("=== Zeroing placeholder files ===")
    for f in PLACEHOLDER_FILES:
        run_cmd(["dd", "if=/dev/zero", f"of={f}", "bs=1M", "count=3"], check=False)
        run_cmd(["chmod", "600", f], check=False)
        print(f"[INFO] Zeroed file: {f}")

# -----------------------------
# Rollout / re-run autogen.sh
# -----------------------------
def rollout():
    print("=== Triggering auto-install / rollout ===")
    autogen = SCRIPT_DIR / "autogen.sh"
    if autogen.exists():
        run_cmd(["bash", str(autogen)], check=False)
    else:
        print(f"[ERROR] Auto-gen script not found: {autogen}")

# -----------------------------
# Main
# -----------------------------
def main():
    print("=== RedCarpet Full Cleanup & Rollout ===")
    cleanup_docker()
    stop_docker_service()
    wipe_logs()
    zero_out_files()
    rollout()
    print("=== RedCarpet Complete ✅ ===")

if __name__ == "__main__":
    main()
