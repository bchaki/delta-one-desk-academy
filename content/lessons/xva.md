## Learn

A swap with a client creates a claim on that client. If the client fails, the desk may lose the value of what it was owed. **Counterparty risk** is the study of that loss, and **XVA** is the family of adjustments that put a price on it and related costs. For a Delta One desk the exposure is small on a day-to-day basis, because swaps reset and are collateralised, but it is real, and a part of every spread.

### Exposure over time

What matters is not today's mark-to-market but how much the client could owe in the future. **Expected exposure (EE)** is the average amount owed, counting only positive values, at each future date. **Potential future exposure (PFE)** is a high quantile, such as the 95th, of the same distribution. The **peak PFE** is the worst date, and the **average EE (EPE)** is the mean across the life.

A total return swap with periodic notional resets has a distinctive profile. Right after a reset the mark-to-market is zero. It then drifts, up or down, as the underlying moves, and resets to zero again. The exposure therefore rises within each period and falls at the reset, a saw-tooth pattern rather than the growth over the trade's life of a vanilla interest rate swap. Resets are what keep equity swap exposure small.

### Collateral and the margin period of risk

With a CSA, the client posts collateral for the mark-to-market. The desk is still exposed to the move that happens during the **margin period of risk (MPOR)**: the time between the last collateral exchange and the close-out if the client defaults, typically around 10 business days. The simulation models this by letting collateral lag the exposure by a number of steps. An uncollateralised 10 million swap on a 25%-volatility stock over a year with quarterly resets, simulated weekly, has a peak PFE of {{ex.profile_unc.expected.peak_pfe:,.0f}} and an EPE of {{ex.profile_unc.expected.epe:,.0f}}. With collateral lagging by two weeks and a zero threshold, the peak PFE falls to {{ex.profile_col.expected.peak_pfe:,.0f}} and the EPE to {{ex.profile_col.expected.epe:,.0f}}. Collateral does not remove the exposure: it shrinks it to the gap risk.

### CVA

**Credit valuation adjustment (CVA)** is the expected loss from client default: **CVA = LGD x sum of EE x discount factor x marginal default probability**. Default probability comes from the credit spread: a flat hazard rate h = spread / LGD, with survival e^{-ht}. For a flat 1 million exposure at years one and two, a 100 bps spread and 60% LGD, CVA is {{ex.cva.expected:,.0f}}. Riskier clients, with wider spreads, cost more: the illustrative table has 250 bps for a hedge fund and 50 bps for a pension fund.

### FVA, KVA and MVA

**Funding valuation adjustment (FVA)** is the cost of funding uncollateralised exposure: **funding spread x sum of EE x discount x time step**. With a 60 bps funding spread on the same profile, FVA is {{ex.fva.expected:,.0f}}. **Capital valuation adjustment (KVA)** is the cost of holding capital against the exposure over time: hurdle x sum of EE x risk weight x CET1 ratio, here {{ex.kva.expected:,.0f}}. **Margin valuation adjustment (MVA)** is the cost of funding initial margin: average margin x funding spread x maturity: {{ex.mva.expected:,.0f}} for 5 million of margin over two years at 40 bps.

### Putting it into the spread

The total XVA is expressed as a spread: **bps a year = total XVA / notional / tenor x 10,000**. 50,000 of XVA on a 10 million swap over two years is {{ex.charge.expected:.1f}} bps a year. That figure is the XVA line in the spread build-up. A client with a weaker credit, no CSA or a longer tenor pays more, and the desk should be able to say why in numbers.

### Wrong-way risk

The model assumes independence between exposure and the client's default. **Wrong-way risk** occurs when they are linked: a hedge fund long a concentrated stock owes the desk most precisely when the stock falls and the fund is in trouble. The simplified model leaves it out and the full version adds correlation. The concentrated-swap failure of 2021 is the case in point: exposures across banks were large against client equity and correlated with the very positions that were failing.

### Who does what

The desk trades and quotes. A dedicated **XVA desk** often manages the adjustments, charging the business and hedging with credit default swaps. **Credit risk** sets counterparty limits and monitors exposure. **Collateral management** runs calls. The TDA's part is to ensure that CSA terms, thresholds and legal entities are booked correctly, since XVA, limits and calls all read from them.

### Limitations

The model uses a lognormal underlying, flat hazard and rate, no netting set, and a simple MPOR gap. A production model adds netting across trades, stochastic rates and credit, collateral eligibility, and calibrated correlations. Treat the numbers as a way to see the shape and the drivers, not as a price.

## Worked example

Price counterparty risk on a 10 million swap.

**Step 1: profile.** Simulate the saw-tooth exposure: peak PFE {{ex.profile_unc.expected.peak_pfe:,.0f}} uncollateralised.

**Step 2: collateral.** With a two-week MPOR and no threshold: peak PFE {{ex.profile_col.expected.peak_pfe:,.0f}}.

**Step 3: CVA.** On a simple flat exposure of 1 million for two years at 100 bps: {{ex.cva.expected:,.0f}}.

**Step 4: FVA.** At a 60 bps funding spread: {{ex.fva.expected:,.0f}}.

**Step 5: KVA and MVA.** KVA {{ex.kva.expected:,.0f}}; MVA {{ex.mva.expected:,.0f}}.

**Step 6: spread.** 50,000 of total XVA on 10 million over two years: {{ex.charge.expected:.1f}} bps a year.

**Step 7: compare.** The XVA line in the spread build-up should match what the XVA desk charges. Check the CSA and credit assumptions behind it.

## Desk reality

**Check the paper.** A trade booked without an active CSA has a very different XVA. The booking validator blocks it for this reason.

**Resets limit exposure.** Reset dates and margin calls are the controls that keep exposure small. A missed reset is a larger exposure.

**Concentration is the real risk.** Exposure to one client's one position, as in 2021, matters more than a diversified average. Know the biggest exposures by client and by name.

**Quote the reason.** When a client asks why its spread is wider, say "your credit and CSA" and show the XVA line.
