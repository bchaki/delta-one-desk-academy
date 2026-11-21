# Claude Code Prompt — Delta One Desk Academy (Streamlit)

Nov 21, 2026 · @Bittesh Chaki

## How to use this prompt

Save this spec as a file in your project and have Claude Code build it in phases. Don't paste it in as one message. This section is for you, not Claude Code. The prompt starts at Section 1.

1. Create an empty folder, run `git init`, and open Claude Code in it.
2. Save this file in the folder as `SPEC.md`. As a file, Claude Code can re-read it in every phase instead of losing it as the conversation grows.
3. Kick off with: *"Read SPEC.md end to end. Plan first: propose the file tree, page list, data models and the Phase 1 tasks. Don't write code until I approve."*
4. Then build one phase at a time (Section 8): *"Implement Phase N of SPEC.md. Run lint, tests and the page smoke test before stopping. Update docs/PROGRESS.md and commit when green."*
5. Start a fresh session between phases if the context gets long. Point Claude Code back to `SPEC.md`, `CLAUDE.md` and `docs/PROGRESS.md`.

Plan for several sessions. The full spec is about 45 pages, a tested analytics library and a large content bank. If you want a first version sooner, build Phases 0 to 3 first and add the rest later.

## 1. Role, mission and audience

You are a senior Python engineer who spent years as a Delta One trader and desk strat at a global investment bank. Build **Delta One Desk Academy**: a polished, multi-page Streamlit app. It should teach a new Trading Desk Assistant (AVP) what they need to know in their first 90 days on an equity Delta One (D1) desk.

**Audience.** A finance graduate, or someone with 2–5 years in markets (operations, product control, risk or another desk). They know what a stock, a future and a swap are. They don't yet know how a D1 desk prices, books, hedges, finances and risk-manages these products, or how the desk makes money.

**Outcome.** After working through the app, the user can:

- explain every product the desk trades, and price each one by hand and in code;
- book a trade correctly and spot booking errors before they cause breaks;
- produce and explain daily PnL, including finding the cause of unexplained PnL;
- read a risk report: delta, dividend, funding, borrow, basis and FX risk, VaR and stress;
- calculate margin and collateral calls under exchange, OTC (CSA/SIMM-style) and prime brokerage methods;
- explain stock borrow and lending economics end to end;
- describe each common D1 strategy, what drives its PnL and what can go wrong;
- handle a simulated desk day: RFQs, resets, dividends, recalls, margin calls, limit checks and PnL sign-off.

**Teaching approach.** Every module follows the same order: intuition → mechanics → formula → worked example with real numbers → interactive sandbox → "Desk reality" (what the TDA actually does, and with whom) → common pitfalls → self-check quiz. Users learn by doing, so every concept that involves a number gets a calculator or simulator.

**Scope.** Equity Delta One:

- cash equities and program trading;
- index futures and total return futures;
- equity swaps, TRS and CFDs;
- ETFs and ADRs;
- dividend derivatives and delta-one notes;
- repo, securities lending, financing and balance sheet.

Options appear only where they matter to D1. Examples: implied dividends and financing from put-call parity, and dividend exposure that exotics desks pass to D1. Out of scope: volatility trading, exotics pricing and fixed income desks.

## 2. Quality bar and guardrails

Get the numbers right first. A good-looking page with a wrong number is worse than no page.

- **Numbers come from tested code.** Every number comes from a function in `core/`, with unit tests checked against hand-worked values. Pages never hard-code results.
- **Offline and deterministic.** No external APIs or live data. Everything runs from a seeded synthetic market (Section 5). The same seed gives the same numbers on every page, so lesson text, quizzes and worked examples can refer to them.
- **No placeholders.** No lorem ipsum, "TODO", "coming soon" or empty tabs. If a feature isn't built yet, keep it out of the navigation.
- **Explicit conventions.** Every rate states its day count and compounding, and every amount its currency. Every spread states bps and its benchmark. Positive PnL means a gain to the desk. Every cash flow says whose side it's from: client or desk.
- **Label illustrative values.** These change over time and differ by bank: regulatory parameters, SIMM risk weights, exchange margin rates, contract specs, tax rates and haircuts. Keep them in `config/*.yaml`. Label them in the UI "Illustrative, verify against the official source", with an as-of date. Never present them as current official calibrations.
- **Real names, synthetic data.** Teaching text can use real product and index names (E-mini S&P 500, EURO STOXX 50 futures, SOFR). All prices, clients and stocks in the data are fictional, and must not resemble real firms.
- **Not tied to one bank.** Where practice differs between banks, say so and show the common variants. Examples: booking systems, sign conventions, PnL sign-off timing. Don't invent system names. Use generic labels such as "FO booking system", "risk engine" and "confirmation platform".
- **Teach misconduct as a compliance lesson.** Cover cases like cum-ex dividend fraud, spoofing, front-running, the 2008 VW squeeze and Archegos-style concentration as what went wrong and which controls catch it. Never present an illegal or abusive strategy as a playbook.
- **Disclaimer.** Put one in the footer and on Home: this is an educational tool, not investment, tax or legal advice, and conventions vary by firm.

**Current facts to use** (checked November 2026; show each in the app with its as-of date):

- US equities moved to T+1 settlement in May 2024. The EU, UK and Switzerland move to T+1 on 11 October 2027 ([FCA](https://www.fca.org.uk/markets/about-t1-settlement)).
- SEC Rule 10c-1a (securities lending reporting to FINRA's SLATE) has been delayed again. FINRA now shows implementation on 28 September 2028 ([FINRA SLATE](https://www.finra.org/filing-reporting/slate)). Flag it as "verify current status".
- Section 871(m) (US tax on dividend equivalents paid to non-US persons through derivatives) applies to delta-one transactions. IRS Notice 2026-61 extends transition relief for non-delta-one transactions through 2028 ([EY summary](https://taxnews.ey.com/news/2026-2025-irs-extends-transitional-relief-for-dividend-equivalents-under-irc-section-871m-through-2028)).
- Overnight benchmarks and day counts: SOFR (USD, ACT/360), €STR (EUR, ACT/360), SONIA (GBP, ACT/365F), TONA (JPY, ACT/365F), SARON (CHF, ACT/360). LIBOR has been discontinued, so mention it only as history.
- Streamlit 1.67 is the current release as of November 2026 ([release notes](https://docs.streamlit.io/develop/quick-reference/release-notes)).

## 3. Tech stack and project structure

Use Python 3.12+ and the current Streamlit, and keep a strict line between the analytics library and the pages.

**Stack**

- Streamlit (latest). Use the modern multipage API: `st.navigation` with grouped sections and `st.Page` objects with `icon` and `help` tooltips. Don't use the legacy `pages/` auto-discovery.
- Plotly for every chart, with one shared template. Use `st.graphviz_chart` with DOT strings for flow diagrams, org charts and lifecycle state machines.
- pandas, numpy and scipy (stats, optimisation, root-finding). pydantic v2 for trade and position models and config validation. PyYAML for content and config.
- pytest and hypothesis for tests. Streamlit's `AppTest` (`streamlit.testing.v1`) for page smoke tests. ruff for linting and formatting.
- `uv` with `pyproject.toml`, plus an exported `requirements.txt` for Streamlit Community Cloud.

**Streamlit patterns**

- `st.cache_data` for synthetic market generation and heavy analytics.
- `st.fragment` around each sandbox, so moving a slider doesn't rerun the whole page.
- `st.session_state` for global settings, progress and the Desk Simulator's state.
- `st.dataframe` with `column_config` (number formats, progress bars, sparklines) for blotters and reports.
- `st.data_editor` for editable trade tickets and scenario inputs.
- `st.download_button` for CSV and Excel export of every table and cheat sheet.

**Architecture rules**

- `core/` is pure Python with no Streamlit imports, fully typed. Every public function has a docstring stating its formula, units and conventions.
- Pages stay thin: read inputs, call `core`, render the results.
- Long-form teaching text lives in `content/` as Markdown and YAML, not in Python strings, so it can be edited without touching code.
- Create `CLAUDE.md` at the repo root holding these conventions. Keep `docs/PROGRESS.md` as a build log, updated at the end of every phase.

**File tree** (adjust names if needed, but keep this separation):

```
delta-one-academy/
  app.py                      # st.navigation, global sidebar, theme
  pyproject.toml  requirements.txt  README.md  CLAUDE.md
  .streamlit/config.toml
  config/                     # illustrative parameters, each with an as-of date
    conventions.yaml  contracts.yaml  margin.yaml  simm_illustrative.yaml
    withholding_tax.yaml  regulation.yaml  scenarios.yaml
  core/
    conventions.py            # day counts, calendars, roll rules, rounding
    rates.py                  # RFR compounding, curves, discount factors, FTP
    dividends.py              # schedules, PV, implied dividends, withholding tax
    corporate_actions.py
    indices.py                # level, divisor, rebalances, inclusion demand
    pricing/    forwards.py futures.py trf.py swaps.py etf.py adr.py
                dividend_derivs.py program_trading.py
    financing/  repo.py sbl.py internalisation.py balance_sheet.py xva_lite.py
    booking/    models.py lifecycle.py validation.py cashflows.py
    risk/       sensitivities.py var.py stress.py liquidity.py limits.py
    pnl/        explain.py attribution.py
    margin/     exchange.py simm_lite.py regt.py portfolio_margin.py pb_house.py csa.py
    strategies/ cash_carry.py roll.py dividend.py etf_arb.py index_events.py
                adr_arb.py pairs.py financing.py
    data/       universe.py market.py book.py scenarios.py
  ui/
    theme.py components.py charts.py formulas.py state.py quiz.py glossary.py
  pages/                      # one file per page; folder = nav section
    start/ foundations/ products/ sbl_repo/ pricing_booking/
    risk_pnl/ margin_capital/ strategies/ practice/
  content/
    lessons/<module>.md
    quizzes/<module>.yaml
    glossary.yaml  interview_questions.yaml  case_studies.yaml
  tests/
    core/...                  # unit and property tests per module
    test_pages_smoke.py       # AppTest: every page renders
  docs/PROGRESS.md
```

## 4. Design system and page template

The app should feel like a modern learning platform crossed with a trading terminal: calm, dense with real numbers, and consistent from page to page.

**Look and feel**

- Dark theme by default with a light option, set in `.streamlit/config.toml` plus a small CSS layer in `ui/theme.py`.
- One accent colour. Monospace for prices and figures, high-contrast numbers, generous whitespace.
- Chart palette must work for colour-blind users. Never use red and green alone to carry meaning: add signs, arrows or labels.

**Navigation and global controls**

- Sidebar sections match Section 7: Start Here, Market Foundations, Products, Stock Borrow & Lending, Pricing & Booking, Risk & PnL, Margin & Capital, Strategy Lab, Practice & Reference. Each page has an icon and a one-line `help` tooltip.
- Global sidebar controls that persist across pages: as-of date within the synthetic history, random seed, reporting currency (USD, EUR, GBP), a "Show the math" toggle, a Beginner/Advanced switch (Advanced reveals extra parameters and edge cases), and a progress ring.

**Page template.** Every module page uses the same building blocks from `ui/components.py`:

1. **Header:** title, one-line purpose, estimated time, difficulty (1–3), linked prerequisites and 3–5 learning objectives.
2. **Tabs:** Learn · Worked example · Sandbox · Desk reality · Check yourself. Pages may add tabs such as Lifecycle or Case study.
3. **Components:**
   - `concept_card(title, body)`.
   - `formula_box(latex, variables, substitution)`: renders the formula with `st.latex` and a legend of variables with units. When "Show the math" is on, it repeats the formula with the current numbers substituted step by step.
   - Callouts with distinct icons and colours: `desk_reality()`, `pitfall()`, `rule_of_thumb()`, `regulatory_note()`.
   - `metric_row()` (KPI tiles with changes), `pnl_waterfall()`, `cashflow_timeline()`, `term_sheet()` (two-column key/value card), `trade_ticket()`, `blotter()`.
   - `glossary_term("implied repo")`: an inline term with a definition tooltip that links to the Glossary page.
   - `quiz_block(module_id)`: loads YAML questions, supports multiple choice and numeric answers with a tolerance, shows explanations and records scores.
   - `mark_complete(module_id)` button at the bottom of each page.
4. **Footer:** related modules, glossary terms used on the page, disclaimer.

**Sandbox rules**

- Defaults should already show something interesting. For example, set the futures slightly rich so the arbitrage is visible straight away.
- Every sandbox has a "Reset to defaults" button and a short "What to try" list. Example: "Raise the dividend forecast by 5%. What happens to fair value, and to a long futures position's PnL?"
- Chart titles state the takeaway. Axes have units, and hover tooltips are on.
- Every table can be downloaded.
- Pages render in under 2 seconds after the first load. Layouts work at laptop width and still hold up on narrow screens.

**Progress.** Track completed modules, quiz scores and simulator results in session state. Let users export and import progress as a JSON file, so no database is needed. Home shows a progress dashboard.

## 5. Synthetic data and market simulator

Build one seeded generator in `core/data/` that creates a consistent world every page draws from. The numbers should look right to a practitioner.

**Universe** (`universe.py`)

- About 60 fictional stocks: 30 US, 20 Europe (DE, FR, NL, CH, ES, IT), 6 UK and 4 Japan, across 11 GICS-like sectors. Fictional names and tickers, for example "Halvorsen Industrial (HLVN)".
- Per stock: currency, exchange, price, shares outstanding, free-float factor, ADV (shares), daily vol, beta, sector and dividend policy (frequency, yield, ex-date pattern).
- Also per stock: borrow tier (GC, warm, special, hard-to-borrow) with fee, utilisation, short interest as % of float, and lendable supply. Five non-US names get ADRs with a ratio.
- Two fictional indices built from constituents, free-float cap-weighted with a capping rule: "D1 US 30" and "D1 Europe 20", each with a divisor history.
- One ETF per index with creation unit size, creation fee, holdings file and cash component.

**Market history** (`market.py`): three years of business days.

- Equity prices from a factor model: market + sector + idiosyncratic. Use fat tails (Student-t shocks), volatility clustering (simple GARCH), earnings jumps and 2–3 stress episodes. Same-sector correlations around 0.5–0.7.
- Dividends paid on schedule, with occasional specials and cuts. Include one European dividend cancellation episode, modelled on 2020.
- Corporate actions: at least one split, one rights issue, one spin-off, one cash merger and one index add/delete.
- Daily SOFR, €STR, SONIA and TONA paths with a few policy moves, plus simple term curves. A desk funding spread over each benchmark (FTP) and a balance-sheet cost parameter.
- FX: EURUSD, GBPUSD and USDJPY with realistic vol and a daily 4pm-style fixing.
- Index futures for both indices: quarterly expiries (Mar/Jun/Sep/Dec, third Friday). Price = fair value from the core pricer plus a mean-reverting rich/cheap deviation, with roll-week behaviour and calendar spreads.
- Total return futures quoted as a spread. Dividend futures on the Europe index with annual expiries five years out.
- Borrow fee time series. Specials spike around corporate events and squeezes, and recalls cluster around AGMs and record dates.

**Desk book** (`book.py`): a realistic, internally consistent book on the as-of date.

- 15 fictional clients with tiers, CSA terms and margin method: hedge funds, asset managers, a pension fund, an insurer and an internal structured products desk.
- About 120 live positions:
  - client equity swaps (long and short; single-name, basket, index and portfolio swaps);
  - the desk's physical and futures hedges, and ETF inventory;
  - SBL borrows and loans, and repo financing;
  - dividend futures and swaps, and a few ADR arbitrage pairs.
- Full trade history with lifecycle events, so the PnL explain between any two dates reconciles to the cent.
- Seeded breaks for the user to find: a missed dividend, a wrong reset fixing, a trade booked at the wrong spread, a counterparty mapped to the wrong legal entity, and a stale price.

**Scenarios** (`scenarios.py`): define these in `config/scenarios.yaml` as factor moves.

- Historical-style: a 1987-type crash, 2008, March 2020 (including dividend cancellations), the 2022 rates shock, and a single-name short squeeze.
- Hypothetical: user-defined shocks.

Key and cache everything on `(seed, as_of_date)`. A Data Explorer page (Section 7I) lets users browse the whole world.

## 6. Core analytics library: conventions and formulas

Implement all of the following in `core/`, with tests. Notation: S spot, F futures or forward price, r funding rate, q dividend yield, D dividend, DF discount factor, b borrow fee, N notional, τ year fraction under the stated day count. Where a formula here is simplified, the docstring must say so and what the full version adds.

**Conventions and rates**

- Year fractions: ACT/360, ACT/365F, 30/360, ACT/ACT. Business-day calendars for US, TARGET, UK and Japan (hard-coded holidays for the synthetic years are fine). Roll rules: following, modified following, preceding.
- Compounding an overnight rate in arrears, with lookback and observation-shift options, compared with simple interest:

```latex
R_{comp} = \left[\prod_{i=1}^{n}\left(1 + \frac{r_i \, d_i}{\text{basis}}\right) - 1\right] \times \frac{\text{basis}}{d}
```

**Forwards and futures**

- Discrete-dividend forward, plus the continuous version `F = S × e^((r − q)T)`:

```latex
F = \frac{S - \sum_i D_i \, DF(t_i)}{DF(T)}
```

- Basis `F − S`; fair basis `FV − S`; rich/cheap `F − FV`, in index points and as annualised bps of financing.
- Implied repo (implied financing rate): solve for the r that makes the model price equal the market price. Simple version: `r_impl = ((F + FV(divs)) / S − 1) × basis / days`.
- No-arbitrage band. The upper bound uses the desk's long funding rate plus costs. The lower bound uses the short-side rate (cash rebate = r − b) minus costs. Costs: commissions, basket and futures bid/ask, market impact, and stamp duty or FTT where it applies.
- Calendar spread fair value, and roll cost in bps per year of exposure.
- Total return futures: convert between the TRF spread (bps over the overnight benchmark) and an equivalent price basis. Show the link to equity swap financing spreads.
- Implied forward and dividends from put-call parity: `C − P = DF(T) × (F − K)`.

**Equity swaps / TRS**

- Equity leg per period: `N(t−1) × (S(t) / S(t−1) − 1)`, plus dividends × pass-through %. Make pass-through configurable, e.g. 100% gross, 85% or 70% net.
- Funding leg per period: `N(t−1) × (compounded benchmark + spread) × τ`. A long client pays funding. A short client receives benchmark minus spread, where the spread includes borrow cost.
- Notional reset vs fixed notional, reset schedules, early termination, partial unwinds and corporate action adjustments.
- Mark-to-market between resets, accrued funding, and a generated cashflow schedule.
- Desk hedge economics. Client long swap: the desk buys the stock and funds it. Client short swap: the desk borrows and sells the stock, earns the rebate and pays the fee.
- Spread build-up: `client spread = funding over benchmark (FTP) + balance-sheet charge + capital charge + borrow cost (shorts) + XVA (simplified) + margin`. Each component is its own function with documented inputs.

**ETFs and ADRs**

- NAV and iNAV from holdings plus cash; premium/discount. Arbitrage exists when `|premium| > creation/redemption fee + basket costs + ETF bid/ask`.
- ADR parity: `ADR fair value = local price × ratio × FX`, adjusted for depositary and conversion fees, with an arbitrage band.

**Indices and program trading**

- Index level: `Σ(P_i × shares_i × free float_i × cap factor_i) / divisor`. Divisor adjustments keep the level unchanged through corporate actions and rebalances.
- Index inclusion demand: `shares to trade = tracked AUM × new weight / price`, expressed as days of ADV, with expected price impact.
- Square-root market impact: `impact (bps) = k × σ_daily × sqrt(Q / ADV) × 10,000`.
- Principal risk bid = half-spread + impact + risk charge (vol × sqrt(liquidation horizon) × risk aversion). Document it as a teaching model.

**Securities financing**

- SBL collateral = loan value × margin (e.g. 102% domestic, 105% cross-border; illustrative).
- SBL accruals: fee = `loan value × fee × days / basis`. Cash rebate = `cash collateral × rebate rate × days / basis`, where `rebate rate = reinvestment rate − fee`.
- SBL also needs: lender and agent revenue split (configurable, e.g. 80/20), daily collateral marks, manufactured dividends, and recall and buy-in costs.
- Repo: cash = market value × (1 − haircut); repo interest; GC vs special; term vs open.
- Internalisation: net client longs and shorts and desk inventory across the book before borrowing externally, and compute the savings.
- Balance sheet: leverage exposure, RWA (a simple standardised approach for teaching), and return on capital per trade or client.

**Risk**

- Cash delta and beta-adjusted delta by underlying, sector, country and currency. FX delta.
- Funding sensitivity (PV change per 1 bp on each benchmark curve). Dividend sensitivity (per 1% change in forecast dividends). Borrow sensitivity. Basis sensitivity (futures rich/cheap).
- Liquidity (days to liquidate at x% of ADV) and concentration metrics.
- VaR: historical simulation (1-day and 10-day, 95% and 99%), parametric (delta-normal) and Monte Carlo. Expected Shortfall at 97.5%. Component and marginal VaR. Backtesting with exception counts and a Basel-style traffic light.
- Stress: apply scenario factor moves to the book and report by sub-book.

**PnL explain.** Decompose daily PnL and reconcile it to the cent:

```latex
\text{Total} = \text{New trades} + \text{Amendments} + \text{Delta} + \text{Carry} + \text{Dividends} + \text{Borrow/lending} + \text{Basis} + \text{FX} + \text{Fees} + \text{Unexplained}
```

Produce both a risk-based explain (sensitivities × market moves) and a full-revaluation explain, and show the difference.

**Margin**

- Exchange margin (SPAN-like teaching model): scenario scan per product, worst loss, spread credits between correlated indices, calendar spread charges. Note that exchanges are moving to VaR-style models, and add a simple historical-VaR alternative.
- Variation margin: daily settlement of futures gains and losses.
- OTC initial margin: schedule-based (notional × % grid) vs SIMM-style equity delta. Weighted sensitivity `WS_k = RW_k × s_k`, aggregated within a bucket as below, then across buckets with γ. Take parameters from `config/simm_illustrative.yaml` and label them clearly.

```latex
K_b = \sqrt{\sum_k WS_k^2 + \sum_k \sum_{l \neq k} \rho_{kl} \, WS_k \, WS_l}
```

- CSA mechanics: threshold, minimum transfer amount, independent amount, rounding, eligible collateral and haircuts, giving the collateral call amount.
- US broker margin: Reg T (50% initial; 25% maintenance for longs under FINRA rules; short-sale margin) vs portfolio margin (worst loss across a price grid, wider for single names than broad indices).
- Prime brokerage house margin: a base rate by liquidity and vol, plus add-ons for concentration, liquidity (position / ADV), directionality and squeeze risk.

## 7A. Pages: Start Here

Three pages that orient the user: what the app is, how a D1 desk works, and what the TDA job involves.

**Home**

- Hero: what the app is and who it's for. A 30-second "What is Delta One?" explainer: linear exposure, delta ≈ 1, no optionality. The desk sells access, financing and liquidity.
- Suggested 4-week learning path with links and completion status:
  - Week 1: foundations and products.
  - Week 2: SBL, financing, pricing and booking.
  - Week 3: risk, PnL and margin.
  - Week 4: strategies, the simulator and interview prep.
- Progress dashboard: modules done, quiz averages by section, weakest topics, best simulator score, and progress export/import.
- "Desk at a glance" from the synthetic book: today's PnL, net delta, top 5 exposures and financing balance. The user sees what the desk looks like on day one.

**Inside a Delta One Desk**

- What D1 means and why the desk exists: client facilitation (synthetic access, financing, liquidity), inventory and internalisation. The desk is the bank's equity financing engine.
- Desk structure: sub-desks (index and futures, ETF, swaps and synthetics, financing and SBL, dividends, program trading) and how they share risk.
- Stakeholder map (graphviz). Teams: traders, TDAs, sales, structuring, prime brokerage, strats/quants, market risk, product control, middle office, operations, treasury, collateral management, compliance, tax and legal. For each team, show what it needs from the TDA and what the TDA needs from it.
- Client types and what each wants:
  - hedge funds: leverage, shorts, synthetic prime;
  - asset managers: index exposure, transition management;
  - pension funds and insurers: efficient beta, securities lending revenue;
  - corporates: buybacks and stake building, with disclosure rules;
  - internal desks: structured products passing on dividend and delta risk.
- How the desk makes money: financing spread, bid/offer, inventory carry, borrow and lending fees, dividend positioning, basis and arbitrage, internalisation. Show an interactive revenue-mix chart from the simulated year, linking to the PnL Generation page.
- Trade lifecycle swimlane: RFQ → quote → execution → booking → hedge → confirmation → settlement → resets and dividends → termination. Show which team owns each step.

**The TDA Playbook**

- The role: PnL production and explain, risk reports, booking checks and break resolution, managing resets, dividends and corporate actions, pricing support, client queries, tool maintenance and automation.
- Day in the life: an interactive hour-by-hour timeline with a London or New York toggle.
  - Morning: pre-open checks, overnight breaks, flash PnL, index rebalance notices, resets due, today's ex-dates.
  - Intraday: borrow recalls, margin calls, client RFQs.
  - Close and after: auctions, EOD marks, risk run, PnL sign-off.
- Daily, weekly, monthly and quarterly checklists as interactive checklists, with state saved in the session.
- A 30/60/90-day plan, questions to ask in week one, and the (generic) systems to get access to.
- Soft skills: when and to whom to escalate, talking to traders under time pressure, and writing a clear PnL commentary, with good and bad examples.

## 7B. Pages: Market Foundations

Four pages on the inputs behind every D1 price: rates, dividends, corporate actions and indices.

**Rates, funding and financing**

- Money market basics. Overnight benchmarks and their conventions (a table from config). Secured vs unsecured funding, and repo rates vs the benchmark.
- The bank's funds transfer pricing (FTP) curve, and why it feeds every D1 price.
- Sandbox: compound SOFR, €STR or SONIA over any period of the synthetic history, with lookback and shift options. Compare simple vs compounded interest. Build a discount curve and inspect the discount factors.
- Desk reality: where the desk's funding rate comes from (treasury), and how funding costs show up in PnL every day.

**Dividends**

- Key dates (declaration, ex, record, pay). Gross vs net. Withholding tax by market and treaty rate (illustrative table). Special dividends, scrip, DRIPs and manufactured dividends.
- Index dividend points. Forecasting dividends: analyst forecasts vs market-implied. Implied dividends from futures and from options.
- Dividend risk: who is long and who is short dividends. Structured products desks are typically long through hedging autocallables, and D1 often takes the other side.
- Case study: the 2020 European dividend cancellations.
- Sandboxes:
  - dividend calendar for an index, as a heatmap by month;
  - index dividend points calculator;
  - change one stock's dividend and see the effect on futures fair value, a swap's cash flows and the desk's dividend risk;
  - withholding tax and pass-through calculator.

**Corporate actions**

- Event types: splits, reverse splits, rights issues, spin-offs, cash and stock mergers, tender offers, special dividends, name and ticker changes. Mandatory vs voluntary vs mandatory with choice.
- Effects on positions, on swaps (notional and price adjustments), on futures (exchange adjustments), on index divisors, and on borrows (recalls around votes and elections).
- Sandbox: apply each event type to a position, a swap and the index. Show quantities, prices, notional and divisor before and after. PnL stays flat when the event is processed correctly. Show the PnL break when it isn't.
- Desk reality: CA notices, election deadlines, who decides elections on hedges, and common breaks.

**Equity indices**

- Construction methods: price-weighted, cap-weighted, free-float, capped and equal-weight. Price vs total return vs net total return indices.
- Divisor mechanics, quarterly and annual reviews, adds and deletes, fast entries, and the timeline from announcement to effective date.
- Sandbox 1: build a mini index from 10 stocks. Pick a weighting scheme and caps, run it through a rebalance and a corporate action, and watch the divisor.
- Sandbox 2: inclusion demand calculator. Tracked AUM × weight gives shares to buy, days of ADV and expected impact.
- Desk reality: index event days at the close, facilitating index funds, and risk around closing auctions.

## 7C. Pages: Products

Six pages, one per product family. The equity swap page is the centrepiece and gets the most depth.

**Cash equities and program trading**

- Agency vs principal. Program (portfolio) trades and transition management. Benchmarks: VWAP, TWAP, implementation shortfall and the close. Risk bids vs agency execution. Closing auctions.
- Sandbox: price a principal risk bid on a basket from per-name impact (square-root model), spread and a risk charge. Chart sensitivity to basket size, liquidity and vol, and show the expected PnL distribution if the desk wins the trade.
- Pitfalls: information leakage, illiquid tails, sector concentration.

**Index futures and total return futures**

- Contract anatomy: a table of illustrative specs for E-mini S&P 500, EURO STOXX 50, DAX, FTSE 100, Nikkei 225 and the two synthetic indices. Columns: multiplier, tick, expiry cycle, last trading day, final settlement method and trading hours.
- Fair value, basis and convergence. Implied repo, rich/cheap, the roll and calendar spreads, roll week. Exchange margin and daily variation margin.
- Total return futures: what they are, and why they exist (trading financing on exchange, more capital-efficient than bilateral swaps). How the TRF spread relates to swap spreads.
- Sandboxes:
  - fair value calculator with discrete dividends and "Show the math";
  - basis convergence chart to expiry;
  - implied repo solver from a market price;
  - roll cost calculator;
  - a link to the futures vs swap vs ETF comparison in 7E.

**Equity swaps, TRS and CFDs**

- Structure: an equity (performance) leg and a funding leg. Single-name, basket, index and portfolio swaps. Funded vs unfunded. CFDs vs swaps. Synthetic prime brokerage.
- Terms: notional, initial price, spread, benchmark, reset frequency, dividend and CA treatment, termination rights, ISDA/CSA, and 871(m) for US underlyings traded with non-US clients.
- Lifecycle tab: trade → reset → dividend → CA → partial unwind → termination, as a graphviz state machine. Selecting a state shows its cash flows and booking events.
- **Centrepiece sandbox: swap lifecycle simulator.**
  - Inputs: underlying, direction, notional, spread, reset frequency, dividend pass-through, notional reset or fixed.
  - It runs the trade along the synthetic price path.
  - Outputs: full cashflow schedule, MTM, accruals, client PnL vs desk PnL including the hedge (stock + funding, or borrow + rebate), and a PnL attribution chart.
- Desk reality: reset-day workflow, reset breaks, client statements, negotiating swap spreads.

**ETFs**

- Structure: physical vs synthetic replication. Primary market (creation and redemption through authorised participants, in-kind or cash) vs secondary market. NAV vs iNAV, premium/discount, creation fees, ETF lending, ETFs as hedges.
- Sandbox: ETF arbitrage simulator. An intraday path of basket and ETF prices, with costs and create/redeem decisions, and the resulting PnL. Show how arbitrage keeps the ETF near NAV, and how the premium or discount widens in stress when the underlying is illiquid.
- Desk reality: create/redeem cut-off times, holdings files, the ETF as a liquidity tool.

**ADRs, GDRs and cross-listings**

- Ratios, depositary banks, fees, conversion process and timing, FX. Dual-listed companies.
- Sandbox: ADR parity calculator with an arbitrage band. Simulated intraday ADR vs local price with FX, and the decision of whether converting is worth the cost.

**Dividend derivatives and delta-one notes**

- Dividend futures and dividend swaps (index and single stock): pricing vs forecasts, term structure, who trades them and why.
- Delta-one notes, certificates and trackers: structure, issuer credit, fees, and how the D1 desk hedges issuance.
- Sandbox: dividend futures curve vs analyst forecast curve, implied vs realised, and the PnL of a dividend swap through a cancellation scenario.

## 7D. Pages: Stock Borrow & Lending and Repo

This is a priority section: give it the same depth as Products, across four to five pages.

**SBL market structure**

- Participants and flows (graphviz): beneficial owners (pension funds, mutual funds, insurers) → agent lenders → prime brokers and D1 desks → hedge funds and market makers. Also triparty agents and centrally cleared lending platforms.
- Why people borrow: covering client and desk shorts, hedging short swaps, avoiding settlement fails, market making, financing and collateral upgrades.
- Legal framework: GMSLA (international) and MSLA (US), title transfer, recall rights, manufactured dividends, voting rights.

**Loan economics**

- Cash vs non-cash collateral. Fee vs rebate. Margin (102%/105%, illustrative). Daily mark-to-market and collateral moves. Term vs open loans.
- Fee tiers: GC, warm, special and hard-to-borrow. Negative rebates.
- Indicators: utilisation, days to cover, short interest, lendable supply and on-loan value. How fees respond, shown as a stylised supply/demand curve.
- Sandboxes:
  1. Loan calculator. Inputs: shares, price, fee, collateral type, reinvestment rate. Outputs: daily fee and rebate accruals, collateral moves along a price path, and the lender/agent revenue split.
  2. All-in cost of a short: price PnL, borrow fee, manufactured dividends and rebate. Chart the cost drag over time for a GC name vs a special.
  3. Utilisation vs fee curve with a squeeze shock (lenders recall supply, demand spikes) and its effect on a short swap's economics.

**Operations and risk**

- Locates and pre-borrows. US Reg SHO: locate requirement, close-out of fails, threshold securities, short-sale price test. EU Short Selling Regulation: net short position disclosure (thresholds from config). Naked shorting.
- Recalls and buy-ins: why they happen (lender sells, votes, record dates), timeline and cost. EU CSDR settlement discipline and penalties.
- Sandbox 1: recall simulator. A recall hits a hard-to-borrow name. The user chooses: re-borrow at a higher fee, buy in, or cover through internalisation, and sees the cost of each.
- Sandbox 2: locate workflow game. A queue of client locate requests against available inventory. Approve, partly fill or reject, and watch utilisation and revenue change.

**Internalisation and the financing book**

- Cover shorts from client longs (within rehypothecation limits), desk inventory and swap hedges before borrowing externally. The "box".
- Sandbox: internalisation optimiser over the synthetic book. Per name: net long/short across clients and desk, internal coverage vs street borrow, and savings in bps and dollars.

**Repo and equity financing**

- Equity repo and reverse repo. GC vs special. Haircuts by asset quality. Triparty. Term vs overnight. Repo as funding for long inventory. Collateral upgrade trades.
- Sandbox: repo calculator (cash lent, haircut, interest, term). Plus a "fund the long book" comparison: unsecured FTP vs repo vs swap-funded.

**Case studies**

- A short squeeze: a fictionalised composite of the 2008 VW and 2021 meme-stock dynamics.
- Cum-ex and cum-cum dividend trades as a compliance case: what happened, why it was illegal or abusive, and which controls exist now.

## 7E. Pages: Pricing & Booking

Four pages on turning a client request into a correct price and a correct booking.

**Pricing Lab: build a client quote**

- Scenario: a client RFQ arrives. Examples: "$50m long swap on D1 US 30, 12 months, monthly resets" or "short 2m shares of HLVN via swap".
- The user builds the price step by step: funding (FTP over the benchmark), borrow for shorts, balance-sheet and capital charges, simplified XVA, hedge execution costs and target margin.
- Output: the quoted spread with a waterfall chart of its components, compared with the financing rate implied by the futures market.
- Advanced mode: client tier, CSA terms and netting set change the capital and XVA charges. Show the break-even spread.

**Cost of exposure: futures vs swap vs ETF**

- The classic D1 sales analysis: the all-in cost of holding index exposure over a chosen horizon through each route.
  - Futures: roll cost, rich/cheap, funding the margin.
  - TRS: spread, dividend pass-through, withholding tax.
  - ETF: expense ratio, bid/ask, lending revenue, tax drag.
- Output: a breakdown table and a cost-vs-horizon chart, with sensitivity to roll richness and swap spread.

**Trade booking and lifecycle**

- Trade capture: every field on an equity swap ticket and a futures ticket, what it means, and what goes wrong when it's wrong. Fields: trade and effective dates, quantity, initial price, notional, currency, benchmark, spread, day count, reset schedule, dividend %, CA terms, counterparty legal entity, book, sales credit, ISDA/CSA reference, 871(m) flag.
- Front-to-back flow (graphviz): FO booking → risk engine → middle office validation → electronic confirmation → operations settlement → finance and product control, with reconciliations at each step.
- Sandboxes:
  1. Trade ticket: an `st.form` ticket with validation rules (business days, spread range, missing CSA, entity mismatch). It books into a session blotter and generates cash flows.
  2. Spot the booking error: a term sheet next to a booked ticket containing 1–3 seeded errors. The user picks the errors, then sees a score and the PnL impact of each one.
  3. Lifecycle processor: pick a booked trade, apply events (reset, dividend, CA, partial unwind, termination), and watch the blotter update.
- Settlement: cycles by market (US T+1; EU and UK T+2 until 11 October 2027), fails, CSDR penalties, SSIs. What T+1 changes in a TDA's day.

**Market data, marks and end of day**

- Closing prices and auctions, stale or suspended prices, FX fixings, futures settlement prices, and dividend forecasts as a marked input.
- Independent price verification by product control. Fair value adjustments and reserves (bid/offer, concentration).
- Sandbox: an EOD marking checklist with a seeded stale price and a wrong FX fixing. The user has to find both before sign-off.

## 7F. Pages: Risk & PnL

Four pages on the reports a TDA produces and explains every day.

**Risk sensitivities**

- Delta (cash and beta-adjusted), FX delta, funding sensitivity per curve, dividend sensitivity, borrow sensitivity, basis risk, hedge correlation (index future vs basket), jump and event risk, concentration and liquidity.
- Interactive risk report on the synthetic book:
  - aggregate by underlying, sector, country, currency, client or sub-book, and drill down to trades with pivot-style controls;
  - maturity ladders for funding and dividend risk, and heatmaps;
  - filters that answer questions like "What's my net delta to Europe after futures hedges?"
- Hedge calculator: for a residual basket exposure, compute the futures hedge ratio (beta or minimum variance) and the tracking error.

**PnL explain and attribution**

- Concepts: clean vs dirty PnL, realised vs unrealised, flash vs final, day-one PnL on new trades, sales credits, reserves.
- Daily PnL explain waterfall for the book between any two dates. Drill down by sub-book and trade. Compare risk-based and full-revaluation explains, and flag unexplained PnL above a threshold.
- "Investigate the unexplained": the seeded breaks create unexplained PnL. The user follows clues (positions, prices, events, bookings) to find the cause, and gets a score.
- Commentary writer: the user drafts the day's PnL commentary, then sees a model commentary for the same day.

**VaR, Expected Shortfall and stress testing**

- Historical, parametric and Monte Carlo VaR side by side, with confidence and horizon controls. Square-root-of-time scaling and its limits. ES at 97.5%, component VaR, stressed VaR. Backtesting with a traffic light.
- Stress testing with predefined and custom scenarios. Sliders shock equities by region, vol, rates, FX, dividends and borrow fees. Results by sub-book.
- Reverse stress: "What move loses $X?"

**Limits, controls and conduct**

- Limit framework: delta, VaR, stress, single-name concentration, liquidity, balance sheet and gross notional.
- Limit utilisation dashboard on the synthetic book, with a seeded breach and the escalation workflow.
- Conduct and regulation for a D1 TDA, each topic with a short scenario quiz: MNPI and information barriers, front-running client orders, best execution, wash trades, spoofing and layering, short-selling rules, disclosure thresholds, US Volcker rule (market making vs proprietary trading), trade surveillance.

## 7G. Pages: Margin, Financing & Balance Sheet

Three pages that explain why financing, margin and balance sheet drive D1 pricing as much as market risk does.

**Margin calculator suite** (one page, six tabs)

1. **Exchange margin:** a futures portfolio across indices and expiries. SPAN-like scan with spread credits, compared with a VaR-style margin. Show how a calendar spread or cross-index hedge cuts margin.
2. **Variation margin:** daily futures settlement along a price path, cumulative cash, and the funding cost of margin.
3. **OTC initial margin:** schedule-based vs SIMM-style equity delta (illustrative parameters), and the netting benefit.
4. **CSA collateral calls:** an exposure path with threshold, MTA, independent amount, rounding and haircuts. Output call and return amounts, and a dispute example.
5. **Reg T vs portfolio margin vs PB house margin** for the same long/short book, and the leverage each allows.
6. **PB house margin add-ons:** concentration, liquidity, directionality and squeeze risk. Show how a concentrated book can look safe under simple margin but not once add-ons apply (the Archegos lesson).

**Funding, balance sheet and capital**

- Why balance sheet is scarce: leverage ratio exposure, RWA basics, NSFR intuition, netting.
- Synthetic (swap) vs physical (margin loan) financing, and their different balance sheet footprints.
- Sandbox: client profitability and return-on-capital calculator. Revenue from spread and fees vs funding, balance sheet and capital costs. Compare a swap with a margin loan for the same client exposure.

**Counterparty risk and XVA basics**

- In plain words: expected exposure (EE), potential future exposure (PFE), CVA, FVA, MVA and KVA, and why each enters swap pricing.
- Sandbox: the PFE profile of a TRS over its life, with and without a CSA.

## 7H. Pages: Strategy Lab

Ten strategy pages plus a PnL Generation capstone. Every strategy page uses the same layout:

1. Thesis.
2. Trade legs, as a diagram.
3. PnL drivers, as a formula.
4. Required inputs.
5. Backtest or simulation on synthetic data, with parameter controls.
6. PnL decomposition chart.
7. Risks and failure modes, each with a button that triggers that scenario.
8. Desk reality: who runs it, capital and balance sheet use, limits.
9. Quiz.

**Strategies**

1. **Index arbitrage (cash-and-carry and reverse).** Trade when futures leave the no-arbitrage band. Include costs, financing, dividend risk and execution slippage. Intraday simulation with entry/exit rules, and PnL vs band width.
2. **Futures roll and calendar spreads.** Trading the roll, the financing implied in the spread, roll-week dynamics and open interest migration.
3. **Financing and basis trades.** Swap vs futures vs TRF, earning the financing spread, balance sheet optimisation, sensitivity to funding costs.
4. **Dividend trading.** Dividend futures vs forecasts, dividend swaps, hedging structured products' dividend exposure, and the cancellation stress.
5. **ETF arbitrage and create/redeem.** Capturing premium/discount, and liquidity in stress.
6. **Index rebalance and event trading.** Forecasting adds and deletes, pre-positioning, facilitating index fund flows at the close, and the risk of crowded trades.
7. **ADR and cross-listing arbitrage.** Parity trading with FX and conversion costs.
8. **Pairs and stat arb.** Cointegration test, z-score entry and exit, half-life. Explain why it's less central to a flow D1 desk but comes up in client conversations.
9. **Securities lending strategies.** Specials, optimising lending revenue, managing recalls, collateral upgrades.
10. **Client flow and inventory management.** Internalisation, axes, risk vs agency, and how flow turns into PnL.

**PnL Generation deep dive** (the section's capstone)

- A simulated year of desk PnL from the synthetic book.
- Revenue by source (financing spread, bid/offer, borrow and lending, dividends, basis and arbitrage, internalisation), by client tier and by sub-book.
- Budget vs actual. Funding, balance sheet and capital costs, to show net contribution.
- How traders think about "client revenue" vs "risk revenue".

## 7I. Pages: Practice & Reference

Seven pages for practice and lookup. Build the Desk Simulator last, because it draws on every other module.

**Desk Simulator: "A day on the desk"**

A session-state machine that walks through a full trading day of timed events. Randomise it from the seed so each run differs.

| Time | Event | What the user does |
| --- | --- | --- |
| 07:00 | Overnight PnL explain with a seeded break | Find the break |
| 08:00 | Corporate action and dividend checks; resets due | Process them |
| 09:00 | Client RFQ for a swap | Build and submit a quote; win or lose against a hidden market level |
| 11:00 | Index rebalance announcement | Estimate demand and decide whether to pre-hedge |
| 13:00 | Recall on a hard-to-borrow name hedging a client short | Choose re-borrow, buy-in or internalise |
| 15:00 | Counterparty margin call with a disputed amount | Check the call and respond |
| 16:30 | Futures rich into the close | Decide on the arbitrage |
| 17:30 | Risk run shows a limit breach | Choose how to escalate |
| 18:00 | PnL sign-off | Write the commentary |

Score accuracy, PnL, risk discipline and escalation. End with a debrief: what an experienced TDA would have done, with links to the relevant modules.

**Quiz centre and interview prep**

- Question bank: at least 15 questions per module, tagged by module and difficulty. Types: multiple choice, numeric with tolerance, and spot-the-error. Every question has an explanation.
- Modes: by module, mixed review, timed mock test, and spaced repetition of missed questions.
- Interview prep: 60+ D1 TDA interview questions (technical, pricing brain-teasers, behavioural) with model answers and follow-ups.

**Glossary.** 250+ terms, searchable and filterable by category. Each has a definition, a formula where relevant, a one-line worked example and links to modules.

**Formula sheet and calculator hub.** Every formula in the app on one page, grouped and rendered with `st.latex`, and every calculator reachable from one place. Downloadable as Markdown or PDF.

**Market conventions and regulation reference**

- Conventions by market: settlement cycle, trading hours, auctions, tick regimes, stamp duty/FTT, dividend withholding tax (illustrative), benchmark rate and day count.
- Regulation tracker. Rules: Reg SHO, EU SSR, MiFID II/MiFIR, EMIR, Dodd-Frank, SFTR, SEC 10c-1a, UMR, Volcker, Basel III/FRTB, CSDR, T+1 and 871(m).
- For each rule: what it means for a D1 desk and its key dates, taken from `config/regulation.yaml` with as-of dates and "verify" flags.

**Automation corner.** TDAs automate a lot. Provide 10 short, runnable Python snippets that use the app's `core` library on the synthetic data, each with a download button:

- daily PnL explain report;
- dividend ex-date checker;
- reset schedule report;
- borrow cost report;
- limit utilisation summary;
- futures fair value monitor;
- SBL recall impact;
- reconciliation of two position files;
- corporate action impact check;
- margin call checker.

**Data explorer.** Browse the synthetic universe, market history, book and trade history, with filters and downloads, so users can run their own analysis.

## 8. Build plan, testing and verification

Build in phases. At the end of every phase, run ruff, the full test suite and the page smoke test, fix everything, update `docs/PROGRESS.md` and commit. Never start a phase with failing tests.

**Phases**

1. **Phase 0: plan.** Read the whole spec. Propose the final file tree, page list with nav sections, pydantic data models and test plan. Wait for approval.
2. **Phase 1: core and data.** Conventions, rates, dividends, pricing (forwards, futures, swaps, ETF, ADR), SBL, repo, basic risk, PnL explain and margin. Then the synthetic universe, market and book. Write unit tests against hand-calculated values for every formula, with the hand calculation in the test docstring.
3. **Phase 2: UI framework.** Theme, components, a navigation shell with every section (only built pages visible), global sidebar, progress tracking, glossary and quiz engines, content loading. Build Home plus one complete reference module (Index futures) end to end. Pause for a look-and-feel review.
4. **Phase 3:** Start Here, Market Foundations and Products (7A–7C).
5. **Phase 4:** Stock Borrow & Lending and Repo, Pricing & Booking (7D–7E).
6. **Phase 5:** Risk & PnL, Margin & Capital (7F–7G).
7. **Phase 6:** Strategy Lab (7H).
8. **Phase 7:** Practice & Reference (7I), with the Desk Simulator last.
9. **Phase 8: polish and QA.** Consistency pass across pages, proofreading, performance, accessibility, and a README with screenshots and run/deploy instructions.

**Tests**

- Unit tests for every public function in `core/`.
- Property tests (hypothesis) that must always hold:
  - futures converge to spot at expiry;
  - with zero rates and zero dividends, the forward equals spot;
  - over one period, a swap's equity and funding legs net against the desk hedge to leave the spread;
  - divisor adjustments leave the index level unchanged;
  - PnL explain components sum exactly to total PnL;
  - SBL collateral ≥ loan value × margin after every mark;
  - VaR rises with confidence level;
  - margin is never negative, and a perfect hedge earns a spread credit.
- Golden-value tests: every worked example in the lesson text must match the code's output. Store example inputs and expected numbers in one place that both the lesson and the test read.
- Smoke tests with `AppTest`: every page loads with default inputs and in Advanced mode, with no exceptions, within a time budget.
- Content checks: every module has a lesson file, at least 15 quiz questions and at least one sandbox, and every glossary link resolves.

**Manual check.** Run `streamlit run app.py`, click through every page and fix layout problems. If a browser tool is available, screenshot each page and review it before calling a phase done.

## 9. Definition of done

The app is done when every box below can be ticked. Report against this list at the end of Phase 8.

- [ ] `uv run streamlit run app.py` starts with no warnings, and all pages (about 45) appear under the nav sections in Section 7.
- [ ] Every module page has Learn, Worked example, Sandbox, Desk reality and Check yourself tabs with real content. That means 1,000–2,000 words of lesson text per module, with numerical worked examples.
- [ ] Every sandbox listed in Section 7 works, about 40 calculators and simulators in total.
- [ ] All numbers come from `core/`. All tests pass, and `core/` test coverage is at least 90%.
- [ ] The synthetic world is deterministic per seed. PnL explain reconciles to the cent, and every seeded break can be found.
- [ ] Content bank: at least 15 quiz questions per module (about 600 in total), 250+ glossary terms, 60+ interview questions, 10 strategy pages and 10 automation snippets.
- [ ] Illustrative parameters live in `config/` and appear in the UI with as-of dates and "verify" labels.
- [ ] The Desk Simulator plays end to end, with scoring and a debrief.
- [ ] Every table can be downloaded. Every chart has a takeaway title and labelled units.
- [ ] The README covers setup, project structure, how to add a module, quiz or glossary term, and deployment to Streamlit Community Cloud.
- [ ] `docs/PROGRESS.md` lists what was built, known limitations and ideas for v2.
