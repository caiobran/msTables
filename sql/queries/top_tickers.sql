-- Query: Top 10 tickers with the most data
-- Last updated: 2025-05-20
SELECT symbol, COUNT(*) as count
FROM tiingo_prices
GROUP BY symbol
ORDER BY count DESC
LIMIT 10; 