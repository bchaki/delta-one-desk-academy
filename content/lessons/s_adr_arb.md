## Learn

An American depositary receipt lets US investors hold a foreign share in dollars. Because each ADR is a claim on a fixed number of local shares, its price should equal the local price times the ratio times the exchange rate. When it does not, there is an arbitrage, limited by the cost of converting between the two lines. This page covers parity, the band, the legs, the risks and why large deviations tend to appear exactly when you cannot trade.

### Thesis

The fair value is **FV = local price x ratio x FX**, where the ratio is local shares per ADR and FX is dollars per unit of local currency. With a local price of 25, a ratio of 2 and an FX rate of 1.10, FV is {{ex.fv.expected:.2f}}. If the ADR trades above fair value by more than costs, **sell the ADR, buy the local shares and deliver them to the depositary to issue new ADRs**. If it is below, **buy the ADR, cancel it for local shares and sell those**. At the end of the cycle you have a flat position and the gap as profit.

### Legs

An ADR arbitrage has four legs. The ADR trades in the US market. The local shares trade in the home market. The FX leg converts proceeds. The **depositary** issues or cancels ADRs and charges a **conversion fee** per ADR. The legs settle at different times and on different calendars, and for part of the day only one market is open.

### The band

The band around parity is the conversion fee plus costs for both sides: bid/asks, FX spread and commissions. With a fee of 0.02 per ADR and 10 basis points of other costs on a fair value of 55, the lower and upper bounds are {{ex.band.expected.lower:.3f}} and {{ex.band.expected.upper:.3f}}, or a half-width of {{ex.bps.expected:.1f}} basis points. If the ADR trades at 55.20 it is above the upper bound by {{ex.edge.expected.1:.3f}} per ADR and the action is to {{ex.edge.expected.0}}. Edges that exist only at the quoted price and vanish when the book is hit are not edges.

### Why FX and timing matter

The local leg trades in local currency, so the dollar value of the position moves with FX until the conversion is complete. A 50 basis point move in FX on a 1 million trade is 5,000, more than a thin edge. In practice the FX leg is executed at the same moment as the share legs, and dealers quote their own parity using live FX. When the local market is closed, the ADR trades alone and its deviation from the last local close is not an arbitrage but the market's guess about where the local share will open.

### Backtest on the synthetic world

The sandbox calculates each synthetic ADR's deviation from parity in basis points, sets a band from your cost input and the depositary fee, and trades outside the band plus an edge back towards half the band. The reported statistics are the number of trades, net PnL and hit rate, with the deviation series and the trading bands shown on the chart. The decomposition separates the gross convergence from the round-trip band costs. A sweep shows net PnL against the edge demanded. The number of trades differs a great deal between ADRs, because their conversion fees and ratios give them different bands.

### Inputs

ADR and local prices at the same time, the FX rate, the ratio, the depositary's fee schedule and cut-offs, local-market borrow cost for short sales, withholding tax on local dividends for the ADR (which can differ from the local holder's net), and local stamp duty or financial transaction tax on purchases.

### Risks and failure modes

**FX gap.** FX moves between the legs.

**Conversion fee change.** The depositary raises the fee.

**Local market closed or halted.** One leg cannot trade; the position is exposed.

**Settlement mismatch.** The legs settle on different days, creating financing and fail risk.

**Withholding tax and tax rules.** ADR holders and local holders may be taxed differently on dividends.

**Short-sale restrictions.** Shorting the local share can be restricted in some markets.

### What the simulation omits

Closing prices on both legs, no settlement mismatch, no borrow on the local leg and no conversion cut-off. A real desk models each, and the depositary's cut-off often decides whether a trade is possible at all.

### Dividends, tax and ratios

ADR holders receive dividends in dollars after the depositary converts them and deducts its fees and any local withholding tax, so the net dividend an ADR holder gets can differ from what a local holder gets. A swap on the ADR and a swap on the local share therefore carry different dividend pass-through, and a desk that hedges one with the other has a residual. The ratio can also change: when an issuer changes the number of local shares per ADR, the ADR price should adjust at once; any gap between the announcement and the adjustment is a corporate-action risk, not an arbitrage. Always check the ratio the depositary currently publishes before trusting a deviation.

### Reading a deviation

When you see a deviation, ask four questions in order. Is parity computed with live FX and with the correct ratio? Are both markets open and are the prices simultaneous? Is the gap larger than the band at executable sizes? Is the position one you can finance and hedge for the settlement period? Only if every answer is yes is it a trade. A standing gap that fails the first or second test is a data problem; one that fails the third is a cost problem; one that fails the fourth is a capital problem.
## Worked example

Check a quoted ADR for parity.

**Step 1: parity.** 25 x 2 x 1.10 = {{ex.fv.expected:.2f}}.

**Step 2: band.** Fee 0.02 per ADR and 10 basis points of costs: bounds {{ex.band.expected.lower:.3f}} to {{ex.band.expected.upper:.3f}}, a half-width of {{ex.bps.expected:.1f}} basis points.

**Step 3: market.** The ADR is at 55.20: above the upper bound.

**Step 4: action.** {{ex.edge.expected.0}}, edge {{ex.edge.expected.1:.3f}} per ADR.

**Step 5: risk.** FX moves 50 basis points between legs: the loss is more than the edge. Execute FX with the shares.

**Step 6: record.** Log the parity inputs, the band and the execution times of all four legs.

## Desk reality

**Who does it.** ADR and cross-listing desks, often within an equity trading group. For a Delta One desk, ADRs show up as hedges for swaps on foreign underlyings and as alternatives when the home market is closed.

**Controls.** Check which line settles first, and whether the swap's underlying is the ADR or the local share; the dividend and tax treatment differ.

**Capital.** Two lines and FX use balance sheet and need borrow on the short leg.

**Warning signs.** A persistent gap in an ADR on a day when the local market is closed, or after a corporate action on one line only.
