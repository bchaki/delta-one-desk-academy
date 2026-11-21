## Learn

An exchange-traded fund (ETF) is a fund whose shares trade on an exchange like a stock. For a Delta One desk ETFs are both a **product** (clients trade them, and the desk makes markets and finances positions in them) and a **hedge** (an ETF is often the quickest liquid way to hedge a basket). They are also a source of arbitrage, because an ETF has two prices: its market price and the value of the assets behind it.

### Structure: physical and synthetic

A **physical** ETF holds the underlying securities (full replication or a sampled basket). A **synthetic** ETF holds collateral and a swap with a counterparty that delivers the index return. Physical funds carry no swap counterparty risk but have tracking differences from sampling; synthetic funds track tightly but add counterparty and collateral risks. Many desks are the swap counterparty to synthetic ETFs, which is a Delta One business in its own right.

### Primary and secondary markets

The **secondary market** is the exchange, where investors trade ETF shares with each other and with market makers. The **primary market** is where **authorised participants (APs)**, large banks like the desk, create or redeem ETF shares directly with the fund in blocks called **creation units**. To **create**, the AP delivers the basket of underlying securities (or cash) and receives new ETF shares. To **redeem**, it hands back ETF shares and receives the basket. Creations and redemptions may be **in kind** (securities) or **in cash**, and the fund charges a **creation fee**.

### NAV, iNAV and premium

The **NAV** is the value of the fund's assets per share at the close: **NAV = (sum of holdings x prices + cash) / ETF shares outstanding**. The **iNAV** is the same calculation intraday using live prices. The ETF price can trade above NAV (a **premium**) or below (a **discount**): **premium = ETF price / NAV - 1**. With holdings of 100 shares of A at 50 and 200 of B at 25, cash 1,000 and 100 ETF shares, NAV is (5,000 + 5,000 + 1,000)/100 = **{{ex.nav.expected:.2f}}**. If the ETF trades at 110.55 the premium is **{{ex.premium.expected:.2%}}**.

### The arbitrage that keeps ETFs at NAV

If the ETF trades above its iNAV by more than costs, an AP can sell the ETF, buy the basket and **create** new shares to deliver against the short, locking in the gap. If it trades below, the AP buys the ETF, **redeems** it for the basket and sells the basket. The trigger is the **break-even threshold**: creation fee over creation-unit value plus basket trading costs plus the ETF's half spread. With a 500 fee on a 5.5 million creation unit, 4 bps of basket cost and 2 bps of ETF half spread, the threshold is **{{ex.threshold.expected:.2f}} bps**. An ETF at 110.80 against an iNAV of 110.00 is 72.7 bps rich, well above the threshold, so a creation earns about **{{ex.arb.expected.pnl_per_creation_unit:,.0f}}** per unit. Arbitrageurs compete this away within seconds, which is why premiums are usually small.

### When it breaks

In stress the underlying market can be illiquid or closed (for example, an ETF on Asian stocks trading in the US session), the iNAV can be stale, borrow for the basket or the ETF can be unavailable, and balance sheet may be scarce. Arbitrage costs rise, thresholds widen and the premium or discount can reach several percent. That is not necessarily a malfunction: the ETF may be giving the more accurate price of assets that cannot trade.

### ETF lending and ETFs as hedges

ETFs are borrowed and lent like stocks, and demand for hard-to-borrow ETFs can create meaningful fees. A trader short a basket of stocks may buy the corresponding ETF to hedge sector risk while building the position. Residual risk (basis risk) remains between the ETF and the basket.

### Costs and who earns what

An ETF holder pays the **total expense ratio (TER)** inside the NAV, a few basis points a year for broad index funds. The fund also earns **securities lending revenue** on its holdings, which partly offsets the TER and is one reason two funds on the same index can differ in performance. The AP earns the arbitrage gap but pays the creation fee, the basket's trading costs and the cost of carrying the position until settlement. Market makers quote the ETF around iNAV, and the spread they show reflects how liquid the basket is: a fund of large US stocks has a tight spread, a fund of small emerging-market stocks does not.

### Settlement mismatch and the primary market

A creation delivers a basket of stocks that may settle on different cycles and in different currencies. An AP that sells the ETF today on a T+1 cycle and buys a European basket that settles T+2 has a funding gap to cover. Cash creations avoid delivering stock but make the fund trade the basket, so the AP pays the fund's costs through an adjustment to the price. These details decide whether a displayed premium is truly an arbitrage, which is why the simple threshold above should be read as a floor, not a promise.

## Worked example

An index ETF has a creation unit of 50,000 shares and a creation fee of 500. The iNAV is 110.00 and the ETF trades at 110.80.

**Step 1: premium.** 110.80 / 110.00 - 1 = 0.727%, or 72.7 bps.

**Step 2: threshold.** Creation unit value is 110 x 50,000 = 5,500,000. Fee: 500 / 5,500,000 x 10,000 = 0.9 bps. Add 4 bps of basket cost and 2 bps of ETF spread: threshold {{ex.threshold.expected:.2f}} bps.

**Step 3: edge.** 72.7 - 6.9 = 65.8 bps.

**Step 4: action.** The ETF is rich, so create: sell ETF, buy basket, deliver the basket for new ETF shares.

**Step 5: PnL.** 65.8 bps of 5,500,000 is about {{ex.arb.expected.pnl_per_creation_unit:,.0f}} per creation unit.

**Step 6: NAV check.** For a fund holding 100 A at 50 and 200 B at 25 with 1,000 of cash and 100 shares outstanding, NAV is {{ex.nav.expected:.2f}}.

## Desk reality

**Cut-offs.** Create and redeem orders have daily cut-off times and settlement cycles that differ by fund and market. The TDA tracks the deadlines, the holdings file (the basket for the day) and fund announcements.

**Holdings files.** The creation basket changes daily. Using yesterday's basket is a classic break and can lead to a failed creation. Check the file date and compare weights with the index.

**ETFs as a liquidity tool.** In a volatile market the desk may hedge basket exposure with ETFs because they trade when the underlying does not. The desk must then reconcile the residual between ETF and basket at the close.

**Marks.** ETF marks should use the primary listing's close. A stale ETF mark is a recurring PnL break, and the synthetic book includes a stale-price example in the Risk and PnL module.
