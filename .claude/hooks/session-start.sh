#!/bin/bash
set -euo pipefail

# Only run in remote Claude Code web sessions
if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

echo '{"async": true, "asyncTimeout": 300000}'

cd "$CLAUDE_PROJECT_DIR"

# Install memetalk with dev, openai, and chroma extras
# --no-build-isolation avoids downloading build tools (setuptools/wheel) that are already present
uv pip install -e ".[dev,openai,chroma]" --system --no-build-isolation
