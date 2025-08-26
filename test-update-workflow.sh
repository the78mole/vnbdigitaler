#!/bin/bash
#
# Local test script for VNBdigitaler Central Data Update Workflow
# This script simulates what the GitHub Actions workflow does
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🔄 VNBdigitaler Central Data Update - Local Test${NC}"
echo "==================================================="

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]]; then
    echo -e "${RED}❌ Error: pyproject.toml not found. Run this script from the project root.${NC}"
    exit 1
fi

# Check for uv
if ! command -v uv &> /dev/null; then
    echo -e "${RED}❌ Error: uv not found. Please install uv first.${NC}"
    exit 1
fi

# Parse command line arguments
FORCE_UPDATE=false
DRY_RUN=false
UPDATE_TYPE="rollout-quotas"

while [[ $# -gt 0 ]]; do
    case $1 in
        --force-update)
            FORCE_UPDATE=true
            shift
            ;;
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --update-type)
            UPDATE_TYPE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [--force-update] [--dry-run] [--update-type TYPE] [--help]"
            echo ""
            echo "Options:"
            echo "  --force-update       Force update even if no changes detected"
            echo "  --dry-run           Show what would be updated without making changes"
            echo "  --update-type TYPE  Type of update: rollout-quotas, bdew-companies, all, check-only"
            echo "  --help              Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --dry-run --update-type rollout-quotas"
            echo "  $0 --force-update --update-type all"
            echo "  $0 --update-type check-only"
            exit 0
            ;;
        *)
            echo -e "${RED}❌ Unknown option: $1${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Install dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
uv sync

# Check environment
echo -e "${YELLOW}🔍 Checking environment...${NC}"
if [[ -z "${DATABASE_URL}" && -z "${NEON_DATABASE_URL}" ]]; then
    echo -e "${YELLOW}⚠️  Warning: No DATABASE_URL or NEON_DATABASE_URL environment variable set${NC}"
    echo "   The update will use configuration from .env file or config defaults"
fi

# Step 1: Check for new reports
echo -e "${BLUE}🔍 Step 1: Checking for updates (Type: $UPDATE_TYPE)...${NC}"
echo "========================================================"

case "$UPDATE_TYPE" in
    "rollout-quotas"|"all"|"check-only")
        echo -e "${YELLOW}📊 Checking BNetzA rollout quotas...${NC}"
        if uv run python src/bnetza/rollout_report_updater.py --check-update --verbose; then
            HAS_ROLLOUT_UPDATES=true
            echo -e "${GREEN}✅ New rollout reports available${NC}"
        else
            HAS_ROLLOUT_UPDATES=false
            echo -e "${YELLOW}ℹ️  No new rollout reports available${NC}"
        fi
        ;;
    *)
        HAS_ROLLOUT_UPDATES=false
        ;;
esac

case "$UPDATE_TYPE" in
    "bdew-companies"|"all"|"check-only")
        echo -e "${YELLOW}🏢 Checking BDEW companies...${NC}"
        echo -e "${BLUE}ℹ️  BDEW update not yet implemented${NC}"
        HAS_BDEW_UPDATES=false
        ;;
    *)
        HAS_BDEW_UPDATES=false
        ;;
esac

# Step 2: Determine action
echo -e "${BLUE}🎯 Step 2: Determining action...${NC}"
echo "================================="

if [[ "$UPDATE_TYPE" == "check-only" ]]; then
    echo -e "${YELLOW}🔍 Check-only mode - no updates will be performed${NC}"
    ACTION_TAKEN="Check completed - Rollout updates: $HAS_ROLLOUT_UPDATES, BDEW updates: $HAS_BDEW_UPDATES"
elif [[ "$DRY_RUN" == "true" ]]; then
    echo -e "${YELLOW}🔍 Running dry run mode...${NC}"
    case "$UPDATE_TYPE" in
        "rollout-quotas"|"all")
            uv run python src/bnetza/rollout_report_updater.py --dry-run --verbose
            ;;
    esac
    ACTION_TAKEN="Dry run completed for $UPDATE_TYPE"
elif [[ "$FORCE_UPDATE" == "true" ]]; then
    echo -e "${GREEN}🚀 Running forced update...${NC}"
    case "$UPDATE_TYPE" in
        "rollout-quotas"|"all")
            uv run python src/bnetza/rollout_report_updater.py --force-update --verbose
            ;;
    esac
    ACTION_TAKEN="Forced update completed for $UPDATE_TYPE"
elif [[ "$HAS_ROLLOUT_UPDATES" == "true" && ("$UPDATE_TYPE" == "rollout-quotas" || "$UPDATE_TYPE" == "all") ]]; then
    echo -e "${GREEN}📊 Running rollout quotas update...${NC}"
    uv run python src/bnetza/rollout_report_updater.py --verbose
    ACTION_TAKEN="Rollout quotas update completed"
else
    echo -e "${YELLOW}ℹ️  No action needed - no updates available for $UPDATE_TYPE${NC}"
    ACTION_TAKEN="No updates needed for $UPDATE_TYPE"
fi

# Step 3: Summary
echo -e "${BLUE}📋 Step 3: Summary${NC}"
echo "=================="
echo "Configuration:"
echo "  - Update Type: $UPDATE_TYPE"
echo "  - Force Update: $FORCE_UPDATE"
echo "  - Dry Run: $DRY_RUN"
echo "  - Rollout Updates Available: $HAS_ROLLOUT_UPDATES"
echo "  - BDEW Updates Available: $HAS_BDEW_UPDATES"
echo ""
echo "Action Taken:"
echo "  - $ACTION_TAKEN"
echo ""
echo -e "${GREEN}🎉 Local test completed successfully!${NC}"
echo ""
echo "Next Steps:"
echo "  - Check your local database for updated data"
echo "  - Start the WebUI to review the imported quotas"
echo "  - Test the BDEW linking functionality"
echo ""
echo "GitHub Actions Usage:"
echo "  - Go to Actions → 'Central Data Update Workflows' → 'Run workflow'"
echo "  - Select update type: all, rollout-quotas, bdew-companies, or check-only"
echo "  - Choose force-update or dry-run options as needed"
