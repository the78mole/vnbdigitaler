#!/bin/bash
set -euo pipefail

# uv DevContainer Feature Installation Script
# This script installs uv, the extremely fast Python package manager

echo "Starting uv installation..."

# Parse options
VERSION="${VERSION:-"latest"}"
INSTALL_PATH="${INSTALLPATH:-"/usr/local/bin"}"
ENABLE_SHELL_COMPLETION="${ENABLESHELLCOMPLETION:-"true"}"

echo "Installing uv version: ${VERSION}"
echo "Installation path: ${INSTALL_PATH}"
echo "Shell completion: ${ENABLE_SHELL_COMPLETION}"

# Ensure we can install to the specified path
if [ ! -d "${INSTALL_PATH}" ]; then
    echo "Creating installation directory: ${INSTALL_PATH}"
    mkdir -p "${INSTALL_PATH}"
fi

# Ensure the install path is writable
if [ ! -w "${INSTALL_PATH}" ]; then
    echo "Error: Installation path ${INSTALL_PATH} is not writable"
    exit 1
fi

# Set up temporary directory for download
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

# Download and install uv
cd "$TEMP_DIR"

if [ "${VERSION}" = "latest" ]; then
    echo "Downloading latest uv version..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    # The install script puts uv in ~/.cargo/bin, so we need to move it
    if [ -f "$HOME/.cargo/bin/uv" ]; then
        mv "$HOME/.cargo/bin/uv" "${INSTALL_PATH}/uv"
    else
        echo "Error: uv installation failed - binary not found"
        exit 1
    fi
else
    echo "Downloading uv version ${VERSION}..."
    # For specific versions, we'll use the GitHub releases
    ARCH=$(uname -m)
    OS=$(uname -s | tr '[:upper:]' '[:lower:]')

    # Map architecture names
    case $ARCH in
        x86_64) ARCH="x86_64" ;;
        aarch64|arm64) ARCH="aarch64" ;;
        *) echo "Unsupported architecture: $ARCH"; exit 1 ;;
    esac

    # Map OS names
    case $OS in
        linux) OS="unknown-linux-gnu" ;;
        darwin) OS="apple-darwin" ;;
        *) echo "Unsupported OS: $OS"; exit 1 ;;
    esac

    BINARY_NAME="uv-${ARCH}-${OS}"
    DOWNLOAD_URL="https://github.com/astral-sh/uv/releases/download/${VERSION}/${BINARY_NAME}.tar.gz"

    echo "Downloading from: ${DOWNLOAD_URL}"

    if ! curl -LsSf "${DOWNLOAD_URL}" -o uv.tar.gz; then
        echo "Error: Failed to download uv version ${VERSION}"
        echo "Please check if the version exists at: https://github.com/astral-sh/uv/releases"
        exit 1
    fi

    tar -xzf uv.tar.gz
    mv "${BINARY_NAME}/uv" "${INSTALL_PATH}/uv"
fi

# Make sure uv is executable
chmod +x "${INSTALL_PATH}/uv"

# Verify installation
if ! "${INSTALL_PATH}/uv" --version; then
    echo "Error: uv installation verification failed"
    exit 1
fi

echo "✅ uv installed successfully!"
"${INSTALL_PATH}/uv" --version

# Set up shell completion if requested
if [ "${ENABLE_SHELL_COMPLETION}" = "true" ]; then
    echo "Setting up shell completion..."

    # Create completion directories
    mkdir -p /etc/bash_completion.d
    mkdir -p /usr/local/share/zsh/site-functions

    # Generate and install bash completion
    if command -v bash >/dev/null 2>&1; then
        "${INSTALL_PATH}/uv" generate-shell-completion bash > /etc/bash_completion.d/uv
        echo "✅ Bash completion installed"
    fi

    # Generate and install zsh completion
    if command -v zsh >/dev/null 2>&1; then
        "${INSTALL_PATH}/uv" generate-shell-completion zsh > /usr/local/share/zsh/site-functions/_uv
        echo "✅ Zsh completion installed"
    fi
fi

# Create a symbolic link if not installing to a standard PATH location
if [ "${INSTALL_PATH}" != "/usr/local/bin" ] && [ "${INSTALL_PATH}" != "/usr/bin" ]; then
    if [ -w "/usr/local/bin" ]; then
        ln -sf "${INSTALL_PATH}/uv" /usr/local/bin/uv
        echo "✅ Created symlink: /usr/local/bin/uv -> ${INSTALL_PATH}/uv"
    fi
fi

# Add uv to PATH in common shell profiles if needed
if ! echo "$PATH" | grep -q "${INSTALL_PATH}"; then
    echo "Adding ${INSTALL_PATH} to PATH..."

    # Add to /etc/bash.bashrc for all bash users
    if [ -f /etc/bash.bashrc ]; then
        echo "export PATH=\"${INSTALL_PATH}:\$PATH\"" >> /etc/bash.bashrc
    fi

    # Add to /etc/zsh/zshrc for all zsh users
    if [ -f /etc/zsh/zshrc ]; then
        echo "export PATH=\"${INSTALL_PATH}:\$PATH\"" >> /etc/zsh/zshrc
    fi

    # Add to /etc/profile for all shells
    if [ -f /etc/profile ]; then
        echo "export PATH=\"${INSTALL_PATH}:\$PATH\"" >> /etc/profile
    fi
fi

echo "🎉 uv installation completed successfully!"
echo ""
echo "Usage examples:"
echo "  uv init my-project          # Create a new Python project"
echo "  uv add requests              # Add a dependency"
echo "  uv run python script.py     # Run Python with managed environment"
echo "  uv sync                      # Install dependencies from lockfile"
echo ""
echo "For more information, visit: https://docs.astral.sh/uv/"
