# VNBdigitaler Database Migrations

This directory contains database migration and initialization scripts for the VNBdigitaler project.

## Current Migration Strategy

**🎯 Single Initialization Script**: We use a single comprehensive initialization script instead of incremental migrations.

### Database Initialization

```bash
# Initialize the complete database schema from scratch
python migrations/init_database.py
```

This script will:

- ⚠️ **Drop all existing VNBdigitaler tables** (with confirmation prompt)
- 🏗️ Create the complete normalized database schema
- 📊 Set up all indexes for optimal performance
- ✅ Validate all constraints and relationships

### Database Schema Overview

The initialization script creates these tables:

| Table | Purpose |
|-------|---------|
| `companies` | BDEW companies with vnbdigital.de integration and geocoding |
| `rollout_companies` | BNetzA company names linked to BDEW companies via `bdew_code` |
| `rollout_quotas` | Time-series rollout quota data with quarter/year tracking |
| `rollout_update_logs` | Automated report processing logs and statistics |
| `rollout_reports` | BNetzA report metadata and AI analysis results |
| `download_sessions` | Download session tracking for report automation |

### Key Relationships

```
companies (BDEW)
    ↓ (bdew_code)
rollout_companies (BNetzA)
    ↓ (rollout_company_id)
rollout_quotas (Time-series data)
```

### Features

- ✅ **Normalized Structure**: Companies and rollout data are properly separated
- ✅ **Foreign Key Constraints**: Proper relationships between tables
- ✅ **Comprehensive Indexes**: Optimized for WebUI query patterns
- ✅ **Data Validation**: Check constraints for data integrity
- ✅ **Flexible JSONB**: Support for additional metadata

## Legacy Migrations

Legacy migration files can be archived to `archive/` folder. They are no longer needed since the initialization script creates the complete schema.

### Archiving Legacy Migrations

```bash
# Archive old migration files (optional)
python migrations/archive_migrations.py
```

## Development Notes

### Adding New Schema Changes

For new schema changes:

1. **Update SQLAlchemy Models** in `src/models.py`
2. **Update the initialization script** `init_database.py`
3. **Test with fresh database** using the init script

### Database Backup Before Initialization

```bash
# Backup existing database (recommended)
pg_dump your_database > backup_$(date +%Y%m%d_%H%M%S).sql
```

### Restoring from Backup

```bash
# Restore from backup if needed
psql your_database < backup_20250826_123456.sql
```

## Production Deployment

For production deployment:

1. **Backup existing database**
2. **Run initialization script** during maintenance window
3. **Import BDEW and rollout data** using data import scripts
4. **Verify data integrity** using application endpoints

⚠️ **Important**: The initialization script drops all tables. Only use on development databases or during planned maintenance with proper backups.
