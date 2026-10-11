"""`main()`'s own wiring, where it cannot be run here.

`main()` builds the whole daemon in one function - D-Bus, ALSA, systemd -
so what these check is read from its source, the way
`test_sources_off.py` checks the reconciliation - with, at the end, the
adapters' watch loops its renderer gate relies on. Each is a defect found
by the code review of 2026-10-12.
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
    assert tail.index("write_hardware(") < tail.index("_restart_renderers(")


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


def test_a_switched_off_source_is_not_restarted_with_the_others():
    """A plain `systemctl restart` of the three renderer units starts one that
    is stopped and disabled: changing the output, the volume type or the
    visualiser's tuning brought a switched-off source back, outside
    arbitration (ADR-0077)."""
    for name in ("_switch_output", "_rewrite_output_conf", "_change_volume_type"):
        body = _closure(name)
        assert "'restart', 'squeezelite.service'" not in body, name
        assert "_restart_renderers(" in body, name
    assert "renderer_enabled(rid)" in _closure("_restart_renderers")


def test_a_renderer_plugin_reopens_the_output_with_the_built_ins():
    """Only the three built-ins were stopped and restarted on a change of
    output, so a playing Plexamp kept the old card open while the volume and
    arbitration moved to the new one."""
    for name in ("_switch_output", "_rewrite_output_conf"):
        assert "*_plugin_renderer_units()" in _closure(name), name
    restart = _closure("_restart_renderers")
    assert "restart_if_enabled(unit) for unit in _plugin_renderer_units()" in restart
    assert "p.kind == 'renderer'" in _closure("_plugin_renderer_units")


def test_a_source_switch_waits_for_the_one_before_it():
    """Each write of a source row ran its own `_apply_renderer` with no lock,
    so a quick off -> on let the slower "off" finish last: Bluetooth's radio
    powered down, or go-librespot stopped, under a switch that said on. The
    row is read inside the lock, so the last tap wins."""
    apply = _closure("_apply_renderer")
    assert "async with renderer_locks.setdefault(renderer_id" in apply
    now = _closure("_apply_renderer_now")
    assert now.index("on = renderer_enabled(renderer_id)") < now.index("set_unit_enabled(")


def test_a_plugin_s_queue_is_published_as_a_queue():
    """A plugin's `queue` event was stored as its own list, which has no
    `to_json`: once the plugin was active every broadcast raised, starting
    with the one inside `Supervisor.acquire`, so the outgoing renderer was
    never released."""
    import json

    from gexis_core.__main__ import plugin_queue
    from gexis_core.model import Queue

    queue = plugin_queue("plexamp", [{"title": "a", "duration": "12"}, "not a track"])
    assert isinstance(queue, Queue)
    assert [item.title for item in queue.items] == ["a", None]
    assert queue.items[0].duration == 12.0 and queue.items[0].source_type == "plexamp"
    json.dumps(queue.to_json())
    assert plugin_queue("plexamp", {"items": []}) is None
    assert "plugin_queue(session.id" in _closure("_plugin_event")


class _Stop(BaseException):
    """Ends a `run()` loop from inside a test, as a cancel would."""


async def _second_watch_reached(adapter, watch_name, monkeypatch):
    calls = []

    async def watch(*_args):
        calls.append(1)
        if len(calls) == 1:
            raise ValueError("an empty reply")
        raise _Stop

    async def no_wait(_seconds):
        pass

    import asyncio as _asyncio
    monkeypatch.setattr(adapter, watch_name, watch)
    monkeypatch.setattr(_asyncio, "sleep", no_wait)
    available = []
    adapter.on_availability_change(available.append)
    try:
        await adapter.run(None, None)
    except _Stop:
        pass
    return len(calls), available


async def test_an_unexpected_error_does_not_end_lms_s_watch(monkeypatch):
    """LMS's `run()` caught only connection errors, so one malformed reply -
    ValueError, TypeError, IndexError - ended its watch for the life of the
    process, in silence."""
    from gexis_core.adapters.lms import LmsAdapter

    calls, available = await _second_watch_reached(
        LmsAdapter("127.0.0.1", 9000, "gexis"), "_watch", monkeypatch)
    assert calls == 2 and available == [False]


async def test_an_unexpected_error_does_not_end_spotify_s_watch(monkeypatch):
    from gexis_core.adapters.spotify import SpotifyAdapter

    calls, available = await _second_watch_reached(
        SpotifyAdapter("127.0.0.1", 3678), "_watch_events", monkeypatch)
    assert calls == 2 and available == [False]


def test_a_watch_that_ends_is_logged_and_started_again():
    gate = _closure("_run_renderer")
    assert "task.add_done_callback(ended)" in gate
    assert "if task is not None and task.done():" in gate


def test_setup_over_the_cable_counts_as_setup_running():
    """Review, 2026-10-12: setup over Ethernet runs 'online' with setup still
    needed; a screen chosen then restarted the player half-way through Finish."""
    from gexis_core.__main__ import _setup_running
    assert _setup_running({"network": "online", "needed": True})
    assert _setup_running({"network": "open", "needed": False})
    assert not _setup_running({"network": "online", "needed": False})
    assert not _setup_running(None)
