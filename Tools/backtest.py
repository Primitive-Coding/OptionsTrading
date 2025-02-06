import pandas as pd
import yfinance as yf


class Backtest:
    def __init__(self) -> None:

        # Formats
        self.decimal_format = "{:,.2f}"

    def multi_year_analysis(
        self,
        candles: pd.DataFrame,
        option_type: str,
        option_side: str,
        window: int,
        strike_price: float,
        years: list = [1, 5, 10],
    ):
        data = {}
        # Convert list in to dates.
        years_ago = [pd.Timestamp.now() - pd.DateOffset(years=y) for y in years]
        if option_type == "call":
            index = 0
            for y in years_ago:
                candle_section = candles.loc[candles.index >= y]
                prob_data = self.backtest_call(
                    candle_section, window, strike_price, option_side=option_side
                )
                data[years[index]] = prob_data
                index += 1
            data["max"] = self.backtest_call(candles, window, strike_price, option_side)
        elif option_type == "put":
            index = 0
            for y in years_ago:
                candle_section = candles.loc[candles.index >= y]
                prob_data = self.backtest_put(
                    candle_section, window, strike_price, option_side=option_side
                )
                data[years[index]] = prob_data
                index += 1
            data["max"] = self.backtest_put(candles, window, strike_price, option_side)

        df = pd.DataFrame.from_dict(data, orient="index")[
            ["total", "match", "distance", "probability"]
        ]
        return df

    """------------- 0 DTE -------------"""

    def backtest_0dte(
        self,
        candles: pd.DataFrame,
        strike_price: float,
        option_type: str,
        option_side: str,
        manual_stock_price: float = 0,
    ):
        prob = self.get_probability(
            candles, 0, strike_price, option_type, option_side, manual_stock_price
        )
        return prob

    """------------- Puts -------------"""

    def backtest_put(
        self,
        candles,
        dte: int,
        strike_price: float,
        option_side: str,
        manual_stock_price: float = 0,
    ):
        """
        Backtest the a put option.

        Parameters
        ----------
        candles : pd.DataFrame
            DataFrame containing OHLCV candle data.
        window : int
            Number of days to expiration.
        strike_price : float
            Strike price of the contract
        option_side : str
            Whether you are buying or selling the option. "buy" or "sell"
        manual_stock_price : float, optional
            Override calculations with a manual stock price if data feeds are unavailable. If 0, it will use last price from data feed, by default 0

        Returns
        -------
        dict
            Dictionary containing probability data.
        """
        prob = self.get_probability(
            candles, dte, strike_price, "put", option_side, manual_stock_price
        )
        return prob

    """------------- Calls -------------"""

    def backtest_call(
        self,
        candles,
        dte: int,
        strike_price: float,
        option_side: str,
        manual_stock_price: float = 0,
    ):
        """
        Backtest the a call option.

        Parameters
        ----------
        candles : pd.DataFrame
            DataFrame containing OHLCV candle data.
        window : int
            Number of days to expiration.
        strike_price : float
            Strike price of the contract
        option_side : str
            Whether you are buying or selling the option. "buy" or "sell"
        manual_stock_price : float, optional
            Override calculations with a manual stock price if data feeds are unavailable. If 0, it will use last price from data feed, by default 0

        Returns
        -------
        dict
            Dictionary containing probability data.
        """
        prob = self.get_probability(
            candles, dte, strike_price, "call", option_side, manual_stock_price
        )
        return prob

    """------------- Probability -------------"""

    def get_probability(
        self,
        candles: pd.DataFrame,
        window: int,
        strike_price: float,
        option_type: str,
        option_side: str,
        manual_stock_price: float = 0,
    ):
        i = 0
        window += 1
        data = {
            "window_start": [],
            "window_end": [],
            "anchor": [],
            "outlier_date": [],
            "outlier_price": [],
            "outlier_change": [],
        }
        if manual_stock_price == 0:
            last_price = candles["Close"].iloc[-1]
        else:
            last_price = manual_stock_price
        strike_spread = self.percentage_handling(last_price, strike_price)
        while True:
            section = candles.iloc[i : i + window]
            if section.empty or len(section) != window:
                break
            section_dates = section.index.to_list()
            j = 0
            anchor = 0
            changes = {}
            prices = {}
            for index, row in section.iterrows():
                close = row["Close"]
                if j == 0:
                    anchor = close
                else:
                    if option_type == "put":
                        value = row["Low"]
                    elif option_type == "call":
                        value = row["High"]
                    prices[index] = value
                    # low_prices.append(low)
                    change = self.percentage_handling(anchor, value)
                    changes[index] = change
                j += 1

            # Lowest change date, lowest change value
            change_date, change_value = self.get_lowest_value(changes)
            # Lowest price date, lowest price value
            price_date, price_value = self.get_lowest_value(prices)
            # Add data to dictionary
            data["window_start"].append(section_dates[0])
            data["window_end"].append(section_dates[-1])
            data["anchor"].append(anchor)
            data["outlier_date"].append(change_date)
            data["outlier_price"].append(price_value)
            data["outlier_change"].append(change_value)
            i += window
        # Create dataframe containing outlier data.
        df = pd.DataFrame(data)
        df["strike_spread"] = strike_spread
        if option_type == "put":
            df["breached"] = df["outlier_change"] < df["strike_spread"]
        elif option_type == "call":
            df["breached"] = df["outlier_change"] > df["strike_spread"]
        # Get sections that were breached (change exceeded strike_spread)
        matches = df[df["breached"] == True]
        # Probability Data
        probability = len(matches) / len(df)
        if option_side == "buy":
            pass
        elif option_side == "sell":
            probability = 1 - probability
        probability_data = {
            "total": len(df),
            "match": len(matches),
            "distance": self.decimal_format.format(strike_spread),
            "probability": probability,
            "p%": self.decimal_format.format(probability * 100),
        }
        df = pd.DataFrame([probability_data]).T
        df.columns = ["Value"]
        return df

    """------------- Dictionary Sorting -------------"""

    def sort_dict(self, data: dict, reverse: bool = False):
        sorted_dict = dict(
            sorted(data.items(), key=lambda item: item[1], reverse=reverse)
        )
        return sorted_dict

    def get_lowest_value(self, data: dict):
        if not data:
            return None  # Return None if the dictionary is empty
        lowest_key = min(data, key=data.get)  # Get the key with the lowest value
        lowest_value = data[lowest_key]  # Get the lowest value
        return lowest_key, lowest_value

    def get_max_value(self, data: dict):
        if not data:
            return None  # Return None if the dictionary is empty
        highest_key = min(data, key=data.get)  # Get the key with the lowest value
        highest_value = data[highest_key]  # Get the lowest value
        return highest_key, highest_value

    def percentage_handling(self, start_value, final_value):
        # Formula for decrease
        value = 0
        if start_value > final_value:
            value = (start_value - final_value) / abs(start_value)
            value *= -1
        # Formula for increase
        elif start_value < final_value:
            value = (final_value - start_value) / abs(start_value)
        elif start_value == final_value:
            return 0
        return value
