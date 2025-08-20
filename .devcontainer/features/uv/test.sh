#!/bin/bash
# Test script for uv DevContainer feature

set -euo pipefail

echo "🧪 Testing uv DevContainer feature..."

# Test if uv is installed
if ! command -v uv &>/dev/null; then
    echo "❌ uv command not found"
    exit 1
fi

echo "✅ uv command found"

# Test uv version
UV_VERSION=$(uv --version)
echo "✅ uv version: $UV_VERSION"

# Test if uv can show help
if ! uv --help &>/dev/null; then
    echo "❌ uv help command failed"
    exit 1
fi

echo "✅ uv help command works"

# Test if shell completion files exist (if enabled)
if [ -f /etc/bash_completion.d/uv ]; then
    echo "✅ Bash completion found"
else
    echo "ℹ️  Bash completion not found (might be disabled)"
fi

if [ -f /usr/local/share/zsh/site-functions/_uv ]; then
    echo "✅ Zsh completion found"
else
    echo "ℹ️  Zsh completion not found (might be disabled)"
fi

# Test if uv can create a basic project
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

cd "$TEMP_DIR"
if uv init test-project; then
    echo "✅ uv init works"
    cd test-project
    if [ -f pyproject.toml ] && [ -f .python-version ]; then
        echo "✅ Project files created correctly"
    else
        echo "❌ Project files missing"
        exit 1
    fi
else
    echo "❌ uv init failed"
    exit 1
fi

echo "🎉 All uv DevContainer feature tests passed!"
