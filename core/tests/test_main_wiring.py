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


def _closure(name: str) -> str:
    """The source of one function defined inside `main()`."""
    for node in ast.walk(ast.Module(body=_main_body(), type_ignores=[])):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.unparse(node)
    raise AssertionError(name)


def test_a_change_of_output_carries_every_kept_level_to_the_new_scale():
    """A change of output or volume type changed what a raw number means and
    kept the published level, Mute's and the one before Fixed as they were.
    The carry has to come straight after the new scale and before the Fixed
    choice, which records the level to come back to from the published one
    (Software -> Fixed recorded the software stage's raw and later wrote it
    to the DAC, up to full scale)."""
    switch = _closure("_switch_output")
    assert switch.index("use_scale(") < switch.index("_carry_levels(") < switch.index(
        "_choose_output_mode("
    )
    carry = _closure("_carry_levels")
    for needle in ("forget_position()", "mute.carry(", "before_fixed['raw'] = carry_raw(",
                   "publish_volume(carry_raw("):
        assert needle in carry, needle


def test_a_change_of_output_puts_the_level_shown_on_the_new_card():
    """In Hardware the new card was left at whatever its control held, under a
    panel showing another level; in Fixed it was never taken to full scale."""
    switch = _closure("_switch_output")
    tail = switch[switch.index("forget_mixers()"):]
    assert "set_raw(volume_bridge.mixer_name, hardware_max())" in tail
    assert "volume_bridge.write_hardware(state_store.state.volume.raw)" in tail
    assert tail.index("write_hardware(") < tail.index("'restart'")


def test_fixed_writes_full_scale_to_the_control_in_use():
    """`config.mixer_name` is the control the daemon started with - the
    software stage after a start in Software, the old card's after a change of
    output - so Fixed wrote full scale to a control no longer in the chain."""
    apply = _closure("_apply_output_mode")
    assert "config.mixer_name" not in apply
    assert "set_raw(volume_bridge.mixer_name, hardware_max())" in apply


def test_from_fixed_to_software_starts_at_the_level_to_come_back_to():
    """With nothing published in Fixed and no software level stored,
    `_start_software_volume` read the card - at full scale in Fixed - and the
    software stage came up at 0 dB."""
    software = _closure("_set_software_volume")
    assert "level_after_fixed(before_fixed['raw']" in software
