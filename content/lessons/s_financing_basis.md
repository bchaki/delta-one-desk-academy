## Learn

Most of what a Delta One desk earns is not a view on markets but a **financing spread**: the difference between what clients pay to hold exposure and what it costs the bank to carry the hedge. This page treats that spread as a trade. The questions it answers: how much does a financed swap earn, which hedge instrument is cheapest, and how quickly does the carry disappear when funding gets more expensive.

### Thesis

A client pays the benchmark plus a spread on a swap. The desk buys the stock as a hedge and funds it. It pays treasury the benchmark plus the **funds transfer price (FTP)** spread, and it pays a charge for the balance sheet the hedge occupies. The benchmark cancels, so **carry = notional x (client spread minus FTP minus balance sheet charge) x days / 360**. On a 50 million swap at 60 basis points over benchmark, with FTP of 35 and a balance sheet charge of 10, the desk keeps 15 basis points: {{ex.carry.expected:,.0f}} a year.

### Legs

The client pays benchmark plus spread. Treasury lends the cash to buy the hedge, charging benchmark plus FTP. The cash market sells the desk the stock. Alternatively the exchange provides a futures hedge, which has no direct balance sheet cost but needs initial margin and has the financing embedded in its price. All rates here are quoted as bps a year on ACT/360 for dollar and euro benchmarks.

### Choosing the hedge

The futures hedge costs the **implied financing spread** in the future's price, plus the funding of its initial margin: **net = client spread minus implied spread minus margin share x FTP**. With a client spread of 60, an implied spread of 20, a margin of 5% of notional and an FTP of 35, the net is {{ex.fut.expected:.2f}} basis points, against {{ex.choice.expected.stock:.0f}} for the stock hedge. The futures hedge is cheaper here because it avoids the 10 basis point balance sheet charge and because the implied spread sits well below the FTP. The decision changes if the implied spread rises: at an implied spread of 50 the stock hedge wins. A desk that watches the implied financing in the futures each day can switch hedge as the numbers move.

### Sensitivity to funding costs

Carry is a small number minus a bigger number, so it is highly sensitive. If the FTP spread rises from 35 to 50 with the other inputs unchanged, the annual PnL goes to {{ex.breakeven.expected:,.0f}}. A rise of 25 basis points held for half a year on 10 million costs {{ex.shock.expected:,.0f}}. The sensitivity chart plots annual PnL against the FTP spread: it is a straight line, with the break-even FTP at the client spread minus the balance sheet charge.

### The implied financing series

The sandbox computes the financing implied by the front future in the synthetic world: the funding spread assumed in fair value plus the deviation, in basis points of spot, divided by the years to expiry. It averages around the assumed funding spread with spikes when the deviation moves. Those spikes are the same events that create index arbitrage opportunities, seen from the financing side.

### Balance sheet optimisation

The balance sheet charge is not fixed. The levers are netting offsetting client trades so there is less hedge stock to hold, internalising borrow, collateral from clients that reduces exposure and choosing futures for index exposure. A desk that earns 15 basis points on a stock hedge and 38 on a futures hedge has a clear instruction: use futures wherever it is allowed.

### Risks and failure modes

**Funding spread increase.** Treasury reprices FTP; the carry falls one for one.

**Balance sheet charge increase.** Quarter-end constraints or a rule change raise the charge.

**Margin doubles.** A volatility spike raises initial margin on futures, increasing funding cost.

**Basis risk between swap and hedge.** The client's swap references the index total return, and the hedge is a future with its own dividend assumption.

**Client behaviour.** A client who unwinds early leaves the desk with hedge costs and a lost spread.

### What the simulation omits

Rates are flat over the period and balance sheet is a single charge. Margin funding timing, tax, multi-currency funding and the term structure of FTP are not modelled.

### Reading the numbers like a trader

Carry is a thin margin on a large balance. A 50 million swap earning 15 basis points a year is 75,000, which is about 0.15% of the notional, and the same trade can lose that in a week if the hedge moves while a client's resets lag. That is why desks quote in basis points and look at the spread between client price and all-in cost, not at the dollar PnL alone. Three habits help. First, always write the spread build-up in the same order: client spread, then FTP, then balance sheet, then margin, then any dividend or borrow cost. Second, change one input at a time and note which one moves the answer most; for most swaps it is the FTP. Third, compare the number to the capital the trade uses, because a trade earning 15 basis points on a lot of capital may earn less than its cost of equity.

### Client conversations

Clients ask why the spread is what it is. A good answer separates what the client controls from what it does not. The client controls size, tenor, collateral and whether the underlying is easy to hedge. It does not control the bank's funding. A client whose swap can be hedged with futures, whose collateral reduces exposure and whose trade offsets other clients' trades will get a tighter spread, and the arithmetic on this page is how you show it. A client that wants a hard-to-borrow short will pay the borrow fee on top, and the financing page of the swap's confirmation shows it separately.

### Summary of the levers

Raise the client spread, lower FTP by moving funding to a cheaper source, reduce the balance sheet charge by netting, or switch to futures. Each lever has a limit and a cost: a higher spread loses flow, cheaper funding needs treasury's agreement, netting depends on client mix and futures need margin and index eligibility.
## Worked example

Pick the best hedge for a 50 million swap at 60 basis points over benchmark.

**Step 1: stock hedge carry.** 60 minus 35 minus 10 gives 15 basis points: {{ex.carry.expected:,.0f}} a year.

**Step 2: futures hedge.** Implied financing in the future is 20 basis points over benchmark, initial margin is 5% of notional. Net {{ex.fut.expected:.2f}} basis points.

**Step 3: compare.** {{ex.choice.expected.futures:.2f}} against {{ex.choice.expected.stock:.0f}}: futures win by about 23 basis points.

**Step 4: stress.** If FTP rises to 50, the stock hedge earns {{ex.breakeven.expected:,.0f}}.

**Step 5: decide.** Hedge with futures if the swap references an index future-eligible basket, and review the hedge choice weekly.

## Desk reality

**Treasury is a counterparty.** FTP is a price set by treasury; know when it is reviewed and how it moves with the bank's funding.

**Quarter ends.** Balance sheet is most expensive at reporting dates. Plan large hedges accordingly.

**Client pricing.** If the carry is thin, the spread you quote is what pays for the desk. Know your cost before quoting.

**Documentation.** The financing spread is in the confirmation; check it matches the booking.
