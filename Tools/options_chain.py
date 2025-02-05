# Data
import re
import math
import numpy as np
import pandas as pd
from scipy.stats import norm

# Date & Time
import datetime as dt

# Yahoo
import yfinance as yf

# Custom
from Tools.options_backtest import OptionsBacktest


class OptionsChain:
    def __init__(
        self,
        ticker: str,
        call: bool,
        put: bool,
        expiration_date: str = "",
        buy: bool = True,
        sell=False,
        contract_fee: float = 0.04,
        backtest_period: str = "max",
    ) -> None:
        self.ticker = ticker.upper()
        if call:
            self.call = True
            self.put = False
            self.option_type = "call"
        elif put:
            self.put = True
            self.call = False
            self.option_type = "put"

        self.expiration_date = expiration_date
        self.buy = buy
        self.sell = sell
        self.contract_fee = contract_fee
        self.backtest_period = backtest_period
        self.backtest = OptionsBacktest(
            ticker,
            strike_price=0,
            call=call,
            put=put,
            buy=buy,
            sell=sell,
            period=backtest_period,
        )
        self.option_chain = pd.DataFrame()
        self.calls = pd.DataFrame()
        self.puts = pd.DataFrame()
        self.candles = self.backtest.candles
        self.stock_price = self.backtest.last_price
        self.risk_free_rate = None

        # Dates
        self.current_date = dt.datetime.now().date()

        # Formats
        self.date_format = "%Y-%m-%d"
        self.decimal_format = "{:,.2f}"
        self.dollar_format = "${:,.2f}"
        self.percent_format = "{:,.0f}%"
        self.percent_decimal_format = "{:,.2f}%"

    def set_all(self):
        self.set_calls()
        self.set_puts()

    # ---------- Options Chain ---------- #
    def set_chain(self):
        stock = yf.Ticker(self.ticker)
        if self.expiration_date == "":
            self.option_chain = stock.option_chain()
        else:
            self.option_chain = stock.option_chain(self.expiration_date)

    def get_chain(self):
        if len(self.option_chain) == 0:
            self.set_chain()
        return self.option_chain

    # ---------- Candles ---------- #
    def set_candles(self):
        self.candles = yf.download(self.ticker, multi_level_index=False)

    def get_candles(self):
        if self.candles.empty:
            self.set_candles()
        return self.candles

    # ---------- Stock Price ---------- #
    def set_stock_price(self):
        candles = self.get_candles()
        self.stock_price = candles["Close"].iloc[-1]

    def get_stock_price(self):
        if self.stock_price == None:
            self.set_stock_price()
        return self.stock_price

    # ---------- Risk Free Rate ---------- #
    def set_risk_free_rate(self, ticker: str = "^TNX"):
        self.risk_free_rate = yf.download(ticker, multi_level_index=False)
        self.risk_free_rate = self.risk_free_rate["Close"].iloc[-1]

    def get_risk_free_rate(self, ticker: str = "^TNX", return_decimal: bool = True):
        if self.risk_free_rate == None:
            self.set_risk_free_rate(ticker)
        if return_decimal:
            return self.risk_free_rate / 100
        else:
            return self.risk_free_rate

    # ---------- Calls ---------- #
    def set_calls(self) -> pd.DataFrame:
        if len(self.option_chain) == 0:
            self.set_chain()
        self.calls = self.option_chain.calls
        self.calls = self.apply_peripherals(self.calls, "call")

    def get_calls(self) -> pd.DataFrame:
        if self.calls.empty:
            self.set_calls()
        return self.calls

    # ---------- Puts ---------- #
    def set_puts(self):
        if len(self.option_chain) == 0:
            self.set_chain()
        self.puts = self.option_chain.puts
        self.puts = self.apply_peripherals(self.puts, "put")

    def get_puts(self):
        if self.puts.empty:
            self.set_puts()
        return self.puts

    # ---------- Option Peripheral ---------- #
    def apply_peripherals(self, option_data: pd.DataFrame, option_type: str):
        # Stock Price & Risk Free Rate
        stock_price = self.get_stock_price()
        risk_free_rate = self.get_risk_free_rate()
        # Strike Spread
        if option_type == "call":
            option_data["strike_spread"] = (
                (option_data["strike"] - self.backtest.last_price)
                / self.backtest.last_price
            ) * 100
        elif option_type == "put":
            option_data["strike_spread"] = (
                (self.backtest.last_price - option_data["strike"])
                / self.backtest.last_price
            ) * -100
        # Expiration Dates
        option_data["expirationDate"] = option_data["contractSymbol"].apply(
            self.apply_expiration_date
        )
        option_data["DTE"] = option_data["expirationDate"].apply(self.apply_dte)
        option_data["TDTE"] = option_data["expirationDate"].apply(self.apply_tdte)
        option_data["mark"] = (option_data["bid"] + option_data["ask"]) / 2
        # Selling data
        option_data["sell_collateral"] = option_data["strike"] * 100
        option_data["sell_credit"] = option_data["bid"] * 100
        option_data["sell_credit_mark"] = option_data["mark"] * 100
        option_data["sell_yield"] = (
            option_data["sell_credit"] / option_data["sell_collateral"]
        ) * 100
        periods = option_data["DTE"] / 365
        option_data["annual_yield"] = option_data["sell_yield"] * periods
        # Volume data
        option_data["volume/OI"] = option_data["volume"] / option_data["openInterest"]
        # Greeks
        option_data["delta"] = option_data.apply(
            lambda row: self.calculate_row_delta(row, stock_price, risk_free_rate),
            axis=1,
        )
        option_data["gamma"] = option_data.apply(
            lambda row: self.calculate_gamma_row(row, stock_price, risk_free_rate),
            axis=1,
        )
        option_data["theta"] = option_data.apply(
            lambda row: self.calculate_theta_row(row, stock_price, risk_free_rate),
            axis=1,
        )
        option_data["vega"] = option_data.apply(
            lambda row: self.calculate_vega_row(row, stock_price, risk_free_rate),
            axis=1,
        )

        columns = [
            "contractSymbol",
            "lastTradeDate",
            "strike",
            "lastPrice",
            "bid",
            "ask",
            "mark",
            "change",
            "percentChange",
            "volume",
            "openInterest",
            "volume/OI",
            "impliedVolatility",
            "inTheMoney",
            "contractSize",
            "currency",
            "strike_spread",
            "expirationDate",
            "DTE",
            "TDTE",
            "sell_collateral",
            "sell_credit",
            "sell_credit_mark",
            "sell_yield",
            "annual_yield",
            "delta",
            "gamma",
            "theta",
            "vega",
        ]
        option_data = option_data[columns]
        option_data.rename(
            columns={
                "percentChange": "change%",
                "openInterest": "OI",
                "impliedVolatility": "IV",
                "inTheMoney": "ITM",
            },
            inplace=True,
        )
        option_data.drop(["contractSize", "currency"], axis=1, inplace=True)
        format_cols = ["mark", "change", "change%", "volume/OI", "IV"]

        for c in format_cols:
            option_data[c] = option_data[c].apply(self.decimal_format.format)

        option_data["probability"] = option_data.apply(
            lambda row: self.apply_probability_row(row, option_type=option_type), axis=1
        )
        return option_data

    # ---------- Delta ---------- #
    def calculate_row_delta(self, row, S, r):
        return self.calculate_delta(
            S=S,
            K=row["strike"],
            T=row["DTE"] / 365,
            r=r,
            sigma=row["impliedVolatility"],
            option_type="call" if "C" in row["contractSymbol"] else "put",
        )

    def calculate_delta(self, S, K, T, r, sigma, option_type="call"):
        """
        Calculate Delta using the Black-Scholes formula.

        Parameters:
        S (float): Current stock price
        K (float): Strike price
        T (float): Time to expiration (in years)
        r (float): Risk-free interest rate
        sigma (float): Implied volatility (as a decimal, e.g., 0.25 for 25%)
        option_type (str): 'call' or 'put'

        Returns:
        float: Delta value
        """
        # print(f"S: {S} K: {K} T: {T} r: {r}  sigma: {sigma} Type: {option_type}")
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        if option_type == "call":
            return norm.cdf(d1)  # Call Delta
        elif option_type == "put":
            return norm.cdf(d1) - 1  # Put Delta
        else:
            raise ValueError("Invalid option_type. Use 'call' or 'put'.")

    # ---------- Gamma ---------- #
    def calculate_gamma_row(self, row, S, r):
        return self.calculate_gamma(
            S=S,
            K=row["strike"],
            T=row["DTE"] / 365,
            r=r,
            sigma=row["impliedVolatility"],
        )

    def calculate_gamma(self, S, K, T, r, sigma):
        """
        Calculate the gamma of an option.

        Parameters:
        S: Spot price
        K: Strike price
        T: Time to expiration (in years)
        r: Risk-free interest rate
        sigma: Volatility (annualized)

        Returns:
        Gamma value
        """
        # Calculate d1
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))

        # Standard normal PDF for d1
        phi_d1 = norm.pdf(d1)  # scipy.stats.norm.pdf(d1) computes φ(d1)

        # Gamma formula
        gamma = phi_d1 / (S * sigma * math.sqrt(T))
        return gamma

    # ---------- Theta ---------- #
    def calculate_theta_row(self, row, S, r):
        return self.calculate_theta(
            S=S,
            K=row["strike"],
            T=row["DTE"] / 365,
            r=r,
            sigma=row["impliedVolatility"],
            option_type="call" if "C" in row["contractSymbol"] else "put",
        )

    def calculate_theta(self, S, K, T, r, sigma, option_type="call"):
        """
        Calculate the theta of an option using the Black-Scholes model.

        Parameters:
        S: float - Spot price of the underlying asset
        K: float - Strike price of the option
        T: float - Time to expiration (in years)
        r: float - Risk-free interest rate
        sigma: float - Volatility (annualized)
        option_type: str - "call" or "put"

        Returns:
        float - Theta value
        """
        # Calculate d1 and d2
        d1 = (np.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * np.sqrt(T))
        d2 = d1 - sigma * np.sqrt(T)

        if option_type == "call":
            theta = (-S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) - r * K * np.exp(
                -r * T
            ) * norm.cdf(d2)
        elif option_type == "put":
            theta = (-S * norm.pdf(d1) * sigma) / (2 * np.sqrt(T)) + r * K * np.exp(
                -r * T
            ) * norm.cdf(-d2)
        else:
            raise ValueError("Invalid option type. Must be 'call' or 'put'")

        return theta / 365

    # ---------- Vega ---------- #
    def calculate_vega_row(self, row, S, r):
        return self.calculate_vega(
            S=S,
            K=row["strike"],
            T=row["DTE"] / 365,
            r=r,
            sigma=row["impliedVolatility"],
        )

    def calculate_vega(self, S, K, T, r, sigma):
        """
        Calculate the vega of an option using the Black-Scholes model.

        Parameters:
        S: float - Spot price of the underlying asset
        K: float - Strike price of the option
        T: float - Time to expiration (in years)
        r: float - Risk-free interest rate
        sigma: float - Volatility (annualized)

        Returns:
        float - Vega value
        """
        # Calculate d1
        d1 = (math.log(S / K) + (r + 0.5 * sigma**2) * T) / (sigma * math.sqrt(T))

        # Standard normal PDF
        phi_d1 = norm.pdf(d1)

        # Vega formula
        vega = S * phi_d1 * math.sqrt(T)

        return vega

    # ---------- Expiration Dates ---------- #
    def apply_expiration_date(self, contract_symbol: str):
        pattern = r"\d{6}"
        # Search for the pattern
        match = re.search(pattern, contract_symbol)
        if match:
            expiration_date = match.group()  # Extract the matched text
            # Format the date (convert YYMMDD to YYYY-MM-DD)
            year = "20" + expiration_date[:2]
            month = expiration_date[2:4]
            day = expiration_date[4:6]
            formatted_date = f"{year}-{month}-{day}"
            return formatted_date
        else:
            return np.nan

    def apply_dte(self, expiration_date: str):
        current_date = dt.date.today()
        expiration_date = dt.datetime.strptime(expiration_date, self.date_format).date()
        delta = expiration_date - current_date
        return delta.days

    # ---------- Trading Days Expiration ---------- #
    def apply_tdte(self, expiration_date: str):
        t1 = self.current_date
        t2 = expiration_date
        t3 = self.backtest.get_time_delta(t1, t2, weekend_adjusted=True)
        return t3

    # ---------- Probability ---------- #
    def apply_probability_row(self, row, option_type: str):
        probability = self.backtest.get_probability(
            row["strike"],
            expiration_date=row["expirationDate"],
            option_type=option_type,
        )
        return probability

    # ---------- Display ---------- #
    def display(
        self,
        row,
        option_type: str,
        num_contracts: int = 1,
        backtest_periods: list = ["1Y", "5Y", "10Y", "max"],
    ):
        # Year range
        one_year = yf.download(self.ticker, period="1y")
        year_low = one_year["Low"].min().values[0]
        year_high = one_year["High"].max().values[0]
        # Spread & Fees
        fees = num_contracts * self.contract_fee
        strike = row["strike"]
        spread = row["strike_spread"]
        # Expiration
        expiration = row["expirationDate"]
        dte = row["DTE"]
        tdte = row["TDTE"]
        # Credit & Premium
        credit = row["sell_credit"] - fees
        collateral = row["sell_collateral"]
        d_labels = []
        for i in backtest_periods:

            backtest = OptionsBacktest(
                self.ticker, strike, self.call, self.put, self.buy, self.sell, period=i
            )
            candles = backtest.candles
            bt = backtest.get_probability(
                strike,
                option_type=option_type,
                expiration_date=expiration,
                return_value=False,
                return_dict=True,
            )
            if i.lower() == "max":
                label = i
            else:
                label = i[:-1]

            d = f"""{label} Year(s): {self.percent_decimal_format.format(bt['probability'])}
"""

            #             d = f"""

            # -- {label} Year --

            # Total Candles: {len(backtest.candles)}
            # Total Periods: {bt['total']}
            # Match Periods: {bt['match']}
            # Probability: {self.percent_decimal_format.format(bt['probability'])}
            #             """
            d_labels.append(d)

        display = f"""
===========================================================
Price: {self.dollar_format.format(self.stock_price)}
Strike: {self.dollar_format.format(strike)}
Distance: {self.percent_decimal_format.format(spread)}

----------
[Expiration]

DTE: {dte}
TDTE: {tdte}

----------
{''.join(d_labels)}

----------
[Profitability]

Premium: {credit}
Collateral: {collateral}

----------
[Year Range]

{self.dollar_format.format(year_low)} - {self.dollar_format.format(year_high)}

        
        
        """
        print(display)

    def get_index_by_value(self, df, column_name, value):
        index = df.index[df[column_name] == value].tolist()
        return index


"""
[Analysis]

        Total Candles: {len(self.candles)}
        Total Periods: {bt['total']}
        Matching Periods: {bt['match']}
        Probability: {self.percent_decimal_format.format(bt['probability'])}"""
