#!/bin/bash
# 
# prepare_system.sh
#
# System preparation script:
# 1. Check OS (Ubuntu) and root privileges.
# 2. Install Docker CE.
# 3. Install system utilities (btrfs, zfs, python).
# 4. Configure kernel modules.
# 5. Initialize Python venv and install Ansible.

set -euo pipefail

# --- Functions ---
# Print header
log_header() {
    echo ""
    echo "============================================================"
    echo "   $1"
    echo "============================================================"
    echo ""
}

# --- Configuration ---
# venv path can be passed as first argument
# ./prepare_system.sh /custom/path/to/venv
VENV_DIR="${1:-/opt/ansible_venv}"
MODULES_TO_LOAD=("btrfs" "zfs")
MODULES_FILE="/etc/modules-load.d/ansible-fs-prereqs.conf"

# --- Checks ---

if [ "$(id -u)" -ne 0 ]; then
    echo "Error: Script must be run with root privileges." >&2
    exit 1
fi

if [ -f /etc/os-release ]; then
    . /etc/os-release
    if [ "$ID" != "ubuntu" ]; then
        echo "Error: This script is designed for Ubuntu only. Current OS: $ID" >&2
        exit 1
    fi
else
    echo "Error: Unable to determine operating system." >&2
    exit 1
fi

# --- Package Installation ---

log_header "Updating package list..."
apt-get update

log_header "Installing dependencies..."
apt-get install -y ca-certificates curl gnupg

log_header "Setting up Docker repository..."
install -m 0755 -d /etc/apt/keyrings
if [ ! -f /etc/apt/keyrings/docker.gpg ]; then
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
fi

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  tee /etc/apt/sources.list.d/docker.list > /dev/null

log_header "Installing Docker and system tools..."
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin \
    btrfs-progs zfsutils-linux xfsprogs python3 python3-pip python3-venv

# --- Kernel Configuration ---

log_header "Configuring kernel modules..."
for module in "${MODULES_TO_LOAD[@]}"; do
    if ! lsmod | grep -q "^$module"; then
        echo "Loading module $module..."
        modprobe "$module"
    fi

    if ! grep -q "^$module$" "$MODULES_FILE" 2>/dev/null; then
        echo "$module" >> "$MODULES_FILE"
        echo "Added $module to autoload."
    fi
done

# --- Ansible Setup ---

log_header "Setting up virtual environment at $VENV_DIR..."
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
fi

VENV_PIP="$VENV_DIR/bin/pip"
VENV_GALAXY="$VENV_DIR/bin/ansible-galaxy"

log_header "Installing Ansible and collections..."
"$VENV_PIP" install --upgrade pip
"$VENV_PIP" install ansible requests docker

"$VENV_GALAXY" collection install ansible.posix
"$VENV_GALAXY" collection install community.general
"$VENV_GALAXY" collection install community.docker

# If running via sudo, change venv owner to actual user
if [ -n "${SUDO_USER:-}" ]; then
    log_header "Changing permissions..."
    chown -R "$SUDO_USER:$(id -g "$SUDO_USER")" "$VENV_DIR"
    echo "Changed ownership of $VENV_DIR to $SUDO_USER."
fi

log_header "Preparation complete."
echo "To activate the virtual environment, run: source $VENV_DIR/bin/activate"
echo ""
echo "NOTE: To change configuration parameters, modify the configs in the ./vars/ directory."
echo ""
echo "To run the tests, execute: ansible-playbook main.yaml -K"