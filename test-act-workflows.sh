#!/bin/bash

# VNBdigitaler GitHub Actions Testing with act
# Startet Artifactory Server und testet Workflows lokal

set -e

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Funktionen
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Banner
echo -e "${BLUE}"
echo "🎭 VNBdigitaler Act Testing Suite"
echo "========================================"
echo -e "${NC}"

# Überprüfe Dependencies
log_info "Checking dependencies..."

if ! command -v act &> /dev/null; then
    log_error "act is not installed. Please install it first:"
    echo "  curl https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    log_error "Docker is not installed or not running"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    log_error "Docker is not running. Please start Docker first."
    exit 1
fi

log_success "Dependencies checked"

# Erstelle Verzeichnisse
log_info "Setting up directories..."
mkdir -p artifacts
mkdir -p tmp
log_success "Directories created"

# Funktion zum Starten des Artifactory Servers
start_artifactory_server() {
    log_info "Starting artifactory server on port 34567..."

    # Kill existing server if running
    pkill -f "act.*artifact-server" || true
    sleep 2

    # Start server in background
    act --artifact-server-path ./artifacts --artifact-server-port 34567 --bind &
    ARTIFACTORY_PID=$!

    # Wait for server to start
    log_info "Waiting for artifactory server to start..."
    for i in {1..10}; do
        if curl -s http://localhost:34567 > /dev/null 2>&1; then
            log_success "Artifactory server is running on http://localhost:34567"
            return 0
        fi
        sleep 1
    done

    log_error "Failed to start artifactory server"
    return 1
}

# Funktion zum Testen eines Workflows
test_workflow() {
    local workflow_name="$1"
    local event_name="$2"
    local inputs="$3"

    log_info "Testing workflow: $workflow_name"
    echo "Event: $event_name"
    echo "Inputs: $inputs"
    echo

    # Build act command
    local act_cmd="act $event_name"

    if [[ -n "$inputs" ]]; then
        act_cmd="$act_cmd --input $inputs"
    fi

    if [[ -n "$workflow_name" ]]; then
        act_cmd="$act_cmd --workflows .github/workflows/$workflow_name"
    fi

    # Run with verbose output
    act_cmd="$act_cmd --verbose --artifact-server-path ./artifacts --artifact-server-port 34567"

    log_info "Running: $act_cmd"
    echo

    if eval $act_cmd; then
        log_success "Workflow $workflow_name completed successfully"
        return 0
    else
        log_error "Workflow $workflow_name failed"
        return 1
    fi
}

# Cleanup function
cleanup() {
    log_info "Cleaning up..."

    # Stop artifactory server
    if [[ -n "$ARTIFACTORY_PID" ]]; then
        kill $ARTIFACTORY_PID 2>/dev/null || true
    fi
    pkill -f "act.*artifact-server" 2>/dev/null || true

    log_success "Cleanup completed"
}

# Trap cleanup on exit
trap cleanup EXIT

# Parse command line arguments
WORKFLOW=""
EVENT="workflow_dispatch"
DRY_RUN="false"
UPDATE_TYPE="check-only"
FORCE_UPDATE="false"

while [[ $# -gt 0 ]]; do
    case $1 in
        --workflow)
            WORKFLOW="$2"
            shift 2
            ;;
        --event)
            EVENT="$2"
            shift 2
            ;;
        --dry-run)
            DRY_RUN="true"
            shift
            ;;
        --update-type)
            UPDATE_TYPE="$2"
            shift 2
            ;;
        --force-update)
            FORCE_UPDATE="true"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo
            echo "Options:"
            echo "  --workflow WORKFLOW    Specific workflow to test (default: all)"
            echo "  --event EVENT         Event type (default: workflow_dispatch)"
            echo "  --dry-run             Enable dry run mode"
            echo "  --update-type TYPE    Update type: all, rollout-quotas, bdew-companies, check-only"
            echo "  --force-update        Force update mode"
            echo "  --help                Show this help"
            echo
            echo "Examples:"
            echo "  $0 --workflow central-data-update.yml --dry-run"
            echo "  $0 --workflow reusable-rollout-update.yml --update-type rollout-quotas"
            echo "  $0 --update-type check-only"
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Start artifactory server
# start_artifactory_server

# Build inputs string
INPUTS="update_type=$UPDATE_TYPE"
if [[ "$DRY_RUN" == "true" ]]; then
    INPUTS="$INPUTS,dry_run=true"
fi
if [[ "$FORCE_UPDATE" == "true" ]]; then
    INPUTS="$INPUTS,force_update=true"
fi

# Run tests
log_info "Starting workflow tests..."
echo "Configuration:"
echo "  - Update Type: $UPDATE_TYPE"
echo "  - Dry Run: $DRY_RUN"
echo "  - Force Update: $FORCE_UPDATE"
echo

if [[ -n "$WORKFLOW" ]]; then
    # Test specific workflow
    test_workflow "$WORKFLOW" "$EVENT" "$INPUTS"
else
    # Test all workflows
    log_info "Testing all workflows..."

    # Test central workflow first
    log_info "=== Testing Central Data Update Workflow ==="
    test_workflow "central-data-update.yml" "$EVENT" "$INPUTS"

    echo
    log_info "=== Testing Reusable Rollout Update Workflow ==="
    # Test reusable workflow (note: this needs to be called via central workflow normally)
    # For direct testing, we'll simulate the inputs
    REUSABLE_INPUTS="force_update=$FORCE_UPDATE,dry_run=$DRY_RUN,check_only="
    if [[ "$UPDATE_TYPE" == "check-only" ]]; then
        REUSABLE_INPUTS="${REUSABLE_INPUTS}true"
    else
        REUSABLE_INPUTS="${REUSABLE_INPUTS}false"
    fi

    # Note: Reusable workflows can't be tested directly with act
    log_warning "Reusable workflows can't be tested directly with act"
    log_info "The reusable workflow is tested as part of the central workflow"
fi

# Show artifacts
echo
log_info "Checking created artifacts..."
if [[ -d "./artifacts" ]] && [[ -n "$(ls -A ./artifacts 2>/dev/null)" ]]; then
    log_success "Artifacts created:"
    ls -la ./artifacts/
else
    log_warning "No artifacts found in ./artifacts/"
fi

# Show tmp files
echo
log_info "Checking tmp files..."
if [[ -d "./tmp" ]] && [[ -n "$(ls -A ./tmp 2>/dev/null)" ]]; then
    log_success "Temp files created:"
    ls -la ./tmp/
else
    log_warning "No temp files found in ./tmp/"
fi

log_success "Act testing completed!"
echo
echo "Next steps:"
echo "  - Review the workflow output above"
echo "  - Check artifacts in ./artifacts/ directory"
echo "  - Verify temp files in ./tmp/ directory"
echo "  - Test different workflow configurations"
echo
echo "Artifact server was running on: http://localhost:34567"
echo "Use --help for more testing options"
