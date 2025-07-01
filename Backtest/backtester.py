# backtester.py

import numpy as np
import pandas as pd

class Backtester:
    def __init__(self, prices, signals, stock_col, starting_capital=10_000):
        """
        prices: DataFrame with prices, must have a DateTime index.
        signals: DataFrame with trade_signal column.
        stock_col: name of the price column for the stock.
        starting_capital: amount to simulate investing.
        """
        self.prices = prices.copy()
        self.signals = signals.copy()
        self.stock_col = stock_col
        self.starting_capital = starting_capital

    def run(self):
        df = self.prices.join(self.signals[['trade_signal']], how='left').fillna(0)

        # Calculate daily returns if needed
        if 'daily_return' not in df.columns:
            df['daily_return'] = df[self.stock_col].pct_change().fillna(0)


        # Convert signals to numeric position
        df['position'] = df['trade_signal'].shift(1).fillna(0)


        # Strategy return
        df['strategy_return'] = df['position'] * df['daily_return']

        # Cumulative returns
        df['buyhold_cum'] = (1 + df['daily_return']).cumprod()
        df['strategy_cum'] = (1 + df['strategy_return']).cumprod()

        # Dollar value
        df['buyhold_value'] = self.starting_capital * df['buyhold_cum']
        df['strategy_value'] = self.starting_capital * df['strategy_cum']

        return df
