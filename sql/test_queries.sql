-- VNB Digitaler PostgreSQL Test Queries
-- Verwende diese Datei zum Testen der Datenbankverbindung

-- 1. Zeige alle Tabellen
SELECT
    table_name,
    table_type
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- 2. Überprüfe BDEW Companies
SELECT
    count(*) as total_companies,
    count(*) FILTER (WHERE is_active = true) as active_companies
FROM bdew_companies;

-- 3. Zeige erste 5 Unternehmen
SELECT
    company_name,
    city,
    federal_state,
    data_quality_score,
    created_at
FROM bdew_companies
WHERE is_active = true
ORDER BY created_at DESC
LIMIT 5;

-- 4. Import Log Status
SELECT
    import_status,
    count(*) as count,
    max(import_timestamp) as latest_import
FROM bdew_import_logs
GROUP BY import_status
ORDER BY latest_import DESC;

-- 5. PostgreSQL Extensions
SELECT
    extname as extension_name,
    extversion as version
FROM pg_extension
ORDER BY extname;

-- 6. Datenbank Info
SELECT
    current_database() as database_name,
    current_user as current_user,
    version() as postgres_version;
