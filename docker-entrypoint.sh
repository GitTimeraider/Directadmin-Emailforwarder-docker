#!/bin/bash
set -e

# If running as root, check if we need to change UID/GID
if [ "$(id -u)" = "0" ]; then
    # Check if USER_UID or USER_GID environment variables are set
    if [ -n "${USER_UID}" ] || [ -n "${USER_GID}" ]; then
        USER_UID=${USER_UID:-1000}
        USER_GID=${USER_GID:-1000}

        # Modify user if UID/GID different from default
        if [ "${USER_UID}" != "1000" ] || [ "${USER_GID}" != "1000" ]; then
            echo "Adjusting user to UID=${USER_UID}, GID=${USER_GID}"

            # Modify group if needed
            if [ "${USER_GID}" != "1000" ]; then
                groupmod -g ${USER_GID} appuser
            fi

            # Modify user if needed
            if [ "${USER_UID}" != "1000" ]; then
                usermod -u ${USER_UID} appuser
            fi
        fi

        # Fix ownership of app directory and data
        chown -R appuser:appuser /app

        # Execute command as appuser
        exec gosu appuser "$@"
    fi
fi

# Execute command directly if not running as root or no UID/GID specified
exec "$@"
