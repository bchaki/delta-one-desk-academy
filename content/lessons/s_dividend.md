## Learn

Dividends are one of the largest and least visible risks on a Delta One desk. Equity swaps pass dividends to clients, futures price them in, structured products pay them out, and a surprise cut hits the books in several places at once. This page treats dividends as something to trade and something to hedge.

### Thesis

A **dividend future** settles on the index dividend points actually paid in its year. If you expect fewer dividends than the market price embeds, sell it; if more, buy it. A **dividend swap** does the same for a single stock or an index basket, with a fixed strike. Dealers also hold dividend exposure through structured products: notes that pay holders the dividends of a basket leave the dealer long dividends on the hedge, and the dealer sells dividend futures or swaps to flatten.

### Legs

A long dividend future receives the realised dividend points at settlement and pays the strike (the entry price). The desk's own legs are on the other side: a structured-note book that pays dividends to holders, a swap book that passes dividends to clients, and the cash book that receives the dividends of the hedge stock. The sum of those exposures, not any one leg, is what the desk hedges.

### PnL drivers

The PnL of a long dividend future is units times the difference between settlement and entry. Long 1,000 units at 20 that settles at 17.5 loses {{ex.long.expected:,.0f}}. A dividend swap is the same with a strike: realised 22 against a strike of 20 gives {{ex.swap.expected:,.0f}} on 1,000 units. Between entry and settlement the position is marked to the market price of the future, which can move a great deal on news.

### Cancellation stress

When dividends are cancelled, the settlement falls. A 30% cancellation of a forecast of 20 points against a strike of 18, on 100 units, produces a PnL of {{ex.cancel.expected:,.0f}} for the long. The sandbox plots the long swap's PnL against a growing share of the forecast being cancelled. The short side gains the same amount, which is why a desk that has sold dividends to hedge notes benefits from a cut, while the notes' investors lose. A dealer that is long dividends through its own books loses.

### Hedging structured-note exposure

Take notes with 1,000 units of dividend exposure, 20 index points a year and a two-year life. If dividends are cut by 25%, the desk expects {{ex.note.expected:,.0f}} less than its model assumed on the hedge. The point of the calculation is the size of the sensitivity: a modest percentage cut applied to a long-dated exposure is large. Dealers monitor this as a **dividend delta** by year and by market.

### The backtest on the synthetic world

The sandbox buys the year's dividend future at the chosen day after listing and holds to settlement, reporting entry, settlement, PnL and the worst mark on the way. The synthetic dividend futures do not converge to a fixed fundamental level, so the history shows large swings. That is the lesson: the path can be worse than the result, and margin and limits respond to the path.

### Risks and failure modes

**Cancellation.** Regulators or boards stop dividends across a sector.

**Forecast error.** Analysts' forecasts are not the same as what is paid.

**Basis between instruments.** Index dividend futures settle on the index definition, which uses free-float weights and adjustment rules; a swap on a single stock does not.

**Path risk.** Mark-to-market losses before settlement cost margin and may breach a limit even if the final result would have been fine.

**Withholding tax.** The dividend the desk receives depends on tax treatment; see the Dividends module.

### What the simulation omits

No discounting between entry and settlement, no basis between swap and future, no forecasts and no seasonal pattern. The full version adds forecast revisions by company and a discounting curve.

### Structured products and the dealer's long dividend position

A structured note that pays investors the dividends of a basket, for instance a capital-protected note with dividend participation, gives the dealer the opposite exposure: the dealer owns the basket as a hedge, receives the dividends, and pays them to investors through the note. That nets out only if the dividends received equal those paid. Where the note references a dividend forecast, a fixed rate, or an index definition different from the stocks held, residual dividend risk remains. Dealers therefore run a dividend book. Its inputs are the schedule of expected dividends by stock and ex-date, the pass-through percentage in each swap, withholding tax rates and the dividend futures and swaps already on the books.

### Dividends in the other modules

The Dividends module shows how a dividend is declared, goes ex and is paid. Equity Swaps shows the pass-through. Index Futures shows how dividends enter fair value. In this module the dividend is the trade itself: what the market pays for it, what you think it is worth and what happens to your book if the number changes. Compare these three views whenever you read a dividend forecast: the market-implied level from futures, the company-level forecast from analysts and the schedule the risk system holds.

### Limits and reporting

A desk typically has a dividend delta limit per year, by market, and a stress limit for a cancellation scenario. A TDA prepares the dividend exposure report: delta by year, the hedge in place, the stress result and any change since the last report. If the book moved overnight, say why: a new trade, a changed forecast or an ex-date passing.
## Worked example

A desk holds notes that pay holders the dividends of a basket.

**Step 1: exposure.** 1,000 units of dividend exposure, 20 points a year, two years.

**Step 2: hedge.** Sell dividend futures to match, so the desk is flat to dividends.

**Step 3: cancellation scenario.** Dividends fall 25%: without the hedge the desk loses {{ex.note.expected:,.0f}}; with it, the short futures offset.

**Step 4: trade view.** Long 1,000 units of a swap with strike 20 pays {{ex.swap.expected:,.0f}} if realised is 22 and {{ex.long.expected:,.0f}} if the future settles at 17.5 from an entry of 20.

**Step 5: report.** Show the exposure by year and what the cancellation stress costs.

## Desk reality

**Concentration.** Dividend risk concentrates by year and by sector. Look at the strip, not the total.

**Seasonality.** Dividends cluster at certain times; ex-date days are busy for operations as well as risk.

**Compliance.** Dividend-related trades around ex-dates and withholding-tax arrangements have been the subject of enforcement cases; the Compliance module treats them as cases to recognise, not as strategies.

**Models.** Know which dividend forecast your risk system uses and who owns it.
