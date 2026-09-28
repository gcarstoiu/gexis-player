"""ADR-0103: the journal kept across restarts, when the user asks."""
from __future__ import annotations

from gexis_core import journal


def paths(tmp_path):
    return tmp_path / "journald.conf.d" / "60-gexis-debug-logs.conf", tmp_path / "var-log-journal"


def test_on_writes_the_dropin_restarts_journald_and_flushes(tmp_path):
    dropin, kept = paths(tmp_path)
    ran = []
    journal.apply(True, dropin=dropin, kept=kept, run=lambda cmd, **kw: ran.append(cmd))
    assert dropin.read_text() == "[Journal]\nStorage=persistent\nSystemMaxUse=100M\n"
    assert ran == [["systemctl", "restart", "systemd-journald"], ["journalctl", "--flush"]]
    assert journal.is_kept(dropin) and journal.matches(True, dropin, kept)


def test_off_removes_the_dropin_and_deletes_the_kept_logs(tmp_path):
    dropin, kept = paths(tmp_path)
    journal.apply(True, dropin=dropin, kept=kept, run=lambda cmd, **kw: None)
    (kept / "abc").mkdir(parents=True)
    (kept / "abc" / "system.journal").write_text("logs")
    ran = []
    journal.apply(False, dropin=dropin, kept=kept, run=lambda cmd, **kw: ran.append(cmd))
    assert not dropin.exists() and kept.is_dir() and not any(kept.iterdir()), "the files go, the folder stays"
    assert ran == [["systemctl", "restart", "systemd-journald"]], "restarted before the files go"
    assert journal.matches(False, dropin, kept)


def test_off_on_a_fresh_image_already_matches(tmp_path):
    """The image ships volatile: nothing to undo, so nothing is restarted."""
    dropin, kept = paths(tmp_path)
    assert journal.matches(False, dropin, kept)
    assert not journal.matches(True, dropin, kept)


def test_logs_left_on_the_card_do_not_match_off(tmp_path):
    """A restore can bring back off over a card that kept logs."""
    dropin, kept = paths(tmp_path)
    (kept / "abc").mkdir(parents=True)
    (kept / "abc" / "system.journal").write_text("logs")
    assert not journal.matches(False, dropin, kept)


def test_the_images_empty_folder_matches_off(tmp_path):
    """systemd's tmpfiles creates /var/log/journal empty on the image; found on
    gexis, where counting it restarted journald at startup for nothing."""
    dropin, kept = paths(tmp_path)
    kept.mkdir()
    assert journal.matches(False, dropin, kept)


def test_a_dropin_someone_edited_is_not_ours(tmp_path):
    dropin, kept = paths(tmp_path)
    dropin.parent.mkdir(parents=True)
    dropin.write_text("[Journal]\nStorage=persistent\n")
    assert not journal.is_kept(dropin)
