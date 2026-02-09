#!/bin/sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

if [ -x "$VENV_DIR/Scripts/python.exe" ]; then
    VENV_PY="$VENV_DIR/Scripts/python.exe"
else
    VENV_PY="$VENV_DIR/bin/python"
fi

# Auto-configure from environment variables if set
CONFIG_DIR="$HOME/.genai-cli"
if [ -n "$GENAI_AUTH_TOKEN" ] && [ -n "$GENAI_API_BASE_URL" ]; then
    mkdir -p "$CONFIG_DIR"
    printf 'GENAI_AUTH_TOKEN=%s\n' "$GENAI_AUTH_TOKEN" > "$CONFIG_DIR/.env"
    chmod 600 "$CONFIG_DIR/.env" 2>/dev/null || true
    printf 'api_base_url: "%s"\n' "$GENAI_API_BASE_URL" > "$CONFIG_DIR/settings.yaml"
    echo "Auto-configured from environment variables."
fi

"$VENV_PY" -m genai_cli "$@"
