## Learn

Securities lending is a fee business, but fees are very uneven. Most stocks are cheap and plentiful to borrow, called general collateral (GC). A small number are scarce, and the fee can jump to hundreds or thousands of basis points. A Delta One desk meets this from both sides: it borrows to hedge client longs and shorts, and it lends the inventory it holds. This page shows how lending revenue works, how fees behave as utilisation rises, how to rank specials, what to do about a recall and how collateral upgrades earn a fee.

### Thesis

Revenue is the lendable value multiplied by utilisation, the fee and the fraction of a year. Revenue = V x u x f x d / 360, with V in currency, u the share of lendable shares that are on loan, f the fee in basis points a year and d the number of days. With 100 million of lendable inventory, 40% utilisation, a fee of 50 basis points and 180 days, the gross revenue is {{ex.rev.expected.gross:,.0f}}. A split with the beneficial owner follows: at 85/15, the owner receives {{ex.rev.expected.lender:,.0f}} and the agent keeps {{ex.rev.expected.agent:,.0f}}.

### Legs

The beneficial owner (a pension fund, say) lends shares to the desk or agent. The borrower pays a fee, or receives a rebate if the loan is against cash. Treasury reinvests any cash collateral. For an upgrade, the desk lends high-quality securities to a counterparty and receives lower-quality collateral, charging a fee for the difference.

### The fee curve

Fees are not linear in utilisation. When few shares are on loan, supply is plentiful and the fee stays close to the GC level; as utilisation approaches 100%, borrowers compete and the fee rises sharply. The illustrative curve in the sandbox is fee = GC x (1 + steepness x u^2 / (1 - u)). With a GC of 30, steepness of 2 and utilisation of 50%, the fee is {{ex.fee.expected:.0f}} basis points, double GC. Multiplying by volume gives the revenue curve, which is steeper still. The consequence is that pricing power is concentrated in a few names at high utilisation.

### Screening for specials

The sandbox ranks the synthetic universe by annual revenue potential: lendable value times utilisation times the current fee. Names that top the list combine large lendable inventory with high utilisation and high fees. It also reveals the other side: a name with an extremely high fee and tiny inventory is a small revenue and a large risk.

### Recalls

A **recall** happens when a lender asks for shares back. The borrower must return them within the settlement period or face a **buy-in**. There are three responses: re-borrow from someone else at a higher fee, buy the shares in the market (a buy-in, with premium and market impact), or internalise by covering from inventory the desk already holds. For 100,000 shares at 50 with fees going from 1% to 5% for 30 days, re-borrowing costs about {{ex.recall.expected.reborrow:,.0f}}, a buy-in with a 2% premium and 1% impact costs {{ex.recall.expected.buy_in:,.0f}} and internalising at 0.5% a year costs {{ex.recall.expected.internalise:,.0f}}. The cheapest is internalisation, but only if the inventory exists. The sandbox's risk button ranks the options.

### Collateral upgrades

A collateral upgrade lends high-quality collateral, such as government bonds, and takes lower-quality collateral, such as equities, in return, for a fee. Twenty million for 90 days at 12 basis points earns {{ex.up.expected:,.0f}}. Risks include the haircut on the lower-quality collateral, its price volatility and wrong-way risk if it correlates with the borrower's credit.

### Inputs

Inventory by stock and its source, utilisation, fee and rebate rates, recall history, collateral eligibility and haircuts, split with beneficial owners, reinvestment policy and settlement calendars.

### Risks and failure modes

**Recall.** Compare the three responses and act before the settlement deadline.

**Squeeze.** Utilisation approaches 100% and the fee spikes, but so does the chance of recalls, buy-ins and reputational damage. The sandbox shows the revenue gain at 97% utilisation and flags that it is not free.

**Reinvestment loss.** Cash collateral reinvested in anything other than very short, safe assets can lose more than a year of fees.

**Concentration.** Revenue in a handful of names makes the desk dependent on them.

**Regulatory.** Short-selling rules and disclosure requirements apply in many markets.

### What the simulation omits

Flat fees over the period, no recall risk netted from revenue, and a stylised fee curve rather than market data. The Case Studies module covers a squeeze.

### Rebates, cash and non-cash collateral

When a loan is against cash collateral, the borrower does not pay a fee directly: the lender reinvests the cash and pays the borrower a **rebate**, which is the reinvestment rate minus the fee. A low or negative rebate means a high fee. When the collateral is non-cash, such as bonds or other equities, the borrower pays the fee explicitly. A desk that compares two borrows should convert both to the same measure, the fee in basis points a year, before choosing. Collateral is marked daily against the loan, and margin of 102% to 105% is typical, higher for cross-border loans; the desk's illustrative values are in the configuration, labelled as such.

### Using the screen in practice

Start with the top of the specials list and ask three questions of each name. Is the fee stable or spiking? Is lendable inventory shrinking, which signals a coming squeeze? Do we have client shorts hedged here, so that a fee rise is a cost to us before it is a revenue? Then compare with the long inventory the desk holds for clients: a name that is both lendable and expensive to borrow is the place where internalisation pays most, covered in the Internalisation module.
## Worked example

Price a lending book.

**Step 1: revenue.** 100 million of inventory, 40% utilisation, 50 basis points, 180 days: {{ex.rev.expected.gross:,.0f}} gross.

**Step 2: split.** {{ex.rev.expected.lender:,.0f}} to the owner, {{ex.rev.expected.agent:,.0f}} to the desk.

**Step 3: curve.** At 50% utilisation and GC of 30, the fee is {{ex.fee.expected:.0f}} basis points.

**Step 4: recall.** The cheapest of three responses is internalisation at {{ex.recall.expected.internalise:,.0f}}; a buy-in is {{ex.recall.expected.buy_in:,.0f}}.

**Step 5: upgrade.** A 12 basis point fee on 20 million over 90 days: {{ex.up.expected:,.0f}}.

**Step 6: report.** List the revenue by tier, the number of recalls and the cost of each response.

## Desk reality

**Who does it.** The securities lending desk, often separate from the swap desk. The swap desk borrows from it for hedges, and internal transfer prices apply.

**Information.** Borrow availability and fees are commercially sensitive; share them only through proper channels.

**Controls.** Daily marks on loans and collateral, recall monitoring, limits on single-name concentration and on cash reinvestment.

**Escalation.** A name going special while the desk is short for clients needs a call to the trader and the client before it hits the P&L.
