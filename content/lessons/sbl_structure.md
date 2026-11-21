## Learn

Securities borrowing and lending (SBL) is the market that lets one holder of stock lend it, for a fee, to someone who needs it for a limited time. The most common reason to borrow is to **sell short**: you cannot deliver a share you do not own, so you borrow it, sell it and later buy it back and return it. For a Delta One desk the market matters twice. Every client short swap is hedged by a short sale, which needs borrow, and the desk can also lend out the long stock it holds as hedges for other clients' swaps. Borrow cost and availability therefore sit inside the price of every short and the economics of every long.

### The chain of participants

The chain has four typical links. **Beneficial owners**, such as pension funds, insurers and asset managers, hold the stock for the long term and lend it to earn extra yield. **Lending agents**, usually custodian banks, run the lending programs for those owners and keep a share of the revenue. **Borrowers' intermediaries**, such as prime brokers and bank desks like ours, borrow from agents and lend on to end borrowers. **End borrowers**, mostly hedge funds, market makers and the desk's own swap hedges, need the stock for shorts, hedging and settlement fails. Some trades are **peer to peer** through electronic platforms, but the intermediated chain still handles most volume.

### Types of loan and collateral

A loan is **open** (can be recalled or returned on demand, repriced daily) or **term** (fixed, usually at a fixed fee). The borrower gives **collateral**: **cash**, **non-cash** securities (government bonds, sometimes equities), or letters of credit. Collateral is worth more than the loan, an excess called the **margin** or **haircut**. The illustrative figures used here are 102% for a domestic loan and 105% for a cross-border loan: lending 10,000,000 of stock domestically needs {{ex.collateral.expected:,.0f}} of collateral, and cross-border needs {{ex.collateral_xb.expected:,.0f}}. The collateral is marked every day. Where cash is the collateral, the lender reinvests it and pays the borrower a **rebate**; where non-cash is the collateral, the borrower pays a **fee**. Loan economics are covered in the next module.

### Who pays and who earns

The beneficial owner earns most of the lending revenue and the agent takes a share for running the program. In the illustrative split the owner receives 80% and the agent 20%: on 100,000 of fee revenue the owner gets {{ex.split.expected.0:,.0f}} and the agent {{ex.split.expected.1:,.0f}}. The intermediary desk earns the **spread** between the fee it charges its client and the fee it pays upstream. The end borrower pays the full fee and is exposed to the risk that the loan is recalled.

### General collateral and specials

Most stocks are **general collateral (GC)**: plentiful supply, fees of a few tens of basis points. Some are **warm**, **special** or **hard to borrow**, with fees from hundreds to thousands of basis points because demand exceeds lendable supply. The illustrative tiers in `config/desk.yaml` are 30, 150, 600 and 3,000 bps. The tier of a name determines whether a short swap is profitable at all: a client paying 40 bps over the benchmark on a short in a stock costing 600 bps to borrow is losing the desk money.

### Supply, demand and utilisation

**Lendable supply** is the amount holders are willing to lend; **on loan** is the amount actually lent; **utilisation** is on loan divided by lendable supply. **Short interest** as a percentage of free float is a related measure. Fees rise slowly while utilisation is low and then accelerate as supply runs out. When supply is exhausted, borrowers are **locked out** and can only cover by buying the stock back.

### Locates and regulation

Many markets require a **locate**, a confirmation that stock can be borrowed, before a short sale. Rules differ by market: some require pre-borrow, some reporting of short positions, and some restrict shorting after sharp declines or in a crisis. The regulation page keeps the current items with dates, labelled illustrative and to be verified. The desk's controls must check locates before the short is sold, not after.

### Manufactured dividends

When a borrowed stock pays a dividend, the borrower no longer holds the shares but the lender is entitled to the dividend. The borrower pays the lender a **manufactured dividend**, the same amount, in lieu. For 50,000 shares and a gross dividend of 1.20 it is {{ex.manufactured.expected:,.0f}}. Manufactured dividends can have a different tax treatment from real ones, and their abuse was part of the dividend-arbitrage schemes taught in the case-study module as a compliance lesson.

### Rehypothecation and reuse

Intermediaries often **reuse** collateral and borrowed stock: the long stock in a client's margin account can be lent out, subject to the client's consent and regulatory limits. That is the engine behind internalisation, covered in its own module. The cost of reuse is the operational burden of recalls and the legal complexity of the chain.

### Documentation

Loans are governed by a master agreement. The **Global Master Securities Lending Agreement (GMSLA)** is common outside the US, and the **Master Securities Loan Agreement (MSLA)** inside it. They set collateral, marks, events of default and what happens on a recall. Each counterparty needs the right paper before the first loan, like swaps need an ISDA.

## Worked example

A hedge fund wants to short 100,000 shares of a stock priced at 50, through a swap with the desk. The desk must borrow the shares to hedge.

**Step 1: locate.** The desk checks availability. Lendable supply is 2,000,000 shares and 60% is on loan: utilisation is 60%, so the name is GC to warm.

**Step 2: borrow.** The desk borrows 100,000 shares through a lending agent from a pension fund. The loan is worth 5,000,000.

**Step 3: collateral.** Domestic loan at 102%: the desk posts 5,100,000 of cash collateral. If the loan were cross-border at 105% it would post 5,250,000.

**Step 4: the split.** If the loan earns a 30,000 fee over the year, the owner receives 24,000 and the agent 6,000 on an 80/20 split.

**Step 5: the hedge.** The desk sells the 100,000 shares in the market and the proceeds fund the cash collateral, which the lender reinvests.

**Step 6: dividend.** A 1.20 dividend goes ex while the loan is open. The desk pays the lender 120,000 as a manufactured dividend, and passes it on to the client in the swap's dividend leg.

**Step 7: return.** At the end of the swap the desk buys the stock back, returns it, and gets back its collateral. The chain closes.

## Desk reality

**Know the lender before you need the recall.** The beneficial owner can sell its stock at any time and the loan comes back. Concentrated lenders create recall risk, which the operations module treats in detail.

**Locates are a control, not a courtesy.** An untracked short with no locate is a regulatory breach. The booking checks and the daily break review both look for it.

**Fees move daily.** An open loan reprices as demand moves. A short swap booked at a fixed spread carries the risk that the borrow fee rises above it, which is why the validator warns when the spread is below the borrow cost.

**Paper first.** A borrow from a new lender without a signed agreement can usually be delayed but not avoided. Sort the documentation before the trade, not after the settlement fails.
