#!/bin/bash
set -euo pipefail

# Only run in remote (cloud) environment
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo '{"async": true, "asyncTimeout": 300000}'

cd "$CLAUDE_PROJECT_DIR"

# Install project with required extras using uv (faster than pip)
# --no-build-isolation works around setuptools version constraint in pyproject.toml
uv pip install --system --no-build-isolation -e ".[dev,openai,chroma]"
