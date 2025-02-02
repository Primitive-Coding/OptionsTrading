import datetime as dt


import numpy as np
import pandas as pd
import yfinance as yf


class OptionsBacktest:
    def __init__(
        self,
        ticker: str,
        buy: bool = True,
        sell: bool = False,
        interval: str = "1d",
        period: str = "max",
    ) -> None:
        self.ticker = ticker.upper()
        self.buy = buy
        self.sell = sell
        self.candles = yf.download(
            self.ticker, interval=interval, period=period, multi_level_index=False
        )
        self.candles["change"] = self.candles["Close"].pct_change() * 100
        self.last_price = self.candles["Close"].iloc[-1]
        self.windows = pd.DataFrame()
        # Formats
        self.date_format = "%Y-%m-%d"
        self.percent_format = "{:,.0f}%"
        self.percent_decimal_format = "{:,.2f}%"
        self.dollar_format = "${:,.2f}"

    def set_window(self, window: int):
        i = 0
        data = {
            "window_start": [],
            "window_end": [],
            "window": [],
            "close_start": [],
            "close_end": [],
            "total_change": [],
            "average_change": [],
        }
        while True:
            j = 0
            dates = []
            change = []
            close = []
            while j < window:
                try:
                    candle_data = self.candles[["Close", "change"]].iloc[i]
                    date = candle_data.name
                    date = dt.datetime.strftime(date, self.date_format)
                    dates.append(date)
                    change.append(candle_data["change"])
                    close.append(candle_data["Close"])
                    i += 1
                    j += 1
                except IndexError:
                    break
            try:
                avg_change = sum(change) / len(change)
                close_start = close[0]
                close_end = close[-1]
                t_change = ((close_end - close_start) / abs(close_start)) * 100
                data["window_start"].append(dates[0])
                data["window_end"].append(dates[-1])
                data["window"].append(len(change))
                data["close_start"].append(close_start)
                data["close_end"].append(close_end)
                data["average_change"].append(avg_change)
                data["total_change"].append(t_change)
            except ZeroDivisionError:
                break
        self.windows = pd.DataFrame(data)

    def get_windows(self, window: int):
        if self.windows.empty:
            self.set_window(window)
        return self.windows

    def get_probability(
        self,
        strike_price,
        expiration_date,
        option_type: str = "call",
        return_value: bool = True,
    ):

        if option_type == "call":
            strike_spread = (
                (strike_price - self.last_price) / abs(self.last_price)
            ) * 100
        elif option_type == "put":
            strike_spread = (
                (self.last_price - strike_price) / abs(self.last_price)
            ) * -100

        now = dt.datetime.now().date()
        window = self.get_time_delta(now, expiration_date, weekend_adjusted=True)
        df = self.get_windows(window)
        if option_type == "call":
            matches = df[df["total_change"] > strike_spread]
        elif option_type == "put":
            matches = df[df["total_change"] < strike_spread]
        df_len = len(df)
        match_len = len(matches)
        probability = (match_len / df_len) * 100
        if self.sell and not self.buy:
            probability = 100 - probability

        if return_value:
            return probability
        else:

            return f"""
========================================================
Last Price: {self.dollar_format.format(self.last_price)}
Strike: {self.dollar_format.format(strike_price)}
Distance: {self.percent_decimal_format.format(strike_spread)}

----------
[Window]
Length(DTE): {window}
Matches: {len(matches)}
Total: {int(len(self.candles) / window)}
Probability: {self.percent_decimal_format.format(probability)}

----------
Trading Days Analyzed: {len(self.candles)}

Over the last \033[4m{len(self.candles)}\033[0m trading days,
\033[4m${self.ticker}\033[0m has dropped \033[4m{self.percent_decimal_format.format(strike_spread)}\033[0m over \033[4m{window}\033[0m days a total of \033[4m{len(matches)}\033[0m time(s). 
            
                
    """

    def get_time_delta(self, t1, t2, weekend_adjusted: bool = True):
        """
        Get the time delta between a two dates.

        Parameters
        ----------
        t1 : str
            Starting date.
        t2 : str
            End date.
        weekend_adjusted : bool, optional
            Determines if weekends should be subtracted from final value, by default True

        Returns
        -------
        int
            Number of days between 't1' and 't2'.
        """
        if type(t1) == str:
            t1 = dt.datetime.strptime(t1, self.date_format).date()
        if type(t2) == str:
            t2 = dt.datetime.strptime(t2, self.date_format).date()
        t3 = t2 - t1
        dte = t3.days
        if not weekend_adjusted:
            return dte
        elif weekend_adjusted:
            weekend_count = 0
            for single_date in pd.date_range(start=t1, end=t2):
                if single_date.weekday() in [5, 6]:  # Saturday and Sunday
                    weekend_count += 1
            # If the current day is a weekend day.
            if t1.weekday() in [5, 6]:
                weekend_count -= 1
            dte -= weekend_count
            return dte
