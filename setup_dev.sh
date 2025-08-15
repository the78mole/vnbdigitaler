#!/bin/bash

# VNBdigitaler Development Environment Setup Script

set -e  # Exit on any error

echo "🚀 Setting up VNBdigitaler development environment..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}📝 Creating .env from template...${NC}"
    cp .env.template .env
    echo -e "${RED}⚠️  Please edit .env with your actual values!${NC}"
    echo -e "${BLUE}   You can open it with: code .env${NC}"
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
fi

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}📦 Installing uv...${NC}"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.bashrc
else
    echo -e "${GREEN}✅ uv is already installed${NC}"
fi

# Install dependencies
echo -e "${YELLOW}📦 Installing dependencies with uv...${NC}"
uv sync --all-extras

# Install pre-commit
echo -e "${YELLOW}🔧 Setting up pre-commit hooks...${NC}"
uv run pre-commit install

# Create required directories
echo -e "${YELLOW}📁 Creating required directories...${NC}"
mkdir -p logs
mkdir -p data
mkdir -p uploads
mkdir -p .streamlit

# Create .streamlit/secrets.toml if it doesn't exist
if [ ! -f .streamlit/secrets.toml ]; then
    echo -e "${YELLOW}📝 Creating Streamlit secrets template...${NC}"
    cp .streamlit/secrets.toml.template .streamlit/secrets.toml
    echo -e "${RED}⚠️  Please edit .streamlit/secrets.toml for local Streamlit testing${NC}"
fi

# Run pre-commit on all files to check setup
echo -e "${YELLOW}🔍 Running pre-commit checks...${NC}"
uv run pre-commit run --all-files || echo -e "${YELLOW}⚠️  Some pre-commit checks failed - this is normal on first run${NC}"

echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo -e "${BLUE}   1. Edit .env with your database credentials${NC}"
echo -e "${BLUE}   2. Set up your Neon database${NC}"
echo -e "${BLUE}   3. Configure your Cloudflare R2 bucket${NC}"
echo -e "${BLUE}   4. Get your OpenRouter API key${NC}"
echo -e "${BLUE}   5. Run: uv run streamlit run streamlit_app.py${NC}"
echo ""
echo -e "${YELLOW}For more detailed setup instructions, see docs/SECRETS_SETUP.md${NC}"
