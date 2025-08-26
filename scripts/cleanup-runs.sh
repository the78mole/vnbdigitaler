#!/bin/bash

# GitHub Actions Run Cleanup Script
# Deletes old workflow runs, keeping only the most recent ones
#
# Usage: ./cleanup-runs.sh [-y] [KEEP_COUNT]
#   -y: Skip confirmation prompt (auto-confirm deletion)
#   KEEP_COUNT: Number of runs to keep (default: 20)
#
# Examples:
#   ./cleanup-runs.sh        # Keep 20 most recent runs (with confirmation)
#   ./cleanup-runs.sh -y     # Keep 20 most recent runs (no confirmation)
#   ./cleanup-runs.sh 50     # Keep 50 most recent runs (with confirmation)
#   ./cleanup-runs.sh -y 50  # Keep 50 most recent runs (no confirmation)

set -e

# Parse command line arguments
AUTO_CONFIRM=false
KEEP_COUNT=20

while [[ $# -gt 0 ]]; do
    case $1 in
        -y|--yes)
            AUTO_CONFIRM=true
            shift
            ;;
        -*)
            echo "Error: Unknown option $1"
            echo "Usage: $0 [-y] [KEEP_COUNT]"
            exit 1
            ;;
        *)
            KEEP_COUNT=$1
            shift
            ;;
    esac
done

# Validate input
if ! [[ "$KEEP_COUNT" =~ ^[0-9]+$ ]] || [ "$KEEP_COUNT" -lt 1 ]; then
    echo "Error: KEEP_COUNT must be a positive integer"
    echo "Usage: $0 [KEEP_COUNT]"
    exit 1
fi

echo "🧹 GitHub Actions Run Cleanup"
echo "📊 Keeping the $KEEP_COUNT most recent runs..."
echo

# Check if gh CLI is available
if ! command -v gh &> /dev/null; then
    echo "❌ Error: GitHub CLI (gh) is not installed or not in PATH"
    echo "Please install it from: https://cli.github.com/"
    exit 1
fi

# Check if we're authenticated with GitHub
if ! gh auth status &> /dev/null; then
    echo "❌ Error: Not authenticated with GitHub CLI"
    echo "Please run: gh auth login"
    exit 1
fi

# Get total number of runs using a higher limit
echo "📈 Analyzing workflow runs..."
# Use a very high limit to get all runs, GitHub API typically limits to ~1000 anyway
MAX_LIMIT=10000
TOTAL_RUNS=$(gh run list --limit $MAX_LIMIT --json databaseId | jq '. | length')
echo "   Found $TOTAL_RUNS total runs"

if [ "$TOTAL_RUNS" -le "$KEEP_COUNT" ]; then
    echo "✅ No cleanup needed - only $TOTAL_RUNS runs found (keeping $KEEP_COUNT)"
    exit 0
fi

RUNS_TO_DELETE=$((TOTAL_RUNS - KEEP_COUNT))
echo "🗑️  Will delete $RUNS_TO_DELETE old runs (keeping newest $KEEP_COUNT)"
echo

# Get IDs of runs to delete (skip the newest KEEP_COUNT runs)
echo "🔍 Collecting run IDs to delete..."
RUN_IDS_TO_DELETE=$(gh run list --limit $MAX_LIMIT --json databaseId | jq -r ".[${KEEP_COUNT}:] | .[].databaseId")

if [ -z "$RUN_IDS_TO_DELETE" ]; then
    echo "✅ No runs to delete"
    exit 0
fi

# Count runs to delete
DELETE_COUNT=$(echo "$RUN_IDS_TO_DELETE" | wc -l)
echo "   Found $DELETE_COUNT runs to delete"
echo

# Confirm deletion
if [ "$AUTO_CONFIRM" = true ]; then
    echo "⚡ Auto-confirming deletion (--yes flag used)"
else
    echo "⚠️  This will permanently delete $DELETE_COUNT workflow runs."
    read -p "Continue? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Cleanup cancelled"
        exit 0
    fi
fi

echo
echo "🗑️  Deleting old runs..."

# Delete runs in batches to avoid overwhelming the API
BATCH_SIZE=5
DELETED_COUNT=0
FAILED_COUNT=0

# Disable exit on error for the deletion loop
set +e

while IFS= read -r RUN_ID; do
    if [ -n "$RUN_ID" ]; then
        printf "   Deleting run %s... " "$RUN_ID"

        # Delete run with automatic confirmation
        if echo "y" | gh run delete "$RUN_ID" >/dev/null 2>&1; then
            echo "✅"
            ((DELETED_COUNT++))
        else
            echo "❌ (failed or already deleted)"
            ((FAILED_COUNT++))
        fi

        # Add small delay every BATCH_SIZE deletions to be API-friendly
        if [ $((DELETED_COUNT % BATCH_SIZE)) -eq 0 ] && [ "$DELETED_COUNT" -gt 0 ]; then
            sleep 1
        fi
    fi
done < <(echo "$RUN_IDS_TO_DELETE")

# Re-enable exit on error
set -e

echo
echo "📊 Cleanup Summary:"
echo "   ✅ Successfully deleted: $DELETED_COUNT runs"
if [ "$FAILED_COUNT" -gt 0 ]; then
    echo "   ❌ Failed to delete: $FAILED_COUNT runs"
fi
echo "   📈 Remaining runs: $KEEP_COUNT (newest)"
echo
echo "🎉 Cleanup completed!"
