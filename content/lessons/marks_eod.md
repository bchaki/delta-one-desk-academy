## Learn

Marks are the prices and rates used to value the book each day. The end-of-day (EOD) process turns them into official PnL, risk and reports. If marks are wrong, everything downstream is wrong, and every number will still look precise. This module covers where marks come from, the checks that catch bad ones, and what the EOD process does with them.

### Where marks come from

For listed stocks and futures, the **official closing price** from the primary exchange. For ETFs, the primary listing's close. For ADRs, the US close. For swaps, the mark follows the **underlying** plus accruals. For benchmark rates, the **fixing** published by the administrator, applied with the lookback or shift defined in the contract. For FX, the **fixing** at the agreed time. For illiquid items such as dividend futures and borrow fees, **broker quotes or models** are used and should be labelled as such.

### Common problems

**Stale prices**: the same price as yesterday on a stock that obviously traded, because a feed stopped or a halted name was left alone. **Wrong source**: a close from a secondary venue. **Bad ticks**: a fat-finger print that is not real. **Wrong currency or scaling**: pence versus pounds, cents versus dollars. **Missing corporate action adjustment**: a pre-split price on a post-split position. **Fixing errors**: the wrong day's rate or a missing fixing. **Time-zone mismatch**: Asian prices marked at a time the market had not yet closed.

### Detection checks

Four simple checks catch most problems. **Unchanged price**: an exact repeat of yesterday's price is flagged. **Large move**: a one-day return above a threshold is checked against news. **Source comparison**: two sources disagreeing by more than a tolerance in bps. **Position-weighted impact**: sort flags by size of position times suspected error, so the largest ones are chased first. In the example below, a price series of 10.0, 10.5, 10.5, 11.13, 11.13 has repeated prices at positions {{ex.stale.expected.0:.0f}} and {{ex.stale.expected.1:.0f}}, and a 6% move at position {{ex.move.expected.0:.0f}} against a 5.5% threshold. Two sources of 10.00 and 10.02 differ by {{ex.source.expected.0.1:.0f}} bps, which breaks a 10 bps tolerance.

### Sizing the impact

The PnL error of a wrong mark is **shares x (wrong price - right price) x FX**. For 1,000 shares marked at 101 instead of 100, the booked PnL is overstated by {{ex.impact.expected:,.0f}}. A stale mark usually reverses the next day when the price corrects, so its effect is a one-day error in PnL and a one-day error in risk. That is still enough to breach a limit or mislead a trader, and it is the reason EOD controls run before the PnL is published.

### The EOD process in order

1. **Load** prices, fixings and FX and compare with expected sources. 2. **Check** for stale, large-move and source-break flags. 3. **Resolve** flags: confirm with the market data team, override with an approved price if justified, and document. 4. **Apply** corporate actions and dividends effective today. 5. **Run** accruals and resets. 6. **Reconcile** positions and cash. 7. **Run** the PnL explain and risk. 8. **Review** unexplained PnL and break flags. 9. **Sign off** with product control and release reports.

### Overrides

A price override should be rare, approved and documented, with the reason (feed fault, halted stock, bad tick) and the evidence. An override that is not documented is how a mark becomes a control failure. Independent price verification by product control compares marks to external sources on a schedule, and a persistent difference is a finding.

### Month end

At month end, marks are checked more heavily: product control re-verifies illiquid marks, accruals are reconciled to the general ledger and unexplained PnL is cleared or explained. A break found after month end becomes a prior-period adjustment, which is disliked by everyone. This is why the TDA starts the month-end checklist a few days before the last business day.

### Marks and risk

VaR, sensitivities and limits all use marks. A stale mark understates volatility for that name; a bad tick overstates it for a window. The risk modules later in the academy assume clean data, and the EOD controls here are what justify the assumption.

## Worked example

Run the checks on one name.

**Step 1: load.** Today's close for a stock held by the desk shows 11.13, the same as yesterday.

**Step 2: flag.** The unchanged-price flag fires. The stock normally moves 1% a day.

**Step 3: compare.** The second source shows 11.35 against the primary 11.13: a difference of about 198 bps, beyond a 10 bps tolerance.

**Step 4: size.** The desk holds 50,000 shares: impact = 50,000 x (11.13 - 11.35) = -11,000, understated PnL if the right price is 11.35. For the small example in the lesson: 1,000 shares marked 101 instead of 100 is {{ex.impact.expected:,.0f}}.

**Step 5: resolve.** Market data confirms the primary feed stopped at 14:10. An approved override to 11.35 is entered with the evidence.

**Step 6: rerun.** The PnL explain no longer shows an unexplained of 11,000.

**Step 7: log.** The break log records the cause (feed stop), the fix (override) and a follow-up (alert on unchanged prices at the close).

## Desk reality

**The cheapest control is a comparison.** Two independent prices and a tolerance catch most errors without sophisticated tooling.

**Documentation protects you.** An approved override with evidence is routine. The same override with no record is a finding.

**Know the cut-off.** If the EOD marks lock at 18:00 London, a correction at 18:30 may need a manual adjustment. Learn the cut-off and the process for late fixes.

**Watch your own reports.** A TDA who sees a flat line in a position chart should ask, not assume. Flat lines are often the first sign of a stale feed.
