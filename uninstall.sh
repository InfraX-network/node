#!/bin/bash

# uninstall script for the project

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
        error_exit "This run script does not support Windows. Please use a compatible Unix-like system." ;;
    *)
        error_exit "Unsupported OS detected" ;;
esac

# check if the Infrax service exists
check_service() {
    if [ "$(uname -s)" = "Linux" ]; then
        check_service_systemd
    elif [ "$(uname -s)" = "Darwin" ]; then
        check_service_launchd
    fi
}

# check if the Infrax service exists using systemd
check_service_systemd() {
    systemctl list-units --type=service | grep infrax || error_exit "Infrax service not found"
}

# check if the Infrax service exists using launchd
check_service_launchd() {
    launchctl list | grep local.infrax || error_exit "Infrax service not found"
}


# stop the service
stop_service() {
    if [ "$(uname -s)" = "Linux" ]; then
        stop_service_systemd
    elif [ "$(uname -s)" = "Darwin" ]; then
        stop_service_launchd
    fi
}

# uninstall the service
uninstall_service() {
    if [ "$(uname -s)" = "Linux" ]; then
        uninstall_service_systemd
    elif [ "$(uname -s)" = "Darwin" ]; then
        uninstall_service_launchd
    fi
}

# stop the Infrax service using systemd
stop_service_systemd() {
    systemctl stop infrax || error_exit "Failed to stop the Infrax service"
}

# stop the Infrax service using launchd
stop_service_launchd() {
    launchctl stop local.infrax || error_exit "Failed to stop the Infrax service"
}

# uninstall the Infrax service using systemd
uninstall_service_systemd() {
    systemctl disable infrax || error_exit "Failed to disable the Infrax service"
    systemctl stop infrax || error_exit "Failed to stop the Infrax service"
    systemctl daemon-reload || error_exit "Failed to reload the systemd daemon"
    systemctl reset-failed || error_exit "Failed to reset the failed systemd services"
    rm /etc/systemd/system/infrax.service || error_exit "Failed to remove the systemd service file"
}

# uninstall the Infrax service using launchd
uninstall_service_launchd() {
    launchctl unload local.infrax.plist || error_exit "Failed to unload the Infrax service"
    rm local.infrax.plist || error_exit "Failed to remove the launchd plist file"
}

# check if the user is root
if [ "$(id -u)" -ne 0 ]; then
    error_exit "This script must be run as root"
fi

# check if the Infrax service exists
check_service

# stop the service
stop_service

# uninstall the service
uninstall_service

echo -e "${GREEN}Uninstall complete${NC}"
