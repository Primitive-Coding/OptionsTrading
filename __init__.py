from Tools.options_chain import OptionsChain
from Tools.options_backtest import OptionsBacktest
from Tools.backtest import Backtest
import yfinance as yf


if __name__ == "__main__":
    ticker = "F"
    candles = yf.download(ticker, multi_level_index=False)
    back = Backtest()
    prob = back.multi_year_analysis(
        candles, option_type="put", option_side="sell", window=2, strike_price=9
    )
    print(f"Prob: {prob}")
    # p = back.backtest_put(candles, 2, 9, "sell", manual_stock_price=9.50)
    # print(f"P: {p}")
    # # oc = OptionsChain("RIVN", buy=False, sell=True)
    # # oc.set_all()
    # # chain = oc.get_calls()
    # # print(f"Chain: {chain}")
