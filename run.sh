#!/bin/bash

# Function to rotate logs - keep only last 50 lines
rotate_log() {
    if [ -f log.txt ] && [ $(wc -l < log.txt) -gt 50 ]; then
        tail -50 log.txt > log.txt.tmp && mv log.txt.tmp log.txt
    fi
}

# Rotate log before starting
rotate_log

# Redirect stdout and stderr to log.txt
exec &> >(while IFS= read -r line; do
    echo "$line" | tee -a log.txt
    rotate_log
done)

rm -rf .venv
uv venv -p 3.12
uv pip install -e '.'

# Set default port if not provided
# SYFTBOX_ASSIGNED_PORT=${SYFTBOX_ASSIGNED_PORT:-8081}
SYFTBOX_ASSIGNED_PORT=8082
uv run uvicorn app:syftbox.app --host 0.0.0.0 --port $SYFTBOX_ASSIGNED_PORT --reload
