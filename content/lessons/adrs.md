## Learn

An American depositary receipt (ADR) is a US-dollar-traded certificate representing shares of a foreign company, held by a depositary bank. GDRs do the same for other markets. Dual-listed companies have shares on two exchanges directly. For the desk these are **cross-listed securities**: the same company trades in two places, in two currencies and (often) at different times, and arbitrage keeps the prices aligned.

### The ratio

An ADR represents a fixed number of local shares: the **ratio**. If one ADR represents 0.5 local shares, a stock at 40 EUR implies an ADR worth 20 EUR before FX. The parity price in dollars is **ADR fair value = local price x ratio x FX**, where FX is dollars per unit of local currency. For 40 EUR, ratio 0.5 and EURUSD 1.10 the fair value is **{{ex.fair_value.expected:.2f}} USD**. For a yen stock, FX is 1 / USDJPY: 3,000 JPY with a ratio of 1 and USDJPY at 150 is **{{ex.jpy_fair_value.expected:.2f}} USD**.

### The depositary and its fees

A **depositary bank** issues and cancels ADRs. To **issue**, someone delivers local shares to the custodian and receives ADRs. To **cancel**, they surrender ADRs and receive local shares. The depositary charges a **conversion fee** per ADR on issuance and cancellation, and an annual **depositary fee** that is usually deducted from dividends. Conversion takes time (one or more days) and local shares may only be deliverable in the local settlement system, which matters for timing.

### The arbitrage band

Costs set a band around parity: the conversion fee plus bid-offer, FX and commission costs. With a 0.02 fee per ADR and 10 bps of other costs, the band around 22.00 is **{{ex.band.expected.lower:.3f}} to {{ex.band.expected.upper:.3f}}**. If the ADR trades above the top, **sell the ADR, buy the local shares, deliver them to issue new ADRs**. If it trades below the bottom, **buy the ADR, cancel it for local shares and sell those**. An ADR at 22.10 is above the band and the edge after costs is about **{{ex.arb.expected.1:.3f}} per ADR**.

### FX and timing

The ADR trades in dollars during US hours, the local stock in local currency during local hours. When the markets overlap, parity can be monitored live; when they don't, the ADR trades off the last local price and the FX rate, and gaps are common. The FX leg is a real risk: converting the local sale proceeds costs spread, and a currency move between legs changes the profit.

### Corporate actions and dividends

Dividends are paid in local currency, converted by the depositary and paid in dollars net of local withholding and the depositary fee. Corporate actions on the local shares change the ratio or the number of ADRs. Both create dividend and adjustment breaks if the booking systems treat the ADR and the local share inconsistently.

### Why the desk cares

ADR positions are common hedges: a US client long a swap on a foreign stock may be hedged with the ADR, while the local line is more efficient at other times. Cross-listings also create **financing and borrow differences**: the ADR can be hard to borrow while the local share is easy. These differences are part of the decision of which line to hold.

### Sponsored, unsponsored and levels

**Sponsored** programs are set up with the issuer's agreement and often listed on a US exchange (Level 2 or 3) with reporting obligations. **Unsponsored** ones are created by a depositary without the issuer and trade over the counter, with thinner liquidity and wider bands. The program level matters to the desk because it sets liquidity, short-sale rules and the data available for pricing.

### Pre-release and borrowing

Depositaries sometimes allow **pre-release**: ADRs issued before the local shares are delivered, against a promise to deliver them. It lets an arbitrageur close the loop faster, but it is capacity-limited and carries operational risk if the local shares fail to arrive. The desk should know whether a program offers it and how much is outstanding, because heavy pre-release has been a source of phantom supply in some names.

### Reading the deviation

In the synthetic data you will see the ADR deviate from parity by a few basis points most days, with larger gaps when the local market is closed and news arrives. The deviation is mean-reverting by construction: the arbitrage is the force that pulls it back. When you see a persistent gap, ask first whether the local line is hard to borrow, whether FX is the issue, or whether the ratio changed after a corporate action.

## Worked example

A European stock trades at 40 EUR. One ADR represents 0.5 shares. EURUSD is 1.10. The ADR trades at 22.10 USD.

**Step 1: parity.** 40 x 0.5 x 1.10 = {{ex.fair_value.expected:.2f}} USD.

**Step 2: band.** Conversion fee 0.02, other costs 10 bps of 22.00 = 0.022. Band: {{ex.band.expected.lower:.3f}} to {{ex.band.expected.upper:.3f}}.

**Step 3: signal.** 22.10 is above 22.042: the ADR is rich, so issue.

**Step 4: edge.** 22.10 - 22.042 = {{ex.arb.expected.1:.3f}} per ADR. On 100,000 ADRs that is about 5,800, before FX risk.

**Step 5: execution.** Sell 100,000 ADRs, buy 50,000 local shares in EUR (converting USD to EUR), deliver them to the custodian, receive new ADRs on T+1 or T+2 and deliver them against the short.

**Step 6: a yen stock.** At USDJPY 150, a 3,000 JPY stock with ratio 1 is worth {{ex.jpy_fair_value.expected:.2f}} USD, and the same arithmetic applies with FX = 1/150.

## Desk reality

**Timing risk.** The ADR and local legs rarely settle on the same day. If the conversion takes two days, the desk is exposed to the price and FX moves meanwhile; the pricing band should include a haircut for that, which the simplified model here leaves out.

**Dividend breaks.** ADR dividends arrive in dollars after FX and fees. Check them against the local dividend and the ratio. Breaks are common after FX conversion rate disputes.

**Borrow.** An ADR can be harder to borrow than the local share. Check both before choosing which line to short, and watch for recalls.

**Voting and pass-through fees.** Holders of ADRs may pay pass-through fees for corporate action elections. For swaps, the confirmation specifies which line is the reference and who bears these fees.
