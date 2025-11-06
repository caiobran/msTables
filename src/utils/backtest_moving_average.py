import backtrader as bt
import pandas as pd
import sqlite3
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)

class SmaCrossStrategy(bt.Strategy):
    params = (('fast', 10), ('slow', 30))

    def __init__(self):
        sma1 = bt.ind.SMA(period=self.p.fast)
        sma2 = bt.ind.SMA(period=self.p.slow)
        self.crossover = bt.ind.CrossOver(sma1, sma2)

    def next(self):
        if not self.position:
            if self.crossover > 0:
                self.buy()
        elif self.crossover < 0:
            self.close()


def load_data_from_db(db_path, ticker):
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql_query(
            f"SELECT date, close, open, high, low, volume FROM tiingo_prices WHERE symbol = ? ORDER BY date ASC",
            conn,
            params=(ticker,)
        )
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')
    return df


def run_backtest(db_path='data/mstables.sqlite', ticker='AAPL'):
    df = load_data_from_db(db_path, ticker)
    if df.empty:
        logging.error(f"No data found for ticker {ticker}")
        return
    data = bt.feeds.PandasData(dataname=df)

    cerebro = bt.Cerebro()
    cerebro.addstrategy(SmaCrossStrategy)
    cerebro.adddata(data)
    cerebro.broker.set_cash(100000)
    logging.info(f"Starting Portfolio Value: {cerebro.broker.getvalue():.2f}")
    result = cerebro.run()
    logging.info(f"Final Portfolio Value: {cerebro.broker.getvalue():.2f}")
    cerebro.plot(style='candlestick', volume=True, iplot=False, savefig=True, filename=f'backtest_equity_curve_{ticker}.png')
    logging.info(f"Equity curve plot saved as backtest_equity_curve_{ticker}.png")


if __name__ == "__main__":
    top_tickers = ['A', 'AAL', 'AAP', 'ABBV', 'ABC', 'ABT', 'ACN', 'ADBE', 'ADI', 'ADM']
    for ticker in top_tickers:
        logging.info(f"Running backtest for ticker: {ticker}")
        run_backtest(ticker=ticker) 