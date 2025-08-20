#!/bin/bash

# Configure git
git config --global core.autocrlf input

# Install dependencies using uv (now installed via DevContainer feature)
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

echo '✅ DevContainer setup completed with uv feature'
