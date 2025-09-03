# Tests Directory

## Current Test Structure (Clean)

### ✅ Active Test Files

- `test_bdew_integration.py` - **Main BDEW integration tests** (18 tests)
- `test_pipeline_architecture.py` - Pipeline architecture tests (5 tests)

### 🚫 Removed/Deprecated Test Files

These files were removed during cleanup and should NOT be recreated:

- ~~`test_bdew_simple.py`~~ - Redundant basic tests
- ~~`test_bdew_working.py`~~ - Redundant working tests
- ~~`test_bdew_integration_full.py`~~ - Broken integration tests
- ~~`test_bdew_repository_complete.py`~~ - Incomplete repository tests

## Test Results

```
✅ 23/23 Total Tests PASSING
✅ 18/18 BDEW Tests PASSING
✅ 5/5 Pipeline Tests PASSING
```

## Test Categories

### BDEW Integration Tests (test_bdew_integration.py)

1. **TestBDEWRepositoryBasics** (4 tests)
   - Single company creation
   - Bulk insert operations
   - Operator ID lookup
   - Company counting

2. **TestBDEWRepositorySearch** (4 tests)
   - Name-based search
   - Federal state filtering
   - Postal code filtering
   - Pagination support

3. **TestBDEWRepositoryQuality** (2 tests)
   - Data quality statistics
   - Complete data validation

4. **TestBDEWRepositoryEdgeCases** (5 tests)
   - Empty database handling
   - Minimal data creation
   - Non-existent searches
   - Error conditions

5. **TestBDEWRepositoryIntegration** (3 tests)
   - Complete workflow testing
   - Duplicate handling
   - Performance with large datasets

### Pipeline Architecture Tests (test_pipeline_architecture.py)

- Basic pipeline execution
- Step dependencies
- Failure handling
- Data extractor functionality

## Maintenance Notes

- Keep only `test_bdew_integration.py` for BDEW testing
- All BDEW functionality is comprehensively covered in this single file
- If adding new BDEW features, extend `test_bdew_integration.py` rather than creating new files
- The .gitignore prevents recreation of deprecated test files

## Running Tests

```bash
# All tests
uv run python -m pytest tests/ -v

# Only BDEW tests
uv run python -m pytest tests/test_bdew_integration.py -v

# Only Pipeline tests
uv run python -m pytest tests/test_pipeline_architecture.py -v
```
