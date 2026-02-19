# Bootstrap Manifest Builder

Production-ready DFS discovery tool that recursively walks file shares, extracts metadata and ACLs, and stores everything in a SQLite manifest database.

## Features

- **Recursive Discovery**: Walks entire DFS tree using `os.scandir` for performance
- **File Extension Filtering**: Only processes supported file types (see list below)
- **Permission Error Handling**: Records permission errors in DB with proper status
- **ACL Extraction**: Tries `getfacl` first, falls back to `stat` info
- **Timeout Handling**: 5-minute timeout per file operation
- **Batch Processing**: Configurable batch inserts (default: 500 records)
- **Resumable**: Safe to restart - uses `INSERT OR IGNORE`
- **Structured Logging**: JSON logs + human-readable console output
- **Production Ready**: Full error handling, retry logic, progress reporting

## Supported File Extensions

Only files with these extensions are processed and stored in the manifest:

| Extension | Notes |
|-----------|-------|
| `.avi` | Early access |
| `.bmp` | |
| `.docx` | |
| `.html` | Converted to markdown format |
| `.jpeg` / `.jpg` | |
| `.json` | Treated as text |
| `.md` | Treated as text |
| `.mkv` | Early access |
| `.mov` | Early access |
| `.mp3` | |
| `.mp4` | Early access |
| `.pdf` | |
| `.png` | |
| `.pptx` | |
| `.sh` | Treated as text |
| `.tiff` / `.tif` | |
| `.txt` | |
| `.wav` | |

**Unsupported files are automatically skipped** - no ACL extraction or database storage.

## Quick Start

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and setup
cd bootstrap
uv sync

# Run discovery
uv run python -m bootstrap /mnt/dfs_share

# Or with options
uv run python -m bootstrap /mnt/dfs_share \
  --db-path ./manifest.db \
  --workers 8 \
  --batch-size 500 \
  --timeout 5 \
  --log-level INFO
```

## Configuration

Configuration can be set via environment variables or CLI arguments:

```bash
# Environment variables (all optional)
export BOOTSTRAP_DFS_PATH=/mnt/dfs_share
export BOOTSTRAP_DB_PATH=./manifest.db
export BOOTSTRAP_LOG_FILE=./logs/bootstrap.log
export BOOTSTRAP_LOG_LEVEL=INFO
export BOOTSTRAP_WORKERS=8
export BOOTSTRAP_BATCH_SIZE=500
export BOOTSTRAP_TIMEOUT=5
export BOOTSTRAP_PROGRESS_INTERVAL=10000
export BOOTSTRAP_ACL_EXTRACTOR=getfacl  # getfacl, stat, or noop

# Then run without arguments
uv run python -m bootstrap
```

## Pluggable ACL Extractors

The ACL extraction is extensible via a plugin architecture. Three built-in implementations are provided:

| Extractor | Description | Use Case |
|-----------|-------------|----------|
| `getfacl` | **Default** - Tries getfacl first, falls back to stat | Best for Linux/CIFS mounts with full ACL support |
| `stat` | Stat only, no getfacl | Faster when you only need basic permissions |
| `noop` | No ACL extraction | Fastest when you don't need ACL info at all |

### Usage Examples

```bash
# Default (getfacl + stat fallback)
uv run python -m bootstrap /mnt/dfs_share

# Stat only (faster, no getfacl dependency)
uv run python -m bootstrap /mnt/dfs_share --acl-extractor stat

# No ACL extraction (fastest)
uv run python -m bootstrap /mnt/dfs_share --acl-extractor noop

# Via environment variable
export BOOTSTRAP_ACL_EXTRACTOR=stat
uv run python -m bootstrap /mnt/dfs_share
```

### Creating Custom ACL Extractors

You can implement custom ACL extractors by subclassing `ACLExtractor`:

```python
from bootstrap.discovery.acl_extractor import ACLExtractor, ACLResult
from pathlib import Path

class MyCustomACLExtractor(ACLExtractor):
    @property
    def name(self) -> str:
        return "my-custom"
    
    async def extract(self, file_path: Path, timeout_seconds: float = 300.0) -> ACLResult:
        # Your custom ACL extraction logic here
        return ACLResult(
            raw_acl="custom_acl_data",
            captured=True,
            method="my-custom",
        )
```

Then use it in the walker:

```python
from bootstrap.discovery import DirectoryWalker

walker = DirectoryWalker(
    acl_extractor=MyCustomACLExtractor()
)
```

## Database Schema

```sql
manifest
  id INTEGER PRIMARY KEY
  file_path TEXT UNIQUE NOT NULL     -- Absolute file path
  file_name TEXT NOT NULL             -- Base name
  parent_dir TEXT NOT NULL            -- Parent directory
  size INTEGER                        -- File size in bytes
  mtime INTEGER                       -- Modification timestamp
  raw_acl TEXT                        -- ACL data (JSON or raw)
  acl_captured BOOLEAN DEFAULT FALSE  -- ACL success flag
  status TEXT DEFAULT 'pending'       -- discovery/permission_denied/acl_failed/error/skipped
  error TEXT                          -- Error message if any
  retry_count INTEGER DEFAULT 0       -- Retry attempts
  is_directory BOOLEAN DEFAULT FALSE  -- True for directories
  first_seen TIMESTAMP                -- First discovery time
  last_seen TIMESTAMP                 -- Last update time
  schema_version INTEGER DEFAULT 1
```

## Error Handling

| Status | Meaning | Action |
|--------|---------|--------|
| `discovered` | Successfully processed | None |
| `permission_denied` | Cannot access file/dir | Check service account permissions |
| `acl_failed` | ACL extraction failed | Check getfacl availability |
| `error` | Other errors | Check logs |
| `skipped` | Symlinks, etc. | Normal - prevents cycles |

## Output Example

```
✓ Bootstrap complete
  Total files discovered: 847,293
  Records added: 847,293
  Records skipped (already existed): 0
  ACL captured: 845,120 (99.7%)
  ACL failed: 2,173
  Permission errors: 0
  Time elapsed: 872.5s
  Records/second: 971.5
```

## Project Structure

```
bootstrap/
├── pyproject.toml           # UV configuration
├── uv.lock                  # Dependency lock
├── bootstrap/
│   ├── __init__.py
│   ├── __main__.py         # CLI entry
│   ├── config.py           # Settings (Pydantic)
│   ├── logging_config.py   # Structured logging
│   ├── main.py             # Orchestrator
│   ├── database/
│   │   ├── connection.py   # SQLite engine with WAL
│   │   ├── schema.py       # Table definitions
│   │   └── repository.py   # DB operations
│   ├── discovery/
│   │   ├── walker.py       # Directory walker
│   │   ├── acl_extractor.py # ACL extraction
│   │   └── batch_processor.py
│   └── models/
│       └── file_record.py  # Data models
├── logs/                   # Log output
└── README.md
```

## Development

```bash
# Run tests
uv run pytest

# Type checking
uv run mypy bootstrap/

# Linting
uv run ruff check bootstrap/
uv run ruff format bootstrap/

# Lock dependencies
uv lock
```

## Resumability

If the bootstrap crashes halfway, simply re-run it:

```bash
# Already processed files are skipped
uv run python -m bootstrap /mnt/dfs_share
```

The tool uses `INSERT OR IGNORE` so existing records are safely skipped, and only new files are added.

## License

MIT