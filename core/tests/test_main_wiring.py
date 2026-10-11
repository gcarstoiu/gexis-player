"""`main()`'s own wiring, where it cannot be run here.

`main()` builds the whole daemon in one function - D-Bus, ALSA, systemd -
so what these check is read from its source, the way
`test_sources_off.py` checks the reconciliation. Each is a defect found by
the code review of 2026-10-12 and fixed in `main()` itself.
"""
from __future__ import annotations

import ast
from pathlib import Path

MAIN = Path(__file__).resolve().parents[1] / "src" / "gexis_core" / "__main__.py"


def _main_body() -> list[ast.stmt]:
    tree = ast.parse(MAIN.read_text())
    [main] = [n for n in tree.body if isinstance(n, ast.AsyncFunctionDef) and n.name == "main"]
    return main.body


def test_no_output_at_all_does_not_leave_the_visualiser_flag_unbound():
    """`meters_available` was assigned only when an output was found and read
    unconditionally later, so the "no playback output found at all" path the
    log line means to survive raised UnboundLocalError and systemd gave up
    after five restarts - no panel, no phone."""
    body = _main_body()
    assigned = [
        i for i, stmt in enumerate(body)
        if isinstance(stmt, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == "meters_available" for t in stmt.targets)
    ]
    branch = next(
        i for i, stmt in enumerate(body)
        if isinstance(stmt, ast.If) and "chosen_output is None" in ast.unparse(stmt.test)
    )
    assert assigned and assigned[0] < branch
