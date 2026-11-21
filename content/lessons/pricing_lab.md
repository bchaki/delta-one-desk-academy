## Learn

The pricing lab pulls the desk's pricing building blocks into one place: the forward and futures price, the financing rate hidden inside it, the swap spread a client pays, and the conversion between a price-return future and a total-return future. Everything here is linear. There is no volatility input anywhere, which is both the simplicity and the trap of Delta One pricing: the formulas are easy, but each hides conventions that decide whether the number is right.

### The forward price

For a stock or index with a known stream of dividends, the no-arbitrage forward is spot grown at the financing rate less the value of the dividends received before expiry. With a continuous dividend yield q: **F = S e^{(r - q) T}**. With 100 of spot, r = 4%, q = 2% and half a year, the forward is {{ex.fwd_cont.expected:.4f}}. With discrete dividends, the forward is **F = S e^{rT} - sum D_i e^{r (T - t_i)}**: each dividend is reinvested at the financing rate from its ex-date to expiry. A single dividend of 1.00 at the three-month point gives {{ex.fwd_disc.expected:.4f}}. The two views differ because a yield spreads dividends evenly while the discrete model puts them on their dates.

### Implied financing

A traded futures price tells you the financing rate the market is using. Rearranging, **r = ((F + FV of dividends) / S - 1) x basis / days**. Take a future at 101.20 against spot 100.00, dividends of 1.00 to expiry and 180 days on a 360 basis: implied repo is {{ex.implied.expected:.2%}}, a simple annualised rate. Compare it with the benchmark: if the implied rate is above the cost of funding, the future is rich and a cash-and-carry earns the difference. The Index Futures module builds the full no-arbitrage band with costs; here the point is the direction of the calculation, from price to rate.

### Swap spread build-up

A client's swap spread is a sum of costs. For a long: **funding (FTP) + balance sheet + capital + XVA + hedging cost + target margin**. The illustrative example of 35, 4, 3, 2, 1 and 5 bps totals {{ex.spread.expected.total_bps:.0f}} bps. For a short the first component is the borrow fee instead of funding. Pricing is quoting this stack, not deriving a single number: the first five lines are cost, and only the last is negotiable. The lab's quote sheet lets you change each line and see the client spread move.

### Price futures to total return futures

A **price future** on an index settles on the price level and carries dividends as a risk in the basis. A **total return future (TRF)** settles on the total return index, so dividends are paid through to the holder and the future is quoted as a **spread over the benchmark**. The two are interchangeable with a conversion. The price basis equivalent of a TRF spread is **F - S = S x (benchmark + spread) x tau - FV(dividends)**. For an index at 5,000, a three-month period, a benchmark of 4%, a spread of 16 bps and 12 index points of dividends, the basis is {{ex.trf_basis.expected:.1f}} points. Run backwards, a future at 5,040 implies a spread of {{ex.trf_spread.expected:.1f}} bps. This is how a trader moves between a price-future quote and a TRF quote for the same exposure.

### Sensitivities of a price

Linear products still have sensitivities. The forward moves one-for-one with spot (delta one). It moves with the **financing rate** (rho): a 1 bp rise in r raises the forward by roughly S x T x 1 bp. It falls with **dividends**: every index point of dividend lowers the forward by about a point. And it moves with **borrow** for shorts. The lab's bump table shows these numerically by repricing with shifted inputs, which is how production risk systems compute them.

### Conventions to check on every price

Which day count and compounding does the rate use? Are dividends gross or net of withholding? Is the forward in the same currency as the cash flows? Does the future settle on the price or the total return index? Is the date convention business-day adjusted? A pricing difference of a few basis points between two systems nearly always traces to one of these.

### Checking a price independently

Never rely on one source. A quick sanity check is to compute the cost of carry in your head: spot x (rate - dividend yield) x T. A 4% rate, 2% yield and a half-year gives about 1% of spot, so the forward should sit a point or so above spot at 100. If a system returns 103 or 99, look for the missing convention.

### Where pricing meets booking

Prices become trades. A swap spread of 40 bps on a booking screen is a number that must match the quote, the confirmation and the legal document. The pricing and booking modules together teach the discipline of carrying one number through the process without it changing.

## Worked example

Quote a client a long swap on an index and cross-check against futures.

**Step 1: forward.** Spot 100, financing 4%, yield 2%, half a year: {{ex.fwd_cont.expected:.4f}}.

**Step 2: discrete check.** One dividend of 1.00 at three months: {{ex.fwd_disc.expected:.4f}}.

**Step 3: implied repo.** The market future is 101.20: implied simple repo {{ex.implied.expected:.2%}}.

**Step 4: spread stack.** Funding 35, balance sheet 4, capital 3, XVA 2, hedge cost 1, margin 5 gives {{ex.spread.expected.total_bps:.0f}} bps.

**Step 5: TRF conversion.** On a 5,000 index, a 16 bps TRF spread equals a price basis of {{ex.trf_basis.expected:.1f}} points with 12 points of dividends.

**Step 6: compare.** The swap at 50 bps over benchmark against a TRF at 16 bps: the 34 bps difference is what the client pays for the bilateral swap's balance sheet, credit and margin versus a cleared future.

**Step 7: decide.** A client who wants one-year exposure may prefer the TRF; one who needs a bespoke basket needs the swap. The Cost of Exposure module compares the choices across holding periods.

## Desk reality

**Different desks quote different bases.** Futures traders quote basis in points, swap traders quote spreads in bps. Know the conversion by heart, because you will be asked to move between them in the middle of a call.

**Dividends are the biggest source of pricing disagreement.** Two systems that disagree on index dividend forecasts will disagree on the forward by several points. Check which forecast each uses.

**Do not hide costs inside the spread without a record.** The build-up should be saved with the quote so that later, when the spread looks wrong, you can see what was assumed.

**Quote validity is short.** A spread quoted at 10:00 is not valid at 14:00 after funding spreads move. Time-stamp every quote.
