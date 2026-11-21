# CLAUDE.md — Delta One Desk Academy

Build spec: `SPEC.md`. Build log: `docs/PROGRESS.md`. Build one phase at a time (SPEC §8) and don't start a phase with failing tests.

## Architecture
- `core/` is pure Python, fully typed, with no Streamlit imports. Every public function has a docstring stating formula, units and conventions. If a formula is simplified, say so and say what the full version adds.
- Pages (`pages/<section>/`) stay thin: read inputs, call `core`, render. They never hard-code results.
- Teaching text lives in `content/` (Markdown and YAML), not in Python strings.
- `content/modules.yaml` is the module registry. It drives nav, page headers, Home and progress. A page appears in nav only when `built: true`.
- Worked-example inputs and expected numbers live in `content/examples/<module>.yaml`. Lessons and `tests/test_golden.py` both read them.
- Use `st.navigation` and `st.Page`, not legacy `pages/` auto-discovery. Wrap sandboxes in `st.fragment`.

## Numbers and conventions
- Offline and deterministic: no external APIs. Everything derives from the seeded synthetic world, keyed on `(seed, as_of_date)`.
- Every rate states day count and compounding, every amount its currency, every spread bps and benchmark. Positive PnL is a gain to the desk. Every cash flow states whose side it is from (client or desk).
- Analytics use float64. Round to cents with `core.types.money()` (half-even) at the cash-flow and booking boundary. `Unexplained` is the residual of the rounded components.
- Illustrative parameters (SIMM weights, margin rates, contract specs, tax, haircuts) live in `config/*.yaml` with `as_of`, `source` and `verify`. The UI labels them "Illustrative, verify against the official source", with the as-of date.
- Real product and index names in text are fine. All stocks, prices and clients in data are fictional. Don't invent bank system names; use generic labels.
- Teach misconduct (cum-ex, spoofing, front-running, squeezes) as compliance cases, never as a playbook.
- No placeholders, "TODO" or empty tabs. Unbuilt features stay out of nav.
- Colour-blind-safe charts; never use red/green alone.

## Workflow
- `uv run ruff check . && uv run ruff format --check .`
- `uv run pytest --cov=core --cov-fail-under=90`
- `uv run pytest tests/test_pages_smoke.py` (from Phase 2)
- Unit tests put the hand calculation in the docstring. Update `docs/PROGRESS.md` at the end of every phase, then commit.
