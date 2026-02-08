#!/bin/sh
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
VENV_DIR="$PROJECT_ROOT/.venv"

# Detect python: prefer python3, fall back to python (Windows only ships "python")
if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    echo "Error: python not found. Install Python 3.10+ and ensure it is on PATH." >&2
    exit 1
fi

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
fi

# Cross-platform venv python detection
if [ -x "$VENV_DIR/Scripts/python.exe" ]; then
    VENV_PY="$VENV_DIR/Scripts/python.exe"
else
    VENV_PY="$VENV_DIR/bin/python"
fi

"$VENV_PY" -m pip install --upgrade pip setuptools wheel

# Install in editable mode. MSYS_NO_PATHCONV prevents Git Bash (MINGW)
# from mangling the [dev] extras specifier as a path.
cd "$PROJECT_ROOT"
MSYS_NO_PATHCONV=1 "$VENV_PY" -m pip install -e ".[dev]"

echo ""
if [ -x "$VENV_DIR/Scripts/python.exe" ]; then
    echo "Setup complete. Activate with: source $VENV_DIR/Scripts/activate"
else
    echo "Setup complete. Activate with: source $VENV_DIR/bin/activate"
fi
