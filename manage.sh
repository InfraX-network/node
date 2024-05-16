#!/bin/bash

# manage script for the project

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

# start the Infrax service
start_service() {
    check_service
    if [ "$(uname -s)" = "Linux" ]; then
        start_service_systemd
    elif [ "$(uname -s)" = "Darwin" ]; then
        start_service_launchd
    fi
}

# stop the Infrax service
stop_service() {
    check_service
    if [ "$(uname -s)" = "Linux" ]; then
        stop_service_systemd
    elif [ "$(uname -s)" = "Darwin" ]; then
        stop_service_launchd
    fi
}

# restart the Infrax service
restart_service() {
    check_service
    if [ "$(uname -s)" = "Linux" ]; then
        restart_service_systemd
    elif [ "$(uname -s)" = "Darwin" ]; then
        restart_service_launchd
    fi
}

# check the status of the Infrax service
status_service() {
    check_service
    if [ "$(uname -s)" = "Linux" ]; then
        status_service_systemd
    elif [ "$(uname -s)" = "Darwin" ]; then
        status_service_launchd
    fi
}

start_service_systemd() {
    # start the Infrax service using systemd
    sudo systemctl start infrax || error_exit "Failed to start the Infrax service"
}

start_service_launchd() {
    # start the Infrax service using launchd
    launchctl load local.infrax.plist || error_exit "Failed to start the Infrax service"
}

stop_service_systemd() {
    # stop the Infrax service using systemd
    sudo systemctl stop infrax || error_exit "Failed to stop the Infrax service"
}

stop_service_launchd() {
    # stop the Infrax service using launchd
    launchctl unload local.infrax.plist || error_exit "Failed to stop the Infrax service"
}

restart_service_systemd() {
    # restart the Infrax service using systemd
    sudo systemctl restart infrax || error_exit "Failed to restart the Infrax service"
}

restart_service_launchd() {
    # restart the Infrax service using launchd
    launchctl unload local.infrax.plist || error_exit "Failed to stop the Infrax service"
    launchctl load local.infrax.plist || error_exit "Failed to start the Infrax service"
}

status_service_systemd() {
    check_service
    # check the status of the Infrax service using systemd
    sudo systemctl status infrax || error_exit "Failed to get the status of the Infrax service"
}

status_service_launchd() {
    check_service
    # check the status of the Infrax service using launchd
    launchctl list | grep local.infrax || error_exit "Failed to get the status of the Infrax service"
}

# display the help message
help_message() {
    echo "Manage script for the Infrax project"
    echo ""
    echo "Usage: $0 {start|stop|restart|status|update|help}"
    echo ""
    echo "Commands:"
    echo "  start   - Start the Infrax service"
    echo "  stop    - Stop the Infrax service"
    echo "  restart - Restart the Infrax service"
    echo "  status  - Check the status of the Infrax service"
    echo "  update  - Update the repository and restart the Infrax service"
    echo "  help    - Display this help message"
}

# check if the user is root
if [ "$(id -u)" -ne 0 ]; then
    error_exit "This script must be run as root"
fi

# Parse the command line arguments
case "$1" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        status_service
        ;;
    update)
        git pull || error_exit "Failed to update the repository"
        restart_service
        status_service
        ;;
    help)
        help_message
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|update|help}"
        exit 1
        ;;
esac

exit 0
