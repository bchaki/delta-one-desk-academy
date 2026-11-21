## Learn

A client who wants the return of an index has at least four ways to get it: **index futures**, an **equity swap**, an **ETF** or the **cash stocks themselves**. They all deliver roughly the same return, and they differ in what they cost. The cost depends on the holding period, the size, the client's funding and tax position, and what happens at the edges: dividends, rolls, fees and spreads. A Delta One desk is asked daily which is cheaper, and the honest answer is "it depends on how long you hold it". This module gives you a way to answer it.

### Measuring cost in excess of the benchmark

The comparison uses a simple convention. Holding the index return is the baseline. The **cost of exposure** is what the investor gives up relative to holding cash that earns the benchmark rate and receiving the equity total return. A cost is positive. Every wrapper has up to four components: a **financing spread** over the benchmark (explicit in a swap or implicit in a future's basis), a **fee** (ETF expense ratio), **dividend leakage** (withholding or pass-through below 100%), and **trading costs** (commission, spread, impact, taxes), which are paid once on entry and once on exit and again at every roll.

The formula for one wrapper over a period: **running cost = notional x (financing + fee + leakage) x days / basis**, and **trading cost = notional x (one-way cost x 2 x round trips + one-off)**. The total in bps a year is the total divided by notional, scaled by basis over days.

### Futures

Futures embed financing in the basis. In excess of the benchmark, the cost is the implied financing spread, a few basis points over a benchmark for liquid indices. Trading costs are low: commissions and a tight spread. But a position held beyond the front contract must **roll**, and every roll is another round trip. Margin must also be funded; the funding of the margin is not a cost in the same way as the financing spread but is a use of liquidity.

### Swaps

A swap's financing spread is explicit: say 40 bps over the benchmark. It also includes a hedging cost on entry and exit. Dividend treatment is negotiated: at 90% pass-through on a 1.5% dividend yield, the investor leaks 15 bps a year. Swaps have no roll and can match a bespoke basket exactly. They carry counterparty exposure and need documentation.

### ETFs

An ETF charges a **total expense ratio**, a few bps a year for broad indices, and has a bid-offer spread and a premium or discount at entry and exit. Dividends pass through net of the fund's own withholding. An ETF requires cash, so the investor's own funding cost matters: an investor financing it at benchmark plus 50 bps pays that spread. ETFs have no roll and no documentation.

### Cash stocks

Buying the stocks outright costs commission, spread, impact and any stamp duty or financial transaction tax on entry, and the same again on exit minus the tax where it applies on purchase only. Dividends pass through net of the investor's withholding tax. There is no fee. For a large basket the operational burden is the real cost.

### Breakeven holding periods

The shapes differ. A swap has low trading cost and high running cost, a future has low running cost but a roll cost, and an ETF's fixed cost is modest but running cost is its fee plus the investor's funding. **Breakeven days between A and B = (fixed A - fixed B) / (running B - running A) x basis**, with fixed and running in bps. It exists only if the wrapper with the higher fixed cost has the lower running cost. For a future with 6 bps fixed and 12 bps a year of running cost against a swap with 4 bps fixed and 55 bps a year, the breakeven is {{ex.breakeven.expected:.1f}} days: hold longer than that and the future is cheaper.

### The example in numbers

With 50 million over 90 days on a 360 basis, using illustrative inputs: the future costs {{ex.fut.expected.total:,.0f}} ({{ex.fut.expected.total_bps_pa:.1f}} bps a year), the swap {{ex.swap.expected.total:,.0f}} ({{ex.swap.expected.total_bps_pa:.1f}} bps a year), the ETF {{ex.etf.expected.total:,.0f}} ({{ex.etf.expected.total_bps_pa:.1f}} bps a year) and cash stocks {{ex.cash.expected.total:,.0f}} ({{ex.cash.expected.total_bps_pa:.1f}} bps a year). The ranking changes with the horizon and the inputs, which is why the lab has sliders.

### What the model leaves out

The model is deliberately simple. It does not include **market impact** beyond the single trading figure, **tax** by investor type, **margin funding** for futures and swaps, **counterparty and documentation** costs, **tracking error** between instrument and index, **basis risk** at the roll, or the **optionality** of early termination. The full version adds them. The conclusion that matters survives: running costs dominate for long holds and trading costs for short ones.

### Judgement beyond cost

The cheapest wrapper is not always the right one. A client with a single-stock view needs a swap or the cash stock. A client who must stay inside an index mandate and hold for years may prefer an ETF for simplicity. A client who needs leverage uses futures or swaps. A client with withholding-tax advantages uses cash stock. Cost is the first filter, not the last.

## Worked example

A client wants 50 million of index exposure for 90 days. Compare the options.

**Step 1: inputs.** ACT/360. Futures: financing spread 12 bps, trading 1.5 bps one-way, two round trips (one roll). Swap: spread 40 bps, 2 bps one-way, 15 bps leakage. ETF: the client's funding spread 50 bps, TER 9 bps, 2 bps one-way, 1 bp one-off. Cash: funding 50 bps, 3 bps one-way, 10 bps one-off.

**Step 2: future.** Total {{ex.fut.expected.total:,.0f}}, equal to {{ex.fut.expected.total_bps_pa:.1f}} bps a year.

**Step 3: swap.** Total {{ex.swap.expected.total:,.0f}}, {{ex.swap.expected.total_bps_pa:.1f}} bps a year.

**Step 4: ETF.** Total {{ex.etf.expected.total:,.0f}}, {{ex.etf.expected.total_bps_pa:.1f}} bps a year.

**Step 5: cash.** Total {{ex.cash.expected.total:,.0f}}, {{ex.cash.expected.total_bps_pa:.1f}} bps a year.

**Step 6: breakeven.** The future beats the swap beyond {{ex.breakeven.expected:.1f}} days.

**Step 7: recommend.** For 90 days the future is cheapest. The swap is justified only if the client needs a custom basket or avoids margin operations, and the desk should say so rather than quote the cheapest number.

## Desk reality

**Clients compare in bps a year, so convert.** A cost of 20,000 on a 90-day hold means nothing until it is annualised and compared to the alternative.

**Quote the whole-life cost.** A cheap entry with expensive rolls is a trap. Include every roll in the horizon.

**Withholding changes the answer.** For a non-US client in US stocks, 871(m) and treaty rates move dividend leakage by tens of bps. Check the client's status.

**Be honest about what is missing.** The model omits impact and tax. If either is large for a client, say so and refine the comparison before the client acts on it.
