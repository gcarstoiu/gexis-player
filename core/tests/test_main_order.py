# SPDX-License-Identifier: GPL-3.0-or-later
"""`main()` uses each of its own names only after it is first assigned.

The suite builds the core's parts one by one and never runs `main()`
(LESSONS 19), so a line wired in above the object it touches passed every
test and stopped the core at start on a player (2026-11-16:
`state_store.is_favourite` set some hundred lines before `state_store`).
Read from the source, in the order `main()` runs: a name used in a
statement before the first statement that assigns it. A use inside a
function or lambda defined in `main()` runs later, and is not one.
"""
import ast
from pathlib import Path

MAIN = Path(__file__).resolve().parents[1] / "src" / "gexis_core" / "__main__.py"


def _main(tree: ast.Module) -> ast.AsyncFunctionDef | ast.FunctionDef:
    return next(n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "main")


def _now(node: ast.AST):
    """The nodes evaluated when `node` runs - not a nested body run later."""
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        for d in node.decorator_list + node.args.defaults + [d for d in node.args.kw_defaults if d]:
            yield from _now(d)
        return
    if isinstance(node, ast.Lambda):
        for d in node.args.defaults + [d for d in node.args.kw_defaults if d]:
            yield from _now(d)
        return
    if isinstance(node, ast.ClassDef):
        for d in node.decorator_list + node.bases:
            yield from _now(d)
        return
    yield node
    for child in ast.iter_child_nodes(node):
        yield from _now(child)


def _assigned(stmt: ast.stmt) -> set[str]:
    names = set()
    for node in _now(stmt):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            names.add(node.id)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            names.update((a.asname or a.name).split(".")[0] for a in node.names)
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        names.add(stmt.name)
    return names


def used_before_assigned(fn) -> list[tuple[str, int]]:
    first: dict[str, int] = {}
    for i, stmt in enumerate(fn.body):
        for name in _assigned(stmt):
            first.setdefault(name, i)
    found = []
    for i, stmt in enumerate(fn.body):
        for node in _now(stmt):
            if (isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)
                    and node.id in first and first[node.id] > i):
                found.append((node.id, node.lineno))
    return found


def test_main_uses_each_of_its_names_after_assigning_it():
    fn = _main(ast.parse(MAIN.read_text()))
    assert len(fn.body) > 100, "main() not found whole"
    assert used_before_assigned(fn) == []


def test_the_check_finds_a_use_above_the_assignment():
    fn = _main(ast.parse(
        "async def main():\n"
        "    later = lambda: store.x\n"           # runs later: not a use
        "    def f():\n        return store\n"    # nor this
        "    store.flag = 1\n"                    # the mistake
        "    store = object()\n"
    ))
    assert used_before_assigned(fn) == [("store", 5)]
