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
