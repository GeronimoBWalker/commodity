import numpy as np
import pandas as pd

class MultiBacktester:
    def __init__(self, prices_dict, signals_dict, starting_capital=10_000):
        """
        prices_dict: { 'AAPL': prices_df, 'AMZN': prices_df, ... }
        signals_dict: { 'AAPL': signals_df, 'AMZN': signals_df, ... }
        """
        self.prices_dict = prices_dict
        self.signals_dict = signals_dict
        self.starting_capital = starting_capital

    def run(self):
        portfolio = pd.DataFrame()
        combined = []

        for ticker, prices in self.prices_dict.items():
            signals = self.signals_dict[ticker]
            df = prices.join(signals[['trade_signal']], how='left').fillna(0)

            df['daily_return'] = prices[ticker].pct_change().fillna(0)
            df['position'] = df['trade_signal'].shift(1).fillna(0)
            df['strategy_return'] = df['position'] * df['daily_return']

            # Save for later
            portfolio[f'{ticker}_strategy'] = df['strategy_return']
            portfolio[f'{ticker}_buyhold'] = df['daily_return']

        # Average across all tickers
        portfolio['combined_strategy_return'] = portfolio.filter(like='_strategy').mean(axis=1)
        portfolio['combined_buyhold_return'] = portfolio.filter(like='_buyhold').mean(axis=1)

        portfolio['combined_strategy_value'] = self.starting_capital * (1 + portfolio['combined_strategy_return']).cumprod()
        portfolio['combined_buyhold_value'] = self.starting_capital * (1 + portfolio['combined_buyhold_return']).cumprod()

        return portfolio
