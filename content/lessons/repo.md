## Learn

A **repurchase agreement (repo)** is a loan of cash secured by securities. One party sells securities and agrees to buy them back later at a higher price; the difference is the interest. In equity repo, the collateral is shares or an index basket. A Delta One desk uses repo in both directions: to **fund** its long hedge positions and to **earn** a return by lending cash against clients' securities. Repo is the other side of securities lending: cash-driven rather than stock-driven.

### The mechanics

The borrower of cash gives securities, the **collateral**, to the lender, who gives cash. The cash lent is the market value of the collateral minus a **haircut**: **cash = market value x (1 - haircut)**. For 10,000,000 of large-cap stock at an 8% haircut, the cash is {{ex.cash.expected:,.0f}}. The haircut protects the cash lender against a fall in the collateral's price while it sells the collateral if the borrower defaults. Riskier, less liquid collateral has a larger haircut. The illustrative table in `config/desk.yaml` uses 5% for index large caps, 8% for large caps, 15% for mid caps, 25% for small caps and 40% for hard-to-borrow names.

### Interest

**Interest = cash x rate x days / basis.** On {{ex.cash.expected:,.0f}} at 4.5% for 7 days on a 360-day basis: {{ex.interest.expected:,.2f}}. Repo rates are quoted as simple annualised rates.

### GC versus special

A repo against general collateral trades near the overnight benchmark: the illustrative GC rate is the benchmark plus 5 bps. A repo against collateral that is **special**, meaning sought-after in the securities lending market, trades at a lower rate. The cash lender who receives a special security effectively pays for it with a lower interest rate on its cash. In the model, **special rate = GC rate + factor x fee**, with a factor of -1, so a stock with a 300 bps borrow fee funds about 300 bps below the GC rate, which can take the rate negative: with a 4% benchmark the special rate is {{ex.special.expected:.2%}}. A negative repo rate means the cash lender pays interest to receive the collateral. That is how the repo and lending markets link: the lower the repo rate, the higher the borrow fee, since both measure scarcity.

### Term and open

**Overnight** repos are rolled daily. **Open** repos have no fixed end and either side can terminate. **Term** repos run for a fixed period at a fixed rate, with a premium for the longer tenor: here a simple 10 bps per year. Term funding lowers rollover risk and costs more.

### Margin calls

Collateral is marked daily. If the price falls, the cash lender has too little collateral for the cash lent, and calls for **margin**. **Call = cash lent - market value x (1 - haircut)**; a negative number is an excess to be returned. If the 10,000,000 of collateral falls to 9,500,000, the call is {{ex.margin_call.expected:,.0f}}, which the borrower meets by delivering more securities or returning cash.

### Why a Delta One desk cares

Funding a book of long stock hedges unsecured costs benchmark plus the desk's FTP spread. Funding it through repo costs less, but only on the cash received after the haircut, since the haircut portion still has to be funded unsecured. A third route is to receive financing through the swap itself, where the client pays benchmark plus spread. The comparison function prices the three: for 100,000,000 for 30 days, benchmark 4%, FTP 50 bps, an 8% haircut, repo spread 15 bps and swap spread 35 bps, the unsecured cost is {{ex.funding.expected.unsecured:,.0f}}, repo {{ex.funding.expected.repo:,.0f}} and swap {{ex.funding.expected.swap:,.0f}}.

### Tri-party and bilateral

A **bilateral** repo is settled between two parties directly. A **tri-party** repo uses an agent bank that selects, values and substitutes collateral under agreed rules. Tri-party lowers the operational burden and supports collateral eligibility schedules. Central clearing is available for some repo markets and reduces counterparty exposure, with margin and capital implications.

### Risks

**Rollover risk**: the repo cannot be renewed in a stress and funding must be found elsewhere. **Collateral value risk**: the price falls and margin calls drain liquidity. **Counterparty risk**: the other side fails while holding the collateral. **Operational risk**: wrong collateral delivered, missed calls. The funding and capital module returns to these in the context of liquidity buffers.

## Worked example

The desk finances 10,000,000 of large-cap stock hedges in repo for a week.

**Step 1: haircut and cash.** 8% haircut: cash received {{ex.cash.expected:,.0f}}.

**Step 2: rate.** Benchmark 4.0% plus 5 bps GC spread, call it 4.05%. The page takes the rate as input.

**Step 3: interest.** On {{ex.cash.expected:,.0f}}, at 4.5% for 7 days: {{ex.interest.expected:,.2f}}.

**Step 4: special.** If the stock is special with a 300 bps borrow fee, the special rate is {{ex.special.expected:.2%}}, and funding is cheaper than GC.

**Step 5: margin call.** The stock falls 5% to 9,500,000. The desk is called for {{ex.margin_call.expected:,.0f}}.

**Step 6: comparison.** Over 30 days on 100 million, unsecured costs {{ex.funding.expected.unsecured:,.0f}}, repo {{ex.funding.expected.repo:,.0f}}, the swap route {{ex.funding.expected.swap:,.0f}}.

**Step 7: decision.** The cheapest route depends on the haircut and the spreads; the desk picks it per book and keeps liquidity in mind.

## Desk reality

**Repo cash is liquidity, and margin calls drain it.** A book funded in repo needs a buffer for falling prices. The treasury team will ask for the stress calls.

**Special collateral earns more in lending than in repo, and vice versa.** The desk decides each day where the same security earns the most.

**Eligibility schedules matter.** A tri-party agent only accepts collateral on the schedule. A new security not on the list cannot be used, which creates a funding gap on the day it is bought.

**Day counts differ.** GBP repos use ACT/365, USD and EUR ACT/360. Interest breaks usually start there.
