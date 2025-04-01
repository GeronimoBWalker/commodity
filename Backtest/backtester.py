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
            commission_pct:float=0.001,    
            commission_fixed:float=1.0):   
        
        self.initial_capital = initial_capital # initialize investment amount
        self.commission_pct = commission_pct # initialize commission percentage
        self.commission_fixed = commission_fixed # initialize baseline commission 
        self.assets_data:Dict={} 
        self.portfolio_history:Dict={}  
        self.daily_portfolio_values:List[float] =[]


    def execute_trade(self, asset:str, signal:int, price:float) -> None:
        """
        Execute a trade based on the signal and price.

        Parameters:
        asset (str): The name of the asset being traded.
        signal (int): The trading signal (1 for buy, -1 for sell, 0 for hold).
        price (float): The current price of the asset.

        This function updates the portfolio by executing buy or sell trades based on the signal.
        """

        # If the signal is positive (buy) and there is available cash, execute a buy order
        if signal > 0 and self.assets_data[asset]["cash"] > 0:
            trade_value = self.assets_data[asset]["cash"] # Use all available cash for the trade
            commission = self.calculate_commission(trade_value) # Calculate the commision for the trade
            shares_to_buy = (trade_value - commission) / price # Determine how many shares can be bought
            
            # Update portfolio: increase positions and decrease cash balance
            self.assets_data[asset]['positions'] += shares_to_buy
            self.assets_data[asset]['cash'] -= trade_value # Deduct full trade value from cash

        # If the signal is negative (sell) and there are shares held, execute a sell order    
        elif signal < 0 and self.assets_data[asset]['positions'] > 0:
            trade_value = self.assets_data[asset]["positions"] * price # Determine total value of held shares
            commission = self.calculate_commission(trade_value) # Calculate the commission for the sale
            
            # Update portfolio: increase cash and reset positions to zero (fully selling the asset)
            self.assets_data[asset]["cash"] += trade_value - commission
            self.assets_data[asset]["positions"] = 0
            

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


    def update_portfolio(self, asset: str, price: float) -> None:
        """
        Update the portfolio with the latest asset price.

        Parameters:
        asset (str): The name of the asset being updated.
        price (float): The current market price of the asset.

        This function updates the value of held positions and calculates the total portfolio value.
        """
        # Calculate the current value of the asset holdings
        self.assets_data[asset]["position_value"] = (self.assets_data[asset]["positions"] * price)
        
        # Compute the total portfolio value as the sum of cash and position value
        self.assets_data[asset]["total_value"] = (
            self.assets_data[asset]["cash"] + self.assets_data[asset]["position_value"])
        self.portfolio_history[asset].append(self.assets_data[asset]["total_value"])


    def backtest(self, data: pd.DataFrame | dict[str, pd.DataFrame]):
        """Backtest the trading strategy using the provided data."""
        if isinstance(data, pd.DataFrame):  # Single asset
            data = {"SINGLE_ASSET": data}  # Convert to dict format for unified processing

        for asset in data:
            self.assets_data[asset] = {
                "cash": self.initial_capital / len(data),
                "positions": 0,
                "position_value": 0,
                "total_value": 0,
            }
            self.portfolio_history[asset] = []

            for date, row in data[asset].iterrows():
                self.execute_trade(asset, row["signal"], row["close"])
                self.update_portfolio(asset, row["close"])
                if len(self.daily_portfolio_values) < len(data[asset]):
                    self.daily_portfolio_values.append(
                        self.assets_data[asset]["total_value"]
                    )
                else:
                    self.daily_portfolio_values[
                        len(self.portfolio_history[asset]) - 1
                    ] += self.assets_data[asset]["total_value"]
    

    def calculate_performance(self, plot: bool = True) -> None:
        """Calculate the performance of the trading strategy."""
        if not self.daily_portfolio_values:
            print("No portfolio history to calculate performance.")
            return

        portfolio_values = pd.Series(self.daily_portfolio_values)
        daily_returns = portfolio_values.pct_change().dropna()

        total_return = calculate_total_return(
            portfolio_values.iloc[-1], self.initial_capital
        )
        annualized_return = calculate_annualized_return(
            total_return, len(portfolio_values)
        )
        annualized_volatility = calculate_annualized_volatility(daily_returns)
        sharpe_ratio = calculate_sharpe_ratio(annualized_return, annualized_volatility)
        sortino_ratio = calculate_sortino_ratio(daily_returns, annualized_return)
        max_drawdown = calculate_maximum_drawdown(portfolio_values)

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
        plt.figure(figsize=(10, 6))

        plt.subplot(2, 1, 1)
        plt.plot(portfolio_values, label="Portfolio Value")
        plt.title("Portfolio Value Over Time")
        plt.legend()

        plt.subplot(2, 1, 2)
        plt.plot(daily_returns, label="Daily Returns", color="orange")
        plt.title("Daily Returns Over Time")
        plt.legend()

        plt.tight_layout()
        plt.show()


    