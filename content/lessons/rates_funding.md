## Learn

Every Delta One trade is a financing trade in disguise. A client who buys exposure through a swap is borrowing money from the desk; a client who shorts is lending stock and receiving cash. The price of that money is quoted as a **spread over an overnight benchmark**, so before anything else you must be fluent in benchmarks, day counts and compounding.

### Overnight benchmarks

Each currency has a risk-free overnight rate that replaced the old term IBORs: [[SOFR]] for USD, [[ESTR]] for EUR, [[SONIA]] for GBP, [[TONA]] for JPY and [[SARON]] for CHF. Each is published once per business day on its own calendar and applies from that day to the next business day. A Friday fixing therefore applies for three calendar days. Spreads on this desk are always quoted in [[bps]] over a named benchmark, never "over the rate".

### Day counts

A rate is meaningless without a day count. USD, EUR and CHF money markets use [[ACT/360]]: interest = principal x rate x actual days / 360. GBP and JPY use [[ACT/365F]]. The same cash flow has different headline rates on different bases: 4.00% on ACT/360 is the same money as 4.00% x 365/360 = **{{ex.basis_convert.expected:.4%}}** on ACT/365F. Mixing bases is the commonest silent error in a spreadsheet, and it is worth about 1.4% of the rate itself, so on a 4% rate roughly 5.6 bps, which is bigger than many client spreads' negotiation range.

For a simple loan the interest is straightforward. Lend 10 million for 91 days at 4.30% on ACT/360 and you receive 10,000,000 x 0.043 x 91 / 360 = **{{ex.simple_interest.expected:,.2f}}**.

### Compounding in arrears

A swap that resets monthly does not pay the average of the overnight rates; it pays the **compounded** rate, because that is what you would have earned rolling the cash every day. With daily fixings r_i applying for d_i calendar days:

**R = [ product of (1 + r_i d_i / basis) - 1 ] x basis / D**

where D is the total calendar days of the period. Take a Monday to the following Monday on SOFR with fixings of 4.00% Monday to Thursday and 4.10% on Friday (which applies for three days). The simple day-weighted average is **{{ex.simple_average.expected:.5%}}**, while the compounded-in-arrears rate is slightly higher at **{{ex.compounded.expected:.5%}}**. The gap grows with the rate level and the period length, and it is exactly the money a "simple average" convention would leave on the table.

Two market conventions change *which* fixings are used, not how they are compounded. A **lookback** takes each day's fixing from a few business days earlier, and an **observation shift** also shifts the weights. Both exist so the payment amount is known a few days before it is due. Check the confirmation: the convention is part of the contract.

### The desk's funding rate

The desk does not borrow at the benchmark. Treasury charges a **funds transfer price** (FTP): benchmark plus a spread that reflects the bank's cost of term funding. With SOFR at 4.30% and a 35 bps FTP spread, the desk's funding rate is **{{ex.funding_rate.expected:.2%}}**. Whenever the desk hedges a client's long swap with stock, it funds the stock at this rate. The swap spread must therefore cover at least the FTP spread (plus other costs) before the trade earns anything.

### Why funding matters for PnL

The desk's economics on a hedged long swap reduce to

**notional x (swap spread - FTP spread) x period**

because the benchmark leg cancels: the client pays benchmark plus the swap spread, the desk pays benchmark plus FTP on the hedge. The same notional, a different spread. If funding costs rise 10 bps and swap spreads do not, the desk's carry falls by 10 bps a year on every long trade. Conversely, on short trades the desk receives the benchmark on short proceeds less the borrow fee, so a higher benchmark helps shorts and hurts nobody on longs, but a higher borrow fee hurts.

### Reading the screens

Three habits will serve you well. First, always ask "benchmark, day count, compounding?" before comparing two rates. Second, convert to a common basis and annualisation before deciding that one rate is cheaper. Third, check which calendar a fixing belongs to: a TONA fixing exists on a Japanese business day that may be a holiday in New York, and a missing fixing is one of the classic reset breaks.

## Worked example

A client long swap has 25 million USD notional resetting monthly. The period runs Monday 2 March to Monday 9 March 2026 for illustration, with the fixings above.

**Step 1: simple average.** (4 x 4.00% + 3 x 4.10%) / 7 = **{{ex.simple_average.expected:.5%}}**. The Friday fixing carries three days because the next business day is Monday.

**Step 2: compounding.** The product of daily factors is (1 + 0.04/360)^4 x (1 + 0.041 x 3/360). Subtracting 1 and multiplying by 360/7 gives **{{ex.compounded.expected:.5%}}** on ACT/360.

**Step 3: restate on another basis.** For a GBP-style ACT/365F comparison multiply by 365/360. A 4.00% ACT/360 rate becomes {{ex.basis_convert.expected:.4%}}.

**Step 4: add the spread.** A 30 bps swap spread gives the client pays about 4.34% on ACT/360 for the week, i.e. 25,000,000 x 0.0434 x 7 / 360 is roughly 21,097.

**Step 5: the desk's funding.** At SOFR plus a 35 bps FTP the desk funds the hedge at {{ex.funding_rate.expected:.2%}} when SOFR is 4.30%. On a 30 bps swap against 35 bps FTP the desk is losing 5 bps a year on funding alone, so the trade needs another source of income (borrow, dividend leakage or a wider spread) to be worth doing. The stored examples in the table are recomputed live from the code.

## Desk reality

**Fixings are your problem.** If a reset uses a fixing that is missing, late or wrong, the swap pays the wrong amount. The TDA checks the fixing file against the rate the client's confirmation names before the reset is released. A fixing 100 bps off on a monthly reset of 25 million is worth about 20,000.

**Basis mistakes.** When a client compares your quote with another bank's, make sure you are both talking about the same benchmark, day count and compounding. A quote of "SOFR plus 40" and "ESTR plus 40" are not the same price, and a GBP quote on ACT/365F is not directly comparable with a USD quote on ACT/360.

**Funding curves change.** Treasury updates FTP spreads periodically and by currency. A trade priced last month at 30 bps may be underwater at this month's FTP. Know where to see the current spread and which trades are most sensitive: large, long, non-USD and long-dated ones.

**Holidays.** A Japanese or UK holiday changes the weights in compounding and can create a missing fixing on a calendar that differs from the trade's. When a reset looks odd, check the calendar before you check the maths.
