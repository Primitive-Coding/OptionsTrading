from Tools.options_chain import OptionsChain
from Tools.options_backtest import OptionsBacktest
from Tools.backtest import Backtest
import yfinance as yf


if __name__ == "__main__":
    ticker = "RKLB"
    candles = yf.download(ticker, multi_level_index=False)
    back = Backtest()
    p = back.backtest_call(candles, 2, 30, "sell")
    print(f"P: {p}")
    # oc = OptionsChain("RIVN", buy=False, sell=True)
    # oc.set_all()
    # chain = oc.get_calls()
    # print(f"Chain: {chain}")
