#!/bin/bash

# Skript zum Extrahieren gelöschter Python-Dateien aus Git-Historie

echo "🔍 Extrahiere gelöschte Python-Dateien..."

# Liste der gelöschten Dateien mit ihren letzten bekannten Commits
declare -A deleted_files
deleted_files["migrations/add_company_geolocation.py"]="fecdd2ec0bfb772a42f3a181356b193de1cac772"  # pragma: allowlist secret
deleted_files["migrations/add_report_year_to_rollout_quotas.py"]="fecdd2ec0bfb772a42f3a181356b193de1cac772"  # pragma: allowlist secret
deleted_files["migrations/create_rollout_update_logs_table.py"]="fecdd2ec0bfb772a42f3a181356b193de1cac772"  # pragma: allowlist secret
deleted_files["migrations/fix_quarter_fields.py"]="fecdd2ec0bfb772a42f3a181356b193de1cac772"  # pragma: allowlist secret
deleted_files["migrations/replace_quarter_with_numeric_report_quarter.py"]="fecdd2ec0bfb772a42f3a181356b193de1cac772"  # pragma: allowlist secret
deleted_files["migrations/update_rollout_logs_quarter_fields.py"]="fecdd2ec0bfb772a42f3a181356b193de1cac772"  # pragma: allowlist secret
deleted_files["migrations/update_rollout_quotas_unique_constraint.py"]="fecdd2ec0bfb772a42f3a181356b193de1cac772"  # pragma: allowlist secret
deleted_files["webui/import_rollout_csv.py"]="fecdd2ec0bfb772a42f3a181356b193de1cac772"  # pragma: allowlist secret
deleted_files["webui/match_rollout_data.py"]="fecdd2ec0bfb772a42f3a181356b193de1cac772"  # pragma: allowlist secret

# Weitere Dateien aus der Git-Historie
deleted_files[".github/scripts/company_updater.py"]="fecdd2ec0bfb772a42f3a181356b193de1cac772"  # pragma: allowlist secret
deleted_files[".github/scripts/enhanced_update.py"]="fecdd2ec0bfb772a42f3a181356b193de1cac772"  # pragma: allowlist secret
deleted_files[".github/scripts/extract_stats.py"]="fecdd2ec0bfb772a42f3a181356b193de1cac772"  # pragma: allowlist secret
deleted_files[".github/scripts/format_companies.py"]="fecdd2ec0bfb772a42f3a181356b193de1cac772"  # pragma: allowlist secret
deleted_files[".github/scripts/format_company_results.py"]="fecdd2ec0bfb772a42f3a181356b193de1cac772"  # pragma: allowlist secret
deleted_files[".github/scripts/test_semantic_versioning.py"]="fecdd2ec0bfb772a42f3a181356b193de1cac772"  # pragma: allowlist secret

extract_file() {
    local filepath="$1"
    local commit="$2"
    local dirname=$(dirname "$filepath")
    local filename=$(basename "$filepath")

    if [ "$dirname" = "." ]; then
        target_dir="archive"
    else
        target_dir="$dirname/archive"
    fi

    mkdir -p "$target_dir"

    # Versuche verschiedene Commit-Versionen
    for suffix in "" "^" "~1"; do
        if git show "${commit}${suffix}:${filepath}" > "$target_dir/$filename" 2>/dev/null; then
            echo "✅ Extrahiert: $filepath -> $target_dir/$filename"
            return 0
        fi
    done

    echo "❌ Konnte nicht extrahieren: $filepath"
    return 1
}

success_count=0
total_count=${#deleted_files[@]}

for filepath in "${!deleted_files[@]}"; do
    commit="${deleted_files[$filepath]}"
    if extract_file "$filepath" "$commit"; then
        ((success_count++))
    fi
done

echo "🎉 Erfolgreich extrahiert: $success_count/$total_count Dateien"
