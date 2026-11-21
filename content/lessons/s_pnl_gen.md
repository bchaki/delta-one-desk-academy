## Learn

This is the capstone of the Strategy Lab. It pulls the sources of desk PnL together: financing, bid/offer, borrow and lending, dividends, basis and arbitrage and fees. Then it subtracts what the desk's activity costs the bank in funding, balance sheet and capital. The answer to "is this desk worth having?" lies in the net figure, not the gross.

### Thesis

A Delta One desk earns from many small, mostly client-driven sources. Each source is easy to understand and small. Together they are large enough to matter, and their costs are also large. **Net contribution = revenue minus funding minus balance sheet cost**, and **economic profit = net contribution minus the cost of the capital used**. A desk with healthy gross revenue and a weak return on capital is a desk that will be asked to shrink.

### Revenue by source

The page groups the synthetic ledger's components into sources: **financing spread** (the funding component), **bid/offer and execution**, **borrow and lending**, **dividends**, **fees** and **basis and arbitrage / risk** (price and FX). The grouping is stated in the code, so you can see exactly what goes where. The values are the sum over the last 250 trading days. In the synthetic book the financing spread is large and positive, borrow and lending is a large negative (the desk is a net borrower of stock), and price and execution are small. That pattern is realistic in direction: swap desks make money on financing and pay for the borrow of hedges.

### By sub-book and client tier

The same total can be cut by **sub-book**, such as Equity Swaps, Swap Hedges, Index Futures, Financing & SBL, ETF, ADR Arbitrage and Dividends. The sub-books net to the same total as the sources. Swap and Hedges books look very different from each other, one strongly positive and one strongly negative, because the hedge book carries the funding and borrow costs that the swap book charges to clients. A manager who looks at the swap book alone overstates the desk's profit; one who looks at the hedge book alone understates it. By **client tier** the revenue is more concentrated in tier 1 clients, as is typical.

### Costs: funding, balance sheet and capital

The cost lines use the swap notional at the as-of date as the average notional. Funding = notional x FTP. Balance sheet = notional x leverage multiple x cost bps. Capital = notional x leverage multiple x capital ratio. The cost of capital is capital x the cost of equity. With revenue of 600,000 on a notional of 100 million, an FTP of 35 basis points, a leverage multiple of 1.5, a balance sheet cost of 8 basis points and a 4% capital ratio at a 10% cost of equity, funding is {{ex.net.expected.funding:,.0f}}, balance sheet {{ex.net.expected.balance_sheet:,.0f}}, capital {{ex.net.expected.capital:,.0f}} and the net contribution {{ex.net.expected.net_contribution:,.0f}}. The return on capital is {{ex.net.expected.return_on_capital:.1%}} and the economic profit {{ex.net.expected.economic_profit:,.0f}}. The example is deliberately a desk that looks profitable and does not earn its cost of capital.

### Budget against actual

A budget is a plan set at the start of the year. The variance table shows actual, budget, variance and variance in percent of budget by source. In the sandbox the budget is illustrative: a seeded 80 to 120% of actual per source, scaled by your slider. The point is the reading: variance in a source with a stable client base means a client behaved differently; variance in basis and arbitrage means markets did. Label variances accordingly in commentary.

### Client revenue and risk revenue

**Client revenue** comes from serving flow: financing spreads, bid/offer, fees and lending. **Risk revenue** comes from holding positions: price and basis moves. The first is repeatable and the second is not. A desk that makes most of its money from client revenue is a utility; one that makes most from risk revenue is a prop shop with a client franchise. Managers want the ratio visible every month. The sandbox splits the two.

### Inputs

Ledger by trade and component, client tiers, the FTP schedule, balance sheet and capital parameters, the budget and the booked PnL breaks that will move numbers between periods.

### Risks and failure modes

**Funding up.** Treasury reprices FTP.

**Lose the top tier.** Revenue concentrates in few clients.

**Balance sheet doubles.** Constraints bite and cost rises.

**Breaks.** Unreconciled differences between the booked and clean ledgers make the reported PnL different from the true one; see the PnL Explain module.

**Misleading cuts.** Reporting a favourable sub-book without the hedge book.

### What the simulation omits

Costs applied at a single point in time, no seasonality, no tax, no allocation of shared costs (technology, people) and no stress-period costs. The full version allocates all of them.

## Worked example

Assess a desk.

**Step 1: revenue.** Take the 250-day revenue by source from the ledger.

**Step 2: cut.** Check it by sub-book and tier: the totals must match.

**Step 3: costs.** For a 100 million notional at FTP 35: funding {{ex.net.expected.funding:,.0f}}, balance sheet {{ex.net.expected.balance_sheet:,.0f}}.

**Step 4: net.** {{ex.net.expected.net_contribution:,.0f}} against revenue of 600,000.

**Step 5: return.** Capital {{ex.net.expected.capital:,.0f}}, return {{ex.net.expected.return_on_capital:.1%}}, economic profit {{ex.net.expected.economic_profit:,.0f}}.

**Step 6: conclusion.** The desk earns positive net contribution but not its cost of capital; the question is whether to reprice, net or shrink.

## Desk reality

**Reporting.** A weekly and monthly PnL pack with sources, sub-books, client tiers, budget variance and cost lines. The TDA assembles it and reconciles it to the booked ledger.

**Commentary.** Write a sentence on every variance over a threshold: what changed, why and what happens next.

**Conversations with management.** They will ask three things: how much came from clients, how much from risk and how much is left after costs.

**Hygiene.** If a break is open, say so. Never present a number you cannot reconcile.
