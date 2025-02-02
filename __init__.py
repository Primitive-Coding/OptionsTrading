from Tools.options_chain import OptionsChain
from Tools.options_backtest import OptionsBacktest


if __name__ == "__main__":

    oc = OptionsChain("RIVN", buy=False, sell=True)
    oc.set_all()
    chain = oc.get_calls()
    print(f"Chain: {chain}")
