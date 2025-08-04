#!/bin/bash
set -e

# Default UID/GID
USER_UID=${USER_UID:-1000}
USER_GID=${USER_GID:-1000}

echo "Starting with UID: $USER_UID, GID: $USER_GID"

# Handle special case for existing users (like nobody with UID 99)
if id -u appuser >/dev/null 2>&1; then
    # User exists, modify it
    echo "Modifying existing appuser..."
    usermod -o -u "$USER_UID" appuser || true
    groupmod -o -g "$USER_GID" appuser || true
else
    # Create new user and group
    echo "Creating new appuser..."
    # Check if group with GID exists
    if ! getent group "$USER_GID" >/dev/null; then
        groupadd -g "$USER_GID" appuser
    else
        # Group exists, use it
        GROUP_NAME=$(getent group "$USER_GID" | cut -d: -f1)
        groupmod -n appuser "$GROUP_NAME" || true
    fi

    # Check if user with UID exists
    if ! id -u "$USER_UID" >/dev/null 2>&1; then
        useradd -o -m -u "$USER_UID" -g "$USER_GID" appuser
    else
        # User exists, rename it
        USER_NAME=$(getent passwd "$USER_UID" | cut -d: -f1)
        usermod -l appuser "$USER_NAME" || true
        usermod -g "$USER_GID" appuser || true
    fi
fi

# Fix permissions for all necessary directories and files
echo "Fixing permissions..."
chown -R "$USER_UID:$USER_GID" /app/data 2>/dev/null || true
chown -R "$USER_UID:$USER_GID" /app/app 2>/dev/null || true
chown -R "$USER_UID:$USER_GID" /app/static 2>/dev/null || true

# Ensure data directory exists with correct permissions
mkdir -p /app/data
chown "$USER_UID:$USER_GID" /app/data

# Create instance directory if using Flask instance folder
mkdir -p /app/instance
chown "$USER_UID:$USER_GID" /app/instance

# Export the user for gosu
export USER=appuser

echo "Running as UID: $(id -u appuser), GID: $(id -g appuser)"

# Execute the main command as the specified user
exec gosu "$USER_UID:$USER_GID" "$@"
