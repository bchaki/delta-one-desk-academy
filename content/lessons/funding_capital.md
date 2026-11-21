## Learn

A swap looks like a spread over a benchmark. Behind that spread sits a bank's balance sheet, capital and funding. Every trade uses some of each, and each has a cost. A desk that quotes without the costs wins flow and loses money. This module shows where the costs come from and how to put numbers on them, using a simplified, standardised teaching approach that is not a regulatory calculation.

### Funds transfer pricing

The desk does not fund itself: treasury charges it an internal rate. **FTP** is that rate: the benchmark plus a spread that depends on currency and tenor, held in `config/desk.yaml` as 35 bps for USD, 30 for EUR and so on. A long position funded at FTP costs the benchmark plus the spread. If rates or spreads rise, so does the cost. The FTP sensitivity from the risk module is the desk's exposure to that change.

### Exposure at default

For a derivative, the amount at risk with the counterparty is the **exposure at default (EAD)**. The simplified SA-CCR version is **EAD = alpha x (replacement cost + add-on)**, with **replacement cost = max(MTM - collateral, 0)** and the **add-on = supervisory factor x notional**. With alpha 1.4, a 1 million MTM, no collateral, a 50 million notional and a 0.32 supervisory factor, EAD is {{ex.ead.expected:,.0f}}. Most of it comes from the add-on, the allowance for future moves. Collateral reduces replacement cost but not the add-on.

### The balance sheet: leverage exposure

A swap with a physical hedge puts more on the balance sheet than the swap itself: the **leverage exposure** is the derivative EAD plus the hedge stock held: {{ex.leverage.expected:,.0f}} for our example, against a 50 million notional. A margin loan sits on the balance sheet at its funded amount. Leverage exposure drives the **leverage ratio** that regulators and the bank's own target set, here 4% of exposure.

### Risk-weighted assets and capital

**RWA = EAD x risk weight.** Risk weights depend on the counterparty: the illustrative table has 1.0 for a hedge fund, 0.5 for an asset manager, 0.2 for a pension fund or insurer and 0 for an internal desk. Hedge stock inventory carries a risk weight too; the teaching default is 1.0, and a lower figure is reasonable for hedged inventory, so the example uses 0.25. For a pension counterparty and the hedge, RWA is {{ex.rwa.expected:,.0f}}. **Capital held = max(leverage ratio x leverage exposure, CET1 ratio x RWA)**, whichever constraint binds. Here the leverage constraint gives {{ex.capital.expected:,.0f}} against {{ex.rwa_capital.expected:,.0f}} from RWA, so the leverage ratio binds. That is a typical outcome for well-hedged, low-risk-weight trades: the balance sheet, not the counterparty, is the scarce resource.

### Turning cost into bps

Two charges go into the spread. The **balance sheet charge** is the leverage exposure over notional times a cost per exposure: {{ex.bs_charge.expected:.2f}} bps a year. The **capital charge** is capital times the cost of equity over notional: {{ex.cap_charge.expected:.2f}} bps a year at a 10% cost of equity. They join funding, XVA, hedging cost and margin in the spread build-up from the Pricing Lab.

### Client profitability

Pull the pieces together for a client. **Net contribution = revenue - funding cost - balance sheet cost. Return on capital = net contribution / capital. Economic profit = net contribution - capital x cost of equity.** For a 50 million swap at 100 bps over benchmark, revenue is 500,000 a year, funding at the 35 bps FTP is 175,000, and the balance sheet cost is 59,040. Net contribution is {{ex.profit.expected.net_contribution:,.0f}}, return on capital {{ex.profit.expected.return_on_capital:.1%}} and economic profit {{ex.profit.expected.economic_profit:,.0f}}: slightly below the hurdle. A desk reading this decides whether to reprice, reduce the hedge's balance sheet cost through netting, or accept a thinner return for a strategic client.

### Levers to improve the numbers

**Netting**: opposing client trades in the same stock reduce hedge inventory and exposure. **Internalisation**: covering shorts internally avoids external borrow and balance sheet. **Collateral**: margin from the client reduces replacement cost. **Hedge choice**: futures for index exposure use margin instead of balance sheet. **Tenor**: shorter trades use capital for less time. **Client mix**: lower risk-weight counterparties need less capital.

### Limits of the simple model

The model omits netting sets, maturity factors, the real SA-CCR formula, market-risk RWA, G-SIB surcharges, central clearing treatment and tax. Real bank figures differ, and the config is clearly labelled illustrative. The reasoning, though, transfers: find the binding constraint, price it per year, divide by notional and compare it with the spread.

### Liquidity and funding risk

Funding is also a liquidity question: can the desk roll its funding and meet margin calls in a stress? Repo and unsecured funding tenors, buffers of liquid assets and stress calls by scenario are the treasury's tools. A TDA contributes by flagging large expected settlements, margin calls and recalls that move cash.

## Worked example

Cost a 50 million swap for a pension client, hedged with stock.

**Step 1: EAD.** Alpha 1.4, MTM 1 million, no collateral, add-on 32% of 50 million: {{ex.ead.expected:,.0f}}.

**Step 2: leverage exposure.** Add the 50 million hedge: {{ex.leverage.expected:,.0f}}.

**Step 3: RWA.** Counterparty weight 0.2 on the EAD and 0.25 on the hedge: {{ex.rwa.expected:,.0f}}.

**Step 4: capital.** 4% of leverage exposure is {{ex.capital.expected:,.0f}}; 12% of RWA is {{ex.rwa_capital.expected:,.0f}}. The larger binds.

**Step 5: bps.** Balance sheet {{ex.bs_charge.expected:.2f}} bps; capital {{ex.cap_charge.expected:.2f}} bps.

**Step 6: profit.** At 100 bps revenue and 35 bps FTP the net contribution is {{ex.profit.expected.net_contribution:,.0f}}, return on capital {{ex.profit.expected.return_on_capital:.1%}}.

**Step 7: decision.** The trade is near the hurdle. Netting against another client's long in the same stock would cut the hedge and improve it.

## Desk reality

**Capital is a price, and clients feel it.** When a quote seems high, the capital line is often why. Explain it in bps.

**The binding constraint changes.** A client that is low-risk-weight and balance-sheet heavy is expensive for the leverage ratio; a hedge fund with a small balance sheet footprint is expensive on RWA. Know which applies.

**Do not quote capital as a fixed number.** It moves with exposure, collateral and the bank's parameters.

**Ask treasury early.** Large trades need funding in advance, and treasury needs to know the tenor and size.
