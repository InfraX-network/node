#!/bin/bash

# install script for the project

# colored log lines
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Function to print error messages and exit
error_exit() {
    echo -e "${RED}ERROR${NC}: $1" >&2
    exit 1
}

# Detect the operating system
OS="$(uname -s)"
case "${OS}" in
    Linux* | Darwin*) ;;
    MINGW* | MSYS* | WindowsNT) 
        error_exit "This installation script does not support Windows. Please use a compatible Unix-like system." ;;
    *)
        error_exit "Unsupported OS detected" ;;
esac

# Common functions for all platforms
create_venv_and_install_dependencies() {
    echo -e "${GREEN}-${NC} Creating a virtual environment and installing the dependencies${NC}"
    python3 -m venv .venv || error_exit "Failed to create virtual environment"
    source .venv/bin/activate || error_exit "Failed to activate the virtual environment"
    python3 -m pip install -r requirements.txt || error_exit "Failed to install dependencies"
}

read_configuration() {
    echo -e "${GREEN}-${NC} Reading configuration${NC}"
    host=$(grep 'local_ip' config.toml | cut -d'=' -f2 | tr -d ' "') || error_exit "Failed to read local_ip from config"
    port=$(grep 'local_port' config.toml | cut -d'=' -f2 | tr -d ' "') || error_exit "Failed to read port from config"
}

create_and_start_service() {
    if [ "$(uname -s)" = "Linux" ]; then
        create_service_file_systemd
        register_service_systemd
    elif [ "$(uname -s)" = "Darwin" ]; then
        create_service_file_launchd
        register_service_launchd
    fi
}

# Linux-specific functionality
create_service_file_systemd() {
    cat <<EOF > infrax.service
[Unit]
Description=InfraX Node service

[Service]
Type=simple
ExecStart=$(pwd)/.venv/bin/python3 -m uvicorn infrax_node.main:app --host ${host} --port ${port}
WorkingDirectory=$(pwd)
Restart=always

[Install]
WantedBy=multi-user.target
EOF
}

register_service_systemd() {
    echo -e "${GREEN}-${NC} Registering systemd service${NC}"
    sudo mv infrax.service /etc/systemd/system/ || error_exit "Failed to move the systemd service file"
    sudo systemctl start infrax || error_exit "Failed to start the systemd service"
    sudo systemctl enable infrax || error_exit "Failed to enable the systemd service at startup"
}

# macOS-specific functionality
create_service_file_launchd() {
    local plist_name="local.infrax.plist"
    cat <<EOF > ${plist_name}
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>local.infrax</string>
    <key>ProgramArguments</key>
    <array>
        <string>$(pwd)/.venv/bin/python3</string>
        <string>-m</string>
        <string>uvicorn</string>
        <string>infrax_node.main:app</string>
        <string>--host</string>
        <string>${host}</string>
        <string>--port</string>
        <string>${port}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$(pwd)</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
EOF
}

register_service_launchd() {
    echo -e "${GREEN}-${NC} Registering launchd service${NC}"
    local plist_name="local.infrax.plist"
    local plist_path="$HOME/Library/LaunchAgents/${plist_name}"
    mv ${plist_name} ${plist_path} || error_exit "Failed to move the launchd plist file"
    launchctl load ${plist_path} || error_exit "Failed to load the launchd plist"
}

# check if the user is root on Unix-like systems
if [ "$(id -u)" -ne 0 ] && [ "$(uname -s)" != "Darwin" ]; then
    error_exit "Please run as root"
fi

create_venv_and_install_dependencies
read_configuration
create_and_start_service

# Deactivate the virtual environment
deactivate

echo -e "${GREEN}-${NC} Installation complete${NC}"
