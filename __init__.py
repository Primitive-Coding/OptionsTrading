from Tools.options_chain import OptionsChain
from Tools.options_backtest import OptionsBacktest
from Tools.backtest import Backtest
import yfinance as yf


if __name__ == "__main__":
    ticker = "F"
    candles = yf.download(ticker, multi_level_index=False)
    back = Backtest()

    # p = back.backtest_0dte(candles, )

    p = back.backtest_put(
        candles=candles,
        dte=30,
        strike_price=8,
        option_side="sell",
        manual_stock_price=9.54,
    )
