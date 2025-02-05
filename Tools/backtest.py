import pandas as pd


class Backtest:
    def __init__(self) -> None:

        # Formats
        self.decimal_format = "{:,.2f}"

    def backtest_put(
        self,
        candles,
        window: int,
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
            low_prices = []
            low_prices = {}
            for index, row in section.iterrows():
                close = row["Close"]
                if j == 0:
                    anchor = close
                else:
                    low = row["Low"]
                    low_prices[index] = low
                    # low_prices.append(low)
                    change = self.percentage_handling(anchor, low)
                    changes[index] = change
                j += 1

            # Lowest change date, lowest change value
            lcd, lcv = self.get_lowest_value(changes)
            # Lowest price date, lowest price value
            lpd, lpv = self.get_lowest_value(low_prices)
            # Add data to dictionary
            data["window_start"].append(section_dates[0])
            data["window_end"].append(section_dates[-1])
            data["anchor"].append(anchor)
            data["outlier_date"].append(lcd)
            data["outlier_price"].append(lpv)
            data["outlier_change"].append(lcv)
            i += window
        # Create dataframe containing outlier data.
        df = pd.DataFrame(data)
        df["strike_spread"] = strike_spread
        df["breached"] = df["outlier_change"] < df["strike_spread"]
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
        }

        return probability_data

    def backtest_call(
        self,
        candles,
        window: int,
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
            high_prices = {}
            for index, row in section.iterrows():
                close = row["Close"]
                if j == 0:
                    anchor = close
                else:
                    high = row["High"]
                    high_prices[index] = high
                    # low_prices.append(low)
                    change = self.percentage_handling(anchor, high)
                    changes[index] = change
                j += 1

            # Lowest change date, lowest change value
            hcd, hcv = self.get_max_value(changes)
            # Lowest price date, lowest price value
            hpd, hpv = self.get_max_value(high_prices)
            # Add data to dictionary
            data["window_start"].append(section_dates[0])
            data["window_end"].append(section_dates[-1])
            data["anchor"].append(anchor)
            data["outlier_date"].append(hcd)
            data["outlier_price"].append(hpv)
            data["outlier_change"].append(hcv)
            i += window
        # Create dataframe containing outlier data.
        df = pd.DataFrame(data)
        df["strike_spread"] = strike_spread
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
        }
        return probability_data

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
