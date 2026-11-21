## Learn

For a Delta One desk a dividend is not income, it is a **cash flow that someone owes someone else**, and the desk's job is to make sure the right amounts move in both directions. Dividends feed futures fair value, swap equity legs, borrow demand, index points and a whole product family of dividend derivatives. They are also the commonest source of booking breaks.

### The dividend calendar

A declared dividend has four dates. The **declaration date** announces the amount. The [[ex-date]] is the first day the shares trade without the right to the dividend; on that day the share price typically falls by roughly the dividend. The **record date** is when ownership is checked, usually one business day after the ex-date in a T+1 market. The **pay date** is when cash arrives. For a swap, the ex-date is what matters: the equity leg pays the dividend to the long when the stock goes ex, even though the desk's own hedge cash arrives on the pay date.

Dividends come as regular quarterly, semi-annual or annual payments, occasional **specials**, and cuts or cancellations. An analyst forecast is a number per share per ex-date. Everything that depends on future dividends (forwards, futures, swap pricing) is therefore sensitive to the forecast, which is why the desk watches announcement calendars closely.

### Yield and present value

The dividend yield is annual dividend divided by price: a stock at 100 paying 3 a year yields 3%. For pricing we need the **present value** of dividends before a date, summing each amount discounted from its ex-date. A 2 dividend going ex in 3 months at a 4% rate has a present value of about 1.98. For an index we sum over every constituent, which brings us to index points.

### Index dividend points

An index future subtracts the dividends of the whole basket. Each stock's dividend per share multiplied by the shares counted in the index (after free float and capping) gives index-currency dividends, and dividing by the **divisor** converts them to **index points**: the same units as the index level. Take one stock paying 0.50 per share with 2,000,000 index shares in an index with a divisor of 100,000. It contributes 0.50 x 2,000,000 / 100,000 = **{{ex.index_points.expected:.1f}} points**. Add every constituent and you get the series that the futures and dividend derivatives use.

### Reading dividends out of prices

If a forward or future is traded you can back out what it assumes. From F = (S - PVD) / DF, **PVD = S - F x DF**. With S = 100, F = 100.60 and DF = 0.99, PVD = 100 - 99.594 = **{{ex.implied_pvd.expected:.3f}}**. Equivalently the continuous implied yield is q = r - ln(F/S)/T. Put-call parity gives the same information from options: PVD = S - K x DF - (C - P). The desk compares these implied numbers with analyst forecasts: the gap is the market's view of cancellations or cuts.

### Withholding tax and pass-through

Most countries tax dividends paid to non-residents at source. The headline rate is the **statutory** rate, a treaty may reduce it, and reclaiming the excess can take months. A hedge holding stock receives the dividend net of withholding. If the swap pays the client the full gross amount (100% pass-through) the desk is out of pocket by the tax, and if it passes through only 85% or 70% it keeps some of the difference. The formula for the desk's gain or loss on a long swap hedged with stock is

**leakage = shares x (gross x (1 - WHT) - pass-through x gross)**

For 100,000 shares and a 2.00 gross dividend with 15% withholding: at 100% pass-through the desk receives 170,000 and pays 200,000, a **loss of {{ex.leakage_full.expected:,.0f}}**; at 70% pass-through it pays 140,000 and **gains {{ex.leakage_70.expected:,.0f}}**. Which one the client gets is a commercial term set in the confirmation, and it is part of the spread discussion.

For a short swap the flow reverses: the desk is short the hedge stock and must pay a manufactured dividend to the stock lender, funded by the dividend the client pays. The lender receives it gross in most structures, so any tax difference is a desk cost or gain again.

### Special situations

A **special dividend** is large relative to the price and usually one-off. It is treated as a corporate action with a price adjustment, and swaps pay it through the dividend leg or by adjusting the strike depending on the terms. A **cancellation** removes the forecast dividend, which shifts fair values of futures and the PnL of dividend swaps overnight. The synthetic world includes an EU cancellation episode in spring 2025 so you can see the effect on the dividend futures curve.

## Worked example

A client holds a long swap on 100,000 shares of a stock listed in a market with a 15% withholding rate. The stock goes ex a gross dividend of 2.00.

**Step 1: net dividend on the hedge.** The desk's stock hedge receives 2.00 x (1 - 15%) = {{ex.net_div.expected:.2f}} per share, or 170,000 in total.

**Step 2: what the swap owes.** At 100% pass-through the swap pays the client 200,000. The desk's dividend leakage is 170,000 - 200,000 = **{{ex.leakage_full.expected:,.0f}}**.

**Step 3: negotiate the pass-through.** At 70% the swap pays 140,000 and the desk is **{{ex.leakage_70.expected:+,.0f}}**. A pass-through below 100% is a way of charging the client for the tax drag.

**Step 4: index points.** A constituent paying 0.50 on 2,000,000 index shares with divisor 100,000 contributes {{ex.index_points.expected:.1f}} points to the index dividend series.

**Step 5: implied dividends.** With S = 100, F = 100.60 and DF = 0.99 the market-implied PV of dividends is {{ex.implied_pvd.expected:.3f}}. If analysts forecast a PV of 1.50, the market is pricing a cut.

**Step 6: yield.** A 100 stock paying 3 a year has an annual yield of {{ex.yield.expected:.1%}}.

## Desk reality

**Ex-date checks.** Every morning the TDA lists the stocks going ex today, checks that the amounts on file match the announcement, and confirms every swap and hedge on those names has a dividend entry. A missed dividend on a large long hedge is real money: the seeded missed-dividend break in the synthetic book is worth about 99,000.

**Currency and gross versus net.** Announcements are in the local currency and usually gross. Check the booking system's amount, currency and withholding treatment match the confirmation. A dividend booked in the wrong currency is a common reconciliation break.

**Forecasts move.** Analyst forecasts lag announcements and are updated on a schedule. Before quoting a dividend-sensitive trade, refresh the forecasts and check for any recent announcements. After a cancellation, expect pricing sheets to be stale until they are rebuilt.

**Tax is a specialist topic.** Withholding, treaty rates and reclaim processes are owned by tax and operations. The TDA's role is to flag, not to decide: if the client's tax status changes or a reclaim looks overdue, route it to the right team with the trade ids and amounts.
