## Learn

A flow desk makes money from clients trading with it. The product is liquidity: a price at which the client can trade now, in size, without moving the market. This page shows how that turns into PnL, why internalisation matters, what inventory costs and how to think about taking risk versus acting as agent.

### Thesis

Each client trade earns the desk a spread over mid. Some trades offset each other, so the desk never has to hedge them; that is **internalisation**. The rest builds up as **inventory** which carries price risk until it is hedged. The desk sets a limit; when inventory breaches it, the excess is hedged at a cost. So **PnL = spread on gross flow, minus hedging costs, plus inventory price PnL**.

### Legs

Clients on one side, buying and selling. The market on the other, used for hedging only what exceeds the limit. Often a third leg: **axes**, the desk's list of positions it would like to trade, shown to clients to attract the opposite flow.

### Agency against risk

In **agency** the desk charges a commission and passes the trade to the market: no inventory, no risk. 10 million at 5 basis points earns {{ex.agency.expected:,.0f}}. In a **risk trade** the desk takes the client's position into inventory at a spread. With a spread of 8 basis points and a hedge cost of 3 on 10 million, the expected gain is {{ex.risk.expected.expected:,.0f}}. The cost is variance: if the stock has daily volatility of 1.5% and the desk needs four days to unwind, the one-sigma risk is {{ex.risk.expected.one_sigma_risk:,.0f}}, sixty times the expected gain. A single risk trade is a bet. A thousand of them, with balanced flow, is a business. Which of the two it resembles depends on how well the desk nets flow.

### The simulation

The sandbox simulates 250 days of client trades in one name. Each day several trades arrive with normal sizes; each is a buy or sell with a probability you control. The desk earns the spread on gross notional, inventory moves opposite to net flow, inventory earns the price move, and anything above the limit is hedged at the hedging cost. It reports total PnL, the share of notional internalised, the worst day and peak inventory, with charts of cumulative PnL and inventory through time. Change the **imbalance** slider and see what one-way flow does: internalisation falls, hedging costs rise and PnL becomes more volatile.

### Axes and inventory management

Showing axes tells clients what you want to trade. If the desk is short a stock because of client flow, it advertises an axe to buy, offering a better price to clients who sell. That moves the inventory back towards flat at a lower cost than the market. The best use of axes is where the desk is already exposed, because the client does a favour in return for a better price. A desk that shows false axes damages trust and in some jurisdictions can raise compliance concerns.

### Limits and the risk of ignoring them

Inventory limits convert flow risk into hedging cost, on purpose. The risk button that switches the limit off shows peak inventory growing by many times; PnL on a good day looks better and on a bad day the loss has no floor.

### Inputs

Client flow history by name and tier, bid/offer and commission schedules, the hedge cost model, inventory and risk limits, volatility estimates and the desk's cost of capital.

### Risks and failure modes

**One-way flow.** All clients on the same side: the desk hedges nearly everything.

**Volatility doubles.** Inventory swings are twice as large.

**Limit ignored.** Risk without a floor.

**Adverse selection.** Informed clients trade just before a move, so the desk is repeatedly on the wrong side. The simulation does not include it, and real desks monitor the price move after each client's trades.

**Concentration.** A single client or name dominating flow.

### What the simulation omits

One name, normal sizes, no adverse selection, no market impact on the hedge and constant spread. A real desk varies the spread by client, size and conditions.

### Reading the daily flow report

A flow report has five numbers worth reading in order: gross client notional, net client flow, the inventory at close, the amount hedged and PnL split into spread, hedge cost and price. If gross is large and net small, the day was internalised and PnL came from spread. If net is large, inventory moved and the hedge cost and price PnL mattered. Compare each number with its own history and with the same number last week. A change in internalisation is usually a change in client mix; a change in spread is a change in competition or in your quoting; a change in price PnL is luck or skill, and you cannot tell which from one day.

### Principles to carry away

Quote to the flow you want, not the flow you get. Net before you hedge. Keep inventory limits tight enough to bind occasionally; a limit that never binds is not a limit. Watch for adverse selection: if a client's trades are regularly followed by moves against you, widen their spread or decline the trade. And keep the record clean: every axe, quote and fill timestamped so that compliance can see what you did and why.
## Worked example

Evaluate a client flow business.

**Step 1: agency.** 10 million at 5 basis points: {{ex.agency.expected:,.0f}}.

**Step 2: risk trade.** Spread 8, hedge cost 3: expected {{ex.risk.expected.expected:,.0f}}.

**Step 3: risk.** One-sigma risk for four days at 1.5% daily is {{ex.risk.expected.one_sigma_risk:,.0f}}; ratio {{ex.risk.expected.ratio:.3f}}.

**Step 4: simulate.** Run 250 days with balanced flow and look at internalisation and total PnL.

**Step 5: stress.** Set a one-way flow and a doubled volatility. Compare hedging cost and worst day.

**Step 6: decide.** Set the inventory limit so that the worst day is within the desk's loss tolerance.

## Desk reality

**Who does it.** Sales traders and flow traders, supported by the desk's quants and the TDA.

**Client tiers.** Revenue comes from a few clients; tier 1 clients get the best spreads and the most attention. Know the revenue per client.

**Surveillance.** Compliance monitors trading ahead of client orders and misuse of client information. Keep clean records of axes and quotes.

**Reports.** The daily flow report: volumes, internalisation, inventory, hedging cost and PnL by client tier.
