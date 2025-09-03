#!/bin/bash

# Configure git
git config --global core.autocrlf input

# Initialize PostgreSQL (if available)
if command -v /usr/local/share/pq-init.sh &> /dev/null; then
    echo "Initializing PostgreSQL..."
    sudo /usr/local/share/pq-init.sh
    echo "PostgreSQL initialized successfully"
fi

# Install dependencies using uv (should already be available through feature)
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

echo '✅ DevContainer setup completed with uv and PostgreSQL'
