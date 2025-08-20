#!/bin/bash

git config --global core.autocrlf input

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.bashrc
fi

# Install dependencies
uv sync

mkdir -p ~/.streamlit
cat > ~/.streamlit/credentials.toml <<HERE
[general]
    email = "noreply@example.com"
[browser]
    gatherUsageStats = false
HERE

echo '✅ DevContainer setup completed'
