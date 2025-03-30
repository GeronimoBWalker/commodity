### CODE SOURCE: https://algotrading101.com/learn/build-my-own-custom-backtester-python/

import pandas as pd

class Strategy:
    """Base class for trading stretegies"""

    def __init__(self, indicators: dict, signal_logic):
        self.indicators = indicators
        self.signal_logic = signal_logic
    
    def generate_signals(
        self, data: pd.DataFrame | dict[str, pd.DataFrame]
        ) -> pd.DataFrame | dict[str, pd.DataFrame]:
        """Genrate signals based on the strategy'y indicators and signal logic"""
        if isinstance(data,dict):
            for _,asset_data in data.items():
                self._apply_strategy(asset_data)
        else:
            self._apply_strategy(data)
        return data
    
    def _apply_strategy(self, df: pd.DataFrame) -> None:
        """Apply strategy to a dataframe"""

        for name, indicator in self.indicators.items():
            df[name] = indicator(df)

        df['signal'] = df.apply(self.signal_logic, axis=1)
        df["positions"] = df['signal'].diff().fillna(0)