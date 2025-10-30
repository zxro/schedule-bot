#!/bin/sh

CURRENT_DIR=
PYTHON_PATH=
LOG_PATH=

cd "$CURRENT_DIR" || exit 1
exec >> "$LOG_PATH" 2>&1
exec "$PYTHON_PATH" -m app.main
