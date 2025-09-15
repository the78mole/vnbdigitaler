#!/bin/bash

# VNB Digitaler - Prefect Development Setup Script

set -e

echo "🚀 Setting up Prefect development environment for VNB Digitaler..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
print_status "Checking prerequisites..."

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Check if curl is available for health checks
if ! command -v curl &> /dev/null; then
    print_warning "curl not found. Health check will use container status only."
    HEALTH_CHECK_METHOD="container"
else
    HEALTH_CHECK_METHOD="api"
fi

print_success "Prerequisites check passed"

# Create necessary directories
print_status "Creating project directories..."

mkdir -p flows/{bdew,bnetza,pricing,monitoring}
mkdir -p deployments
mkdir -p prefect_config/{blocks,work_pools}
mkdir -p data/{sqlite,storage,logs}
mkdir -p logs

print_success "Directories created"

# Copy environment file if it doesn't exist
if [[ ! -f .env.prefect ]]; then
    print_warning ".env.prefect not found - should have been created already"
else
    print_success "Environment configuration found"
fi

# Build and start services
print_status "Building Prefect worker image..."
docker compose -f docker-compose.prefect.yml build prefect-worker

print_status "Starting Prefect services..."
docker compose -f docker-compose.prefect.yml up -d

# Wait for Prefect server to be ready
print_status "Waiting for Prefect server to be ready..."
timeout=60
counter=0

while true; do
    if [ $counter -eq $timeout ]; then
        print_error "Prefect server failed to start within $timeout seconds"
        print_status "Checking logs..."
        docker compose -f docker-compose.prefect.yml logs prefect-server
        exit 1
    fi

    # Get container ID
    PREFECT_SERVER_CONTAINER=$(docker compose -f docker-compose.prefect.yml ps -q prefect-server)

    if [ -n "$PREFECT_SERVER_CONTAINER" ]; then
        # Check container health status first
        CONTAINER_STATUS=$(docker inspect "$PREFECT_SERVER_CONTAINER" --format='{{.State.Health.Status}}' 2>/dev/null || echo "none")

        if [ "$CONTAINER_STATUS" = "healthy" ]; then
            break
        elif [ "$HEALTH_CHECK_METHOD" = "api" ] && [ "$CONTAINER_STATUS" = "none" ]; then
            # If no health check defined, try API directly
            if docker exec "$PREFECT_SERVER_CONTAINER" curl -s http://localhost:4200/api/health > /dev/null 2>&1; then
                break
            fi
        fi
    fi

    sleep 2
    counter=$((counter + 2))
    echo -n "."
done

echo ""
print_success "Prefect server is ready!"

# Setup work pool
print_status "Creating development work pool..."

# Get the actual container name (Docker Compose generates names based on directory)
PREFECT_SERVER_CONTAINER=$(docker compose -f docker-compose.prefect.yml ps -q prefect-server)

if [ -z "$PREFECT_SERVER_CONTAINER" ]; then
    print_error "Prefect server container not found!"
    exit 1
fi

# Use docker exec to run prefect commands in the server container
docker exec "$PREFECT_SERVER_CONTAINER" prefect work-pool create vnb-digitaler-dev \
    --type process \
    --set-as-default || print_warning "Work pool might already exist"

# Optional: Create some example blocks
print_status "Setting up development blocks..."

# Create a simple JSON block for configuration
docker exec "$PREFECT_SERVER_CONTAINER" prefect block register \
    --module prefect.blocks.system || true

print_success "Basic blocks registered"

# Display status
print_status "Checking service status..."
docker compose -f docker-compose.prefect.yml ps

echo ""
print_success "🎉 Prefect development environment is ready!"
echo ""
echo "📋 Next steps:"
echo "   • Prefect UI: http://localhost:4200"
echo "   • Run flows: uv run python flows/example_flow.py"
echo "   • Check logs: docker compose -f docker-compose.prefect.yml logs -f"
echo "   • Stop services: docker compose -f docker-compose.prefect.yml down"
echo ""
echo "🔧 Development commands:"
echo "   • Add dependencies: uv add prefect[optional-extras]"
echo "   • Shell into worker: docker exec -it \$(docker compose -f docker-compose.prefect.yml ps -q prefect-worker) bash"
echo "   • Restart services: docker compose -f docker-compose.prefect.yml restart"
echo ""
print_warning "Note: This setup uses SQLite. For production, migrate to Neon PostgreSQL."
