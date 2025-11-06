# Docker Setup Guide

## Architecture Overview

This project uses a hybrid database architecture optimized for different use cases:

### **Financial Data: PostgreSQL (Docker Container)**
- **Purpose**: Production financial data storage
- **Why**: Better concurrent access, scalability, performance for large datasets
- **Location**: Docker container (`postgres` service)
- **Port**: 5432
- **Database**: `mstables`
- **User**: `mstables_user`

### **DandE.db: SQLite (Local File)**
- **Purpose**: Development/operational tracking (tests, errors, trials, TODOs)
- **Why**: Simpler setup, no container needed, lightweight for metadata
- **Location**: `data/DandE.db` (local file, mounted as volume)
- **Tracked**: Version controlled in git

## Quick Start

### 1. Start Docker Services

```bash
# Start PostgreSQL and app containers
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f postgres
docker-compose logs -f app
```

### 2. Verify PostgreSQL Connection

```bash
# Connect to PostgreSQL
docker exec -it mstables-postgres psql -U mstables_user -d mstables

# Or from host machine
psql -h localhost -p 5432 -U mstables_user -d mstables
```

### 3. Verify DandE.db

```bash
# Check if DandE.db exists
ls -la data/DandE.db

# Query DandE.db
sqlite3 data/DandE.db "SELECT * FROM versions LIMIT 5;"
```

## Database Configuration

### Environment Variables

The application uses environment variables for database configuration:

```bash
# PostgreSQL (Financial Data)
POSTGRES_HOST=postgres          # Container name or localhost
POSTGRES_PORT=5432
POSTGRES_USER=mstables_user
POSTGRES_PASSWORD=mstables_password
POSTGRES_DB=mstables
FINANCIAL_DB_TYPE=postgresql

# SQLite (DandE.db)
DANDE_DB_PATH=data/DandE.db
SQLITE_DB_PATH=data/mstables.sqlite
```

### Connection Strings

The `DatabaseAdapter` class automatically detects the database type:

```python
from src.utils.database_adapter import FinancialDataDB, DandEDB

# PostgreSQL connection (auto-detected from env vars)
financial_db = FinancialDataDB()

# SQLite connection (DandE.db)
dande_db = DandEDB()
```

## Development Workflow

### 1. Version Bump with Tests

```bash
# Run version bump script (increments version, runs tests, commits)
python scripts/version_bump.py "Added new feature"

# Or increment manually
python -c "from src.utils.version_manager import VersionManager; vm = VersionManager(); vm.increment_nano(); vm.save_version()"
```

### 2. Run Tests

```bash
# Run all tests (unit, integration, e2e)
python -c "from src.utils.test_runner import TestRunner; runner = TestRunner(); runner.run_all_tests()"

# Run specific test type
pytest tests/unit/ -v
pytest tests/integration/ -v
pytest tests/e2e/ -v
```

### 3. Check DandE.db Status

```bash
# View version history
sqlite3 data/DandE.db "SELECT version, created_at, description FROM versions ORDER BY created_at DESC LIMIT 10;"

# View test results
sqlite3 data/DandE.db "SELECT test_name, status, completed_at FROM tests ORDER BY completed_at DESC LIMIT 10;"

# View errors
sqlite3 data/DandE.db "SELECT error_type, severity, occurred_at FROM errors WHERE resolved_at IS NULL ORDER BY occurred_at DESC LIMIT 10;"
```

## Data Migration

### From SQLite to PostgreSQL

If you have existing data in `mstables.sqlite`, you can migrate:

```bash
# Create migration script (example)
python scripts/migrate_sqlite_to_postgres.py
```

### Backup and Restore

```bash
# Backup PostgreSQL
docker exec mstables-postgres pg_dump -U mstables_user mstables > backup.sql

# Restore PostgreSQL
docker exec -i mstables-postgres psql -U mstables_user mstables < backup.sql

# Backup DandE.db
cp data/DandE.db data/backup/DandE_$(date +%Y%m%d_%H%M%S).db
```

## Docker Commands

### Start Services

```bash
docker-compose up -d          # Start in background
docker-compose up             # Start with logs
docker-compose start          # Start existing containers
```

### Stop Services

```bash
docker-compose stop           # Stop containers
docker-compose down           # Stop and remove containers
docker-compose down -v        # Stop and remove volumes (⚠️ deletes data!)
```

### Access Containers

```bash
# Access app container
docker exec -it mstables-app bash

# Access PostgreSQL container
docker exec -it mstables-postgres bash

# Run command in container
docker exec mstables-app python main.py
```

### View Logs

```bash
docker-compose logs -f        # All services
docker-compose logs -f postgres  # PostgreSQL only
docker-compose logs -f app    # App only
```

## Testing with Docker

### Run Tests in Container

```bash
# Run all tests
docker exec mstables-app pytest tests/ -v

# Run specific test type
docker exec mstables-app pytest tests/unit/ -v
docker exec mstables-app pytest tests/integration/ -v
docker exec mstables-app pytest tests/e2e/ -v
```

### Test Database Connections

```bash
# Test PostgreSQL connection
docker exec mstables-app python -c "from src.utils.database_adapter import FinancialDataDB; db = FinancialDataDB(); print('Connected!'); db.close()"

# Test SQLite connection
docker exec mstables-app python -c "from src.utils.database_adapter import DandEDB; db = DandEDB(); print('Connected!'); db.close()"
```

## Troubleshooting

### PostgreSQL Connection Issues

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check PostgreSQL logs
docker-compose logs postgres

# Test connection
docker exec mstables-postgres pg_isready -U mstables_user
```

### DandE.db Issues

```bash
# Check if DandE.db exists
ls -la data/DandE.db

# Recreate DandE.db
rm data/DandE.db
python -c "from src.utils.dande_db import DandEDatabase; db = DandEDatabase(); db.close()"
```

### Volume Issues

```bash
# Check volumes
docker volume ls

# Inspect volume
docker volume inspect mstables_postgres_data

# Remove and recreate (⚠️ deletes data!)
docker-compose down -v
docker-compose up -d
```

## Performance Tuning

For large datasets, you can tune PostgreSQL:

```bash
# Edit postgresql.conf in container
docker exec -it mstables-postgres bash
# Edit /var/lib/postgresql/data/postgresql.conf
# Increase shared_buffers, work_mem, etc.
```

## Security Notes

- Change default passwords in `docker-compose.yml` for production
- Use secrets management for sensitive data
- Restrict PostgreSQL port exposure if not needed externally
- Regularly backup both databases

