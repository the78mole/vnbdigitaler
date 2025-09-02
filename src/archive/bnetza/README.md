# BNetzA Data Providers

This directory contains modules for interacting with data sources from the **Bundesnetzagentur (BNetzA)**.

## Current Modules

### 📊 Rollout Reports

- **`rollout_report_discovery.py`**: Discovery and classification of smart meter rollout reports
- **`rollout_report_updater.py`**: High-level interface for updating rollout data

## Architecture

```
src/bnetza/
├── __init__.py                     # Package initialization
├── rollout_report_discovery.py    # Low-level BNetzA report discovery
├── rollout_report_updater.py      # High-level update orchestration
└── README.md                      # This file
```

## Future Expansion

This structure allows for easy addition of other BNetzA data providers:

```
src/bnetza/
├── rollout_reports/               # Smart meter rollout data
├── grid_operators/                # Grid operator registrations
├── energy_prices/                 # Energy pricing data
├── market_data/                   # Electricity market data
└── regulatory_reports/            # Other regulatory reports
```

## Usage Examples

### Basic Report Discovery

```python
from src.bnetza.rollout_report_discovery import BNetzAReportDiscovery

discovery = BNetzAReportDiscovery()
has_new = discovery.has_new_reports()
```

### Complete Update Workflow

```python
from src.bnetza.rollout_report_updater import RolloutReportUpdater

updater = RolloutReportUpdater()
success = updater.discover_and_download()
```

## Design Principles

- **Separation of Concerns**: Discovery logic separate from update orchestration
- **Extensibility**: Easy to add new data providers
- **Consistency**: Common patterns across different BNetzA data sources
- **Testing**: Comprehensive test coverage for all modules

## Data Flow

```
1. Discovery Service  → Find new reports on BNetzA website
2. Classification    → AI-powered report identification
3. Download         → Secure file retrieval with ETag tracking
4. Processing       → Extract and normalize data
5. Storage          → Update database tables
6. Validation       → Verify data integrity
```
