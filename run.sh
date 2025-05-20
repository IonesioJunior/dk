#!/bin/bash

# Redirect stdout and stderr to log.txt
exec &> >(tee -a log.txt)

rm -rf .venv
uv venv -p 3.12
uv pip install -e '.'

# Set default port if not provided
# SYFTBOX_ASSIGNED_PORT=${SYFTBOX_ASSIGNED_PORT:-8081}
SYFTBOX_ASSIGNED_PORT=8082
uv run uvicorn app:syftbox.app --host 0.0.0.0 --port $SYFTBOX_ASSIGNED_PORT --reload
