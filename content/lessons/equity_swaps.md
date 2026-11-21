## Learn

An equity swap (total return swap, TRS) lets a client get the economics of owning shares without owning them. The client pays a financing rate, and in return receives the total return of the underlying: price change plus dividends. For the desk it is the core product: it creates the client flow, it is hedged with stock or futures, and it earns a spread. A contract for difference (CFD) is the retail-style cousin: the same economics, typically on a single stock, with a daily financing charge and the dividend paid as a cash adjustment.

### Two legs

**Equity leg.** The payer of the equity leg pays the *positive* total return and receives the *negative* one. For a long client, the desk pays the client the price increase plus dividends and the client pays the desk any price fall. **Funding leg.** The client pays a floating rate (a benchmark such as SOFR) **plus a spread**, on the notional. A short client receives the benchmark **minus** a spread, because the desk has to borrow the stock, and the spread covers the borrow fee.

Variants: **single-name**, **basket**, **index** and **portfolio** swaps; **funded** swaps where the client posts the cash up front, and **unfunded** ones where margin and the CSA do the work. **Synthetic prime brokerage** packages a hedge fund's whole book as swaps so it can lever up without a prime broker's balance sheet.

### Cash flows by hand

Take a client long 10,000 shares bought at 100 with a spread of 40 bps over SOFR. The first period runs a week, SOFR compounds in arrears at 4.044%, and the price ends at 104. With resetting notional the funding notional for the period is the shares times the starting price, 1,000,000.

- Equity: 10,000 x (104 - 100) = **{{ex.client_long.expected.price_cf:,.0f}}** to the client.
- Funding: -1,000,000 x (7/360) x (4.044% + 0.40%) = **{{ex.client_long.expected.funding_cf:,.2f}}** (the client pays).
- Net to the client: **{{ex.client_long.expected.net_cf:,.2f}}**.

A short client in the same market receives funding, because short proceeds earn the benchmark less the spread: **{{ex.client_short.expected.funding_cf:+,.2f}}**, and pays the price rise.

### The hedge and the desk's economics

The desk is on the other side of the client and hedges. For a long client, it **buys the stock** and funds the purchase at the benchmark plus its funding spread. For a short client it **borrows and sells the stock**, earns the benchmark on the proceeds, and pays the borrow fee. With a 100% pass-through of dividends, no withholding and a notional that resets, every term cancels except the spread:

**desk PnL = notional x (client spread - FTP spread) x period** on longs, and **notional x (client spread - borrow fee) x period** on shorts.

Our long swap earns 1,000,000 x (40 - 35) bps x 7/360 = **{{ex.desk_long.expected.spread_edge:.2f}}** for the week, and the engine's full calculation (swap plus hedge, with each piece rounded to cents) gives **{{ex.desk_long.expected.total:.2f}}**. The equity move of 40,000 cancels between swap and hedge. A short swap at 40 bps against a 150 bps borrow fee loses **{{ex.desk_short.expected.total:,.2f}}** in the same week: spreads can be negative if the borrow is expensive, which is why the spread build-up below matters.

### Spread build-up

A client spread is assembled from components: funding (FTP) for longs or borrow for shorts, balance sheet usage, capital, counterparty credit and funding valuation adjustments, hedging costs, and the desk's target margin. For a long with 35 bps funding, 4 balance sheet, 3 capital, 2 credit, 1 hedging and 5 margin the quote is **{{ex.spread_build.expected.total_bps:.0f}} bps**. Negotiation happens on the last component; the rest is cost.

### Terms that matter

The **notional** and **initial price** fix the starting point. The **reset frequency** (monthly, quarterly) controls when cash settles and how the notional updates: with notional reset, the funding base moves with the price; with a fixed notional it does not, which creates a residual the desk must manage. The **dividend** treatment sets how much of each dividend is passed through (pass-through, 100% gross or less) and who bears withholding tax. **Corporate action** terms say who adjusts for splits and mergers. **Termination rights** specify who can end the trade and how the final price is set. The **ISDA master agreement** and **CSA** govern documentation and collateral. For US underlyings traded with non-US clients, **871(m)** can tax dividend equivalents, and the booking must carry the right flag.

### The lifecycle

Trade, reset, dividend, corporate action, partial unwind, termination. Each step has cash flows, booking events and a team that owns it. The lifecycle tab and the simulator in this module follow a swap through all of them on the synthetic price path.

## Worked example

The same 10,000-share long swap at 100, spread 40 bps, one week, SOFR 4.044% compounded.

**Step 1: equity leg.** Price rises from 100 to 104. The desk owes the client {{ex.client_long.expected.price_cf:,.0f}}.

**Step 2: funding leg.** The client owes the desk 1,000,000 x 7/360 x (4.044% + 0.40%) = {{abs ex.client_long.expected.funding_cf:,.2f}}.

**Step 3: net.** The client receives {{ex.client_long.expected.net_cf:,.2f}}. Round each component to cents first, then add: the net is the sum of the rounded parts, so the schedule always reconciles.

**Step 4: hedge.** The desk buys 10,000 shares at 100. It gains 40,000 as the stock rises, pays financing of about 854 on its own funding (benchmark plus 35 bps), and receives no dividends this week.

**Step 5: net desk PnL.** Swap -39,135.89, hedge +39,145.61: total about {{ex.desk_long.expected.total:.2f}}, equal to the spread edge of {{ex.desk_long.expected.spread_edge:.2f}} up to rounding.

**Step 6: dividends.** A 2.00 dividend at 85% pass-through on 10,000 shares would be {{ex.swap_dividend.expected:,.0f}} paid to the client.

**Step 7: partial unwind.** The client closes 40% of the trade: 4,000 shares terminate and 6,000 remain, and the desk sells 4,000 hedge shares the same day.

## Desk reality

**Reset day.** Resets are the swap team's heartbeat. The TDA checks the fixing, the reset price source, the notional and the dividend amounts against the confirmation, then releases the cash flows. A wrong fixing or price on 25 million notional is worth thousands, and the client will notice.

**Client statements.** Clients receive statements showing positions, accruals, and cash. When a client queries a number, reproduce it from the swap terms: shares, prices, rate, days. The sandbox mirrors that workflow.

**Negotiating spreads.** Sales will ask how tight the desk can go. Know the build-up: FTP, borrow and balance sheet are costs; only margin is negotiable. For shorts, the borrow fee can change daily, so a fixed short spread carries risk if the stock gets harder to borrow.

**Booking correctness.** The wrong spread, legal entity, benchmark or 871(m) flag are the classic booking breaks. The synthetic book contains one of each so you can practise finding them in the PnL explain module.
