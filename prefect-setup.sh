#!/bin/bash

# VNB Digitaler - Prefect Quick Start

echo "🚀 VNB Digitaler - Prefect Quick Start"
echo "====================================="
echo ""

# Check if dependencies are installed
echo "📦 Installing Prefect dependencies..."
uv sync

# Create directories if they don't exist
echo "📁 Setting up directory structure..."
mkdir -p flows/{bdew,bnetza,pricing,monitoring}
mkdir -p deployments
mkdir -p prefect_config/{blocks,work_pools}
mkdir -p data/{sqlite,storage,logs}

# Make setup script executable
chmod +x scripts/setup_prefect_dev.sh

echo ""
echo "✅ Setup completed! Next steps:"
echo ""
echo "🐳 Start Prefect services:"
echo "   ./scripts/setup_prefect_dev.sh"
echo ""
echo "🌐 Access Prefect UI:"
echo "   http://localhost:4200"
echo ""
echo "🧪 Test example flow:"
echo "   uv run python flows/example_flow.py"
echo ""
echo "📚 Documentation:"
echo "   📄 README.prefect.md - Setup guide"
echo "   📄 docs/PREFECT_*.md - Detailed docs"
echo ""
echo "💾 Database migration (later):"
echo "   python prefect_config/neon_migration.py"
