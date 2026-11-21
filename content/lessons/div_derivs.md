## Learn

Dividend derivatives let investors trade the dividends themselves, separately from the share price. A **dividend future** or **dividend swap** pays the difference between the realised dividends of an index (or stock) over a period and a fixed strike. They matter to a Delta One desk because every index swap, future and structured note has dividend risk embedded in it, and the dividend market is where that risk is traded.

### Dividend swaps and futures

A **dividend swap** is an OTC contract: the long pays the strike and receives the realised dividends of the reference over a period (usually a calendar year); it settles in cash. A **dividend future** is the exchange-traded version with a fixed contract size, daily variation margin and a cleared exposure. The payoff for the long is **units x (realised - strike)**. With 1,000 units, a strike of 90 index points and 95 realised, the long gains **{{ex.swap_pnl.expected:,.0f}}**. Before settlement the value is the expected realised amount less strike, discounted: with an expected 95 and a discount factor of 0.97 the value is **{{ex.swap_pv.expected:,.0f}}**.

### Term structure

Dividend futures exist for several years ahead, so the strip forms a curve of expected dividends by year. The value of a strip of annual contracts is the sum of units x (expected - strike) x discount factor for each year. The term structure usually prices far-dated dividends *below* analyst forecasts, because the main sellers (structured product desks that hedge by selling dividend exposure) push the market down.

### Implied versus forecast

The difference between the market-implied level and the analyst forecast is the market's view of cuts or risk premium: a market of 88 against a forecast of 92 is **{{ex.implied.expected.0:.0f}} points or {{ex.implied.expected.1:.1%}}** below forecast. In normal times, that gap is partly a risk premium; in a crisis it can widen as the market prices cancellations.

### Cancellations

In stress, companies cut or cancel dividends: the synthetic market includes an EU cancellation episode in spring 2025. A long dividend position loses when dividends come in below the strike. If a forecast of 95 is cancelled by 60%, realised is 38 and the long on a 90 strike loses **{{ex.cancel.expected:,.0f}}** per 1,000 units. A short position gains. The curve and the PnL of existing trades move together.

### Who trades and why

**Structured products desks** issue notes that pay dividends to investors, so they are long dividends in the underlying stocks and sell dividend futures to hedge. **Long-only and dividend-focused funds** buy dividends for yield. **Hedge funds** express views on cuts. The **Delta One desk** warehouses the residual: dividend leakage on swaps, and basis between single-stock dividends and the index.

### Delta-one notes, certificates and trackers

A **delta-one note** (also certificate or tracker) is a bond-like security issued by a bank that pays the performance of an underlying: a stock, basket or index, with a fee. The investor takes the issuer's credit risk. Value = notional x (1 + total return) x (1 - fee)^years: a 1,000,000 note with 8% return, a 1% annual fee and two years is worth **{{ex.note.expected:,.0f}}**. The issuer hedges by holding the underlying or a total return swap, which is where the D1 desk comes in: it takes the hedge, pays or receives the total return, and charges financing.

### Dividend risk in the book

A hedged swap with 100% pass-through has no dividend risk. With less than 100% pass-through or withholding drag the desk is long dividends. A book of many swaps accumulates a net dividend position that the desk can hedge with dividend futures or swaps, to the extent the reference matches.

### Discounting and the carry link

Dividend swaps settle at the end of the period, so their value discounts expected dividends, and a long position also has a relationship to index futures: the future embeds the market's view of dividends to expiry, and a dividend swap is the cleanest way to isolate that piece. A desk that is short index futures and long the index in a cash-and-carry is implicitly long dividends, which is why the roll and basis work in the strategy modules keeps pointing back here.

### Stress behaviour

When forecasts fall, near-dated contracts reprice quickly because realised dividends become observable, while far-dated contracts move less but still fall. In the synthetic spring 2025 episode the curve flattens and inverts: the near year drops towards a level consistent with cancellations and later years follow at a discount. A desk that held long dividend exposure through the episode would show a mark-to-market loss long before any dividend failed to be paid, which is a reminder that these are traded instruments with marks, not just accounting for cash flows.

## Worked example

A desk buys 1,000 units of a dividend future on an index at a strike of 90 points.

**Step 1: payoff.** If realised dividends are 95, PnL is 1,000 x (95 - 90) = {{ex.swap_pnl.expected:,.0f}}.

**Step 2: PV before settlement.** With an expected 95 and a discount factor of 0.97, PV is 1,000 x 5 x 0.97 = {{ex.swap_pv.expected:,.0f}}.

**Step 3: strip.** Three annual contracts with strikes 90, 88, 86 and expected 95, 92, 90 with discount factors 0.97, 0.94, 0.91 give a PV of {{ex.strip.expected:,.0f}}.

**Step 4: implied versus forecast.** The market is at 88 against an analyst forecast of 92: {{ex.implied.expected.0:.0f}} points, {{ex.implied.expected.1:.1%}}.

**Step 5: cancellation.** If 60% of a 95-point forecast is cancelled, realised is 38 and PnL is {{ex.cancel.expected:,.0f}}.

**Step 6: tracker note.** A 1,000,000 note with an 8% total return, a 1% annual fee and two years has value {{ex.note.expected:,.0f}}, before issuer credit.

## Desk reality

**Where dividend risk hides.** Look for it in swap pass-through, withholding, hedges using ETFs (which pass through dividends differently) and index futures (which embed forecast dividends). The TDA's risk report should show a dividend sensitivity: PnL for a 10% change in forecast dividends.

**Settlement.** Dividend futures settle to the sum of dividends in index points over the calendar year, determined by an index provider. Check how special dividends are treated and the exact ex-dates counted.

**Marks.** Far-dated dividend futures are thinly traded; marks come from broker quotes and curve models. Stale marks on a strip are a PnL risk, especially after an announcement.

**Notes.** For delta-one notes, ask who the issuer is, what the fee is and how the hedge is documented. The note's value includes the issuer's credit, which the desk does not own but must understand.
