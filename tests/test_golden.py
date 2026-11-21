"""Golden values: every worked example stored in content/examples/*.yaml must match core."""

import pytest
import yaml

from ui.content import CONTENT, check_example, run_example

FILES = sorted((CONTENT / "examples").glob("*.yaml"))
CASES = [
    (f.stem, k, v) for f in FILES for k, v in yaml.safe_load(f.read_text())["examples"].items()
]


@pytest.mark.parametrize(("module", "name", "ex"), CASES, ids=[f"{m}:{n}" for m, n, _ in CASES])
def test_golden_example(module, name, ex):
    assert check_example(ex), f"{module}:{name} result {run_example(ex)!r} != {ex['expected']!r}"
