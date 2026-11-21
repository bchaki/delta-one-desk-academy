## Learn

Loan economics answer one question: what does it cost, or earn, to hold one stock on loan for a period? There are two collateral structures, cash and non-cash, and two sides, the lender and the borrower. The arithmetic is simple, but the names (fee, rebate, reinvestment, spread, short cost drag) are used loosely on desks, so it is worth fixing them early.

### Fee on a non-cash loan

When the borrower posts non-cash collateral, such as government bonds, it pays the lender a **borrow fee** on the loan value: **fee amount = loan value x fee x days / basis**. A 5,000,000 loan at a fee of 1.5% for 30 days on a 360-day basis costs {{ex.fee.expected:,.2f}}. Fees are quoted in basis points a year: 150 bps is 1.5%. Day-count conventions follow the loan currency: ACT/360 for USD and EUR, ACT/365 for GBP.

### Rebate on cash collateral

When the borrower posts cash, the lender reinvests it and earns a return. The lender pays the borrower a **rebate**, the share of that return given back, and keeps the fee as the difference. **Rebate rate = reinvestment rate - fee.** If the lender reinvests at 4.25% and the fee is 1.5%, the rebate rate is {{ex.rebate_rate.expected:.2%}}. On 5,100,000 of cash collateral for 30 days, the borrower receives {{ex.cash_rebate.expected:,.2f}}. Two things follow. First, for a given fee, a low reinvestment rate means a low rebate. Second, when the fee exceeds the reinvestment rate, the rebate is **negative**: the borrower pays to hold the short. That is common for hard-to-borrow names, and it is how fees of thousands of basis points are expressed in the cash-collateral market.

### The cost of a short

A short seller faces more than the fee. The **cost of carry** of a short is the borrow fee plus **manufactured dividends**: any dividend paid while short must be paid to the lender. For 100,000 shares at 50, a 3% fee over 90 days on a 360 basis, and a 1.00 dividend during the period, the fee is {{ex.short_drag.expected.fee:,.0f}}, the dividend {{ex.short_drag.expected.dividends:,.0f}}, and the total drag {{ex.short_drag_total.expected.total:,.0f}}. A short must generate more than this from price decline to break even, which is one reason squeezed shorts can lose twice, from the price and from the rising fee.

### Who earns what

For a desk running a book, there are three revenue lines. **Fee income** from lending stock to clients and others. **Spread** between the fee charged to a borrower and the fee paid to the upstream lender. **Reinvestment income** on cash collateral held, to the extent the desk keeps part of it. Against these are the costs of **balance sheet** and **capital** for the loan and its collateral, covered in the margin and capital modules.

### The utilisation-to-fee curve

Fees depend on utilisation. A stylised curve is **fee = GC fee x (1 + steepness x u^2 / (1 - u))**. With a GC fee of 30 bps and steepness 2, the fee at 80% utilisation is {{ex.fee_curve_80.expected:.0f}} bps and at 95% it is {{ex.fee_curve_95.expected:,.0f}} bps. The curve is convex: little pricing power at low utilisation and a spike as supply runs out. It is illustrative, not market data, but the shape matches what desks see.

### Fixed versus floating fee

A fixed fee on a term loan protects the borrower if the name becomes special but pays a premium for that insurance. A floating fee on an open loan tracks the market and can be repriced daily. The desk often borrows open and lends term to clients, or the reverse, and the mismatch is a spread risk.

### Reinvestment risk

A lender that reinvests cash collateral takes credit and liquidity risk on the reinvestment vehicle. In the 2008 crisis some lenders lost money on reinvestments that were meant to be safe. For the desk, the lesson is to look at where the cash is reinvested whenever the lender is also a source of financing.

### Quoting: all-in versus fee

Desks quote shorts to clients in two ways. **All-in**: the client pays benchmark plus a single spread that includes the expected borrow. **Pass-through**: the client pays benchmark plus a fixed spread plus the actual borrow fee. Pass-through is safer for the desk and more transparent. All-in is simpler for the client but leaves the desk with the risk of borrow fees moving, which has to be priced in.

## Worked example

A client is short 100,000 shares at 50 for 90 days. Compare the cost to the desk under the two collateral structures.

**Step 1: loan value.** 100,000 x 50 = 5,000,000.

**Step 2: non-cash fee.** At a 3% fee, 5,000,000 x 3% x 90/360 = {{ex.short_drag.expected.fee:,.0f}}.

**Step 3: cash collateral.** Collateral at 102% is 5,100,000. If the reinvestment rate is 4.25% and the fee 3%, the rebate rate is 1.25%. The borrower receives 5,100,000 x 1.25% x 90/360 = 15,937.50.

**Step 4: lender's view.** The lender earns 4.25% on 5,100,000, pays 1.25% rebate and keeps 3.00% on the cash, which is slightly more than the non-cash fee because the collateral exceeds the loan.

**Step 5: dividends.** A 1.00 dividend adds {{ex.short_drag.expected.dividends:,.0f}} of manufactured dividend.

**Step 6: total drag.** {{ex.short_drag_total.expected.total:,.0f}} over 90 days, or about 2.75% of the loan annualised.

**Step 7: the client's price.** The desk charges the client benchmark minus the spread on the short, passes through the dividend, and keeps the difference between what the client pays and what the desk pays upstream. If the fee rises to 6% mid-way, the desk's margin shrinks unless the swap passes fees through.

## Desk reality

**Look at both numbers.** Traders talk about fees, finance teams about rebates. A negative rebate and a high fee are the same fact stated differently, and a spreadsheet that mixes them gives wrong answers.

**Dividends are where short carry surprises.** A high-yield stock at ex-date is expensive to hold short. The calendar of ex-dates is part of the daily checklist.

**Fees are marked daily.** Open loans reprice. A TDA who only looks at the trade date fee will mis-state the carry. Check the fee series for every short name.

**Watch cross-currency.** A loan in one currency with collateral in another carries FX exposure in the collateral mark, handled in the operations module.
