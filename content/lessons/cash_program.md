## Learn

Cash equities are the raw material of the whole desk: every swap on a single stock is hedged with shares, every ETF creation needs a basket and every index trade eventually touches the underlying stocks. A Delta One desk trades cash equities in two modes, **agency** and **principal**, and it prices large baskets as **program trades**.

### Agency and principal

In an **agency** trade the desk is a broker. It works the order in the market on the client's behalf, the client bears the market risk and pays commission, and the price is whatever the market gives, measured against a benchmark. In a **principal** trade the desk takes the other side. The client gets a guaranteed price and the desk takes the risk of getting out of the position, so it charges for it: half the bid-offer spread, the market impact it expects to cause, and a risk charge for the market moving while it unwinds. A principal basket quote is a **risk bid**.

### Benchmarks

An order is judged against a benchmark: **VWAP** (volume-weighted average price over a window), **TWAP** (time-weighted), **arrival price** (the price when the order arrived, which gives *implementation shortfall*) or the **close**. Choosing the benchmark transfers risk: a client who asks for the close trades at a known reference, and the desk bears the risk of how it gets there. A **closing auction** price is attractive because index funds and ETFs need it, but auctions can be crowded and are one-way on rebalance days.

### Program trades and transition management

A **program trade** is a basket of stocks traded together, such as an index rebalance or a pension fund moving between managers (**transition management**). Baskets diversify: the risk of a 100-stock basket is far smaller than the sum of its parts, so a principal desk can price it tighter than it would price each stock alone, provided the basket is not concentrated in illiquid names or one sector.

### Square-root impact

Large orders move prices. A standard model says the impact in basis points is

**impact = k x daily volatility x sqrt(quantity / ADV) x 10,000**

where k is a coefficient near 0.5 to 1 and ADV is average daily volume in shares. For k = 0.7, daily volatility of 2% and an order of 10% of ADV, impact is 0.7 x 0.02 x sqrt(0.1) x 10,000 = **{{ex.impact.expected:.1f}} bps**. Doubling the order does not double the impact: it multiplies it by about 1.41, which is why splitting and patience help, and why the biggest orders are the ones most worth pricing carefully.

### Risk charge

While the desk unwinds a won basket the market keeps moving. The risk charge compensates for that: **basket volatility x sqrt(horizon days) x risk aversion x 10,000 bps**. A basket with 1.2% daily volatility, a two-day horizon and risk aversion 0.5 gives about **{{ex.risk_charge.expected:.1f}} bps**. Diversification matters here: basket volatility depends on pairwise correlation, and the lower the correlation the lower the charge.

### The risk bid

The principal bid is half spread plus weighted impact plus the risk charge. For a basket of two legs, the example below builds it from the parts: half spread, the impact of each leg weighted by notional, and the diversified risk charge. If the desk wins, its expected PnL is the risk charge (the half spread and impact are costs it pays out as it trades), and the standard deviation of PnL is the market risk it carries while liquidating. That asymmetry is the heart of the business: you are paid a small, near-certain premium and you take a larger, symmetric risk.

### Costs the desk sees

Commission and exchange fees, the bid-offer spread, stamp duty or financial transaction taxes in some markets, and short-sale restrictions or borrow costs when shorting. The desk's own cost figures are in `config/desk.yaml`: stock commission 1.0 bps, stock half spread 2.0 bps and an impact coefficient of 0.7, all illustrative.

### Pitfalls

**Information leakage:** telling too many people about a large basket moves prices before you trade. **Illiquid tails:** a few names with high days-to-trade dominate the risk. **Sector concentration:** correlated names diversify far less than the formula assumes. **Winner's curse:** the desk usually wins the baskets that other bidders were more afraid of.

## Worked example

A client asks for a principal bid on a 2-stock basket. Leg A: 100,000 shares at 50, ADV 1,000,000, daily volatility 2%. Leg B: 50,000 shares at 100, ADV 500,000, daily volatility 1.5%.

**Step 1: impact per leg.** Leg A trades 10% of ADV: 0.7 x 0.02 x sqrt(0.1) x 10,000 = {{ex.impact.expected:.1f}} bps. Leg B also trades 10% of ADV: 0.7 x 0.015 x sqrt(0.1) x 10,000 = 33.2 bps. Both notionals are 5,000,000 so the weighted impact is the average.

**Step 2: basket volatility.** With a correlation of 0.5 the basket volatility is {{ex.basket_vol.expected:.4%}} a day, below the average of the two.

**Step 3: risk charge.** Horizon two days, risk aversion 0.5: basket vol x sqrt(2) x 0.5 x 10,000.

**Step 4: add up.** The bid is half spread (2 bps) plus weighted impact plus the risk charge: total {{ex.risk_bid.expected.total_bps:.1f}} bps, or {{ex.risk_bid.expected.total_amount:,.0f}} on 10,000,000 of notional.

**Step 5: PnL if the desk wins.** Expected PnL equals the risk charge in money terms, {{ex.win_pnl.expected.0:,.0f}}; standard deviation {{ex.win_pnl.expected.1:,.0f}}.

## Desk reality

**Execution reports.** After a program trade the TDA checks fills against the order, reconciles quantities with the client's list, books the trade and the hedges, and prepares the execution report with the benchmark comparison. Differences between the client's list and the fills are a classic break.

**Auctions.** Closing auction orders have cut-off times that vary by exchange, and imbalance information is published before the close. For index events the desk knows roughly what is coming; for everything else it needs the exchange's rules in front of it.

**Short selling.** Shorting is restricted or reported in some markets, and locating borrow before selling is a requirement in others. A basket with shorts needs borrow sourced before it trades.

**Limits.** Each principal trade uses risk and liquidity limits. The TDA monitors days-to-liquidate and concentration for the basket in the days after a win, because the risk charge assumed a two-day exit, not a stuck position.
