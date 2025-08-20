#!/bin/bash

# Install system packages if packages.txt exists
[ -f packages.txt ] && \
sudo apt update && \
sudo apt upgrade -y && \
sudo xargs apt install -y <packages.txt;

# Install Python dependencies with uv (now installed via DevContainer feature)
echo "Updating Python dependencies with uv..."
uv sync

echo '✅ Packages installed and requirements met'
