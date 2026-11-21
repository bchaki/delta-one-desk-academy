## Learn

Booking is where a quoted price becomes a legal and accounting record. The booking system holds the trade, drives its cash flows, feeds risk and PnL, and sends data to operations, finance and the client. A booking error is not a clerical slip: it is a wrong cash flow, a wrong risk number or a wrong legal party, repeated every day until someone finds it. This module covers what a good booking contains, how to validate it, and how the trade changes over its life.

### What a swap booking contains

A swap ticket carries **identity** (trade ID, book, counterparty, legal entity, ISDA reference), **economics** (underlying, direction, shares, initial price, spread, benchmark, day count, reset frequency, dividend pass-through, notional reset flag) and **regulatory flags** (871(m), reporting). Dates matter: **trade date** (when agreed), **effective date** (when it starts accruing) and the reset schedule. The sign convention is always from the **client's** direction: a long client receives the equity return and pays funding. The desk's side is the mirror image, and cash flows are labelled with whose side they are from.

### Validation rules

Validation catches mistakes before they reach the ledger. The rules in the academy's validator are: the effective date must be a business day on the benchmark's calendar and not before the trade date; shares and price positive; spread within a range; short spread not below the borrow cost (a warning); dividend pass-through between 0 and 100%; reset frequency one of the allowed values; benchmark consistent with currency; an ISDA reference present; the counterparty known and with a CSA in force; legal entity matching the counterparty's; and the 871(m) flag set when a US underlying is traded with a non-US client. **Errors block booking; warnings need a second look.** The ticket sandbox runs these live.

### The lifecycle events

After booking, the trade changes through events: a **reset** (period end, cash settles, price and notional update), a **dividend payment** (pass-through amount), a **corporate action adjustment** (quantity or price factor), a **partial unwind** (shares reduce), an **amendment** (a field changes, sometimes with an upfront payment) and **termination**. Each event has a date and a trade ID, and each changes the **state** of the swap: shares outstanding, current spread, status. The state is derived by replaying events on the initial ticket. That is why the position is derived and never stored, so the audit trail always explains the number.

### Cash flows and rounding

Each period produces three cash flows: equity, dividend and funding. Analytics run in float64, but cash is rounded to cents at the booking boundary with **half-even** (banker's) rounding, so 2.675 books as {{ex.round_up.expected:.2f}} and 0.125 as {{ex.round_down.expected:.2f}}. Rounding each component and then adding gives a net that reconciles to the cent. Rounding the net would not.

### Reset dates

Reset dates are generated from the start by adding the reset frequency in months and adjusting to the next trading day. A trade starting on 15 January with quarterly resets and an end of 30 June has a single reset, on {{ex.reset_count.expected.0}}; the next would fall on 15 July, after the end. Adjusting to a business day means two trades with the same frequency can have slightly different accrual lengths, and the day count then matters.

### Packages and hedges

A client swap is linked to its hedge by a **linked trade ID** or a **package ID**. The link lets PnL and risk be attributed to the client and ensures an unwind of the swap triggers the unwind of the hedge. Orphan hedges, hedges with no client trade, are a standard break to look for.

### Amendments and their cost

Changing a spread on a live trade is not free: the new terms apply from the amendment date, and if the old terms were off-market, an **upfront payment** compensates. A mis-keyed spread corrected later changes PnL for the period in between, which is why such breaks must be found early. A 10 bps spread error on 25 million over a 30-day period is {{ex.spread_shortfall.expected:,.0f}}.

### Trade date, effective date and settlement

Three dates are easy to mix up. The **trade date** is when the price was agreed and is the date risk starts. The **effective date** is when financing begins to accrue, often the trade date plus the settlement cycle of the underlying. The **settlement date** of the hedge is when stock and cash actually move. A swap that starts accruing on the trade date while its hedge settles two days later has two days of funding mismatch, which the desk either charges for or absorbs. Booking the wrong one is a classic source of small, persistent PnL differences.

### Controls around booking

**Four eyes** (a second person checks), **ticket validation** (above), **confirmation matching** (the client's confirmation agrees with the booking), **daily position and cash reconciliation** and **break ageing reports**. A TDA owns the first and last of these in practice.

## Worked example

Book and follow a swap.

**Step 1: ticket.** Client long 10,000 shares at 100 on a US stock, spread 40 bps, SOFR, monthly resets, ISDA reference present, non-US client.

**Step 2: validate.** The 871(m) flag is required for this combination. Without it, the validator raises an error: the trade cannot be booked.

**Step 3: book.** With the flag set the trade books. The hedge is linked.

**Step 4: first reset.** Cash flows for the period: equity, dividend (if any) and funding, each rounded to cents, then added.

**Step 5: partial unwind.** The client closes 40% of the swap. State changes: 6,000 shares remain; the hedge reduces by 4,000.

**Step 6: error.** An amendment keyed the spread at 30 instead of 40 bps. The 10 bps shortfall on 25 million over 30 days is {{ex.spread_shortfall.expected:,.0f}}. The PnL explain shows it as unexplained.

**Step 7: fix.** Correct the spread from the right date, book the catch-up payment, and note the cause in the break log.

## Desk reality

**Booking from a chat message is a risk.** Always book from a ticket or confirmed email, and keep the source with the booking.

**Dates cause more breaks than prices.** Business-day adjustment, effective versus trade date, holidays in a second currency. Check them first.

**Do not fix by overwriting.** Amend with an event so the history explains the change.

**Every break has a cause category.** Tag it: economics, legal entity, flag, date, hedge link, market data. The tags show where to improve.
