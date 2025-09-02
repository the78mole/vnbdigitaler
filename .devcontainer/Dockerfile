FROM mcr.microsoft.com/devcontainers/python:1-3.11-bullseye

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Add uv to vscode user's PATH as well
USER vscode
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/home/vscode/.local/bin:$PATH"

# Switch back to root for any final setup
USER root
