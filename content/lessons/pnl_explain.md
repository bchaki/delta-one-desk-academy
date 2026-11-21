## Learn

PnL explain is the daily reconciliation between what the desk made and what the desk thinks it should have made. The booked PnL comes from the books and ledgers. The expected PnL comes from a clean model: price moves, FX, execution, dividends, funding, borrow and repo, fees and dividend derivatives. The difference is **unexplained PnL**. When it is small, the books agree with the model. When it is large or persistent, something is wrong, and the job is to find out what.

### The components

The explain splits PnL into components, each a formula that the model can reproduce. **Price**: position x price change x FX on the previous day's end position. **FX**: position x previous price x FX change, the translation of foreign-currency inventory. **Execution**: traded quantity x (close - execution price), the slippage or spread paid on trade day. **Dividends**: gross dividends received on hedges less amounts passed through to clients. **Funding**: swap funding legs less hedge funding. **SBL and repo**: fees paid and received and the repo funding effect. **Fees**: sales credits paid and amendment upfronts received. **Dividend derivatives**: mark-to-market of dividend futures and swaps. The sum of the components is the **explained** PnL.

### Unexplained and the cent

The residual is **unexplained = total - explained**. In practice components are rounded to cents first, and unexplained is the residual of the rounded components, so the lines always add to the total exactly. For a total of 100.00 with components 60.126 and 39.874 the rounded lines are 60.13 and 39.87 and the unexplained is {{ex.unexplained.expected:.2f}}. A residual of a few cents is rounding. A residual of thousands is a break.

### Why a break shows up as unexplained

The total comes from the booked ledger, which includes any booking errors. The components come from the clean model, which does not. A booking error therefore lands in unexplained at its full size. Four classic breaks, each with a signature, are in the synthetic book.

**Wrong spread.** A swap booked with the wrong spread earns or pays the wrong funding spread every day. The impact is **notional x (booked - correct) x days / basis**: a 30 bps booking instead of 40 bps on 25 million for 30 days is {{ex.spread.expected:,.0f}}. The signature is a steady drift in unexplained that scales with notional.

**Missed dividend.** A dividend received on a hedge but never booked. The impact is **-shares x gross**: a 1.20 dividend on 50,000 shares is {{ex.missed.expected:,.0f}}. The signature is a one-day jump on the ex-date or pay-date, matching shares times a dividend amount.

**Wrong fixing.** A benchmark rate booked off. The impact on a long swap's funding leg is **notional x (booked - correct) x days / basis**: 4.10% instead of 4.00% on 10 million for 7 days is {{ex.fixing.expected:,.2f}}. The signature is a persistent small effect during the period that uses the fixing.

**Stale price.** A mark that did not update. The impact is **shares x (stale - right)**: 50,000 shares at 11.13 against 11.35 is {{ex.stale.expected:,.0f}}. The signature is a one-day error that reverses the next day.

**Wrong legal entity.** A booking under the wrong counterparty entity has no PnL impact at all, but is a legal and margin error, which is why it is on the list: not every break shows in unexplained.

### The diagnostic method

1. **Size and sign.** How big, and a gain or a loss? 2. **Timing.** One-off, steady drift, or a spike that reverses? 3. **Scope.** One trade, one name, one client, one book, or everything? 4. **Candidates.** For each suspect, compute the expected impact with the formulas above. 5. **Match.** The candidate within a tolerance of the unexplained is the likely cause. 6. **Confirm.** Open the trade or the market data and check. 7. **Fix and log.** The classify function in the engine does step 5: it returns the candidate closest to the amount, within a tolerance.

### Attribution

Explain says why PnL moved by component. **Attribution** says where it came from: by **book**, by **client**, by **ticker**, by **trade**. The usual daily view is a table of books against components, and a short list of top and bottom movers. The desk uses attribution to find which client or name a break belongs to, and to show the trader which parts of the book earned the money.

### Risk-based and full revaluation explain

The component method above is a **full revaluation** by cash flow. A **risk-based** explain approximates PnL as sensitivities times market moves (delta x return, rho x rate change) and treats the rest as unexplained. Delta-one books are simple enough that both agree to high precision. Where they disagree, you have found either a missing sensitivity or a break.

### Thresholds and escalation

Teams set a threshold for unexplained as a percentage of gross PnL or a fixed amount. Above it, the break must be investigated the same day. Persistent small unexplained values, a few thousand a day for a week, can be worse than a single large one because they are easy to dismiss.

## Worked example

Work a break the way a TDA would.

**Step 1: size and sign.** The explain shows an unexplained of {{ex.missed.expected:,.0f}} on the day, a loss against the model.

**Step 2: timing.** It appeared on a single day and did not reappear. The ex-date of a dividend is the same day.

**Step 3: scope.** It sits in one hedge book on one stock.

**Step 4: candidates.** Missed dividend on 50,000 shares at 1.20: {{ex.missed.expected:,.0f}}. Wrong spread: about {{ex.spread.expected:,.0f}} a month. Stale price: {{ex.stale.expected:,.0f}}.

**Step 5: match.** Missed dividend fits to the cent.

**Step 6: confirm.** The dividend schedule shows the stock went ex that day and no receipt was booked on the hedge.

**Step 7: fix.** Book the receipt, rerun the explain, and add the cause to the log. The classify function would return "missed_dividend" for this amount and these candidates.

## Desk reality

**Unexplained is a message, not a number.** The same total can be a cent of rounding or a missed dividend. Always ask which one.

**Find the date first.** The date a break starts usually names the cause: a dividend date, a reset, a trade date or a market-data failure.

**Never plug.** A plug to make explain reconcile hides the break and breaks the audit trail. Escalate instead.

**Write the signature in the log.** Next time a similar pattern appears you will recognise it in a minute.
