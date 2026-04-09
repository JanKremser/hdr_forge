#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_VERSION="3.14.0"

# Check if Docker is available
if ! command -v docker &> /dev/null; then
    echo "[error] Docker is not installed or not in PATH"
    exit 1
fi

echo "[build] Starting Docker-based PyInstaller build (debian:trixie / Python ${PYTHON_VERSION})"

docker run --rm \
  -v "$SCRIPT_DIR:/build" \
  -w /build \
  debian:trixie \
  bash -c "
    set -euo pipefail
    export DEBIAN_FRONTEND=noninteractive

    echo '[docker] Installing system dependencies...'
    apt-get update -qq
    apt-get install -y -qq \
      build-essential curl git libssl-dev libffi-dev zlib1g-dev \
      libbz2-dev libreadline-dev libsqlite3-dev liblzma-dev \
      libgl1 libglib2.0-0 binutils

    echo '[docker] Installing pyenv...'
    export PYENV_ROOT=\"/root/.pyenv\"
    curl -fsSL https://pyenv.run | bash
    export PATH=\"\$PYENV_ROOT/bin:\$PYENV_ROOT/shims:\$PATH\"
    eval \"\$(pyenv init -)\"

    echo '[docker] Installing Python ${PYTHON_VERSION}...'
    pyenv install ${PYTHON_VERSION}
    pyenv global ${PYTHON_VERSION}

    echo '[docker] Installing project dependencies...'
    pip install --quiet -r requirements.txt
    pip install --quiet .

    echo '[docker] Running PyInstaller...'
    python -m PyInstaller --clean --onefile src/hdr_forge/main.py --name hdr_forge \
      --hidden-import=hdr_forge \
      --collect-submodules hdr_forge
  "

echo "[build] Done. Binary: $SCRIPT_DIR/dist/hdr_forge"
echo "[build] Verifying binary..."
file "$SCRIPT_DIR/dist/hdr_forge"
