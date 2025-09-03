#!/bin/bash

# Install system packages if packages.txt exists
[ -f packages.txt ] && \
sudo apt update && \
sudo apt upgrade -y && \
sudo xargs apt install -y <packages.txt;

# Ensure uv is in PATH
export PATH="$HOME/.local/bin:$PATH"

# Install dependencies using uv
echo "Updating Python dependencies with uv..."
uv sync

echo '✅ Packages installed and requirements met'
