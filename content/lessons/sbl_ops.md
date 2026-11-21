## Learn

Once a loan is booked the work is operational: marking collateral, handling corporate actions, processing recalls and keeping the chain reconciled. Most losses in this business are not market losses. They are operational: a missed recall, a margin call not sent, a dividend not manufactured.

### The daily collateral mark

Every day the loan and collateral are re-valued. The requirement is **shares x price x margin**. If collateral is below the requirement, the borrower posts more. If it is above, the lender returns the excess, but only when the excess exceeds a **minimum transfer amount**, so as not to move tiny amounts every day. After a mark, collateral is never below the requirement. With 100,000 shares, collateral of 5,100,000 (price 50, margin 102%) and a rise to 52, the requirement is 5,304,000 and the borrower must post **{{ex.mark_up.expected.transfer:,.0f}}**. When the price falls to 48 the requirement is 4,896,000, and the excess of 204,000 is returned if the minimum transfer is 100,000 (**{{ex.mark_down.expected.transfer:,.0f}}**) but not if it is 250,000 (**{{ex.mark_down_min.expected.transfer:,.0f}}**).

### Why marks matter

A late call leaves the lender under-collateralised for a day, which is credit exposure to the borrower. Many desks mark intraday for volatile names. Disputed marks usually come from different price sources or cut-off times, so the desk's control is to agree the source and the time in the agreement.

### Recalls

The lender can recall the shares at any time on an open loan, subject to the settlement cycle. The borrower must return the stock, usually within the standard settlement period. Reasons for a recall: the lender sells the shares, wants to vote them, or sees the fee as too low. Handling choices for the borrower are three. **Re-borrow** from another lender, probably at a higher fee. **Buy in**: buy the stock back, which closes the short. **Internalise**: cover from internal inventory. The costs are not equal. For a 100,000-share loan at 50, recalled when the fee rises from 1% to 4%, with a 30-day horizon, a 2% buy-in premium, 1% impact and 0.5% internal cost, the costs are: re-borrow {{ex.recall.expected.reborrow:,.0f}}, buy-in {{ex.recall.expected.buy_in:,.0f}}, internalise {{ex.recall.expected.internalise:,.0f}}. Re-borrowing is cheap if the stock is available; the buy-in is the worst case, and the one that makes squeezes expensive.

### Failed deliveries and buy-ins

If the borrower cannot return the shares, the lender can **buy in** at the borrower's cost. The settlement regime, such as the penalty regimes in some regions, adds fines for fails. Prevention is better than cure: monitor recall notices daily and start the re-borrow before the deadline.

### Corporate actions on loans

When a loaned stock has a corporate action, the economics follow the entitlement. **Dividends**: manufactured by the borrower to the lender. **Splits**: the quantity of the loan changes with the ratio. **Rights and other elections**: the lender decides, and the borrower may need to recall the stock to let the lender vote or elect. **Mergers**: the loan is closed out or converted, depending on the terms. Missing a corporate action on a loan creates a break that the lender, not the market, will correct, usually with a claim.

### Reconciliation

Positions, collateral and fees must agree with the agent and the lender. Daily reconciliations compare quantities, prices, rates, accruals and collateral. Typical breaks are a quantity mismatch after a partial return, a rate mismatch after a re-rate, and a missing manufactured dividend. Each should be investigated by cause, not by plug.

### Counterparty and concentration

Exposure to a single lender or borrower is limited. A borrower's default leaves the lender holding collateral worth slightly more than the loan, and the margin is there to absorb a price move while the lender liquidates the collateral. Concentration in one lender is the main recall risk. Diversifying the sources reduces it at a cost of operational complexity.

### Controls to know

Locate checks before short sales, daily recall monitoring, mark disputes within a fixed window, manufactured dividend checks on every ex-date, agent statement reconciliation, concentration reporting by lender and by name, and a break log with ageing.

## Worked example

A desk is borrowing 100,000 shares through an agent. Price 50, margin 102%.

**Step 1: opening.** The loan is 5,000,000, collateral 5,100,000 in cash.

**Step 2: day 1 price rises to 52.** The requirement becomes 5,304,000. The desk posts {{ex.mark_up.expected.transfer:,.0f}} before the cut-off.

**Step 3: day 5 price falls to 48.** The requirement is 4,896,000. With a 100,000 minimum transfer the lender returns {{abs ex.mark_down.expected.transfer:,.0f}}.

**Step 4: recall.** On day 10 the lender recalls the shares, and the fee in the market is 4% against the 1% on the loan. The desk compares: re-borrow {{ex.recall.expected.reborrow:,.0f}}, buy-in {{ex.recall.expected.buy_in:,.0f}}, internalise {{ex.recall.expected.internalise:,.0f}}.

**Step 5: decision.** Internal supply is available, so the desk internalises at the lowest cost and informs the trader.

**Step 6: dividend.** A dividend on day 20 is manufactured to the lender, and the TDA checks the amount against the lender's statement.

**Step 7: reconciliation.** At the end of the day the agent statement matches the book. A residual fee difference of a few dollars is traced to a rounding convention and logged.

## Desk reality

**Recall days are bad days.** Recalls cluster around market stress and ex-dividend dates. Build the habit of reading recall notices first thing.

**Margin disputes are mostly price-source disputes.** Agree the source in advance. If a call is disputed, pay the undisputed portion and resolve the rest.

**Treat manufactured dividends like cash.** They are real cash flows with real tax. Reconcile them within the day.

**Escalate fails early.** A fail that becomes a buy-in is much more expensive than the same fail resolved two days earlier.
