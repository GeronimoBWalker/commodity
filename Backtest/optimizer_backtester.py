# backtester.py
import numpy as np

class OpBacktester:
    def __init__(self, features, signals, stock_col):
        self.features = features.copy()
        self.signals = signals.copy()
        self.stock_col = stock_col

    def run(self):
        df = self.features.join(self.signals[['trade_signal']], how='left').fillna(0)
        df['daily_return'] = df[self.stock_col]
        df['strategy_return'] = df['trade_signal'].shift(1) * df['daily_return']

        df['cumulative'] = (1 + df['strategy_return']).cumprod()
        return df
