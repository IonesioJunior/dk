#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# App to install
APP_TO_INSTALL="https://github.com/IonesioJunior/dk"

# Function to display success messages
success() {
    echo -e "${GREEN}$1${NC}"
}

# Function to display error messages
error() {
    echo -e "${RED}$1${NC}"
}

# Function to display warning messages
warning() {
    echo -e "${YELLOW}$1${NC}"
}

# Function to run the app installation
run_install_app() {
    echo
    success "Installing app ${APP_TO_INSTALL}..."
    eval ~/.local/bin/syftbox app install --force "${APP_TO_INSTALL}" < /dev/tty
}

# Function to configure environment
configure_environment() {
    # Create the .env file in the app directory
    ENV_FILE="$HOME/SyftBox/apps/dk/.env"
    ENV_DIR="$HOME/SyftBox/apps/dk"

    # Create directory if it doesn't exist
    if [ ! -d "$ENV_DIR" ]; then
        mkdir -p "$ENV_DIR"
    fi

    # Write username to .env file
    echo "SYFTBOX_USER_ID=$username" > "$ENV_FILE"
    echo "SYFTBOX_USERNAME=$username" >> "$ENV_FILE"

    success "Environment configured: Username saved to ${ENV_FILE}"
}

# Function to fix code issues
fix_code_issues() {
    success "Fixing code issues..."

    if [ -f "./fix_exceptions.py" ]; then
        success "Running code fixes for QueryParams import issue"
        python3 ./fix_exceptions.py . --fix classes --recursive

        if [ $? -eq 0 ]; then
            success "Code fixes applied successfully!"
        else
            warning "Some issues occurred while applying code fixes, but continuing installation"
        fi
    else
        warning "fix_exceptions.py not found, skipping code fixes"
    fi
}

# Main script logic
main() {
    echo "Starting installation process..."

    # Check if ~/.syftbox/config.json exists
    if [ ! -f ~/.syftbox/config.json ]; then
        error "Error: ~/.syftbox/config.json not found!"
        warning "You must install syftbox and configure it first."
        warning "Please run: syftbox login"
        exit 1
    fi

    success "Found syftbox configuration."

    # Ask for username before installation
    echo
    echo -n "Please enter your username: "
    read -r username < /dev/tty

    if [ -z "$username" ]; then
        error "Username cannot be empty!"
        exit 1
    fi

    # Run the installation first
    run_install_app

    # Check if installation was successful
    if [ $? -eq 0 ]; then
        success "App installation completed successfully!"

        # Configure environment AFTER successful installation
        echo
        success "Configuring environment..."
        configure_environment

        # Create config.json file
        echo
        success "Creating config.json file..."
        CONFIG_FILE="$HOME/SyftBox/apps/dk/config.json"
        mkdir -p "$(dirname "$CONFIG_FILE")"
        cat > "$CONFIG_FILE" << EOF
{
  "app_name": "syft_agent",
  "host": "0.0.0.0",
  "port": 8082,
  "log_level": "INFO",
  "syftbox_user_id": "$username",
  "syftbox_username": "$username",
  "websocket_server_url": "https://distributedknowledge.org",
  "websocket_retry_attempts": 3,
  "websocket_retry_delay": 5,
  "private_key_filename": "websocket_private.pem",
  "public_key_filename": "websocket_public.pem",
  "scheduler_startup_delay": 0,
  "websocket_startup_delay": 5
}
EOF
        success "Created $CONFIG_FILE with user information"

        # Fix code issues before initialization
        echo
        fix_code_issues

        # Install development dependencies and pre-commit
        echo
        success "Installing development dependencies and pre-commit..."
        pip install pre-commit
        pip install -e ".[dev]"
        pre-commit install

        # Initialize syftbox
        echo
        success "Initializing syftbox..."
        syftbox

        if [ $? -eq 0 ]; then
            success "Syftbox initialized successfully!"
        else
            error "Failed to initialize syftbox."
            exit 1
        fi
    else
        error "App installation failed."
        exit 1
    fi

    echo
    success "Installation process completed!"
}

# Run the main function
main
