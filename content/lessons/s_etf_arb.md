## Learn

An exchange-traded fund trades like a stock but is made of a basket. What keeps its price close to the value of that basket is a mechanism: authorised participants can create new ETF shares by delivering the basket, or redeem shares for the basket. This page covers the trade that enforces that link, what it costs and why it gets harder exactly when it is needed most.

### Thesis

The ETF's **NAV** per share is the value of the basket plus cash divided by shares outstanding. During the day the market's best estimate is the **iNAV**. The **premium or discount** is the ETF price over NAV minus one. If the ETF trades at a premium larger than the costs of the round trip, you **sell the ETF, buy the basket and deliver it to create new ETF shares**. If it trades at a discount, you **buy the ETF, redeem it for the basket and sell the basket**. Either way you lock in the gap, because the creation or redemption happens at NAV.

### Legs

The ETF leg is traded on the exchange. The basket leg is traded in the cash market, possibly across several currencies and venues. The third leg is the creation or redemption itself, done by an **authorised participant** (AP) with the fund, which charges a creation fee per unit. A creation unit is a block of ETF shares, for example 50,000, and the fee is a fixed amount per unit regardless of its value.

### PnL drivers and the threshold

An ETF at 100.50 against an iNAV of 100.00 has a premium of {{ex.prem.expected:.1%}}, which is {{ex.arb.expected.premium_bps:.0f}} basis points. The break-even is the creation fee over the unit's value, plus basket execution costs, plus the ETF half-spread. With a fee of 5,000 on a unit worth 5 million, that is 10 basis points for the fee, 3 for the basket and 2 for the ETF: a threshold of {{ex.thr1.expected:.0f}} basis points. The edge is the premium less the threshold, {{ex.arb.expected.edge_bps:.0f}} basis points, and on a unit worth 5 million that is {{ex.arb.expected.pnl_per_creation_unit:,.0f}}. The action is {{ex.arb.expected.action}}: the ETF is rich.

### Why liquidity vanishes in stress

The fee does not move but market costs do. If basket costs and the ETF spread double, the threshold goes to {{ex.thr2.expected:.0f}} basis points, and at four times it is {{ex.thr4.expected:.0f}}. The wider band means the premium or discount can stay large without any arbitrage closing it. This is not a failure of the mechanism: it is the arbitrageur correctly pricing the risk that the basket cannot be bought or sold at the quoted prices. It is also why ETFs holding less liquid assets can trade at wide discounts in sell-offs. The risk button in the sandbox sets stress costs to four times the base and shows the number of trades that survive.

### Backtest on the synthetic world

The sandbox computes the premium of each synthetic ETF to NAV (index total return times the fund's scale), sets a threshold from your cost inputs, adds an edge you demand and trades back to half the threshold. It reports the number of trades, net PnL, hit rate and the premium series with the trading bands. A second chart shows net PnL against the edge demanded, and a waterfall separates the gross convergence from the round-trip costs. Notice how few trades happen at four times costs: that is the liquidity effect in numbers.

### Inputs

Holdings and cash for NAV, the basket price feed, the ETF price, the creation unit size, the creation fee, basket execution costs including impact, FX if the basket is multi-currency, and the settlement timing of each leg. The fee and unit size are published by the fund; the costs are the desk's estimates.

### Risks and failure modes

**Liquidity stress.** Costs widen and the threshold with them.

**Creation fee changes.** A higher fee widens the band, and the effect is larger for smaller units.

**Stale or wrong NAV.** An apparent premium may be a stale price in the basket, not an opportunity. Always check the basket prices before trading a large gap.

**Settlement mismatch.** The ETF may settle on a different cycle from the basket, creating financing costs.

**Basket tracking.** The basket you deliver may differ from the fund's published basket, with its own tracking error.

**Concentration.** A fund with a few illiquid names makes the basket leg the bottleneck.

### What the simulation omits

Closing prices, no intraday iNAV drift, one currency, no financing of the basket between trade and settlement and no fund-specific rules about custom baskets. The full version models each of these and the AP's own limits.

## Worked example

Trade a rich ETF.

**Step 1: premium.** ETF 100.50, iNAV 100.00: {{ex.arb.expected.premium_bps:.0f}} basis points.

**Step 2: threshold.** Fee 10 bps of unit value, basket 3 bps, ETF 2 bps: {{ex.arb.expected.threshold_bps:.0f}} basis points.

**Step 3: edge.** {{ex.arb.expected.edge_bps:.0f}} basis points.

**Step 4: action.** {{ex.arb.expected.action}}: sell the ETF, buy the basket, deliver it for new shares.

**Step 5: PnL.** On one creation unit worth 5 million: {{ex.arb.expected.pnl_per_creation_unit:,.0f}}.

**Step 6: stress.** At twice market costs the threshold is {{ex.thr2.expected:.0f}} basis points and the edge falls to 30; at four times the threshold is {{ex.thr4.expected:.0f}} and the edge is only 20. The edge remains positive here but can vanish for smaller premiums.

## Desk reality

**Who does it.** An ETF market-making and arbitrage team, usually separate from the swap desk, with an AP relationship. A Delta One desk meets ETF arbitrage when clients trade swaps on ETFs and when the desk hedges baskets with ETFs.

**Capital.** The basket sits on balance sheet from execution to settlement.

**Controls.** Every creation and redemption has cut-off times; missing one means holding the position overnight.

**Warning signs.** A discount that does not close after the market opens, or a premium on a day when the underlying market is closed, often reflects a data problem or a real constraint rather than a free lunch.
