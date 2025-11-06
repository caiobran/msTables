# DDD Compliance Merge Plan

## Overview

This document outlines the plan to merge `Project_Template/` and other folders into mstables for DDD (Domain-Driven Design) compliance, as required by PDS v2.0.0.

## Current State

### Folders to Merge
1. **`Project_Template/`** (inside mstables) - Contains universal codebase improvement framework
2. **`mstables_002/`** - Appears to be an older version/copy of mstables
3. **`Project_Template/`** (at root level `/Users/xavier/PycharmProjects/Project_Template/`) - The source template

### Issues Identified
- ❌ **Project_Template** inside mstables is redundant (should be merged or removed)
- ❌ **mstables_002** appears to be duplicate/old version (should be merged or archived)
- ❌ **No DDD domain structure** - Code is not organized by domain boundaries
- ❌ **No clear separation** between domain, application, and infrastructure layers

## DDD Structure Requirements (PDS v2.0.0)

### Required Structure
```
mstables/
├── src/
│   ├── domain/           # Domain layer (business logic, entities, value objects)
│   │   ├── entities/     # Domain entities
│   │   ├── value_objects/ # Value objects
│   │   ├── services/     # Domain services
│   │   └── repositories/ # Repository interfaces
│   ├── application/      # Application layer (use cases, application services)
│   │   ├── commands/     # Command handlers
│   │   ├── queries/      # Query handlers
│   │   └── services/      # Application services
│   ├── infrastructure/   # Infrastructure layer (external concerns)
│   │   ├── database/     # Database implementations
│   │   ├── api/          # API clients
│   │   ├── storage/     # File storage
│   │   └── messaging/    # Message queues
│   └── presentation/     # Presentation layer (UI, CLI)
│       ├── cli/          # CLI commands
│       └── api/          # REST API (if needed)
├── tests/
│   ├── unit/
│   │   └── domain/       # Domain unit tests
│   ├── integration/
│   │   └── application/  # Application integration tests
│   └── e2e/
│       └── infrastructure/ # Infrastructure E2E tests
└── docs/
    ├── domain/           # Domain documentation
    ├── architecture/     # Architecture diagrams
    └── api/              # API documentation
```

## Merge Strategy

### Phase 1: Analyze and Plan (Version 1.0.3)

#### Step 1.1: Analyze Project_Template Contents
- [ ] Identify reusable components from `Project_Template/`
- [ ] Map components to DDD layers (domain/application/infrastructure)
- [ ] Identify dependencies and conflicts
- [ ] Document merge conflicts

#### Step 1.2: Analyze mstables_002 Contents
- [ ] Compare `mstables_002/` with current `mstables/`
- [ ] Identify unique code/data that needs to be preserved
- [ ] Identify duplicate code that can be removed
- [ ] Plan migration of any unique data

#### Step 1.3: Create DDD Domain Model
- [ ] Identify domain entities (Stock, Market, Portfolio, etc.)
- [ ] Identify value objects (Price, Date, Symbol, etc.)
- [ ] Identify domain services (MarketAnalysis, RiskCalculation, etc.)
- [ ] Identify aggregates (Portfolio, TradingStrategy, etc.)

### Phase 2: Restructure for DDD (Version 1.0.4)

#### Step 2.1: Create Domain Layer
- [ ] Create `src/domain/entities/` - Domain entities
- [ ] Create `src/domain/value_objects/` - Value objects
- [ ] Create `src/domain/services/` - Domain services
- [ ] Create `src/domain/repositories/` - Repository interfaces
- [ ] Migrate business logic from `src/utils/` to domain layer

#### Step 2.2: Create Application Layer
- [ ] Create `src/application/commands/` - Command handlers
- [ ] Create `src/application/queries/` - Query handlers
- [ ] Create `src/application/services/` - Application services
- [ ] Migrate use cases to application layer

#### Step 2.3: Reorganize Infrastructure Layer
- [ ] Move database code to `src/infrastructure/database/`
- [ ] Move API clients to `src/infrastructure/api/`
- [ ] Move file storage to `src/infrastructure/storage/`
- [ ] Keep SLURM in `src/infrastructure/` (already correct)

### Phase 3: Merge Project_Template (Version 1.0.5)

#### Step 3.1: Extract Useful Components
- [ ] Extract `universal_codebase_improver.py` → `src/infrastructure/codebase_improver.py`
- [ ] Extract `pds_compliance_checker.py` → `src/infrastructure/compliance_checker.py`
- [ ] Extract `master_implementation_script.py` → `scripts/master_implementation.py`
- [ ] Extract documentation → `docs/pds/`

#### Step 3.2: Merge Documentation
- [ ] Merge `Project_Template/Assets/PROJECT_DEVELOPMENT_STANDARD.md` → `docs/PDS.md`
- [ ] Merge `Project_Template/CRITICAL_LESSONS_LEARNED.md` → `docs/CRITICAL_LESSONS_LEARNED.md`
- [ ] Merge `Project_Template/UNIVERSAL_CODEBASE_IMPROVEMENT_FRAMEWORK.md` → `docs/IMPROVEMENT_FRAMEWORK.md`
- [ ] Update cross-references

#### Step 3.3: Clean Up
- [ ] Remove `Project_Template/` folder from mstables
- [ ] Update imports and references
- [ ] Update tests

### Phase 4: Merge mstables_002 (Version 1.0.6)

#### Step 4.1: Compare and Extract
- [ ] Compare `mstables_002/src/` with `mstables/src/`
- [ ] Extract unique code/data
- [ ] Identify version differences
- [ ] Plan migration

#### Step 4.2: Migrate Unique Content
- [ ] Migrate unique code to appropriate DDD layer
- [ ] Migrate unique data to `data/archive/`
- [ ] Update database schemas if needed

#### Step 4.3: Archive
- [ ] Move `mstables_002/` to `data/archive/mstables_002/`
- [ ] Document what was archived
- [ ] Update CHANGELOG.md

## DDD Domain Model for mstables

### Domain Entities
- **Stock** - Represents a stock/security
- **Market** - Represents a market/exchange
- **Portfolio** - Represents a portfolio of holdings
- **TradingStrategy** - Represents a trading strategy
- **BacktestResult** - Represents backtest results

### Value Objects
- **Price** - Stock price with currency
- **Date** - Date value object
- **Symbol** - Stock symbol with exchange
- **Volume** - Trading volume
- **Return** - Return percentage

### Domain Services
- **MarketAnalysisService** - Market analysis logic
- **RiskCalculationService** - Risk calculation logic
- **PriceCalculationService** - Price calculation logic
- **PortfolioOptimizationService** - Portfolio optimization

### Aggregates
- **Portfolio** - Aggregate root for portfolio management
- **TradingStrategy** - Aggregate root for strategy management
- **Backtest** - Aggregate root for backtest management

## Implementation Checklist

### Phase 1: Analysis (Version 1.0.3)
- [ ] Create domain model document
- [ ] Analyze Project_Template contents
- [ ] Analyze mstables_002 contents
- [ ] Create merge conflict resolution plan
- [ ] Document merge strategy

### Phase 2: Restructure (Version 1.0.4)
- [ ] Create domain layer structure
- [ ] Create application layer structure
- [ ] Reorganize infrastructure layer
- [ ] Migrate business logic to domain layer
- [ ] Update tests to match new structure

### Phase 3: Merge Project_Template (Version 1.0.5)
- [ ] Extract useful components
- [ ] Merge documentation
- [ ] Remove Project_Template folder
- [ ] Update imports
- [ ] Update tests

### Phase 4: Merge mstables_002 (Version 1.0.6)
- [ ] Compare and extract unique content
- [ ] Migrate unique code/data
- [ ] Archive mstables_002
- [ ] Update CHANGELOG.md

## Files to Create

### Domain Layer
- `src/domain/entities/stock.py`
- `src/domain/entities/market.py`
- `src/domain/entities/portfolio.py`
- `src/domain/value_objects/price.py`
- `src/domain/value_objects/symbol.py`
- `src/domain/services/market_analysis_service.py`
- `src/domain/repositories/stock_repository.py`

### Application Layer
- `src/application/commands/import_stock_command.py`
- `src/application/queries/get_stock_query.py`
- `src/application/services/stock_import_service.py`

### Infrastructure Layer
- `src/infrastructure/codebase_improver.py` (from Project_Template)
- `src/infrastructure/compliance_checker.py` (from Project_Template)
- `src/infrastructure/database/postgresql_repository.py`
- `src/infrastructure/database/sqlite_repository.py`

## Files to Update

- `CHANGELOG.md` - Add merge entries
- `README.md` - Update structure documentation
- `pyproject.toml` - Update package structure
- `tests/` - Update test structure to match DDD
- All imports - Update to new DDD structure

## Files to Remove

- `Project_Template/` folder (after merge)
- `mstables_002/` folder (after archive)
- Duplicate code files
- Old structure files

## Success Criteria

### DDD Compliance
- ✅ 100% of business logic in domain layer
- ✅ 100% of use cases in application layer
- ✅ 100% of external concerns in infrastructure layer
- ✅ Clear separation of concerns
- ✅ Dependency inversion (domain depends on nothing)

### Merge Completion
- ✅ All useful code extracted from Project_Template
- ✅ All useful code extracted from mstables_002
- ✅ No duplicate code
- ✅ All tests passing
- ✅ All imports updated
- ✅ Documentation updated

## Risk Assessment

### Risks
1. **Breaking Changes** - Restructuring may break existing code
   - **Mitigation**: Incremental migration, comprehensive tests
2. **Data Loss** - Merging may lose unique data
   - **Mitigation**: Backup before merge, verify all data migrated
3. **Import Errors** - New structure may break imports
   - **Mitigation**: Update all imports, run tests

### Rollback Plan
- Keep backup of original structure
- Git tags for each phase
- Ability to revert to previous structure

## Timeline

- **Version 1.0.3** (Next): Analysis and planning
- **Version 1.0.4**: Restructure for DDD
- **Version 1.0.5**: Merge Project_Template
- **Version 1.0.6**: Merge mstables_002
- **Version 1.1.0**: DDD compliance complete

---

**Status**: Planning phase
**Next Action**: Create domain model document and analyze Project_Template contents

