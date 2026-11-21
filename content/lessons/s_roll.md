## Learn

Anyone who holds index exposure through futures has to roll it. As the near contract approaches expiry, the position is sold and the next contract is bought. The price of that move, and whether it is fair, is the subject of this page. For a Delta One desk the roll matters twice: as a cost to clients who hold futures-based exposure, and as a trade in its own right when the spread between the two contracts is rich or cheap against its fair carry.

### Thesis

The spread between two expiries of the same index future should equal the carry between those dates: the financing cost of holding the basket minus the dividends it pays. A long position that rolls pays the spread; that is the **roll cost**. If the market spread is wider than fair carry, rolling is expensive and the **calendar spread** (sell the far, buy the near) is rich; if narrower, the roll is cheap. The trade is to sell the roll when it is rich and buy it when it is cheap, with the near and far legs largely offsetting each other so that the outright index exposure is small.

### Legs

A calendar spread has two legs on the same exchange. A **long roll** sells the near contract and buys the far one. The financing and dividend assumptions sit outside the trade as the model for fair spread. Because both legs are on the same index, the spread has far less market risk than an outright position, and exchanges give a margin credit for it (see the Margin module).

### PnL drivers

The roll cost in points is far minus near. With the near contract at 5,000 and the far at 5,030, the cost is {{ex.cost.expected:.0f}} points. A long of ten contracts on a multiplier of 50 pays {{ex.pnl.expected:,.0f}} (shown as a negative PnL). To compare rolls across tenors the cost is annualised: dividing the spread by the near price and by the time between expiries, in years, gives {{ex.bps.expected:.0f}} basis points a year for a three-month gap. Rolls four times a year do not multiply that: the annualised figure is already a rate. The cost per roll is the annualised cost divided by the rolls per year, {{ex.drag.expected:.0f}} basis points.

The part of the cost that is a fair carry is not a mispricing. **Richness** is the spread minus the fair spread. If the fair spread is 25 points against a market spread of 30, the richness is 5 points, or {{ex.rich.expected:.0f}} basis points a year. Fair spread itself is computed from the carry model; with spot 5,000, a 5% rate, no dividends and expiries a quarter and a half year away, it is {{ex.fair_sp.expected:.2f}} points. The model matters: add dividends between the expiries and the fair spread shrinks.

### Inputs

You need both contract prices at the same time, spot, the financing rate and a dividend forecast for the period between the two expiries. In the sandbox the roll events are taken from the synthetic world at a chosen number of trading days before each near expiry, with the funding spread as a parameter.

### Simulation

The sandbox lists every roll in the synthetic history with spread, fair spread, richness and the annualised figures. It plots gross roll cost and richness through time and decomposes the PnL of a long position that rolls each quarter into the gross cost, the fair carry and the richness. The decomposition shows the key idea: most of the roll cost is not a loss in the economic sense, because holding futures instead of stock saved the financing on the basket. Only the richness is the trade.

### Roll week

In the real market, roll week is when open interest migrates from near to far. Spreads can move sharply as large holders roll together; liquidity thins in the near contract; and benchmark providers and index funds roll on published dates. The synthetic world does not model open interest, and the page says so. What it does model is the principle: by rolling earlier or later you pick a different spread, and the sandbox slider lets you see how richness changes with the day you choose.

### Risks and failure modes

**Rolling on the last day.** You have no time to wait for a better price and you roll with everyone else.

**Spread dislocation.** A calendar spread can move against you, especially when a dividend forecast changes or funding costs spike. The risk button shows the size of the largest spread in the history and what it means for a position.

**Carry model wrong.** Richness is only as good as the fair spread. If the funding input is 25 basis points off, the average richness changes sign for some indices. Treat any signal that disappears when you change the funding input by a small amount with suspicion.

**Basis between instruments.** If the client holds a swap and the desk hedges with futures, the roll cost lands on the desk until the swap's spread is repriced.

### What the simulation omits

One flat rate per roll date, no open-interest data, no roll-week liquidity effects and no execution costs on the spread itself. The full version would add an intraday spread series and the cost of crossing the spread in each leg.

## Worked example

A client is long 100,000 index units through futures and asks what the roll will cost.

**Step 1: contracts.** The near contract is 5,000, the far 5,030, a quarter of a year apart.

**Step 2: cost in points.** The roll costs {{ex.cost.expected:.0f}} points.

**Step 3: cost in money.** Ten contracts of multiplier 50 pay {{ex.pnl.expected:,.0f}} in the roll. Scale to the client's size.

**Step 4: annualise.** {{ex.bps.expected:.0f}} basis points a year, or {{ex.drag.expected:.0f}} basis points for this roll.

**Step 5: fair or rich?** The fair spread from the carry model is 25 points, so the roll is rich by 5 points, or {{ex.rich.expected:.0f}} basis points a year.

**Step 6: action.** The client pays the market. The desk can offer to roll the position through a swap at a price near fair carry and take the richness as a profit, or tell the client to wait if the richness is likely to fall.

## Desk reality

**Who does it.** The futures trader on the desk, with the swap trader who wants the client's roll priced consistently.

**Calendar discipline.** Know the exchange's expiry dates and the benchmark's roll dates. A missed roll is an unwanted delivery or an expiring position.

**Margin.** A calendar spread earns a margin credit; an outright position does not. Check the credit before assuming the spread is cheap to carry.

**Communication.** Clients ask why their futures-based exposure underperformed the index. The roll cost and the dividends not received are part of the answer.
