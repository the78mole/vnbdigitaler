[ -f packages.txt ] && \
sudo apt update && \
sudo apt upgrade -y && \
sudo xargs apt install -y <packages.txt;

# Install uv if not already installed
if ! command -v uv &> /dev/null; then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.bashrc
fi

# Install Python dependencies with uv
uv sync

echo '✅ Packages installed and Requirements met'
