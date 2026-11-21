## Learn

This module teaches from cases: what happens in a short squeeze, how a recall wave unfolds, and how a dividend-arbitrage scheme known as cum-ex defrauded tax authorities. These are not playbooks. They are compliance and risk cases that every person on a desk should understand, because they show how routine mechanics, such as lending, borrowing and dividends, can be misused or can fail.

### Case 1: the short squeeze

A **short squeeze** happens when a heavily shorted stock rises, short sellers cover to limit losses, and their buying pushes the price higher still. Three ingredients combine: **high short interest** relative to free float, **limited lendable supply**, and a **catalyst** such as news or coordinated buying. Rising prices raise margin and collateral requirements, so shorts are forced out. Rising demand for the stock raises utilisation, borrow fees spike and **lenders recall** shares to sell into the rally. A recall forces the short to buy or re-borrow at a worse fee.

The synthetic world contains one such episode. Its mechanics can be read from the series: utilisation climbs towards the cap, the borrow fee follows the convex curve from the loan economics module, recalls hit, and the price jumps. The squeeze function in the engine gives the utilisation: if demand is 600,000 shares, supply 1,000,000, 20% of supply is recalled and demand rises by a factor of 1.5, utilisation would be {{ex.sqz_util.expected:.2f}} (capped at 99%). The fee at 99% utilisation with a 30 bps GC fee and steepness 2 is {{ex.sqz_fee.expected:,.0f}} bps.

What the desk should do before and during a squeeze: monitor short interest, utilisation and the fee series daily; limit short swap exposure in names with thin lendable supply; make sure client short swaps pass through borrow and are not all-in; model the buy-in cost and recall costs for the biggest shorts; and agree a communication line with sales, risk and the client before the squeeze starts. The record of past squeezes also shows which actions made things worse: ignoring recall notices, relying on a single lender, and quoting fixed all-in spreads on special names.

### Case 2: the recall wave

A recall wave is less visible: several lenders recall in the same week, perhaps because a market-wide event raises their cost of funding or an index rebalance pulls stock out of lending programs. Fees rise across many names. The desk faces simultaneous re-borrow and buy-in decisions. The operations module gives the cost comparison per name; here the lesson is to look at the book as a whole. If every recall is handled by re-borrowing from the same few lenders, the next recall wave hits the same lenders.

### Case 3: the cost of an unlocated short

A trader sells a stock short before confirming a locate. The borrow fails, the delivery fails, and the settlement regime fines the fail and may force a buy-in. The financial loss is small. The regulatory finding is serious, because it shows a control that did not operate. The lesson: locates are a pre-trade control. Evidence of the locate must be retained and tied to the trade.

### Case 4: dividend arbitrage and cum-ex

In schemes known as **cum-ex** and its variants, participants arranged trades in shares around the dividend date so that several parties each claimed a refund of tax withheld on a dividend that had only been withheld once. The structures used short sales, lending and forward contracts to create the appearance of multiple owners of one share at the dividend date. Tax authorities in several countries later treated such claims as unlawful, prosecuted individuals and sought repayments from banks and funds that had participated or financed the trades.

The lessons for a desk are about **recognising red flags**, not about the mechanics. Red flags include trades concentrated around ex-dates with no commercial purpose other than the tax refund; very large volumes in a stock relative to its free float at the dividend date; financing and lending chains that return the same shares to the starting party; counterparties asking for particular dividend-date settlement timing; and returns that depend entirely on the tax treatment. If you see them, escalate to compliance, preserve records, and do not process the trade until it has been reviewed. The conduct and controls module covers the escalation path.

### Case 5: manufactured dividend disputes

Even without fraud, the tax treatment of manufactured dividends differs by jurisdiction. A mismatch can leave a lender claiming a credit it is not entitled to or a borrower under-withholding. The remedy is documentation: the loan agreement states the manufactured dividend treatment, and operations checks it against the dividend schedule on every ex-date.

### How the cases fit together

All of these cases come down to three ideas. **Scarcity is priced**: fees, rebates and repo rates rise together when supply is short. **Procedures protect you**: locates, recall monitoring and dividend checks are routine controls that prevent rare, expensive events. **Incentives can distort**: when a tax refund or a fee is large enough, people invent structures to capture it, and the desk must see the structure rather than only the trade.

## Worked example

Read a squeeze like a TDA would.

**Step 1: the position.** A client is short 120,000 shares at 100 via a swap (12,000,000 of notional). The borrow fee is 80 bps and utilisation is 55%.

**Step 2: the warning.** Utilisation climbs to 90% over a week and the price rises 12%. The fee model moves from 80 bps towards several hundred.

**Step 3: the recall.** A lender recalls 20% of its loans. Supply falls and demand has risen: utilisation hits the cap.

**Step 4: the fee.** At the cap, the model fee is {{ex.sqz_fee.expected:,.0f}} bps: carrying 12,000,000 at that fee costs about {{ex.sqz_carry.expected:,.0f}} a month.

**Step 5: the choices.** Re-borrow, if any is available, at the new fee; buy in at a premium; or internalise if the desk holds stock. The recall-options function from the operations module prices all three.

**Step 6: the client.** If the swap passes borrow through, the client carries the cost and may cover. If it was quoted all-in, the desk carries it. Check the paper.

**Step 7: the review.** After the event, record the lessons: concentration in lenders, the speed of the response, the client communication.

## Desk reality

**Squeezes are rare, and the process is the protection.** You will rarely see one, but the daily utilisation and fee checks are what let you see it early.

**Compliance cases are not abstract.** People in your position, not only executives, were charged in the cum-ex cases. If a trade does not make sense without the tax angle, ask why.

**Keep evidence.** Locates, recall notices, mark disputes and escalations should be retained and findable.

**Do not discuss client positions in the middle of a squeeze outside the people who need to know.** Information barriers and market abuse rules apply.
