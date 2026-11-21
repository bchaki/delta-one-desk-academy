## Learn

Equity indices are the underlying of the desk's index futures, index swaps and ETF hedges. To price and risk those products you need to understand how an index level is built from its constituents, how weights and caps work, and what happens to the divisor when the membership changes.

### Index level and divisor

A price-weighted-by-market-cap index defines an **adjusted total market value**: for each constituent, price x shares outstanding x free-float fraction x capping factor, summed. The index level is that sum divided by a number called the **divisor**:

**level = sum(P_i x shares_i x free float_i x cap factor_i) / divisor**

Take three stocks priced 100, 50 and 20 with 1,000, 2,000 and 5,000 shares, free floats of 100%, 50% and 100%, and no capping. The value is 100,000 + 50,000 + 100,000 = 250,000. With a divisor of 100 the level is **{{ex.level.expected:,.0f}}**. The divisor is not a constant of nature; it is the bookkeeping number that lets the level stay continuous when the basket changes.

### Free float and capping

**Free float** counts only shares available to investors: a stock with half its shares held by the founder has a free float of 50% and counts half as much. **Capping** limits any single name's weight, for example to 10% or 25%, so that one giant does not dominate. Capped weights are found by clipping the excess and redistributing it pro rata to the uncapped names, repeating until no name exceeds the cap. With weights 50%, 30% and 20% and a 40% cap, the first name is held at 40% and the others scale to 36% and 24%. The **capping factor** is what you multiply the share count by to produce that weight. In the synthetic indices a 25% cap is applied at each quarterly rebalance.

### Divisor adjustments

When a stock joins, leaves or is capped differently, the total market value jumps but the level must not. The divisor absorbs the jump:

**D' = D x (value after change) / (value before change)**

with both values at the same prices. If the value goes from 250,000 to 300,000 at a divisor of 100, the new divisor is **{{ex.divisor.expected:.0f}}** and the level stays at 2,500. A property to remember: if the level moves on the day of a reconstitution because of the divisor, something is wrong. A TDA checking index levels after an event compares the published level against the level recomputed with the old and the new divisor.

### Weighting schemes

Market-cap weights follow value, equal weights treat every stock alike and need rebalancing as prices drift, and price weights (like the Dow) give high-priced stocks the most influence. Futures and ETFs on a given index follow its rules, so you must know which one you are hedging with.

### Rebalances and inclusion demand

Indices rebalance on a schedule, often quarterly. When a stock enters, funds tracking the index must buy it, and the amount is predictable: **shares = tracked assets x new weight / price**. With 200 billion tracked, a weight of 0.2% and a price of 50, funds need to buy **{{ex.inclusion.expected.shares:,.0f}} shares**, which is {{ex.inclusion.expected.days_of_adv:.1f}} days of average daily volume if ADV is 4 million. The expected price impact from the square-root model is about {{ex.inclusion.expected.impact_bps:.0f}} bps with the parameters used. That predictable flow is why rebalance days have huge closing-auction volumes, and why strategies around index events exist.

### Price and total return

A **price index** ignores dividends. A **total return index** reinvests them: TR' = TR x (P' + D) / P, with D the dividend points going ex over the step. Net total return indices deduct withholding. The difference between the two is the dividend stream. Futures on the price index subtract dividends in fair value; total return futures and swaps on the total return index do not.

### Index calculation in practice

Real indices have intricate rules: staggered effective dates, buffer zones, announcement dates, provisional constituent lists, and treatment of corporate actions. The synthetic indices here simplify these: quarterly rebalances on the third Friday, a fixed cap, mergers deleting a name the next day. Treat the simplification as a model, and read the real methodology document for any real index.

## Worked example

Three constituents, prices 100, 50, 20, shares 1,000, 2,000, 5,000, free float 100%, 50%, 100%.

**Step 1: value and level.** Value = 100 x 1,000 + 50 x 2,000 x 0.5 + 20 x 5,000 = 100,000 + 50,000 + 100,000 = 250,000. At a divisor of 100 the level is {{ex.level.expected:,.0f}}.

**Step 2: a change in membership.** A new constituent lifts value to 300,000 at the same prices. The divisor must become 100 x 300,000 / 250,000 = {{ex.divisor.expected:.0f}}, leaving the level at 2,500.

**Step 3: capping.** Weights 50%, 30%, 20% with a 40% cap become 40%, 36%, 24%. The first stock's capping factor is below 1 relative to the others.

**Step 4: inclusion demand.** A new addition with a 0.2% weight in a 200 billion tracked pool needs {{ex.inclusion.expected.shares:,.0f}} shares to be bought, {{ex.inclusion.expected.days_of_adv:.1f}} days of ADV at 4 million shares a day.

**Step 5: total return.** A price index moves from 1,000 to 1,010 with 4 dividend points going ex. The total return index multiplies by (1,010 + 4) / 1,000 = 1.014.

## Desk reality

**Index events calendar.** The TDA tracks announcement and effective dates for rebalances, constituent changes, and index methodology changes for every index the desk trades. After an event, the swaps and ETF baskets referencing the index must be updated, and the hedges re-sized.

**Level breaks.** When the published level and the computed level differ after an event, the usual causes are a stale divisor, a missing constituent, an incorrect free-float or capping factor, or a corporate action not applied. Check in that order.

**Rebalance day liquidity.** Closing auctions on rebalance days are enormous. The desk's index arbitrage and ETF teams position around them, and TDAs watch for operational issues such as late constituent files and hedge fills in the auction.

**Know the methodology.** Free float, capping and treatment of dividends vary by index provider. A client asking why two similar-looking indices diverge is usually asking about one of those three things.
