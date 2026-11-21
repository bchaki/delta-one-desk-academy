## Learn

A corporate action is any event that changes a company's shares, price or ownership outside normal trading: a split, a rights issue, a spin-off, a merger, a special dividend. For a Delta One desk it is a **contract event**. A swap, a hedge and a futures position all have to be adjusted so that the client is economically where they would have been had they held the shares, and the desk's hedge must be adjusted to match. A wrong adjustment is a PnL break and often a client complaint.

### The one rule: value must be preserved

Every adjustment follows a single principle: **the value of the position just before the event equals its value just after**, counting cash and any new securities received. We express an adjustment as a quantity factor, a price factor, any cash per old share, and any new asset received per old share. Value per old share after the event is then

**P x price factor x qty factor + cash + ratio x new asset price.**

If that number differs from the pre-event price, someone gained or lost for no reason, which is a booking error.

### Splits

A 2-for-1 split gives two new shares for each old one and halves the price: quantity factor {{ex.split.expected.qty_factor:.1f}}, price factor {{ex.split.expected.price_factor:.2f}}. A reverse split goes the other way (0.1 for a 1-for-10). Swaps adjust the share count and the initial price, and the notional is unchanged. The risk is not the maths but the timing: the system must apply it on the ex-date, not a day later, and any open orders or limits denominated in shares need adjusting too.

### Rights issues

A rights issue lets holders buy new shares at a discount. The price falls to the **theoretical ex-rights price (TERP)**:

**TERP = (P + ratio x K) / (1 + ratio)**

where K is the subscription price and ratio the new shares per old share. With P = 50, K = 40 and 1 new share for every 4 held (ratio 0.25), TERP = (50 + 10) / 1.25 = **{{ex.terp.expected:.2f}}**. The price factor is 0.96 and, if the holder takes up the rights, the quantity factor is 50/48 = {{ex.rights.expected.qty_factor:.4f}} so the notional is unchanged. In the synthetic market the rights issue on a stock is built exactly this way.

### Spin-offs

In a spin-off the parent distributes shares of a subsidiary. The parent's price falls by the value of what was spun off, and holders receive new shares in a new line. With the parent at 100 and a spin-off worth 12 per parent share, delivered as 0.5 new share per parent share, the parent's price factor is **{{ex.spin.expected.price_factor:.2f}}** and each new share is worth **{{ex.spin.expected.new_asset_price:.0f}}**. A swap on the parent must now track two securities, which usually means booking a new swap on the spun-off line or adding it to the basket. Index treatment matters too: the spun-off share may join the index at once, which the synthetic index in this app does.

### Mergers

In a **cash merger** the target is acquired for a fixed price per share and the position closes: quantity factor zero, cash equal to the offer. In the synthetic market a cash takeover of one stock converges to the offer as the deal nears completion, and the index drops the stock the day after. In a **stock merger** holders receive acquirer shares at an exchange ratio plus perhaps cash. With a target at 30, an acquirer at 50, a ratio of 0.5 and 5 of cash, value per target share is 0.5 x 50 + 5 = **30**, so value is preserved only if the target traded exactly at the deal value. When it did not, the merger-arb spread is real PnL.

### Special dividends

Treated as an adjustment, a special dividend reduces the price by the amount and pays that amount as cash. Contracts differ on whether the equity leg adjusts the price, adjusts the strike, or pays the amount through the dividend leg. Always read the confirmation.

### Elections, tenders and deadlines

Some events involve a choice (take cash or shares) with a deadline. For a swap the client usually cannot make the election; the swap terms specify a default outcome. For stock hedges the desk's custodian handles the election. The TDA's job is to track the deadlines and confirm what was elected.

## Worked example

A client is long a swap on 10,000 shares with an initial price of 100.

**Step 1: split.** After a 2-for-1 split the swap becomes 20,000 shares at 50. Notional is 1,000,000 before and after.

**Step 2: rights.** A different swap on a stock at 50 faces a rights issue at K = 40, ratio 0.25. TERP is **{{ex.terp.expected:.2f}}**, price factor 0.96, quantity factor {{ex.rights.expected.qty_factor:.4f}}. The quantity multiplied by the price is unchanged.

**Step 3: spin-off.** The parent at 100 spins off 12 of value per parent share as 0.5 new share each. The parent's price factor is {{ex.spin.expected.price_factor:.2f}}. Value check: 0.88 x 100 + 0.5 x {{ex.spin.expected.new_asset_price:.0f}} = 88 + 12 = 100, so value is preserved.

**Step 4: cash merger.** A target is bought at 31.25 a share: the swap terminates, with cash {{ex.cash_merger.expected.cash_per_old_share:.2f}} per share.

**Step 5: stock merger.** Target 30, acquirer 50, ratio 0.5, cash 5: the quantity factor is {{ex.stock_merger.expected.qty_factor:.1f}}, the price factor 50/30, and the value per old share is 30. The table below recomputes each from the code.

## Desk reality

**Every morning.** The TDA reviews the corporate action calendar for the day and the next week: ex-dates, record dates, election deadlines. For each event, list the swaps, hedges and futures affected and confirm the adjustment has been applied consistently to both sides.

**Hedge mismatches.** The most expensive error is applying the adjustment to the client swap but not the hedge, or the reverse. The desk is then outright long or short the underlying until it is caught. Reconcile the swap and hedge share counts after every event.

**Contract terms vary.** Confirmations define "potential adjustment events" and who decides the adjustment (the calculation agent). Ask for the legal wording before assuming that a standard factor applies. For a rights issue, the terms may say whether rights are deemed sold or exercised.

**Communication.** Clients ask what happened to their position. Be ready with before-and-after quantity, price, notional and any cash, and be explicit about the effective date.
