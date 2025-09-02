#!/bin/bash

# Configure git
git config --global core.autocrlf input

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # Add to PATH for current session
    export PATH="$HOME/.local/bin:$PATH"
fi

# Install dependencies using uv
echo "Installing Python dependencies with uv..."
uv sync

# Configure Streamlit
mkdir -p ~/.streamlit
cat > ~/.streamlit/credentials.toml <<HERE
[general]
    email = "noreply@example.com"
[browser]
    gatherUsageStats = false
HERE

echo '✅ DevContainer setup completed with uv'
