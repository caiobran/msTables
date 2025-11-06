# Commodities and Metals System Plan

## Current State Analysis

### Database Tables Status
- **commodities_data**: Empty (0 records) - ready for import
- **metal_prices**: 102 records - contains currency data, misnamed
- **crypto_archive**: 608,807 records - well populated
- **ustsb_savbondissueredeemmat_all_years**: 406 records - some bond data

### Existing Infrastructure
- **Data Shepherd**: Extended with multi-asset class support
- **Metal Price API**: Available at `src/metalprice/metalprice_api.py`
- **Import Systems**: Built for commodities and crypto
- **Error Logging**: Systematic logging in place

## Phase 1: Commodities System Build (Priority 1)

### 1.1 Database Schema Enhancement
```sql
-- Enhanced commodities_data table
CREATE TABLE IF NOT EXISTS commodities_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    date TEXT,
    price REAL,
    volume REAL,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    commodity_type TEXT,
    source TEXT,
    unit TEXT,
    region TEXT,
    quality TEXT,
    commodity TEXT,
    one_month_change REAL,
    twelve_month_change REAL,
    ytd_change REAL,
    year TEXT,
    sum_of_value TEXT,
    market_hogs TEXT,
    feeder_pigs TEXT,
    gross_value_of_production TEXT,
    UNIQUE (symbol, date, commodity_type)
);
```

### 1.2 Commodity Categories
- **Agricultural**: Wheat, Corn, Soybeans, Rice, Barley
- **Energy**: Oil, Gas, Coal, Diesel, Gasoline
- **Metals**: Gold, Silver, Copper, Aluminum, Iron
- **Livestock**: Beef, Pork, Poultry, Lamb
- **Soft Commodities**: Coffee, Cocoa, Sugar, Cotton
- **Fisheries**: Salmon, Shrimp, Fish products

### 1.3 Data Sources Integration
- NOAA Fisheries (fisheries data)
- IMF Commodity Prices (global indices)
- USDA Commodity Costs and Returns
- Trading Economics API
- Alpha Vantage (commodity futures)

### 1.4 Import Pipeline
1. **File Detection**: Auto-detect commodity files in input folders
2. **Format Parsing**: Handle CSV, Excel, XLSB formats
3. **Data Validation**: Validate price ranges, date formats
4. **Error Logging**: Log problematic rows for review
5. **Metadata Addition**: Add source, category, region info

## Phase 2: Metals Table Restructuring (Priority 2)

### 2.1 Current metal_prices Table Analysis
```sql
-- Current schema (contains currency data)
CREATE TABLE metal_prices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT,
    price REAL,
    timestamp TEXT
);
```

### 2.2 Restructuring Plan
1. **Rename current table**: `metal_prices` → `currency_prices`
2. **Create new metals table**: `precious_metals_data`
3. **Migrate data**: Move currency data to appropriate table
4. **Update references**: Fix all code references

### 2.3 New Metals Table Schema
```sql
CREATE TABLE precious_metals_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    symbol TEXT NOT NULL,
    date TEXT NOT NULL,
    price_usd REAL,
    price_eur REAL,
    price_gbp REAL,
    price_jpy REAL,
    volume REAL,
    market_cap REAL,
    metal_type TEXT, -- 'precious', 'industrial', 'base'
    purity TEXT, -- '999.9', '995', '925', etc.
    unit TEXT, -- 'oz', 'kg', 'ton'
    exchange TEXT, -- 'COMEX', 'LME', 'TOCOM'
    source TEXT,
    timestamp TEXT,
    UNIQUE (symbol, date)
);
```

### 2.4 Metals API Integration
- **Metal Price API**: Already available with API key
- **Supported Metals**: Gold (XAU), Silver (XAG), Platinum (XPT), Palladium (XPD)
- **Data Frequency**: Real-time and historical
- **Rate Limiting**: Implement proper rate limiting

## Phase 3: Data Shepherd Enhancement (Priority 3)

### 3.1 Multi-Asset Class Support
- **Stocks**: Already implemented
- **Commodities**: Ready for implementation
- **Metals**: New implementation needed
- **Bonds**: Framework exists, needs data
- **Forex**: Framework exists, needs implementation

### 3.2 Automated Data Pipeline
1. **Gap Detection**: Find missing data points
2. **Source Selection**: Choose best data source
3. **Rate Limiting**: Respect API limits
4. **Error Recovery**: Handle failures gracefully
5. **Data Validation**: Ensure data quality

## Phase 4: PostgreSQL Migration (Future - Priority 5)

### 4.1 Docker Setup
```yaml
# docker-compose.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: mstables
      POSTGRES_USER: mstables_user
      POSTGRES_PASSWORD: secure_password
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  airflow:
    image: apache/airflow:2.7.1
    depends_on:
      - postgres
    environment:
      AIRFLOW__CORE__SQL_ALCHEMY_CONN: postgresql+psycopg2://airflow:airflow@postgres/airflow
    volumes:
      - ./dags:/opt/airflow/dags
      - ./logs:/opt/airflow/logs
```

### 4.2 Migration Strategy
1. **Schema Migration**: Convert SQLite schema to PostgreSQL
2. **Data Migration**: Bulk import existing data
3. **Code Updates**: Update all database connections
4. **Testing**: Validate data integrity
5. **Rollback Plan**: Keep SQLite as backup

## Implementation Timeline

### Week 1-2: Commodities System
- [ ] Implement commodity import pipeline
- [ ] Test with sample data files
- [ ] Add data validation and error handling
- [ ] Create commodity analysis tools

### Week 3-4: Metals Restructuring
- [ ] Rename metal_prices table
- [ ] Create new precious_metals_data table
- [ ] Implement metals API integration
- [ ] Update all code references

### Week 5-6: Data Shepherd Enhancement
- [ ] Add metals support to data shepherd
- [ ] Implement automated gap filling
- [ ] Add data quality monitoring
- [ ] Create data source management

### Week 7-8: Testing and Documentation
- [ ] Comprehensive testing of all systems
- [ ] Performance optimization
- [ ] Documentation updates
- [ ] User training materials

## Success Metrics

### Data Quality
- **Commodities**: >10,000 records across all categories
- **Metals**: Real-time data for major precious metals
- **Coverage**: >90% of requested symbols available
- **Accuracy**: <1% data validation errors

### Performance
- **Import Speed**: <5 minutes for 1000 records
- **Query Performance**: <1 second for standard queries
- **API Efficiency**: <80% of rate limits used

### Reliability
- **Uptime**: >99% system availability
- **Error Rate**: <5% failed imports
- **Recovery Time**: <30 minutes for data issues 