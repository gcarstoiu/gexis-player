"""ADR-0119: `plexamp-run` settles Plexamp's claim before starting it."""
from __future__ import annotations

import importlib.machinery
import json
import sys
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[2] / "image/stage-gexis/08-plexamp/files/plexamp-run"
# No __pycache__ beside a file the image ships.
_write, sys.dont_write_bytecode = sys.dont_write_bytecode, True
run = importlib.machinery.SourceFileLoader("plexamp_run", str(PATH)).load_module()
sys.dont_write_bytecode = _write


@pytest.fixture
def home(tmp_path):
    return {"settings": tmp_path / "Settings", "previous": tmp_path / "Settings.previous",
            "state_path": tmp_path / "gexis-plexamp/claim.json"}


def claim(settings: Path, value="Sabc123") -> None:
    settings.mkdir(parents=True, exist_ok=True)
    (settings / run.TOKEN_FILE).write_text(value)


def state(home) -> dict:
    return json.loads(home["state_path"].read_text())


def test_the_name_is_the_device_s_and_no_token_is_no_claim(home):
    env = run.prepare({"GEXIS_DEVICE_NAME": "Kitchen", "PATH": "/bin"}, **home)
    assert env["PLEXAMP_PLAYER_NAME"] == "Kitchen" and env["PATH"] == "/bin"
    assert "PLEXAMP_CLAIM_TOKEN" not in env
    assert run.prepare({}, **home)["PLEXAMP_PLAYER_NAME"] == "gexis"


def test_a_first_claim_hands_the_token_over_once_and_records_success(home):
    env = run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-one"}, **home)
    assert env["PLEXAMP_CLAIM_TOKEN"] == "claim-one"
    assert state(home)["state"] == "trying"
    assert "claim-one" not in home["state_path"].read_text(), "the hash, never the token"
    claim(home["settings"])  # Plexamp claimed and kept running
    env = run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-one"}, **home)
    assert "PLEXAMP_CLAIM_TOKEN" not in env
    assert state(home)["state"] == "claimed"


def test_a_failed_first_claim_is_not_tried_again(home):
    run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-dead"}, **home)
    # Plexamp exited 255 and wrote nothing; the unit restarts it.
    env = run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-dead"}, **home)
    assert "PLEXAMP_CLAIM_TOKEN" not in env, "a dead token cannot loop the unit"
    assert state(home)["state"] == "failed"
    env = run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-dead"}, **home)
    assert "PLEXAMP_CLAIM_TOKEN" not in env


def test_claim_again_keeps_the_old_claim_until_the_new_one_works(home):
    claim(home["settings"], "Sold")
    run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-one"}, **home)  # adopted as the claim's own
    assert state(home)["state"] == "claimed"
    env = run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-two"}, **home)
    assert env["PLEXAMP_CLAIM_TOKEN"] == "claim-two"
    assert not home["settings"].exists() and home["previous"].is_dir(), "set aside, not deleted"
    # It failed: the old claim comes back.
    run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-two"}, **home)
    assert (home["settings"] / run.TOKEN_FILE).read_text() == "Sold"
    assert not home["previous"].exists()
    assert state(home)["state"] == "failed"


def test_claim_again_that_works_drops_the_old_store(home):
    claim(home["settings"], "Sold")
    run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-one"}, **home)
    run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-two"}, **home)
    claim(home["settings"], "Snew")
    run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-two"}, **home)
    assert (home["settings"] / run.TOKEN_FILE).read_text() == "Snew"
    assert not home["previous"].exists()
    assert state(home)["state"] == "claimed"


def test_a_token_stored_on_an_already_claimed_player_is_not_tried(home):
    """gexis: claimed by Plexamp's own setup, with a spent token in Settings.
    The first start after this update must not set its claim aside."""
    claim(home["settings"])
    env = run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-spent"}, **home)
    assert "PLEXAMP_CLAIM_TOKEN" not in env
    assert home["settings"].is_dir() and not home["previous"].exists()


# -- 2026-10-08: what guestpi's three claims showed ------------------------------

def unclaimed_store(settings: Path) -> None:
    settings.mkdir(parents=True, exist_ok=True)
    (settings / "%40Plexamp%3Auser%3AanonymousIdentifier").write_text("Sbefore")


def test_a_failed_claim_on_an_unclaimed_player_leaves_nothing_behind(home):
    """Plexamp wrote the user, Plex refused the sign-in, Plexamp exited 255:
    the store as it was before comes back, not half an account."""
    unclaimed_store(home["settings"])
    run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-one"}, **home)
    assert home["previous"].is_dir(), "an unclaimed store is set aside too"
    claim(home["settings"], "Sissued")
    (home["settings"] / "%40Plexamp%3Auser%3Aname").write_text("Sowner")
    run.stopped({"EXIT_CODE": "exited", "EXIT_STATUS": "255"}, **home)
    assert state(home)["state"] == "failed"
    assert sorted(p.name for p in home["settings"].iterdir()) == ["%40Plexamp%3Auser%3AanonymousIdentifier"]
    assert not home["previous"].exists()


def test_a_sign_in_written_before_the_exit_is_not_taken_for_a_claim(home):
    """The next start used to see the token file and record *claimed*."""
    run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-one"}, **home)
    claim(home["settings"], "Sissued")
    run.stopped({"EXIT_CODE": "exited", "EXIT_STATUS": "255"}, **home)
    env = run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-one"}, **home)
    assert state(home)["state"] == "failed" and "PLEXAMP_CLAIM_TOKEN" not in env
    assert not home["settings"].exists(), "nothing of the failed claim stays"


def test_a_stop_while_claiming_settles_nothing(home):
    run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-one"}, **home)
    claim(home["settings"])
    run.stopped({"EXIT_CODE": "killed", "EXIT_STATUS": "TERM"}, **home)
    assert state(home)["state"] == "trying"
    run.stopped({"EXIT_CODE": "exited", "EXIT_STATUS": "0"}, **home)
    assert state(home)["state"] == "trying"
    run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-one"}, **home)
    assert state(home)["state"] == "claimed"


def test_the_attempt_is_timed_for_the_plugin(home):
    run.prepare({"PLEXAMP_CLAIM_TOKEN": "claim-one"}, **home)
    assert isinstance(state(home)["at"], float)
