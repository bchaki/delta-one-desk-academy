# Delta One Desk Academy

A multi-page Streamlit app that teaches a new Trading Desk Assistant what they need to know in their first 90 days on an equity Delta One desk. The build spec is in `SPEC.md`.

This is an educational tool, not investment, tax or legal advice. Conventions vary by firm. All stocks, prices and clients are fictional and generated offline from a seeded synthetic world. Illustrative parameters (margin, SIMM weights, contract specs, tax) live in `config/*.yaml` and are labelled "Illustrative, verify against the official source".

## Run

```bash
uv sync
uv run streamlit run app.py
```

Python 3.12. The app is offline and deterministic: the world is keyed on `(seed, as_of_date)`, set in the sidebar.

## Layout

- `core/`: pure, typed Python (pricing, financing, margin, risk, PnL, strategies, simulator, synthetic world). No Streamlit imports.
- `ui/`: Streamlit helpers (module page template, quiz, glossary, charts, state).
- `pages/<section>/`: thin pages that read inputs, call `core`, and render.
- `content/`: lessons (Markdown), quizzes, golden examples, glossary, interview and spot-the-error banks, formulas, snippets. `content/modules.yaml` is the registry that drives navigation; a page appears only when `built: true`.
- `config/`: illustrative parameters with `as_of`, `source` and `verify`.
- `tests/`: unit, property (hypothesis), golden-value, content, snippet and AppTest smoke tests.

## Checks

```bash
uv run ruff check . && uv run ruff format --check .
uv run pytest --cov=core --cov-fail-under=90
uv run pytest tests/test_pages_smoke.py
```

## Deploy

Streamlit Community Cloud or any host that runs `streamlit run app.py` with `requirements.txt` installed. No secrets or external APIs are needed.

## Content

48 pages, about 600 quiz questions, 257 glossary terms, 64 interview questions, 12 spot-the-error items, 56 formulas, 10 runnable automation snippets and a nine-step Desk Simulator with scoring. Progress is stored in the session and can be exported.
