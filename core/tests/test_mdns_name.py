# SPDX-License-Identifier: GPL-3.0-or-later
"""The player's own .local name back after a clash (George, 2026-10-14: the
bar answered as shelvespi-2.local for a day). The script is run as it is, with
`hostname` and `busctl` stood in for on the PATH."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "image/stage-gexis/03-core/files/gexis-mdns-name.sh"


def run(tmp_path, announced):
    bin_ = tmp_path / "bin"
    bin_.mkdir(exist_ok=True)
    calls = tmp_path / "calls"
    (bin_ / "hostname").write_text("#!/bin/sh\necho shelvespi\n")
    (bin_ / "busctl").write_text(
        "#!/bin/sh\n"
        f'echo "$*" >> "{calls}"\n'
        'case "$*" in *GetHostName*) echo \'s "' + announced + '"\' ;; esac\n'
    )
    for f in bin_.iterdir():
        f.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_}:{os.environ['PATH']}", "GEXIS_MDNS_TRIES": str(tmp_path / "run/tries")}
    out = subprocess.run(["sh", str(SCRIPT)], env=env, capture_output=True, text=True, check=True).stdout
    sets = [line for line in (calls.read_text().splitlines() if calls.exists() else []) if "SetHostName" in line]
    return out, sets


def test_a_renamed_player_claims_its_name_back(tmp_path):
    out, sets = run(tmp_path, "shelvespi-2")
    assert sets == ["--system call org.freedesktop.Avahi / org.freedesktop.Avahi.Server SetHostName s shelvespi"]
    assert "shelvespi-2.local" in out and "claiming shelvespi.local back" in out


def test_its_own_name_or_another_is_left_alone(tmp_path):
    assert run(tmp_path, "shelvespi")[1] == []
    assert run(tmp_path, "kitchen")[1] == []
    assert run(tmp_path, "shelvespi-two")[1] == []


def test_it_stops_after_five_tries_a_start(tmp_path):
    for _ in range(7):
        _, sets = run(tmp_path, "shelvespi-2")
    assert len(sets) == 5


def test_the_system_package_installs_and_enables_it():
    build = (ROOT / "packaging/system/build.sh").read_text()
    assert "/usr/lib/gexis/mdns-name.sh" in build
    assert "gexis-mdns-name.timer" in build and "systemctl enable gexis-mdns-name.timer" in build
