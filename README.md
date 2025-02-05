# Options Trading

---

### cash_secured_puts.ipynb

This notebook will streamline the process to get data for `cash-secured-puts`.
Below is how you can interact with the notebook.

---

###### Create object & set data

Within the notebook you will find the first cell with this code below.
Run this after changing the desired parameters.

In this example, I am looking at selling a `cash-secured-put` on Ford (F).
It has a strike price of $9, and expires in 3 days (as of writing).

```
from Tools.options_chain import OptionsChain

ticker = "F" # Change ticker here.
exp = "2025-02-07" # Change expiration date here.
strike_price = 9 # Change strike price here.

oc = OptionsChain(ticker, exp, buy=False, sell=True, backtest_period="1Y")
oc.set_all()
puts = oc.get_puts()
index = oc.get_index_by_value(puts, "strike", strike_price)[0]
row = puts.iloc[index]

oc.display(row, option_type="put")

```

#### Explanation:

===========================================================
Price: $10.16
Strike: $9.00
Distance: -11.42%

---

[Expiration]

DTE: 3
TDTE: 3

---

1 Year(s): 98.81%
5 Year(s): 99.52%
10 Year(s): 99.40%
max Year(s): 99.68%

---

[Profitability]

Premium: 3.96
Collateral: 900.0

---
