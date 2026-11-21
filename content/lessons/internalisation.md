## Learn

Internalisation means covering a client's short position from stock the desk already has, rather than borrowing it in the street. The stock may come from other clients' long positions that the desk is allowed to reuse, or from the desk's own inventory. Done well, it is one of the most profitable and least visible levers on a Delta One desk. Done carelessly, it creates recall risk, regulatory breaches and client complaints.

### The idea

A hedge fund is short a stock through a swap. The desk must borrow stock to hedge. Meanwhile, other clients hold the same stock long in their financing accounts, and the desk has the right to reuse some of it. Instead of paying the street borrow fee of, say, 300 bps, the desk uses the clients' long stock at an internal cost of, say, 50 bps. The difference is a saving, and desks usually share some of it with clients as a lower borrow price, which also wins flow.

### The arithmetic

**Short demand** is the client shares short. **Internal supply** is rehypothecable client longs plus desk inventory. **Internal cover = minimum of demand and supply**. The remainder is borrowed in the street. The saving is **cover x price x (street fee - internal cost) x days / basis**. For a name with 200,000 shares of short demand, 150,000 shares of client longs of which half can be reused, and 20,000 shares of desk inventory, supply is {{ex.name.expected.internal_supply:,.0f}} and cover is {{ex.name.expected.internal_cover:,.0f}}. The street still needs {{ex.name.expected.street_borrow:,.0f}} shares. At a price of 50, a street fee of 300 bps, internal cost of 50 bps and 30 days, the saving is {{ex.name.expected.savings:,.2f}} over the period.

### Rehypothecation limits

The desk can only reuse a share of client longs. The limits come from the client's agreement and the regulation: in some markets only a fraction of the client's debit balance can be rehypothecated, and elsewhere clients must give written consent. The model has a single **rehypothecation fraction** to represent this. The lower it is, the less supply is available, and the more is borrowed from the street.

### Coverage

**Coverage ratio** is the notional covered internally divided by the notional of short demand. Across a book of names it measures how well the desk's inventory matches its shorts. High coverage in names that are expensive to borrow is the most valuable, since the saving is proportional to the street fee.

### Which names matter

Savings concentrate in special and hard-to-borrow names, where the street fee is high. In GC names the saving per share is tiny. The best way to read an internalisation report is to rank names by saving in currency, not by coverage ratio, and check that the largest savings are not also the largest recall risks.

### The risks

**Recall risk**: the client whose long stock is being reused can sell it, which pulls the supply and may force a street borrow at a high fee. **Concentration**: reliance on one client's inventory. **Conflicts**: the desk is using client assets, so disclosures and consents matter. **Reporting**: some regulators require reporting of rehypothecation and limit it. **Operational**: tracking which client's long covers which short is a daily reconciliation task.

### Pricing it into the spread

The desk can reflect the expected saving in the quoted spread for a short: lower borrow component, tighter price, more flow. A conservative desk shares only part of the saving so that a single recall does not turn the trade negative. The spread build-up in the swaps module shows where borrow sits among the components.

### Allocation: which short gets which long

When supply is short of demand, the desk has to decide who is covered internally and who goes to the street. Common rules are **pro rata** (every short gets the same fraction), **first come first served**, and **by value** (cover the shorts where the street fee is highest first). Pro rata is simple and fair to clients, while by-value maximises the saving. Whatever the rule, it must be documented, applied consistently and auditable, since two clients with identical shorts getting different borrow prices will ask why.

### Interaction with swaps and financing

A client's short swap creates a hedge need, but a client's long swap creates a hedge the desk may hold in stock. The desk's hedge for a long swap is a long stock position that can itself be lent out, which means internalisation links the swap book and the SBL book: longs feed shorts. This is why the swap, financing and SBL teams on a Delta One desk meet daily, and why the internalisation figure belongs in the swap spread build-up.

### Measuring success

Useful measures include the coverage ratio, the saving in currency and in bps of short notional (annualised), the street borrow remaining, the share of savings coming from special names, and the number of recalls triggered. A desk that increases coverage but also increases recalls should look at the quality of the supply it is using.

## Worked example

Take one name.

**Step 1: demand.** Clients are short 200,000 shares at a price of 50.

**Step 2: supply.** Client longs 150,000, of which 50% can be reused (75,000). Desk inventory is 20,000. Supply is {{ex.name.expected.internal_supply:,.0f}}.

**Step 3: cover.** Min(200,000, 95,000) = {{ex.name.expected.internal_cover:,.0f}}.

**Step 4: street.** 200,000 - 95,000 = {{ex.name.expected.street_borrow:,.0f}} shares to borrow externally.

**Step 5: saving.** 95,000 x 50 x (300 - 50) bps x 30/360 = {{ex.name.expected.savings:,.2f}}.

**Step 6: annualised.** Measured on the whole short notional, the saving is {{ex.name_bps.expected.savings_bps:.1f}} bps a year of short notional.

**Step 7: sensitivity.** Halve the rehypothecation fraction and supply falls to 57,500, cover falls with it and the street borrow rises. The page lets you move this slider.

## Desk reality

**The reuse limit is a hard line.** A desk that exceeds the permitted rehypothecation has a regulatory problem, not a PnL problem. The limit check must run before the allocation.

**Rank by money, then by risk.** The biggest saving may come from a name where one client holds most of the long stock. Check concentration before celebrating.

**Know who is exposed to what.** When a client sells a long, the desk may suddenly have to borrow in the street for someone else's short. The TDA is the one who spots it first, from the position reconciliation.

**Share the saving carefully.** Giving too much to the client makes the trade unprofitable the first time a recall hits.
