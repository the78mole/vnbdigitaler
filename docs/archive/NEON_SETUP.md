# Neon Database Setup

This guide explains how to set up and configure Neon PostgreSQL database for the VNBdigitaler application.

## 1. Neon Account Setup

1. **Create Neon Account**: Go to [neon.tech](https://neon.tech) and create a free account
2. **Create Project**: Create a new project (e.g., "vnbdigitaler")
3. **Get Connection String**: Copy the connection string from the Neon dashboard

## 2. Environment Variables

Add the following to your `.env` file:

```bash
# Neon Database Configuration
NEON_DATABASE_URL=postgresql://username:password@ep-xxx-xxx.region.neon.tech/database  # pragma: allowlist secret
```

### Alternative: Individual Components

```bash
NEON_USER=your_username
NEON_PASSWORD=your_password
NEON_HOST=ep-xxx-xxx.region.neon.tech
NEON_PORT=5432
NEON_DATABASE=your_database_name
```

### Optional Settings

```bash
# Enable SQL query logging (development only)
DATABASE_ECHO=true

# Neon API credentials (for advanced operations)
NEON_API_KEY=your_neon_api_key
NEON_PROJECT_ID=your_project_id
NEON_BRANCH_ID=br_xxx  # Specific branch
```

## 3. Database Schema

The application uses these main tables:

### `rollout_reports`

Stores BNetzA Roll-Out Quoten report metadata:

- `id`: Primary key
- `filename`: Report filename (e.g., "Roll-out-Quoten_Q1_2025.xlsx")
- `url`: Full download URL
- `quarter`: Quarter identifier ("Q1", "Q2", "Q3", "Q4")
- `year`: Report year
- `confidence`: AI analysis confidence ("high", "medium", "low")
- `method`: Analysis method ("ai_analysis", "fallback_pattern")
- `reasoning`: AI reasoning for selection
- `ai_model_used`: AI model name
- `ai_tokens_used`: Tokens consumed
- `is_latest`: Flag for latest report per quarter/year
- `created_at`, `updated_at`: Timestamps

### `download_sessions`

Tracks BNetzA download sessions:

- `session_id`: Unique session identifier
- `temp_directory`: Local temp directory path
- `total_urls_found`: Number of URLs discovered
- `excel_urls_found`: Number of Excel URLs found
- `status`: Session status ("running", "completed", "failed")
- `metadata`: Raw session metadata (JSON)

### `analysis_sessions`

Tracks AI analysis sessions:

- `download_session_id`: Link to download session
- `model_used`: AI model identifier
- `dry_run`: Boolean flag for simulation mode
- `selected_report_id`: Selected report ID
- `total_tokens_used`: Total tokens consumed
- `status`: Analysis status

## 4. Database Initialization

### Manual Setup

```bash
# Create tables
uv run python -c "
import asyncio
from src.database import get_db_manager

async def setup():
    db = get_db_manager()
    await db.create_tables()
    print('✅ Database tables created')

    # Test connection
    if await db.test_connection():
        print('✅ Database connection successful')
    else:
        print('❌ Database connection failed')

    await db.close()

asyncio.run(setup())
"
```

### Programmatic Setup

```python
from src.database import get_db_manager

# Initialize database
db_manager = get_db_manager()
await db_manager.create_tables()

# Test connection
if await db_manager.test_connection():
    print("✅ Connected to Neon database")
```

## 5. Usage Examples

### Save Roll-Out Report

```python
from src.repository import get_repository

async with get_repository() as repo:
    report = await repo.save_roll_out_report(
        filename="Roll-out-Quoten_Q1_2025.xlsx",
        url="https://www.bundesnetzagentur.de/...",
        quarter="Q1",
        year=2025,
        confidence="high",
        method="ai_analysis",
        reasoning="AI selected this as latest quarterly report",
        ai_model_used="NousResearch/Hermes-2-Pro-Llama-3-8B",
        ai_tokens_used=637,
        download_session_id="bnetza_download_20250815_193252"
    )
    print(f"✅ Saved report: {report.id}")
```

### Get Latest Report

```python
async with get_repository() as repo:
    latest = await repo.get_latest_report(quarter="Q1", year=2025)
    if latest:
        print(f"Latest Q1 2025 report: {latest.filename}")
```

## 6. Integration with Scripts

The database integration can be added to existing scripts:

### 01_download_bnetza_data.py

- Save download session metadata
- Track URLs found and processing status

### 02_find_roll_out_report.py

- Save analysis results to database
- Mark latest reports
- Track AI token usage

## 7. Neon Features

### Branching

Neon supports database branching for development:

```bash
# Create development branch
curl -X POST \
  https://console.neon.tech/api/v2/projects/{project_id}/branches \
  -H "Authorization: Bearer {api_key}" \
  -H "Content-Type: application/json" \
  -d '{"name": "development"}'
```

### Connection Pooling

Neon automatically handles connection pooling. The application uses:

- `pool_pre_ping=True`: Test connections before use
- `pool_recycle=3600`: Recycle connections after 1 hour

### Security

- All connections use SSL by default
- Credentials are encrypted in transit
- Use environment variables for sensitive data

## 8. Monitoring

### Connection Status

```python
from src.database import get_db_manager

db = get_db_manager()
if await db.test_connection():
    print("✅ Database healthy")
else:
    print("❌ Database connection issues")
```

### Query Performance

Enable query logging during development:

```bash
DATABASE_ECHO=true
```

## 9. Troubleshooting

### Connection Issues

1. **Check URL format**: Must start with `postgresql://` or `postgresql+asyncpg://`
2. **Verify credentials**: Ensure username/password are correct
3. **Network access**: Ensure Neon endpoint is reachable
4. **SSL requirements**: Neon requires SSL connections

### Common Errors

- `connection refused`: Check host and port
- `authentication failed`: Verify credentials
- `database does not exist`: Check database name
- `SSL required`: Ensure SSL is enabled

### Debug Mode

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# This will show all SQL queries
DATABASE_ECHO=true
```

## 10. Best Practices

1. **Use transactions**: Wrap related operations in transactions
2. **Connection management**: Use async context managers
3. **Error handling**: Implement proper exception handling
4. **Index usage**: Key fields are already indexed
5. **Data validation**: Use Pydantic models for validation
6. **Environment separation**: Use different databases for dev/prod
