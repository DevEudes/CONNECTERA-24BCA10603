#!/usr/bin/env bash
# Connectera - start the app (macOS / Linux)
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { echo "Run ./setup.sh first."; exit 1; }
echo "Connectera → http://127.0.0.1:8000  (CTRL+C to stop)"
.venv/bin/python manage.py runserver
