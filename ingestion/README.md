# NVIDIA RAG Ingestion Module

Production-ready ingestion module that reads from the bootstrap manifest database and uploads documents to NVIDIA RAG with ACL metadata.

## Features

- **Batch Processing**: Configurable batch size (default: 100 files)
- **Resume Capability**: JSON-based checkpointing with automatic recovery
- **Retry Logic**: Exponential backoff with configurable max retries
- **State Tracking**: Updates ingestion status in manifest database
- **ACL Metadata**: Parses raw_acl column and sends as document metadata
- **Error Handling**: Continue on error or stop on first failure
- **Progress Reporting**: Detailed logging with statistics

## Quick Start

```bash
# Setup
cd ingestion
uv sync

# Run ingestion
uv run python -m ingestion --db-path ../bootstrap/manifest.db --collection-name docs

# Resume from checkpoint
uv run python -m ingestion --resume --checkpoint-file ./checkpoint.json

# With all options
uv run python -m ingestion \
  --db-path ./manifest.db \
  --ingestor-host localhost \
  --ingestor-port 8082 \
  --collection-name secure_docs \
  --batch-size 100 \
  --create-collection \
  --continue-on-error
```

## Configuration

Configuration via environment variables (all optional):

```bash
export INGESTION_DB_PATH=./manifest.db
export INGESTION_INGESTOR_HOST=localhost
export INGESTION_INGESTOR_PORT=8082
export INGESTION_COLLECTION_NAME=documents
export INGESTION_BATCH_SIZE=100
export INGESTION_LOG_LEVEL=INFO

# Then run
uv run python -m ingestion
```

## Database Schema

The module expects these columns in the manifest table (add via migration):

```sql
-- Add to existing manifest table
ALTER TABLE manifest ADD COLUMN ingestion_status TEXT DEFAULT 'pending';
ALTER TABLE manifest ADD COLUMN ingestion_attempts INTEGER DEFAULT 0;
ALTER TABLE manifest ADD COLUMN ingestion_error TEXT;
ALTER TABLE manifest ADD COLUMN ingested_at TIMESTAMP;

-- Create index for performance
CREATE INDEX idx_manifest_ingestion_status ON manifest(ingestion_status);
```

## Module Structure

```
ingestion/
├── ingestion/
│   ├── __init__.py          # Package exports
│   ├── __main__.py          # CLI entry point
│   ├── config.py            # Pydantic settings
│   ├── client.py            # NVIDIA RAG HTTP client
│   ├── checkpoint.py        # Resume capability
│   ├── processor.py         # Main ingestion logic
│   ├── repository.py        # Database operations
│   └── main.py              # Orchestrator
├── pyproject.toml
└── README.md
```

## CLI Options

| Option | Description | Default |
|--------|-------------|---------|
| `--db-path` | Path to manifest database | `./manifest.db` |
| `--ingestor-host` | RAG ingestor host | `localhost` |
| `--ingestor-port` | RAG ingestor port | `8082` |
| `--collection-name` | Target collection | `documents` |
| `--batch-size` | Files per batch | `100` |
| `--checkpoint-interval` | Save every N batches | `10` |
| `--resume` | Resume from checkpoint | `False` |
| `--create-collection` | Create collection first | `True` |
| `--continue-on-error` | Skip failed files | `True` |
| `--max-retries` | Retry attempts per file | `3` |

## How It Works

1. **Query Database**: Fetches files with `status='discovered'` and `ingestion_status='pending'`
2. **Verify Files**: Checks if files exist on disk before processing
3. **Build Payload**: Creates metadata payload with ACL information from `raw_acl` column
4. **Upload Batch**: Sends files via multipart POST to `/v1/documents`
5. **Update State**: Marks files as completed/failed in database
6. **Checkpoint**: Saves progress every N batches
7. **Resume**: Can restart from last checkpoint

## Error Handling

- **File Not Found**: Marked as failed, continues processing
- **Upload Failure**: Retried with exponential backoff
- **API Errors**: Logged with detail, optionally continues
- **Interrupt**: Saves checkpoint on Ctrl+C

## License

MIT
