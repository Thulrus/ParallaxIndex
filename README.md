# Parallax Index

**Global Sentiment & Cultural Drift Tracker**

A modular, extensible system for tracking sentiment across diverse data sources and aggregating them into a unified global metric.

## Overview

Parallax Index is a foundational MVP designed for long-term stability and extensibility. It implements a plugin-based architecture where data sources are periodically collected, distilled into normalized snapshots, and aggregated into global sentiment metrics.

### Core Principles

1. **Plugins define capabilities; source instances define configuration**
   - Each plugin type (e.g., "numeric_index") defines *how* to collect and distill data
   - Each source instance (e.g., "S&P 500") provides *what* configuration to use

2. **Raw data is ephemeral**
   - Raw collected data exists only during the collect → distill pipeline
   - Only distilled snapshots are persisted to storage
   - This design prevents storage bloat and focuses on actionable insights

3. **Distilled snapshots are canonical and append-only**
   - All analysis operates on normalized `DistilledSnapshot` records
   - Snapshots are immutable once created
   - Historical data is preserved for trend analysis

4. **Extracted terms are not "raw data"**
   - Terms (keywords, entities) may be stored as part of distilled snapshots
   - They represent processed insights, not raw content

5. **Schemas are explicit, documented, and stable**
   - All data structures use Pydantic models with comprehensive docstrings
   - Schema changes require careful migration planning
   - Backward compatibility is a design priority

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Web Interface                           │
│              (FastAPI + Server-rendered HTML)                │
└───────────────────────────┬─────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────┐
│                           │                                   │
│  ┌────────────────┐  ┌───▼──────────┐  ┌────────────────┐  │
│  │  Aggregation   │  │   Scheduler   │  │ Plugin Registry│  │
│  │    Engine      │  │  (APScheduler)│  │                │  │
│  └────────┬───────┘  └───┬──────────┘  └────────┬───────┘  │
│           │              │                       │           │
│           │     ┌────────▼────────┐             │           │
│           └────►│    Database     │◄────────────┘           │
│                 │    (SQLite)     │                          │
│                 └─────────────────┘                          │
│                                                               │
│                      Core System                              │
└───────────────────────────────────────────────────────────────┘
                            │
                    ┌───────┴───────┐
                    │               │
            ┌───────▼─────┐  ┌──────▼──────┐
            │ Numeric     │  │   Future    │
            │ Index Plugin│  │   Plugins   │
            └─────────────┘  └─────────────┘
```

### Component Responsibilities

#### Core (`/core`)
- **schemas.py**: Pydantic models for all data structures
- **aggregation.py**: Weighted sentiment aggregation logic
- **scheduler.py**: Periodic collection orchestration

#### Plugins (`/plugins`)
- **base.py**: Abstract base class defining plugin interface
- **registry.py**: Plugin discovery and instantiation
- **numeric_index.py**: Example plugin for numeric data sources

#### Storage (`/storage`)
- **database.py**: SQLite database operations and schema management

#### Web (`/web`)
- **routes.py**: FastAPI endpoints for UI and API
- **templates/**: Jinja2 HTML templates for dashboard and forms

## Data Schemas

### PluginDefinition
Defines a plugin type's capabilities and configuration requirements.

```python
{
    "plugin_id": "numeric_index",
    "plugin_version": "1.0.0",
    "display_name": "Numeric Index",
    "description": "Tracks numeric values from URLs",
    "source_category": "NUMERIC",
    "config_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "format": "uri"},
            "baseline": {"type": "number"}
        },
        "required": ["url"]
    }
}
```

### SourceInstance
A configured instance of a plugin that will be periodically collected.

```python
{
    "source_id": "550e8400-e29b-41d4-a716-446655440000",
    "plugin_id": "numeric_index",
    "display_name": "S&P 500 Index",
    "enabled": true,
    "config": {"url": "https://api.example.com/sp500", "baseline": 4000},
    "weight": 2.0,
    "sentiment_polarity": "POSITIVE_IS_GOOD",
    "schedule": "0 * * * *"
}
```

### DistilledSnapshot (Canonical Storage)
The fundamental unit of persisted data. All analysis operates on these.

```python
{
    "source_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": "2026-01-14T12:00:00Z",
    "sentiment": 0.35,              # -1.0 to +1.0
    "sentiment_confidence": 0.8,    # 0.0 to 1.0
    "volatility": 0.12,             # Recent fluctuation measure
    "terms": [                      # Extracted keywords (may be empty)
        {
            "term": "market growth",
            "weight": 0.8,
            "polarity": 0.6,
            "novelty": 0.3
        }
    ],
    "term_entropy": 2.4,            # Diversity of terms
    "anomaly_score": 0.15,          # How unusual this snapshot is
    "coverage": 1.0                 # Data quality metric
}
```

### GlobalSentiment (Computed, Not Stored)
Aggregated metric computed on-demand from latest snapshots.

```python
{
    "timestamp": "2026-01-14T12:30:00Z",
    "global_sentiment": 0.42,
    "confidence": 0.75,
    "source_count": 5,
    "volatility": 0.18
}
```

## How the Plugin System Works

### Plugin Lifecycle

1. **Registration** (at startup)
   - Plugin classes are discovered in `/plugins` directory
   - Each plugin registers its definition with the registry
   - Definitions describe configuration schema and capabilities

2. **Configuration** (by user)
   - User selects a plugin type via web UI
   - User provides configuration matching plugin's schema
   - System creates a `SourceInstance` record

3. **Scheduling** (automatic)
   - Scheduler loads all enabled sources
   - Creates cron jobs based on each source's schedule
   - Jobs trigger the collect → distill pipeline

4. **Collection** (periodic)
   ```python
   raw_snapshot = await plugin.collect(source_instance)
   # Raw data is NOT persisted
   ```

5. **Distillation** (immediate)
   ```python
   history = await db.get_snapshot_history(source_id, limit=50)
   distilled = await plugin.distill(raw_snapshot, history)
   await db.save_snapshot(distilled)
   # Raw data is now discarded
   ```

6. **Aggregation** (on-demand)
   ```python
   global_sentiment = await aggregator.compute_global_sentiment()
   # Uses latest snapshots from all enabled sources
   ```

### Creating a New Plugin

To add a new data source type:

1. **Create plugin file** in `/plugins/my_plugin.py`

2. **Implement the interface**:
   ```python
   from plugins.base import PluginBase
   from core.schemas import *
   
   class MyPlugin(PluginBase):
       def get_definition(self) -> PluginDefinition:
           return PluginDefinition(
               plugin_id="my_plugin",
               plugin_version="1.0.0",
               display_name="My Data Source",
               description="Collects data from...",
               source_category=SourceCategory.TEXT,
               config_schema={
                   "type": "object",
                   "properties": {
                       "api_key": {"type": "string"},
                       "query": {"type": "string"}
                   },
                   "required": ["api_key"]
               }
           )
       
       async def collect(self, instance: SourceInstance) -> RawSnapshot:
           # Fetch data from external source
           # Return RawSnapshot with payload
           pass
       
       async def distill(self, raw: RawSnapshot, 
                        history: list[DistilledSnapshot]) -> DistilledSnapshot:
           # Extract sentiment, terms, calculate metrics
           # Return DistilledSnapshot for persistence
           pass
   ```

3. **Restart the application** - plugin is auto-discovered

4. **Add source instances** via web UI

### Plugin Best Practices

- **Collect**: Keep collection fast and focused. Include diagnostic info in `RawSnapshot.diagnostics`
- **Distill**: Use `history` to calculate volatility, anomaly scores, and trends
- **Terms**: Extract only meaningful keywords/entities. Empty list is valid for numeric sources
- **Errors**: Raise exceptions from `collect()` - scheduler will log and continue
- **Validation**: Override `validate_config()` for custom config validation logic

## Installation & Setup

### Requirements
- Python 3.12+
- SQLite 3

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/parallax-index.git
cd parallax-index

# Option A: Automated setup (recommended)
# Linux/macOS:
bash setup_venv.sh

# Windows:
setup_venv.bat

# Option B: Manual setup
python3.12 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python setup_check.py
```

### Running the Application

```bash
# Activate virtual environment (if not already activated)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Start the application
python main.py

# Or use VS Code task: Ctrl/Cmd+Shift+P → Tasks: Run Task → Run: Start Application
```

The application will:
1. Initialize the database (`parallax_index.db`)
2. Discover and register plugins
3. Start the scheduler
4. Launch the web server on `http://localhost:8000`

### First Steps

1. **Visit the dashboard**: `http://localhost:8000`
2. **Add a source**: Click "Add Source" and configure a numeric index
3. **Enable the source**: Toggle to start periodic collection
4. **Wait for data**: First snapshot appears after the next scheduled run
5. **View results**: Dashboard shows global sentiment and source details

## Adding Your First Source

Example: Tracking a public API that returns a numeric value

1. Navigate to `/sources/new`
2. Select **Numeric Index** plugin
3. Configure:
   - **Display Name**: "Example Metric"
   - **URL**: `https://api.example.com/value`
   - **Enabled**: ✓
   - **Weight**: 1.0
   - **Schedule**: `0 * * * *` (every hour)
4. Click **Create Source**

The system will:
- Validate the configuration
- Schedule hourly collection
- Begin collecting at the next hour mark
- Display results on the dashboard

## Configuration

### Schedule Format (Cron)

```
 ┌───────── minute (0 - 59)
 │ ┌─────── hour (0 - 23)
 │ │ ┌───── day of month (1 - 31)
 │ │ │ ┌─── month (1 - 12)
 │ │ │ │ ┌─ day of week (0 - 6) (Sunday = 0)
 │ │ │ │ │
 * * * * *
```

Examples:
- `0 * * * *` - Every hour at minute 0
- `*/15 * * * *` - Every 15 minutes
- `0 */4 * * *` - Every 4 hours
- `0 9 * * 1` - Every Monday at 9:00 AM

### Weight & Polarity

- **Weight** (0-10): Influence in global aggregation. Higher = more influence
- **Polarity**:
  - `POSITIVE_IS_GOOD`: Higher values = positive sentiment (e.g., GDP)
  - `NEGATIVE_IS_GOOD`: Lower values = positive sentiment (e.g., unemployment)
  - `NEUTRAL`: No directional interpretation

## Schema Stability Guarantees

### What Will NOT Change
- Core field names in `DistilledSnapshot` (sentiment, confidence, volatility, etc.)
- Plugin interface method signatures (`collect`, `distill`)
- Database table primary structures

### What MAY Change (with migration)
- Addition of optional fields to schemas
- New plugin interface methods with default implementations
- Database schema additions (new tables, optional columns)

### Migration Strategy
- All schema changes will be announced and documented
- Migration scripts will be provided for database changes
- Old plugin versions will continue to work (forward compatibility)

## API Endpoints

### Dashboard
- `GET /` - Main dashboard with global sentiment
- `GET /sources` - List all sources
- `GET /sources/new` - Form to add new source
- `GET /sources/{id}` - View source details

### Source Management
- `POST /sources/create` - Create new source
- `POST /sources/{id}/toggle` - Enable/disable source
- `POST /sources/{id}/collect` - Trigger immediate collection
- `DELETE /sources/{id}` - Delete source

### API (JSON)
- `GET /api/plugins` - List available plugins
- `GET /api/sources` - List sources as JSON
- `GET /api/sentiment/global` - Current global sentiment
- `GET /health` - System health check

## Development

### Project Structure
```
parallax-index/
├── core/
│   ├── __init__.py
│   ├── schemas.py          # Pydantic models
│   ├── aggregation.py      # Sentiment aggregation
│   └── scheduler.py        # Collection scheduling
├── plugins/
│   ├── __init__.py
│   ├── base.py            # Plugin interface
│   ├── registry.py        # Plugin discovery
│   └── numeric_index.py   # Example plugin
├── storage/
│   ├── __init__.py
│   └── database.py        # SQLite operations
├── web/
│   ├── __init__.py
│   ├── routes.py          # FastAPI routes
│   └── templates/         # HTML templates
│       ├── base.html
│       ├── dashboard.html
│       ├── sources.html
│       ├── source_form.html
│       └── source_detail.html
├── main.py                # Application entry point
├── requirements.txt       # Python dependencies
├── .gitignore
└── README.md
```

### Running Tests

```bash
# TODO: Implement test suite
# pytest tests/
```

### Code Style
- Follow PEP 8
- Use type hints throughout
- Document all public methods with docstrings
- Keep functions focused and testable

## Roadmap

### Phase 1: Foundation (Complete)
- ✅ Plugin system architecture
- ✅ Source instance management
- ✅ Scheduled collection and distillation
- ✅ Database layer
- ✅ Web interface
- ✅ Numeric index plugin

### Phase 2: Enhancement
- [ ] Additional plugins (TEXT, EVENT categories)
- [ ] Advanced anomaly detection
- [ ] Historical trend visualization
- [ ] Export/import functionality
- [ ] Comprehensive test suite

### Phase 3: Scale
- [ ] Multi-user support (optional authentication)
- [ ] Plugin marketplace/registry
- [ ] Advanced aggregation strategies
- [ ] API rate limiting and caching
- [ ] Distributed collection (optional)

## Troubleshooting

### Source not collecting data
1. Check source is enabled: `GET /sources/{id}`
2. Verify schedule syntax is valid cron format
3. Check application logs for errors
4. Try manual collection: `POST /sources/{id}/collect`

### Database locked errors
- SQLite is single-writer. High-frequency collection may cause conflicts
- Increase collection intervals or migrate to PostgreSQL

### Plugin not appearing
- Ensure plugin file is in `/plugins` directory
- Check class inherits from `PluginBase`
- Verify no syntax errors in plugin file
- Restart application to re-discover plugins

## Contributing

This is a foundational MVP designed for extensibility. Contributions welcome:

1. **New Plugins**: Implement `PluginBase` for new data source types
2. **Enhancements**: Improve aggregation algorithms, add visualizations
3. **Documentation**: Clarify usage, add examples
4. **Tests**: Add unit and integration tests

## License

[Specify your license here]

## Contact

[Your contact information]

---

**Parallax Index** - Tracking the global sentiment landscape, one snapshot at a time.
