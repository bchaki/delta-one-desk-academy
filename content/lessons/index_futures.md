## Learn

An index future is a standardised, exchange-traded agreement to receive the level of an index at a future date against a price agreed today. It is cash settled: nobody delivers 500 shares. For a Delta One desk it is the cheapest, most liquid way to hold or hedge broad equity exposure, so it sits underneath index swaps, ETF hedges and a large share of client flow.

### Fair value: the cost of carry

Buying the future instead of the basket saves you the cash you would have spent on the shares, and costs you the dividends you would have received. So the fair price is today's index, grown at the financing rate, less the dividends the basket pays before expiry, each grown to expiry:

**F = S e^(rT) - sum of D_i e^(r (T - t_i))**

with S the spot index level (index points), r the continuously compounded financing rate (annual), T the time to expiry in years, D_i the dividend in index points going ex at time t_i. Dividends after expiry do not matter: the future holder never receives them.

Take S = {{ex.fair_value.args.spot:,.0f}}, r = {{ex.fair_value.args.r:.1%}}, T = {{ex.fair_value.args.t}} years and one dividend of {{ex.fair_value.args.divs.0.1:.0f}} points going ex after {{ex.fair_value.args.divs.0.0}} years. The financing term lifts the index to 5,056.57, the dividend takes off 15.10 (the 15 points plus a little interest, because it is received early and can be reinvested), and fair value is **{{ex.fair_value.expected:,.2f}}**. The market price is usually quoted a few points either side of that.

### Basis and convergence

The **basis** is future minus spot: F - S. With positive rates and modest dividends it is positive, because carry exceeds dividends. At expiry the future is settled to the index, so the basis must be exactly zero. That is [[convergence]]: the future is not drifting towards the index by luck, it is forced there by the settlement rule. A long future therefore *loses* its basis over time even if the index does not move, and that decay is the financing cost of the position. A long holder is paying [[cost of carry]] through the price.

### Implied repo: reading the price as a rate

Instead of asking "what is the fair price at a rate of 4.5%?" the desk asks the reverse: "what financing rate is this price telling me?". That is the [[implied repo]]. In its simple form, with dividends valued at expiry and ACT/360:

**r = ((F + FV(divs)) / S - 1) x 360 / days**

With S = 5,000, F = 5,040, dividends of 14.5 points at expiry and 91 days, the simple implied repo is **{{ex.implied_repo_simple.expected:.3%}}**. The exact version solves the continuous-compounding model for r numerically and gives **{{ex.implied_repo_exact.expected:.3%}}** (a continuously compounded rate sits a touch above the simple rate for the same cash flows). Compare the number with what it costs the desk to fund: if implied repo is *above* funding the future is rich, because selling it and buying the stock earns more than it costs. If below, the future is cheap.

### Rich, cheap and the no-arbitrage band

A [[cash and carry]] arbitrage sells the future and buys the basket, funded at the desk's long funding rate. A [[reverse cash and carry]] buys the future and shorts the basket, earning the short rebate (benchmark less borrow fee). Costs on both sides mean the future can sit anywhere inside a band without a free lunch. With 4.9% long funding, a 4.1% short rebate and 3 bps of costs, the band for our example is **{{ex.no_arb_band.expected.lower:,.2f}} to {{ex.no_arb_band.expected.upper:,.2f}}**, with a midpoint of {{ex.no_arb_band.expected.mid:,.2f}}. A market price of 5,060 is 11.98 points above the top: sell the future, buy the stock, and lock in about that edge before the scale of the trade and the risk of execution.

### The roll and calendar spreads

Contracts expire quarterly. To keep exposure you sell the near contract and buy the next, which is a [[calendar spread]] trade. If the near is 5,040 and the far 5,075 over a quarter, staying long costs **{{ex.roll_cost.expected:,.0f}} bps a year**: that is the [[roll]] cost, and it should be compared with the fair carry for the period. Roll week is when this trade is done by everybody at once, so the spread can move more than fair value suggests, and rich or cheap rolls are a real source of PnL and cost.

### Total return futures

A price future embeds the dividend: fair value subtracts it. A [[total return future]] (TRF) pays the *total* return of the index, dividends included, so the dividend disappears from the financing and the contract is quoted directly as a **spread over the overnight benchmark**. That makes the financing explicit and tradable on an exchange: more capital efficient than a bilateral swap, cleared, and easy to compare with swap spreads. A TRF at benchmark 4.3% plus 40 bps on 5,000 over a quarter is equivalent to a price-future basis of **{{ex.trf_basis.expected:.2f}} points** once 14.5 points of dividends are netted. Run it backwards: a price future at 5,040 implies a TRF spread of only **{{ex.trf_spread_from_price.expected:.1f}} bps**, so if clients pay 40 bps for the same exposure through a swap, the gap is worth looking at. The bilateral swap spread equals the TRF spread plus whatever the cleared contract does not carry: balance sheet, credit and bilateral margin.

### Margin and variation margin

The exchange clearing house requires **initial margin** when a position is opened (a buffer against a bad move, set by a SPAN-like scan of price scenarios) and settles **[[variation margin]]** in cash every day: gains are paid in, losses paid out. A long of 10 contracts with a multiplier of 50 that sees +12 points then -8 points receives {{ex.variation_margin.expected.0:,.0f}} and pays {{abs ex.variation_margin.expected.1:,.0f}}. Daily cash is not just a nuisance: it has a [[funding cost]] when the balance is negative, which is one reason a future and a swap with the same economics are not identical.

## Worked example

A client buys 10 contracts of an index future today and holds for two days. The multiplier is 50 currency units per index point.

**Step 1: profit on a move.** The future rises from 5,000 to 5,012. PnL is quantity x multiplier x change = 10 x 50 x 12 = **{{ex.futures_pnl.expected:,.0f}}**.

**Step 2: variation margin.** The cash moves daily. Day 1: +12 points, so the holder receives {{ex.variation_margin.expected.0:,.0f}}. Day 2: the price falls to 5,004, which is -8 points, so the holder pays {{abs ex.variation_margin.expected.1:,.0f}}. The net is +2,000, which equals 10 x 50 x 4.

**Step 3: fair value.** With S = 5,000, 4.5% continuously compounded, a quarter to expiry and one 15-point dividend after 0.1 years, F = **{{ex.fair_value.expected:,.4f}}**. A market price of 5,040 is about 1.5 points below that, so at a 4.5% rate the future is slightly cheap. Whether that is *tradable* depends on the desk's own funding and costs, which is the next step.

**Step 4: implied repo.** At 5,040 the simple implied repo is {{ex.implied_repo_simple.expected:.3%}} on ACT/360. The exact solve gives {{ex.implied_repo_exact.expected:.3%}} continuously compounded. That sits between the 4.1% short rebate and the 4.9% long funding rate, so neither arbitrage pays. At 5,060 the implied repo is well above funding and a cash-and-carry opens.

**Step 5: the band.** The band is {{ex.no_arb_band.expected.lower:,.2f}} to {{ex.no_arb_band.expected.upper:,.2f}}. Inside it, there is nothing to do. Above it, sell the future and buy the basket.

**Step 6: roll cost.** Rolling from 5,040 to 5,075 over a quarter costs {{ex.roll_cost.expected:,.1f}} bps a year, compared with a fair carry that you can read from the sandbox.

**Step 7: TRF.** The same exposure through a TRF at 40 bps over 4.3% costs {{ex.trf_funding.expected:,.0f}} of funding on 25m over 91 days (ACT/360), and is equivalent to a basis of {{ex.trf_basis.expected:.2f}} points on the price future.

## Desk reality

**Where the numbers come from.** The spot index, the dividend forecast and the funding rate are three different feeds owned by three different people. When a future looks 10 points rich, the first question is not "can we trade it?" but "which input is stale?". Dividend forecasts are the usual culprit, because analyst estimates lag announcements and an EU cancellation can move the whole curve overnight.

**Roll week.** Roll week is when TDAs check that every client position and hedge has rolled to the right contract, that the spread paid is in line with the screen, and that the swap hedge book still matches the futures held at the clearer. A missed roll leaves a client trade hedged with an expiring contract that settles to cash and leaves the desk unhedged.

**Margin calls.** Variation margin is paid in cash the next morning, so a large move on a hedged book (the client swap gains while the hedge loses) can create a funding need before the swap is settled. TDAs watch the daily margin file and make sure the treasury team knows the number before the call, not after.

**Quoting a TRF against a swap.** Clients compare a TRF spread with a swap spread. If a swap is quoted 30 bps wider than the TRF, the client will ask why. The honest answer is the premium for balance sheet, credit and margin that the exchange route does not carry. Know the number before the call.
