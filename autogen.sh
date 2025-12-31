#!/bin/bash
set -e

# -----------------------------
# Header flags
# -----------------------------
VERBOSE=${VERBOSE:-1}      # 1=verbose, 0=quiet
MANUAL_MODE=${MANUAL_MODE:-0}  # 1=skip auto steps
NOIP_SERVICE=0 # NAT-IP

echo "=== Phase 2 Auto Installer: Bash Dual Backend ==="

# -----------------------------
# OS detection (Linux only, flavor detection)
# -----------------------------
OS=""
OS_FLAVOR=""
OS_VERSION=""
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS_FLAVOR=$ID
        OS_VERSION=$VERSION_ID
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
else
    echo "Unsupported OS: $OSTYPE"
    exit 1
fi
echo "Detected OS: $OS ($OS_FLAVOR $OS_VERSION)"

# -----------------------------
# Install prerequisites
# -----------------------------
echo "Installing prerequisites..."
if [ "$OS" = "linux" ]; then
    if command -v apt-get &>/dev/null; then
        sudo apt-get update
        sudo apt-get install -y \
            ca-certificates curl gnupg lsb-release linux-headers-$(uname -r) wget unzip software-properties-common || true
    elif command -v yum &>/dev/null; then
        sudo yum install -y epel-release
        sudo yum install -y wget curl gnupg lsb-release kernel-headers unzip || true
    elif command -v pacman &>/dev/null; then
        sudo pacman -Syu --noconfirm
        sudo pacman -S --noconfirm wget curl gnupg lsb-release linux-headers unzip || true
    fi
fi

# -----------------------------
# Docker installation (manual override for Kali)
# -----------------------------
if [ "$MANUAL_MODE" -eq 0 ]; then
    if ! command -v docker &>/dev/null; then
        echo "Docker not found. Attempting install..."
        # Kali/Debian workaround for GPG key
        TMP_KEY="/tmp/docker.gpg"
        curl -fsSL https://download.docker.com/linux/debian/gpg -o "$TMP_KEY" || true
        sudo mv "$TMP_KEY" /etc/apt/trusted.gpg.d/docker.gpg || true
        sudo apt-get update || true
        sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin || true
        sudo systemctl daemon-reload || true
        sudo systemctl enable docker || true
        sudo systemctl start docker || true
    fi
fi

# -----------------------------
# Pull & run Redis and Dragonfly containers
# -----------------------------
if [ "$MANUAL_MODE" -eq 0 ]; then
    echo "Setting up backend containers..."
    docker pull redis:7
    docker run -d --name local-redis -p 6379:6379 redis:7 || true

    # Dragonfly latest static version detection (simplified)
    DRAGONFLY_VER="v1.27.1"
    docker pull dragonflydb/dragonfly:$DRAGONFLY_VER
    docker run -d --name local-dragonfly -p 6380:6379 dragonflydb/dragonfly:$DRAGONFLY_VER || true
fi

# -----------------------------
# Configure environment
# -----------------------------
ENV_FILE="$HOME/.notecli_env"
echo "Setting environment variables in $ENV_FILE"
cat <<EOL > "$ENV_FILE"
export NOTE_BACKEND=dual
export REDIS_URL='redis://localhost:6379'
export DRAGONFLY_URL='redis://localhost:6380'
export UPSTASH_REDIS_URL='https://your-upstash-url'
export UPSTASH_REDIS_TOKEN='your-token'
EOL

if ! grep -q ".notecli_env" ~/.bashrc; then
    echo "source $ENV_FILE" >> ~/.bashrc
fi
source "$ENV_FILE"

# -----------------------------
# Crontab skeleton (OFF by default)
# -----------------------------
CRON_FILE="$HOME/.notecli_cron"
cat <<EOL > "$CRON_FILE"
# NOTE: Monitoring crontab OFF by default
# * * * * * /path/to/monitor_script.sh
EOL

# -----------------------------
# Post-installation verification
# -----------------------------
echo "=== Post-installation verification ==="
declare -a files=("$ENV_FILE" "$CRON_FILE")
for f in "${files[@]}"; do
    if [ -f "$f" ]; then
        echo "[✔] $f exists"
        tail -n 3 "$f"
    else
        echo "[✖] $f missing!"
    fi
done

# -----------------------------
# Systemd service status verbose
# -----------------------------
SERVICES=("docker")
for s in "${SERVICES[@]}"; do
    echo ">>> Status for service: $s"
    sudo systemctl status "$s" --no-pager || echo "No systemd unit found for $s"
done

# -----------------------------
# Local connectivity check (ping only)
# -----------------------------
echo ">>> Local connectivity check (ping only)"
ping -c 1 localhost &>/dev/null && echo "Ping to localhost OK ✅"

# -----------------------------
# Completion
# -----------------------------
echo "Crontab skeleton for monitoring installed (OFF by default) ✅"
echo "Ensure ports 6379 (Redis) and 6380 (Dragonfly) are NATed for remote access."
echo "You can run the CLI using: python notecli_v4.py"
echo "=== Auto-installation complete! ✅ ==="

# -----------------------------
# Configure environment
# -----------------------------
ENV_FILE="$HOME/.notecli_env"
echo "Setting environment variables in $ENV_FILE"
cat <<EOL > "$ENV_FILE"
export NOTE_BACKEND=dual
export REDIS_URL='redis://localhost:6379'
export DRAGONFLY_URL='redis://localhost:6380'
export UPSTASH_REDIS_URL='https://your-upstash-url'
export UPSTASH_REDIS_TOKEN='your-token'
EOL

# Export variables for current session immediately
export NOTE_BACKEND=dual
export REDIS_URL='redis://localhost:6379'
export DRAGONFLY_URL='redis://localhost:6380'
export UPSTASH_REDIS_URL='https://your-upstash-url'
export UPSTASH_REDIS_TOKEN='your-token'

# Ensure .notecli_env is sourced on new shells
if ! grep -q ".notecli_env" ~/.bashrc; then
    echo "source $ENV_FILE" >> ~/.bashrc
fi
source "$ENV_FILE"
