## Learn

Risk on a Delta One desk is the study of what is left after hedging. A client swap is hedged by stock or futures, so the price risk cancels. What remains is smaller, more varied and easier to overlook: basis, dividends, funding, borrow, FX and liquidity. This module teaches the **sensitivities**, the first-order measures of how PnL changes when one input moves, and how to read the desk's risk report as a list of questions to ask.

### Delta and gross

**Delta** is the PnL change for a 1% move in the underlying, or simply the exposure in currency: **delta = shares x price x FX**. For 10,000 shares at 50 with EUR at 1.10 the delta is {{ex.delta.expected:,.0f}} in USD. A book has two views of delta. **Net delta** adds long and short exposures and is the number that shows directional risk. **Gross** adds absolute values and shows the size of the balance sheet and operational footprint. A fully hedged swap book can have a net delta near zero and a gross of hundreds of millions, which is why gross is a limit too.

### Where the delta comes from

The synthetic desk's risk snapshot splits delta by source. **Cash**: stock the desk holds as hedges or arbitrage inventory. **Swap**: the desk's side of client swaps, which is the opposite of the client's position (a client long is the desk short). **Futures**: index hedges. A swap and its stock hedge appear in different columns of the same row and net to zero. A hedge without a swap, or a swap without a hedge, leaves a net exposure on that name, and that is exactly the kind of break risk reports exist to find.

### Beta-adjusted delta

Exposures to different stocks are not equal in market terms. **Beta-adjusted delta = delta x beta** converts each position into an equivalent exposure to the index. A 550,000 position with a beta of 1.2 is {{ex.beta.expected:,.0f}} of index-equivalent risk. Summed across the book it gives a single number for market risk. Beta delta is useful for index hedging but depends on a beta estimate, which is unstable for single names, so risk managers show both.

### FX delta

A position in a foreign stock has the price exposure and the FX exposure of the local currency. Hedges in a different currency from the client swap leave residual FX. **FX delta is the PnL for a 1% move of the currency**: for 1,000,000 of EUR inventory, a 2% fall in the euro costs {{ex.fx.expected:,.0f}}. The desk usually hedges FX at the portfolio level, and the residual is a limit.

### Funding sensitivity

Long inventory is funded at the benchmark plus the desk's FTP spread. If the spread widens by 1 bp, the annual cost rises by inventory x 1 bp. On 100 million of longs that is {{ex.ftp.expected:,.0f}} a year per basis point. The sign matters: the desk is exposed to higher funding costs when it carries unfunded longs and is protected where client swaps pay a fixed spread over its funding. The funding sensitivity is a small number day to day and a large one in a stress.

### Dividend sensitivity

A net long stock position earns dividends. If forecast dividends fall 10%, a 10 million position with a 3% yield loses {{ex.div.expected:,.0f}} over twelve months. A swap book with 100% pass-through has no dividend risk by construction, so the sensitivity picks up pass-through below 100%, withholding drag and hedges held in ETFs or futures. The risk report shows it as "dividend minus 10%" so it can be compared with other sensitivities in currency.

### Borrow sensitivity

Shorts pay borrow fees, and lent stock earns them. The desk's borrow sensitivity is the annual PnL change if every live fee moves 100 bps. It is negative for a net borrower and positive for a net lender. A short book in hard-to-borrow names has a large sensitivity to a rise in fees and, behind it, a recall risk the number does not capture.

### Liquidity and concentration

Risk is not only price sensitivity but also how fast you can get out. **Days to liquidate = |shares| / (participation x ADV)**. Selling 500,000 shares where ADV is 1,000,000 at 20% participation takes {{ex.dtl.expected:.1f}} days. **Concentration** is how much of the book sits in a few names: the top-five share and the **Herfindahl index**, which runs from 1/n for an even book to 1 for one name. Four equal names give {{ex.hhi.expected:.2f}}. Liquidity and concentration are limits on the desk because they decide how a stress turns into a loss.

### Reading the report

Read a risk report as questions. Is net delta within limits and does it match what the trader intends? Which names make up gross, and are they all hedged? Is FX delta concentrated in one currency? Did funding, dividend or borrow sensitivity change since yesterday, and why? Which names take more than three days to liquidate? Risk reports are most useful when the TDA reads them before the trader asks.

### What first-order measures miss

Sensitivities are linear approximations. They miss convexity (a delta-one book has little), correlation shifts in a stress, jumps (a corporate action or a halt) and the interaction of sensitivities (a funding squeeze and a recall happening together). The VaR and stress modules in this section add portfolio-level views. The sensitivities remain the language the desk speaks every morning.

## Worked example

Read a small risk snapshot.

**Step 1: delta.** A client is long 10,000 shares at 50 EUR with EURUSD 1.10: the desk's swap delta is -{{ex.delta.expected:,.0f}} USD. The hedge is +{{ex.delta.expected:,.0f}}. Net zero, gross 1.1 million.

**Step 2: beta.** The stock has a beta of 1.2, so the beta-adjusted exposure on each leg is {{ex.beta.expected:,.0f}}.

**Step 3: FX.** If the hedge were held in USD stock instead of EUR, the swap leg would carry 550,000 of EUR exposure with no offset: a 2% EUR fall changes PnL by about 11,000.

**Step 4: funding.** The desk carries 100 million of long inventory funded at the FTP: 1 bp costs {{ex.ftp.expected:,.0f}} a year.

**Step 5: dividends.** If 10 million of the long inventory is not covered by pass-through and dividends fall 10%, the PnL change is {{ex.div.expected:,.0f}}.

**Step 6: liquidity.** A 500,000-share position at 50% of ADV is {{ex.dtl.expected:.1f}} days at 20% participation.

**Step 7: action.** The TDA checks that the net on the single name is zero, flags the FX residual and notes the dividend exposure for the trader. That is a complete morning read of the risk report.

## Desk reality

**Net delta of zero is where the questions start.** Ask what is in gross, and whether every swap has a live hedge. Orphan hedges and unhedged swaps are the common finds.

**Sensitivities are in different units.** Delta is currency per percent, funding is currency per basis point a year and dividends are currency per percent of forecast. Convert before comparing.

**Check the date.** A risk report run on a stale snapshot misses the day's trades. Confirm the snapshot time and the trade cut-off before you rely on it.

**Know the limits behind each number.** Each measure has a soft limit that triggers a conversation and a hard limit that triggers action. The Limits module has the full set.
