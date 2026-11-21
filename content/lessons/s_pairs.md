## Learn

Pairs trading is the best-known form of statistical arbitrage. Two related stocks tend to move together, so when their prices drift apart, you bet they will come back. A flow Delta One desk rarely runs this as a business, but clients ask for swaps on pairs and baskets, and interviewers like it. This page shows the mechanics and, just as important, the ways it fails.

### Thesis

Take two stocks A and B in the same sector. If a combination of them, such as the log of A minus a multiple of the log of B, behaves like a stationary series that reverts to a mean, you can trade it. When the spread is unusually high, short A and buy B in the right ratio. When it falls back, close. The profit comes from reversion, not from the market's direction.

### Legs

Two stock positions: a long and a short. The short leg needs borrow and pays a borrow fee. Both legs are financed, and a swap structure can package them as a single spread trade with a financing leg for each.

### Hedge ratio, cointegration and half-life

The **hedge ratio** beta comes from regressing log A on log B. If A is exactly the square of B, the regression returns a hedge ratio of {{ex.beta.expected.0:.0f}} and an intercept of {{ex.beta.expected.1:.0f}}. The **spread** is the residual. A **cointegration test** checks whether the residual is stationary. The Engle-Granger style test regresses the spread's change on its lagged level and looks at the t-statistic; below about minus 3.34 is the rough five percent threshold used here. The test is a rule of thumb, not a publication-grade procedure: it has no augmentation lags and no correction for the many pairs you screen.

The **half-life** says how long reversion takes. For a series that decays by a factor phi each period, half-life is minus ln 2 divided by ln phi. With phi of 0.9 it is {{ex.hl.expected:.2f}} periods. A series with no reversion, like a steadily rising one, has an infinite half-life. A long half-life means capital tied up and borrow paid for months, so even a real relationship may not be worth trading.

### The z-score rule

Trade the spread's **z-score**: its distance from a rolling mean, in rolling standard deviations. Enter when it exceeds an entry level, for example 2, exit when it falls inside half a standard deviation and treat costs as a fixed amount in z units. The sandbox does exactly this on the synthetic world for the best pairs in a sector. It reports the hedge ratio, the test statistic, the half-life and the backtest PnL, with a z-score chart showing the entry bands.

### Why it is not a main business for a flow desk

A flow desk earns a spread on client flow and financing. A pairs strategy earns from a view on relative value, takes risk capital, needs a research process and has crowded exits. When it matters for the desk is when a client wants a swap on a pair, for example long one stock and short another as a single trade. Then the desk needs to know the hedge ratio the client intends, the borrow cost of the short, the correlation between the two legs (which drives margin and VaR) and what happens if one leg is acquired or suspended.

### The traps

**Multiple testing.** Screen enough pairs and some will look cointegrated by chance. The screen table shows how close the best pairs sit to the threshold, and why a pair that passes in sample may fail out of sample. Report how many pairs you tested.

**Look-ahead in the hedge ratio.** The sandbox fits beta on the whole sample. A live version must estimate it only from past data, which makes results worse.

**Regime change.** A merger, a scandal or a change in business model can break the relationship forever.

**Costs.** Round-trip costs on two legs plus borrow can exceed the edge.

### Inputs

Price histories for both stocks, borrow availability and fee, volatility, the correlation of the legs, liquidity (ADV) and any corporate actions on either name.

### Risks and failure modes

**Relationship breaks.** The spread does not revert and the loss can be large; use a stop in z-score terms.

**Slow reversion.** The half-life is too long for the carry cost.

**Data mining.** The pair was chosen because it looked good.

**Short squeeze.** The short leg is recalled or squeezed, forcing a close at the worst moment.

### What the simulation omits

Borrow on the short leg, dividends on either leg, a time-varying hedge ratio and position sizing. It uses constant beta and closing prices.

### Cointegration and correlation are different

Two stocks can be highly correlated in daily returns and still drift apart without limit, because correlation says nothing about the level of the spread. Cointegration is about levels: it says a combination of prices is stationary. That is why traders who rely on a high correlation alone are surprised when a pair keeps diverging. For risk and margin, however, correlation of returns is what counts, because VaR and portfolio margin are built from returns. A pair can be an excellent statistical trade and an expensive one to margin, or the reverse.

### Sizing and exits

Size a pairs trade by the dollar volatility of the spread, not by notional. Two legs of 5 million each with a spread volatility of 1% a day have a daily risk of about 50,000. Set a stop in z-score terms, such as 3.5, and a time stop at a multiple of the half-life, since a position that has not reverted after three half-lives is likely to be wrong. Record the reason for every exit; the log is what separates a process from a hope.
## Worked example

Test a pair.

**Step 1: hedge ratio.** If A is exactly B squared, the regression returns {{ex.beta.expected.0:.0f}}.

**Step 2: spread.** Build the spread as the residual of the regression.

**Step 3: test.** Compute the ADF statistic; below minus 3.34 suggests stationarity.

**Step 4: half-life.** For phi of 0.9 the half-life is {{ex.hl.expected:.1f}} periods.

**Step 5: trade rule.** Enter at plus or minus 2 in z-score, exit inside 0.5.

**Step 6: report.** State the number of pairs tested, the hedge ratio estimation window and the cost assumption.

## Desk reality

**Where you meet it.** Clients with quant strategies trade pairs and baskets through swaps. The desk's job is to price the financing, borrow and margin, not to share the view.

**Margin.** A well-hedged pair earns margin offsets under portfolio margin but not under simple Reg T.

**Controls.** Watch for restricted lists, corporate actions on either leg and sudden borrow cost increases.

**Conversation.** Know the vocabulary: cointegration, half-life, z-score, stat arb. Use it correctly and say when a claim is not supported.
