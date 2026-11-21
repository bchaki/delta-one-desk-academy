## Learn

Margin is collateral posted against a position so the other side is protected if you cannot pay. A Delta One desk lives with margin in both directions: it posts margin to exchanges and clearers for futures, collects margin from clients on swaps and financing, and posts margin to its own lenders. Different counterparties use different methods, and the same book can need very different amounts of margin depending on the method. This module walks through six of them, each in a tab of the sandbox: exchange (SPAN-like), the ISDA-style initial margin (schedule and SIMM-lite), US broker margin (Reg T), portfolio margin, prime-brokerage house margin and CSA collateral calls. All parameters are illustrative.

### Initial margin and variation margin

**Initial margin (IM)** is a buffer against a future move while a defaulter's positions are closed out. **Variation margin (VM)** is the daily settlement of mark-to-market gains and losses. IM is set by a model and moves with risk; VM moves with prices. A futures position of 10 contracts at a multiplier of 50 that goes from 5,000 to 5,020 and back to 5,010 pays flows of {{ex.vm.expected.0:,.0f}} and {{ex.vm.expected.1:,.0f}}: the sign shows who pays that day.

### Exchange margin (SPAN-like)

Exchanges scan a position across a grid of price moves and charge the worst loss. For 10 long contracts of a product with a notional of 2.5 million and a scan range of 7%, the scan risk is {{ex.span_single.expected.gross:,.0f}}. Two refinements cut the charge. **Calendar spreads**: a long in one expiry against a short in another is charged a small percentage of the matched notional instead of the full scan. Long 10 December and short 10 March charges {{ex.span_cal.expected.gross:,.0f}}, mostly the calendar charge. **Inter-commodity credits**: opposite positions in correlated products earn a credit. Long 10 contracts in one index and short 10 in a close cousin gross {{ex.span_spread.expected.gross:,.0f}} but are credited {{ex.span_spread.expected.credits:,.0f}}, leaving {{ex.span_spread.expected.net:,.0f}}.

### Schedule-based IM

Uncleared swaps between big counterparties need IM too. The **schedule method** charges a percentage of gross notional (15% in this teaching grid) and reduces it with netting through the **net-to-gross ratio (NGR)**: **net IM = gross IM x (w + (1 - w) x NGR)**. With 100 million gross and 20 million net, gross IM is {{ex.schedule.expected.gross:,.0f}} and net is {{ex.schedule.expected.net:,.0f}}, a netting benefit of {{ex.schedule.expected.credits:,.0f}}.

### SIMM-lite

A **SIMM-style** model is sensitivity-based: sensitivities per 1% move are multiplied by risk weights, combined within each bucket with a correlation, and across buckets with another. The engine's equity delta version, with invented weights, gives a net margin of {{ex.simm.expected.net:,.0f}} for sensitivities in two buckets, against a sum of standalone bucket margins of {{ex.simm.expected.gross:,.0f}}. The difference is diversification between buckets. The official calibration is published by the industry; the numbers here are not it, and the page says so.

### Reg T (US broker margin)

For a US customer margin account, **initial margin is 50% of long market value plus 50% of short market value** (the short proceeds count as the first 100%), and **maintenance** is 25% of longs plus 30% of shorts in this simplified version. For 1,000,000 long and 500,000 short, initial is {{ex.regt.expected.0.gross:,.0f}} and maintenance {{ex.regt.expected.1.gross:,.0f}}. The **gross leverage** the book allows is gross exposure over initial margin, {{ex.leverage.expected:.1f}} times here. Reg T is simple and conservative: it ignores hedges between positions.

### Portfolio margin

**Portfolio margin** charges the worst loss across a grid in which positions move together, so a long single-name book hedged with a short index earns an offset. With 1 million long in a single name and 1 million short in an index, standalone worst losses sum to {{ex.pm.expected.gross:,.0f}} but the portfolio worst loss is {{ex.pm.expected.net:,.0f}}. The offset is partial because single names have a wider grid than indices, a reminder that a hedge with a different instrument is not a perfect one.

### Prime brokerage house margin

A prime broker sets its own margin above regulatory minima. The teaching model starts from a **base** rate that scales with volatility, then adds charges for **concentration** (positions large against client equity), **liquidity** (positions large against ADV), **directionality** (a book that is mostly one-sided) and **squeeze risk** (shorts with high short interest). For a client with 10 million of equity, a 5 million long in a 100,000-share-ADV name and a 2 million short in a stock with 25% short interest, the base is {{ex.pb.expected.base:,.0f}} and the add-ons {{ex.pb.expected.addons:,.0f}}, for a total of {{ex.pb.expected.total:,.0f}}. The lesson: a concentrated book can look safe under simple margin and expensive under house margin. The 2021 collapse of a highly concentrated swap book, financed across several banks that did not see each other's exposures, is the case taught in the compliance and risk modules.

### CSA collateral calls

A **CSA** sets how counterparties post collateral against the mark-to-market of their swaps: a **threshold** (unsecured amount), a **minimum transfer amount (MTA)**, **independent amounts**, a **rounding** multiple and eligible collateral with **haircuts**. Required collateral is **max(E - threshold, 0) minus the mirror for the desk, plus independent amounts**. If exposure is 5.2 million and 4.0 million is held, with a 250,000 MTA and 100,000 rounding, the call is {{ex.csa_call.expected.amount:,.0f}}. Calls round up and returns round down. If the desk's calculation says 1.2 million and the counterparty's says 0.9 million, standard practice is to transfer the undisputed {{ex.dispute.expected.undisputed:,.0f}} and resolve the {{ex.dispute.expected.disputed:,.0f}} difference.

### Choosing and comparing

The same 1,000,000 long and 500,000 short book costs {{ex.regt.expected.0.gross:,.0f}} under Reg T and far less under portfolio margin if hedged. The comparison tab lets you run one book through several methods. The point is not which is right: each is right for its counterparty. The point is to know which method applies, so that when a client asks why the call is larger today, you can say whether the position, the volatility, the method or the concentration changed.

## Worked example

Run a client's book through margin.

**Step 1: exchange.** The desk hedges with 10 ES-like futures: margin {{ex.span_single.expected.gross:,.0f}}.

**Step 2: calendar.** Rolling to a spread of long December and short March cuts the margin to {{ex.span_cal.expected.gross:,.0f}} while the position is open.

**Step 3: OTC.** The same client's swaps carry 100 million gross and 20 million net. Schedule IM is {{ex.schedule.expected.net:,.0f}} after netting.

**Step 4: broker.** A US account long 1,000,000 and short 500,000 needs {{ex.regt.expected.0.gross:,.0f}} initial margin under Reg T.

**Step 5: portfolio.** The same book as portfolio margin is {{ex.pm.expected.net:,.0f}} on a long single name against a short index.

**Step 6: house.** The prime broker adds concentration and squeeze charges, giving {{ex.pb.expected.total:,.0f}} for the example book.

**Step 7: call.** The collateral call on the swap is {{ex.csa_call.expected.amount:,.0f}} after MTA and rounding. A disputed difference is settled for the undisputed {{ex.dispute.expected.undisputed:,.0f}} first.

## Desk reality

**Know the method before you explain the number.** Clients ask "why did the call double?" The answer is usually volatility, concentration or a hedge that stopped offsetting. Have the model's components in front of you.

**Calls have deadlines.** A call sent late is a call paid late. Diary every deadline and know the settlement cut-off in each currency.

**Margin is liquidity.** Variation margin on futures can drain cash in a rally against the desk's hedges. Treasury will ask for the stress call.

**Disputes are normal.** Pay the undisputed amount, record the disputed one with evidence and resolve it in the following days.
