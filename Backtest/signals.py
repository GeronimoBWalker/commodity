# signals.py
import numpy as np
import pandas as pd
from scipy.stats import linregress

def compute_features(commodity, stock, window=14, lag=1):
    commodity = commodity.where(commodity > 0).dropna()
    stock = stock.where(stock > 0).dropna()

    commodity_name = commodity.name + f'_lag_{lag}'
    stock_name = stock.name

    commodity_returns = np.log(commodity).diff(lag)
    stock_returns = np.log(stock).diff(1)

    df = pd.concat([commodity_returns, stock_returns], axis=1).dropna()
    df.columns = [commodity_name, stock_name]

    df['rolling_corr'] = df[commodity_name].rolling(window=window).corr(df[stock_name])
    df['gradient'] = df[commodity_name].rolling(window=3).apply(
        lambda x: linregress(range(3), x).slope, raw=True
    )

    return df.dropna()

def detect_trade_signals(df, threshold=0.95, min_streak=3, quantile=0.5):
    df['over_thresh'] = df['rolling_corr'] > threshold
    df['streak'] = df['over_thresh'].astype(int).groupby(
        df['over_thresh'].ne(df['over_thresh'].shift()).cumsum()
    ).cumsum()

    signals = df[df['streak'] >= min_streak].copy()
    cutoff = signals['gradient'].abs().quantile(quantile)
    signals = signals[signals['gradient'].abs() >= cutoff]
    signals['trade_signal'] = signals['gradient'].apply(lambda x: 1 if x > 0 else -1)
    return signals[['rolling_corr', 'gradient', 'trade_signal']]
