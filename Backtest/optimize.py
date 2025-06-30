# optimize.py
from signals import compute_features, detect_trade_signals
from optimizer_backtester import OpBacktester
import numpy as np
import pandas as pd

def optimize(commodity, stock, param_grid):
    results = []

    for threshold in param_grid['threshold']:
        for min_streak in param_grid['streak']:
            for quantile in param_grid['quantile']:
                features = compute_features(commodity, stock)
                signals = detect_trade_signals(features, threshold, min_streak, quantile)
                bt = OpBacktester(features, signals, stock.name)
                results_df = bt.run()

                final_return = results_df['cumulative'].iloc[-1]
                results.append({
                    'threshold': threshold,
                    'streak': min_streak,
                    'quantile': quantile,
                    'final_return': final_return
                })

    return pd.DataFrame(results).sort_values(by='final_return', ascending=False)
