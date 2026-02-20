# AGENTS.md - Agent Coding Guidelines

This file provides guidelines for agents working on this codebase.

## Project Overview

This repository contains two main modules:
- **bootstrap/**: DFS bootstrap manifest builder - recursively walks file shares, extracts metadata and ACLs, stores in SQLite manifest database
- **ingestion/**: NVIDIA RAG ingestion module - reads from bootstrap manifest and uploads documents to NVIDIA RAG

## Build/Lint/Test Commands

### Common Operations (both modules)

```bash
# Install dependencies
uv sync

# Run all tests
uv run pytest

# Run a single test (specify test path)
uv run pytest path/to/test_file.py::test_function_name

# Type checking
uv run mypy <module>/

# Lint check
uv run ruff check <module>/

# Format code
uv run ruff format <module>/

# Lock dependencies
uv lock
```

### Bootstrap Module

```bash
cd bootstrap

# Run discovery
uv run python -m bootstrap /path/to/dfs_share

# With options
uv run python -m bootstrap /path/to/dfs_share \
  --db-path ./manifest.db \
  --workers 8 \
  --batch-size 500 \
  --timeout 5
```

### Ingestion Module

```bash
cd ingestion

# Run ingestion
uv run python -m ingestion --db-path ../bootstrap/manifest.db --collection-name docs

# Resume from checkpoint
uv run python -m ingestion --resume --checkpoint-file ./checkpoint.json
```

## Code Style Guidelines

### General

- **Python Version**: 3.12+
- **Line Length**: 100 characters (configured in pyproject.toml)
- **Package Manager**: UV
- **Build System**: Hatchling

### Imports

- Use absolute imports: `from ingestion.client import IngestionClient`
- Group imports: stdlib, third-party, local
- Sort imports alphabetically within groups
- Use `|` union types (Python 3.10+ syntax)

### Formatting

- Follow Ruff formatting rules (line-length: 100)
- Use 4 spaces for indentation
- Use `ruff format` to auto-format

### Type Annotations

- Use strict mypy settings (configured in pyproject.toml)
- Always type annotate function arguments and return values
- Use `X | None` instead of `Optional[X]`
- Use `dict[str, str]` instead of `Dict[str, str]`

### Naming Conventions

- **Classes**: `PascalCase` (e.g., `IngestionClient`)
- **Functions/variables**: `snake_case` (e.g., `get_ingestion_stats`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `POLL_INTERVAL`)
- **Modules**: `snake_case` (e.g., `client.py`)

### Error Handling

- Use custom exception classes for domain errors:
  ```python
  class IngestionError(Exception):
      """Custom exception for ingestion errors."""
      pass
  ```
- Always chain exceptions with `from e`
- Log errors with appropriate level before raising
- Use specific exception types, avoid bare `except:`

### Code Patterns

#### Configuration (Pydantic Settings)

Use Pydantic for configuration:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="INGESTION_")
    
    db_path: Path = Path("./manifest.db")
    log_level: str = "INFO"
```

#### Database Operations

- Use SQLAlchemy with explicit connection management
- Use context managers for transactions
- Store connection in repository classes

#### Logging

- Use structured logging with `structlog` (in bootstrap)
- Use standard `logging` module (in ingestion)
- Include relevant context in log messages

#### Async Code

- Use `async`/`await` syntax
- Use proper async context managers
- Avoid blocking calls in async functions

### Lint Rules (Ruff)

Enabled rules: E, F, W, I, N, D, UP, B, C4, SIM

Key rules:
- E: pycodestyle errors
- F: pyflakes
- W: warnings
- I: isort
- N: naming conventions
- D: docstrings
- UP: pyupgrade
- B: flake8-bugbear
- C4: flake8-comprehensions
- SIM: flake8-simplify

### Testing

- Use pytest with pytest-asyncio
- Place tests in appropriate locations
- Follow naming: `test_*.py` or `*_test.py`
- Use descriptive test function names

### File Structure

```
<module>/
├── pyproject.toml           # UV configuration
├── <module>/                # Main package
│   ├── __init__.py          # Package exports
│   ├── __main__.py          # CLI entry
│   ├── config.py            # Settings
│   ├── main.py              # Orchestrator
│   ├── client.py            # HTTP client
│   ├── repository.py        # DB operations
│   └── ...
├── logs/                    # Log output
└── README.md
```

## Common Issues to Avoid

1. **Don't use bare `except:`** - catch specific exceptions
2. **Don't suppress exceptions silently** - log or handle appropriately
3. **Don't use mutable default arguments** - use `None` and assign inside function
4. **Don't forget to close resources** - use context managers
5. **Don't ignore type hints** - mypy strict mode is enabled
6. **Don't use relative imports** - use absolute imports

## Environment Variables

### Bootstrap
- `BOOTSTRAP_DFS_PATH`
- `BOOTSTRAP_DB_PATH`
- `BOOTSTRAP_LOG_LEVEL`
- `BOOTSTRAP_WORKERS`
- `BOOTSTRAP_BATCH_SIZE`
- `BOOTSTRAP_ACL_EXTRACTOR`

### Ingestion
- `INGESTION_DB_PATH`
- `INGESTION_INGESTOR_HOST`
- `INGESTION_INGESTOR_PORT`
- `INGESTION_COLLECTION_NAME`
- `INGESTION_BATCH_SIZE`
