### CODE SOURCE: https://algotrading101.com/learn/build-my-own-custom-backtester-python/

import numpy as np
import pandas as pd
from typing import List,Optional,Dict,Any
import matplotlib.pyplot as plt
from openbb import obb


# class DataHandler:
#     """Data handler class for loading and processing data."""

#     def __init__(
#         self,
#         symbol: str,
#         start_date: Optional[str] = None,
#         end_date: Optional[str] = None,
#         provider: str = "fmp",
#     ):
#         """Initialize the data handler."""
#         self.symbol = symbol.upper()
#         self.start_date = start_date
#         self.end_date = end_date
#         self.provider = provider

#     def load_data(self) -> pd.DataFrame | dict[str, pd.DataFrame]:
#         """Load equity data."""
#         data = obb.equity.price.historical(
#             symbol=self.symbol,
#             start_date=self.start_date,
#             end_date=self.end_date,
#             provider=self.provider,
#         ).to_df()

#         if "," in self.symbol:
#             data = data.reset_index().set_index("symbol")
#             return {symbol: data.loc[symbol] for symbol in self.symbol.split(",")}

#         return data

#     def load_data_from_csv(self, file_path) -> pd.DataFrame:
#         """Load data from CSV file."""
#         return pd.read_csv(file_path, index_col="date", parse_dates=True)
    

class Strategy:
    """Base class for trading stretegies"""

    def __init__(self, indicators: dict, signal_logic:Any):
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



class Backtester:
    """Backtester class for testing strategies"""
    def __init__(
            self,
            initial_capital:float=10000.0, 
            commission_pct:float=0.005,    
            commission_fixed:float=1.0,
            trade_fraction: float = 0.25):   
        
        self.initial_capital = initial_capital # initialize investment amount
        self.commission_pct = commission_pct # initialize commission percentage
        self.commission_fixed = commission_fixed # initialize baseline commission 
        self.assets_data:Dict={} 
        self.portfolio_history:Dict={}  
        self.daily_portfolio_values:List[float] =[]
        self.dates: List[pd.Timestamp] = []
        self.trade_log: Dict[str, List[dict]] = {}


     def execute_trade(self, asset: str, signal: int, price: float, date: pd.Timestamp = None, per_trade_value: float = None) -> None:
        if signal > 0 and self.assets_data[asset]["positions"] == 0:
            
            trade_value = per_trade_value if per_trade_value is not None else (
                self.assets_data[asset]["cash"] + self.assets_data[asset]["position_value"]
            ) * self.trade_fraction

            trade_value = min(trade_value, self.assets_data[asset]["cash"])
            commission = self.calculate_commission(trade_value)
            shares_to_buy = (trade_value - commission) / price

            if shares_to_buy > 0:
                self.assets_data[asset]['positions'] += shares_to_buy
                self.assets_data[asset]['cash'] -= trade_value

                self.trade_log.setdefault(asset, []).append({
                    "date": date,
                    "type": "BUY",
                    "shares": shares_to_buy,
                    "price": price,
                    "value": trade_value,
                    "commission": commission,
                    "cash_remaining": self.assets_data[asset]['cash'],
                })

        elif signal < 0 and self.assets_data[asset]['positions'] > 0:
            shares_to_sell = self.assets_data[asset]["positions"]
            trade_value = shares_to_sell * price
            commission = self.calculate_commission(trade_value)

            self.assets_data[asset]["cash"] += trade_value - commission
            self.assets_data[asset]["positions"] = 0

            self.trade_log.setdefault(asset, []).append({
                "date": date,
                "type": "SELL",
                "shares": shares_to_sell,
                "price": price,
                "value": trade_value,
                "commission": commission,
                "cash_remaining": self.assets_data[asset]['cash'],
            })

    def update_portfolio(self, pair:str, price:float) -> None:
        """
        Update the portfolio with the latest pair price.

        Parameters:
        asset (str): The name of the pair being updated.
        price (float): The current market price of the asset.

        This function updates the value of held positions and calculates the total portfolio value.
        """

        # Calculate the current value of the asset holdings
        self.assets_data[pair]["position_value"] = (self.assets_data[pair]["positions"] * price)
        self.assets_data[pair]["total_value"] = (self.assets_data[pair]["cash"] + self.assets_data[pair]["position_value"])
        self.portfolio_history[pair].append(self.assets_data[pair]["total_value"])


    def backtest(self, data: pd.DataFrame | dict[str, pd.DataFrame]):
        """
        Backtest the trading strategy using the provided data.

        Parameters:
        data (pd.DataFrame): A combined DataFrame with multiple asset pairs, each row containing:
                         - a 'pair' column (e.g., "PA=F_lag_1_AAPL")
                         - a 'signal' column
                         - a price column (e.g., 'stock_price')
                         - and indexed by date
        """
        unique_pairs = data['pair'].unique()
        for pair in unique_pairs:
            self.assets_data[pair] = {
                "cash": self.initial_capital / len(unique_pairs),
                "positions": 0,
                "position_value": 0,
                "total_value": 0,
            }
            self.portfolio_history[pair] = []

        grouped = data.groupby(data.index)

        for date, group in grouped:
            total_portfolio_value = 0

            # Determine which buy signals are valid (no open position)
            eligible_buys = group[
                (group['signal'] > 0) & (group['pair'].apply(lambda p: self.assets_data[p]['positions'] == 0))
            ]

            top_signals = eligible_buys.head(20)  # max 20 positions per day
            num_trades = len(top_signals)

            for _, row in group.iterrows():
                pair = row['pair']
                price = row['price']
                signal = row['signal']

                # Calculate how much to allocate per trade (split across valid buys)
                if signal > 0 and pair in top_signals['pair'].values and num_trades > 0:
                    total_value = self.assets_data[pair]["cash"] + self.assets_data[pair]["position_value"]
                    per_trade_value = total_value * self.trade_fraction / num_trades
                    self.execute_trade(pair, signal, price, date, per_trade_value=per_trade_value)
                elif signal < 0:
                    self.execute_trade(pair, signal, price, date)
                    
                total_portfolio_value += self.assets_data[pair]["total_value"]

            self.daily_portfolio_values.append(total_portfolio_value)
            self.dates.append(date)
    
    #### #######################################  ####################################### Functions  ####################################### ####
    def calculate_commission(self, trade_value: float) -> float:
        """Calculate the commission fee for a trade."""
        """
            Returns the Max of (commmsssion as percentage of the trade and minimum commission) 
        """
        return max(trade_value * self.commission_pct, self.commission_fixed)

    def calculate_total_return(self, final_value: float, initial_value: float) -> float:
        """Calculate the total return of the portfolio."""
        return (final_value - initial_value) / initial_value

    def calculate_annualized_return(self, total_return: float, num_days: int, periods_per_year=252) -> float:
        """Calculate annualized return from total return."""
        return (1 + total_return) ** (periods_per_year / num_days) - 1

    def calculate_annualized_volatility(self, daily_returns: pd.Series, periods_per_year=252) -> float:
        """Calculate annualized volatility using daily returns."""
        return daily_returns.std() * np.sqrt(periods_per_year)

    def calculate_sharpe_ratio(self, annualized_return: float, annualized_volatility: float, risk_free_rate=0.02) -> float:
        """Calculate the Sharpe Ratio."""
        if annualized_volatility == 0:
            return np.nan
        return (annualized_return - risk_free_rate) / annualized_volatility

    def calculate_sortino_ratio(self, daily_returns: pd.Series, annualized_return: float, risk_free_rate=0.02, periods_per_year=252) -> float:
        """Calculate the Sortino Ratio using downside volatility."""
        downside_returns = daily_returns[daily_returns < 0]
        downside_volatility = downside_returns.std() * np.sqrt(periods_per_year)

        if downside_volatility == 0:
            return np.nan
        return (annualized_return - risk_free_rate) / downside_volatility

    def calculate_maximum_drawdown(self, portfolio_values: pd.Series) -> float:
        """Calculate the maximum drawdown of the portfolio."""
        cumulative_max = portfolio_values.cummax()
        drawdown = (portfolio_values - cumulative_max) / cumulative_max
        return drawdown.min()
    
    ####################################### #######################################  #######################################  #######################################
    def calculate_performance(self, plot: bool = True) -> None:
        """Calculate the performance of the trading strategy."""
        if not self.daily_portfolio_values:
            print("No portfolio history to calculate performance.")
            return

        portfolio_values = pd.Series(self.daily_portfolio_values,index=self.dates)
        daily_returns = portfolio_values.pct_change().dropna()

        total_return = self.calculate_total_return(portfolio_values.iloc[-1], self.initial_capital)
        annualized_return = self.calculate_annualized_return(total_return, len(portfolio_values))
        annualized_volatility = self.calculate_annualized_volatility(daily_returns)
        sharpe_ratio = self.calculate_sharpe_ratio(annualized_return, annualized_volatility)
        sortino_ratio = self.calculate_sortino_ratio(daily_returns, annualized_return)
        max_drawdown = self.calculate_maximum_drawdown(portfolio_values)

        print(f"Final Portfolio Value: {portfolio_values.iloc[-1]:.2f}")
        print(f"Total Return: {total_return * 100:.2f}%")
        print(f"Annualized Return: {annualized_return * 100:.2f}%")
        print(f"Annualized Volatility: {annualized_volatility * 100:.2f}%")
        print(f"Sharpe Ratio: {sharpe_ratio:.2f}")
        print(f"Sortino Ratio: {sortino_ratio:.2f}")
        print(f"Maximum Drawdown: {max_drawdown * 100:.2f}%")

        if plot:
            self.plot_performance(portfolio_values, daily_returns)

    def plot_performance(self, portfolio_values:Dict, daily_returns:pd.DataFrame):
        """Plot the performance of the trading strategy."""
        fig,axs = plt.subplots(2,1,figsize=(10, 6))

        
        axs[0].plot(portfolio_values, label="Portfolio Value")
        axs[0].set_title("Portfolio Value Over Time")
        axs[0].legend()

        
        axs[1].plot(daily_returns, label="Daily Returns", color="orange")
        axs[1].set_title("Daily Returns Over Time")
        axs[1].legend()

        plt.tight_layout()
        plt.show()


    
