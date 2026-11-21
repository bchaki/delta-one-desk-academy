## Learn

Index arbitrage is the oldest trade in equity derivatives and the cleanest test of whether you understand futures pricing. The idea is simple: a futures contract on an index and the basket of stocks that make up the index are two ways of owning the same thing, so their prices are tied together by financing and dividends. When the future drifts outside that tie, you can trade the gap. Every strategy page in the Strategy Lab uses the same layout: thesis, legs, PnL drivers, inputs, simulation, decomposition, risks, desk reality and a quiz. This page is the model.

### Thesis

The model price of a future is **F = S e^{rT} minus the future value of dividends** over the contract's life, where S is the index level, r the financing rate (continuously compounded, ACT/365) and T the time to expiry in years. With a spot of 5,000, a 5% rate, a quarter of a year to expiry and a 20-point dividend 0.1 years ahead, the model price is {{ex.fair.expected:,.2f}}. If the market future is rich against that, you **sell the future and buy the basket**: the **cash-and-carry**. If it is cheap, you **buy the future and short the basket**: the **reverse cash-and-carry**. At expiry the future settles at the index, so the gap closes by construction. That convergence is the profit; there is no view on direction.

### The legs

A cash-and-carry has three legs. You sell the future on the exchange. You buy the stocks in the cash market, funded by your treasury at the benchmark plus the funding transfer price (FTP) spread. You receive the dividends the stocks pay. A reverse trade shorts the stocks, which means borrowing them and paying a borrow fee, and you pay the dividends the stocks distribute (a **manufactured dividend**). The funding and the borrow are part of the model price, so a wrong input there creates an arbitrage that is not real.

### PnL drivers

For one trade, the gain in index points is the signed deviation at entry minus the deviation at exit, less costs. If the future is 2.0 points rich and converges to 0.1, the gross gain is 1.9 points; after 0.2 points of cost, the net is {{ex.rich.expected:.1f}} points. The cheap side mirrors this: a deviation of minus 2.0 converging to minus 0.1 also earns {{ex.cheap.expected:.1f}} points. To convert to money, multiply by the multiplier and contracts. Selling ten contracts at 5,030 and buying them back at 5,010 on a multiplier of 50 earns {{ex.currency.expected:,.0f}}.

The costs matter more than the signal. A round trip costs the stock commission and half-spread on every constituent, the futures half-spread and commission, the market impact of trading a large basket and the slippage between the closing price you modelled and the price you obtained. For an index of thirty stocks this is often a few basis points of notional, so a deviation of two basis points of spot is not an opportunity at all.

### Inputs you need

You need the spot index and the future at the same instant, the financing rate for the right currency and day count, a dividend forecast to expiry in index points, the borrow fee on the stocks if you are short, and your cost estimate for the basket. In this academy the deviation series is computed from the synthetic world: the front future against model value with the funding spread you choose. Change the funding spread and the signal changes: that is the first lesson, because a fair value that is wrong by ten basis points a year on a three-month contract is only about 2.5 basis points of spot, but it is enough to flip many trades from profit to loss.

### Simulation and band width

The sandbox runs a simple rule on the deviation series. Enter when the deviation exceeds an entry threshold in basis points of spot, exit when it falls back inside an exit threshold, and hold to the last observation before an expiry change. Costs are charged once per round trip, slippage on entry and again on exit. A narrow entry band trades often and pays costs on small edges. A wide band trades rarely and waits for large dislocations. The bar chart plots net PnL against entry band width; for most parameters there is a peak in the middle and a slump at both ends. That shape is the trade-off every arbitrage desk faces.

The test statistics reported are the number of trades, net PnL, hit rate and worst trade. For three trades of 3, minus 1 and 2 the total is {{ex.stats.expected.total:.0f}}, the worst is {{ex.stats.expected.worst:.0f}} and the hit rate {{ex.stats.expected.hit_rate:.2f}}. A high hit rate with a poor total means small wins and rare large losses, which is what a short-volatility profile looks like.

### Risks and failure modes

**Dividend risk.** The model assumes dividends are known. If a dividend is cut, the future's fair value rises and a short future position loses. The 2020-style episode in which several European issuers cancelled dividends is exactly this risk. The risk button in the sandbox shows the loss from a 20% cut in the remaining dividend points.

**Execution slippage.** Basket execution is rarely at the close you modelled. If slippage doubles, a thin edge turns negative.

**Funding input wrong.** If your funding spread is 50 basis points too low, you will see rich futures that are not rich and sell them repeatedly.

**Band tighter than costs.** Trading a deviation smaller than the cost of the round trip loses money on every trade. The simulation makes this vivid with a 3 basis point entry.

**Borrow and recall.** The reverse trade needs stock to borrow. A recall can force you to close the trade at the worst time.

**Limit and capital use.** The stock leg uses balance sheet, and the trade is a user of margin on the futures. A trade that looks profitable before capital can be unattractive after it.

### What the simulation does not capture

The sandbox uses closing prices, a single round-trip cost and no intraday path. Real index arbitrage runs intraday, often in an automated way, with partial fills, tracking error in the basket and queueing in the future. The synthetic data contains a mean-reverting deviation by construction, so a profit in the sandbox shows the mechanism, not a forecast of what the real market offers today.

## Worked example

Follow one cash-and-carry from signal to PnL.

**Step 1: fair value.** Spot 5,000, rate 5%, T = 0.25, one dividend of 20 points at t = 0.1. Model price {{ex.fair.expected:,.2f}}.

**Step 2: signal.** The market future trades 2.0 points above that. It is rich: sell the future, buy the basket.

**Step 3: entry.** Sell 10 contracts. Buy the stocks representing the same notional with funding at the benchmark plus FTP.

**Step 4: convergence.** Over the following days the deviation falls from 2.0 points to 0.1.

**Step 5: PnL.** Gross {{ex.rich.expected:.1f}} points after 0.2 points of costs. On ten contracts with a multiplier of 50, each point is 500, so the trade earns about 850 after costs. A 20-point move of the future against you would have earned or lost {{ex.currency.expected:,.0f}} on the future alone, which shows why the trade must be hedged on both legs.

**Step 6: record.** Log entry, exit, costs and slippage. Compare with the sandbox statistics to see whether realised performance matches the backtest.

## Desk reality

**Who runs it.** Index arbitrage is a specialist, mostly automated business. On a Delta One desk the same maths drives the quoting of futures and swaps, and traders watch the basis to decide when to hedge with futures rather than stock.

**Capital and balance sheet.** The stock leg uses balance sheet and the futures leg uses margin. Ask treasury what each costs before you size the trade.

**Limits.** Expect limits on gross stock position, on delta, on dividend exposure and on the futures position by expiry.

**What to check every morning.** The dividend forecast, the funding rate, any change in index constituents or weights, and any halted stock in the basket.
