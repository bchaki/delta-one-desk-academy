# Build progress

## Phase 0 — plan: done
Plan approved (file tree, 48 pages, data models, test plan).

## Phase 1a — scaffolding and analytics: done
Built and tested (hand-calculated values in test docstrings, hypothesis properties):
- Scaffolding: `pyproject.toml` (uv), `CLAUDE.md`, ruff, pytest, `.streamlit/config.toml`, `requirements.txt`.
- `config/*.yaml` (8 files, each with `as_of`, `source`, `verify`) and typed loaders in `core/config.py`.
- `core/types.py` (enums, `money()` half-even rounding), `core/conventions.py` (4 day counts, US/TARGET/UK/Japan calendars, roll rules, schedules).
- `core/rates.py` (compounding in arrears with lookback / observation shift, discount curves, deposit bootstrap, FTP).
- `core/dividends.py`, `core/corporate_actions.py` (value-preserving adjustments), `core/indices.py` (level, divisor, weights, capping, inclusion demand, total return).
- `core/pricing/`: forwards, futures (implied repo by closed form and Brent, no-arb band, calendar and roll), trf, swaps (period flows, notional reset vs fixed, MTM, unwind, CA, desk hedge economics, spread build-up), etf, adr, dividend_derivs, program_trading.
- `core/financing/`: sbl, repo, internalisation, balance_sheet, xva_lite (simulated EE/PFE, CVA/FVA/KVA/MVA).
- `core/margin/`: exchange (SPAN-like, VaR-style, variation margin), simm_lite, regt, portfolio_margin, pb_house, csa.
- Property tests: futures converge to spot, forward = spot at zero rates and dividends, swap legs net to the spread, divisor invariance, SBL collateral >= requirement, margin >= 0 and hedge credit.

## Phase 1b — risk, PnL and synthetic world: done
- `core/data/universe.py` (61 fictional stocks, 5 ADRs, 2 indices, 2 ETFs, planned corporate actions), `market.py` (3 years of business days: factor-model prices with GARCH, Student-t, earnings jumps, 3 stress episodes; dividends with specials, cuts and an EU cancellation episode; split, rights, spin-off, cash merger; rate paths; FX; index levels with divisors; futures, TRF spreads, dividend futures; borrow fees with a squeeze and recalls; ADR and ETF prices), `book.py` (15 clients, ~50 swaps with resets, dividends, unwinds, terminations, amendments; hedges, SBL, repo, ETF, dividend futures, ADR pairs; 5 seeded breaks), `scenarios.py`, `world.py` (cached on seed; `as_of` clamps to history).
- `core/booking/` models (pydantic unions), validation (ticket rules), lifecycle, cash flows.
- `core/pnl/ledger.py` (daily USD ledger by component, book and trade), `explain.py` (components from the clean model, total from the booked ledger, Unexplained = residual of rounded components), `attribution.py`.
- `core/risk/`: snapshot and sensitivities, VaR (historical, parametric, Monte Carlo), ES, component and marginal VaR, backtest zones, stress by factor, liquidity and concentration, limits from `config/desk.yaml`.
- Tests: determinism, hedged swaps net to zero price risk, ledger totals, each seeded break's impact (missed dividend by hand), explain reconciles to the cent, full-history Unexplained equals the sum of break impacts. 196 tests, 99% coverage of `core`.

## Known limitations
- Calendars are rule-based teaching approximations, not an official holiday source.
- Swap model is single-underlying with periodic equity settlement; deferred-settlement variants are described in the docstring but not modelled.
- Margin, SIMM, haircut and tax parameters are illustrative (labelled in config).

## Ideas for v2
- Basket / portfolio swaps with per-name legs; term-structure compounding from market curves.

## Phase 1b simplifications (teach these)
- One shared trading calendar for all synthetic exchanges (days that are business days on US, TARGET, UK and Japan calendars).
- The ledger accrues funding daily on the previous day's fixing, not compounded in arrears; index swaps carry financing through the futures basis.
- Dividends are gross in the ledger (withholding tax is a separate lesson). Stale price affects the hedge inventory mark only.
- Several borrow fees in the book are very high because the squeeze name and hard-to-borrow tier were drawn from the same pool.

## Phase 2 — UI framework, Home, Index Futures: done
- `ui/`: state (settings, progress export/import, cached world), theme (CSS, colour-blind-safe Okabe-Ito palette, Plotly template), content (registry, lessons with `{{ex.*}}` golden tokens, `[[term]]` tooltips), glossary, quiz engine, charts, components (formula box with "Show the math", callouts, metric row, term sheet, blotter with CSV download, cashflow timeline, quiz block, mark complete, footer), `module_page.render_module` (Learn / Worked example / Sandbox / Desk reality / Check yourself + extra tabs), `nav` (only `built: true` pages), `app.py`.
- `content/modules.yaml` registers all 48 modules; 2 built (Home, Index Futures). Index Futures: 1,600-word lesson, 10 golden examples, 16 quiz questions, 6-part sandbox (fair value with Show the math, convergence, implied repo with no-arbitrage band, roll cost, TRF vs price, margin and variation margin) and a contract specs tab. Glossary seeded with 40 terms.
- Tests: golden examples, content completeness, page smoke (Beginner and Advanced, time budget), navigation lists only built pages. 218 tests pass, 99% core coverage.
- Not done: the spec's look-and-feel pause and screenshots. The browser extension was not connected, so layout was checked only through AppTest and a headless start (health 200). Needs a human look.

## Phase 3 — Start Here, Foundations, Products: done
- Built (13 modules): Inside a Delta One Desk, TDA Playbook; Rates & Funding, Dividends, Corporate Actions, Equity Indices; Cash Equities & Program Trading, Equity Swaps/TRS/CFDs, ETFs, ADRs, Dividend Derivatives & D1 Notes (plus Index Futures from Phase 2).
- Each has a 1,000+ word lesson, golden examples (where a core function exists), 15 quiz questions, glossary terms and a sandbox. Equity Swaps has a lifecycle simulator on the synthetic price path (schedule, client vs desk PnL, waterfall) and a Lifecycle state tab.
- New: `ui/sandbox_kit.py` (typed inputs, `calculator`), and golden examples can build objects via `{"$": "module.Class", "args": [...], "kwargs": {...}}`.
- Gate: ruff clean, 99% core coverage, page smoke green in Beginner and Advanced.
- Not done: visual review (no browser extension); Equity Swaps has no golden dividend example because dividends are objects (a pass-through amount example covers that).

## Phase 4 — SBL & Repo, Pricing & Booking: done
- Built (10 modules): SBL Market Structure, Loan Economics, SBL Operations & Risk, Internalisation, Repo, SBL Case Studies; Pricing Lab, Cost of Exposure, Trade Booking & Lifecycle, Market Data, Marks & EOD.
- New core: `core/pricing/exposure.py` (cost of exposure, breakeven days) and `core/booking/marks.py` (stale, move and source-break flags, mark impact), with tests that carry the hand calculations.
- Sandboxes: collateral marks on a synthetic price path, recall option costs, internalisation book ranked by street fee, squeeze replay on the seeded squeeze name, cost-of-exposure curves by horizon, ticket validator with live rules, lifecycle replay with cash flows, mark flag scanner that can apply the seeded stale price.
- Misconduct is taught as compliance: cum-ex is a red-flag recognition exercise with an escalation path, not a mechanism.
- `ui/content.py`: golden examples may return dicts (key access) and string-compare dates.
- Honest note: the swap and booking lessons stay near the 1,000-word floor (about 1,000 to 1,200 words each); the visual review is still outstanding.

## Phase 5 — Risk & PnL, Margin & Capital: done
- Built (7 modules): Risk Sensitivities, PnL Explain & Attribution (with a Break detective), VaR/ES & Stress, Limits/Controls/Conduct; Margin Calculator Suite (exchange, schedule and SIMM-lite, Reg T, portfolio, PB house, CSA), Funding/Balance Sheet/Capital, Counterparty Risk & XVA.
- New core: `core/risk/basic.py` (delta, beta, VaR for one and two positions, scaling, ES, days to liquidate, HHI, dividend and funding sensitivity), `core/pnl/diagnose.py` (sizes spread, dividend, fixing and stale-mark breaks; `classify` matches an unexplained amount to a suspect), `swap_rwa` in `balance_sheet.py`. All have tests with the hand calculation in the docstring.
- Misconduct (front-running, spoofing, closing manipulation, inside information, cum-ex) is taught as compliance cases in `content/case_studies.yaml` with red flags and what to do; the SBL red-flag exercise reads from the same file. `ui.content.data_file` loads YAML teaching data.
- The in-sample VaR check on the VaR page is labelled a teaching illustration, not a genuine backtest.
- Capital example uses a pension counterparty and a 0.25 hedge risk weight so the leverage ratio binds; the config default hedge risk weight is 1.0 and the page lets you change it. All parameters are illustrative.
- Known gap: roles, checklists and the 30/60/90 plan in the Start Here pages are still Python lists; to be moved to `content/` in the polish phase.

## Phase 6 — Strategy Lab: done
- Built (11 pages): Index Arbitrage, Roll & Calendar Spreads, Financing & Basis, Dividend Trading, ETF Arbitrage, Index Rebalance & Events, ADR Arbitrage, Pairs & Stat Arb, Securities Lending Strategies, Client Flow & Inventory, and the PnL Generation capstone.
- Every strategy page has: thesis, a legs diagram (`ui/strategy_kit.legs_diagram`), the PnL driver formula, parameter controls, a backtest or simulation on the synthetic world, a PnL decomposition waterfall, risk buttons that each run a scenario (`risk_buttons`), a desk-reality tab and a 15-question quiz.
- New core: `core/strategies/` (common, cash_carry, roll, basis, dividend, meanrev, etf_arb, adr_arb, pairs, index_events, sbl_strats, flow, pnl_gen). `meanrev.threshold_backtest` is shared by ETF, ADR and pairs. Tests carry the hand calculation in the docstring, plus an integration test on the synthetic world.
- `tests/test_strategy_risks.py` clicks every risk button on every strategy page.
- Honest notes: backtests use closing prices and a single round-trip cost; the synthetic dividend futures do not converge to a fixed fundamental level (the dividend page says so); the index-event study shows the method, as no announcement effect is built into the synthetic prices; the capstone's budget is an illustrative seeded plan, not real.
- Compliance: the rebalance lesson separates trading on public methodology from front-running on confidential client information.

## Phase 7 — Practice & Reference: done
- Built (7 pages): Desk Simulator, Quiz Centre & Interview Prep, Glossary, Formula Sheet & Calculator Hub, Conventions & Regulation, Automation Corner, Data Explorer. All are `reference: true` (no five-tab template or lesson).
- Desk Simulator: `core/sim/desk_day.py` is a pure seeded scenario generator and scorer with the nine timed events of the spec (07:00 explain with a seeded break through to the 18:00 sign-off). Four scores: accuracy, PnL, risk discipline, escalation, plus a debrief with the model answers and module links. Tests: perfect play scores at least 90 on 8 seeds, poor play fails, every step is graded, and AppTest plays a whole day.
- Quiz Centre: by module, mixed review, 30-minute mock test (time reported at submit; no live countdown), spaced repetition of missed questions (a correct answer leaves the queue), 12 spot-the-error items and 64 interview questions (24 technical, 20 pricing brain-teasers with checked numbers, 20 behavioural) with model answers and follow-ups.
- Glossary: 257 terms, searchable and filterable. Honest gap: only about 30 terms have a one-line worked example; the rest have definitions (and 10 have formulas).
- Formula sheet: 56 formulas rendered with `st.latex`, linked to modules; download as Markdown. PDF export is not built.
- Automation Corner: 10 snippets in `content/snippets/`, each runnable from the repo root and tested on the synthetic world.
- Fixed a duplicate quiz id between `dividends` and `s_dividend` (now `sd01` to `sd15`); a test now guards uniqueness across modules.

## Phase 8 — Polish: done (with gaps)
- Glossary examples filled for every term (257/257). README written with run, layout, checks and deploy notes.
- Full gate re-run (ruff, pytest with coverage, smoke test); app starts headless with HTTP 200 and no warnings other than Streamlit's optional watchdog hint.
- Honest gaps: no browser screenshots (the Chrome extension was not connected, so layout was not visually reviewed); README has no screenshots; the timed mock reports elapsed time at submit rather than a live countdown; no PDF export of the formula sheet; some teaching strings in `desk_inside`, `tda_playbook` and `sbl_structure` pages remain in Python rather than `content/`.
