#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v pipenv >/dev/null 2>&1; then
  echo "pipenv is required but was not found in PATH" >&2
  exit 1
fi

pipenv install --dev --skip-lock
pipenv run sphinx-build -b html docs docs/_build/html
