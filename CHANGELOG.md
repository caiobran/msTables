# Changelog

All notable changes to mstables will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Nano Versioning](https://semver.org/):
- 1.0.1, 1.0.2, ..., 1.0.9 (patch increments)
- 1.0.9 → 1.1.0 (minor increment when patch reaches 9)
- 1.9.9 → 2.0.0 (major increment when minor reaches 9)

---

## [Unreleased]

### Added
- DandE.db database for tracking tests, errors, trial runs, and TODOs
- Nano versioning system (VersionManager)
- DDD test pyramid structure (Unit, Integration, E2E tests)
- Docker setup with PostgreSQL for financial data
- SQLite for DandE.db (development/operational tracking)
- Version tracking in CHANGELOG.md

### Changed
- Updated project structure to support Docker architecture

### Fixed
- Database connection handling
- Test infrastructure setup

---

## [1.0.1] - 2025-01-XX

### Added
- Initial nano versioning setup
- DandE.db schema for test/error/trial/TODO tracking
- Docker Compose configuration
- PostgreSQL service for financial data
- SQLite for DandE.db (local development tracking)
- CHANGELOG.md with version tracking

### Changed
- Updated pyproject.toml version to 1.0.1

### Architecture
- **Financial Data**: PostgreSQL (Docker container)
  - Production-ready database
  - Better concurrent access
  - Scalable for large datasets
  - Port: 5432
- **DandE.db**: SQLite (local file in data/)
  - Development/operational metadata
  - Test results, errors, trials, TODOs
  - Simpler setup, no container needed
  - Tracked in version control

---

[Unreleased]: https://github.com/datatalking/mstables/compare/v1.0.1...HEAD
[1.0.1]: https://github.com/datatalking/mstables/releases/tag/v1.0.1

