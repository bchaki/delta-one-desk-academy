## Learn

Index funds track an index, so when the index changes they must trade. Additions require buying, deletions require selling, and weight changes require a mix. The amounts are large, the date is known and the price pressure is predictable in direction, which makes index events one of the most studied trades in equity markets. This page covers forecasting changes, pre-positioning, facilitating the funds at the close and the risk of a crowded trade, and ends with a compliance note.

### Thesis

On the effective date, funds tracking the index buy new members at the close. If the stock is expected to be added, buyers who step in earlier hope to sell to the funds at a higher price. A dealer can instead **facilitate** the funds: guarantee them the closing price and take the other side, then manage the hedge through the day. The first is a view with price risk; the second is a service with a fee and hedging risk.

### Legs

Pre-positioning is a single outright position, bought before the announcement or the effective date and sold at or after the close. Facilitation has two legs: a **market-on-close (MOC) guarantee** with the fund and a hedge in the market during the day. A swap desk may also be asked to take the other side of a fund's trade through a swap.

### Demand and impact

Inclusion demand equals the assets tracking the index multiplied by the new member's weight, divided by the share price. With 50 billion tracking an index and a weight of 1.5%, the notional demand is {{ex.demand.expected.notional:,.0f}}. At a price of 50 that is {{ex.demand.expected.shares:,.0f}} shares, or {{ex.demand.expected.days_of_adv:.0f}} days of average daily volume if the stock trades a million shares a day. The expected price impact, using a square-root model with coefficient 0.7 and daily volatility of 2%, is {{ex.demand.expected.impact_bps:.0f}} basis points. The numbers are deliberately large to show the principle: a stock with thin volume and a heavy index weight is a major event.

### PnL drivers

Pre-positioning earns the move before the effective date less impact and costs. Buying 5 million ahead of a 40 basis point rise, with 10 basis points of impact and 2 of costs, earns {{ex.pre.expected:,.0f}}. Facilitation earns the fee less the hedge slippage versus the close: 1 million shares at 50, with a fee of 6 basis points and slippage of 2, earns {{ex.moc.expected:,.0f}}. The fee is certain, and the slippage is a risk: if the desk hedges badly it can turn negative.

### The crowded trade

If many participants pre-position the same way, the exit is crowded. Impact on selling is then a multiple of the normal square-root impact. With a crowding multiplier of three on 100,000 shares in a stock trading a million a day, volatility 2% and coefficient 1.0, exit impact is {{ex.crowd.expected:.0f}} basis points. A trade that looked profitable at normal impact loses money at crowded impact. The sandbox lets you raise the multiplier and watch the PnL decomposition change.

### Event study on the synthetic membership

The sandbox lists every addition and deletion in the synthetic index history, with the move from several days before the effective date to the date, and the move over the following days. In real markets prices often rise into an addition and partly reverse afterwards; in the synthetic world no such effect is built in, so the numbers show the method, not an expected profit. If the average pre-event move is near zero, that is the correct finding.

### Inputs

Index methodology and review dates, constituents and weights, tracking AUM, the stock's ADV and volatility, borrow cost for deletions, and the announcement calendar.

### Risks and failure modes

**Crowded exit.** Many hold the same pre-position.

**No move.** The gain you expected does not appear; costs are certain.

**Wrong forecast.** The stock is not added, or is added with a different weight.

**Hedge slippage.** The facilitation hedge is worse than the close.

**Borrow on deletions.** Shorting a deleted stock may be expensive.

### Compliance note

Pre-positioning on **public** information and public methodology is legitimate. Using **confidential** information, such as a client's index-tracking order or a desk's facilitation book, to trade ahead of the client or of the market is **front-running** or misuse of inside information. Desks run information barriers and surveillance for exactly this reason. The rule of thumb is simple: if you know something because of a client's confidence, you may not trade on it for your own benefit. The Limits, Controls and Conduct module covers the case in detail.

### What the simulation omits

No market-impact feedback into synthetic prices, no announcement dates, no cross-impact between stocks and no option for the desk to cross with other client flow.

## Worked example

A stock is expected to join an index.

**Step 1: demand.** 50 billion tracks the index, weight 1.5%: {{ex.demand.expected.notional:,.0f}} of buying, {{ex.demand.expected.days_of_adv:.0f}} days of ADV.

**Step 2: pre-position.** Buy 5 million before the announcement. A 40 basis point rise with 10 of impact and 2 of costs earns {{ex.pre.expected:,.0f}}.

**Step 3: check the exit.** At three times crowding the exit impact is {{ex.crowd.expected:.0f}} basis points on a smaller position, which can erase the gain.

**Step 4: alternative.** Guarantee the close for 1 million shares: {{ex.moc.expected:,.0f}} after hedge slippage.

**Step 5: control.** Confirm the trade is based on public information only and record the rationale.

## Desk reality

**Who does it.** Program trading and equity-linked teams. A swap desk is asked to price index-linked trades.

**Information barriers.** Know who can see client index orders. Never discuss them outside permitted channels.

**Capital.** Facilitation of a large order consumes risk capital for a day, and the loss tail is the whole market day.

**Calendar.** Index review dates are public. Keep a calendar and flag stocks near the cut-off.
