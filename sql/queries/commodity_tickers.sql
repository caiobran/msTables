-- Query: Check for commodity tickers
-- Last updated: 2025-05-20
SELECT DISTINCT symbol
FROM tiingo_prices
WHERE symbol LIKE '%GC%' OR symbol LIKE '%SI%' OR symbol LIKE '%HG%' OR symbol LIKE '%LITHIUM%' OR symbol LIKE '%COPPER%' OR symbol LIKE '%GOLD%' OR symbol LIKE '%SILVER%'; 