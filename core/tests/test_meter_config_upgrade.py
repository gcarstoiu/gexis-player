"""An upgrade of gexis-system keeps the device's keys in PeppyMeter's config.

The package ships the file whole; the core writes five of its keys (the pack
and screen it draws, ADR-0111, and the needle's smoothing). Overwritten, the
visualiser found no skin until the core's next skins pass (sofapi,
2026-10-18). preinst keeps the device's copy and postinst puts the five
back; this runs that postinst block as it is in build.sh.
"""

import ast
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BUILD = ROOT / "packaging/system/build.sh"
SHIPPED = ROOT / "image/stage-gexis/05-peppy/files/peppy-meter.txt"
PEPPY = ROOT / "core/src/gexis_core/peppy.py"

PACK = "/opt/gexis-peppy/packs/1280x800/gelo5-420/templates"


def _restore_block() -> str:
    build = BUILD.read_text()
    start = build.index("METER=/opt/gexis-peppy/peppymeter/config.txt\nKEPT=")
    end = build.index('rm -f "$KEPT"', start) + len('rm -f "$KEPT"')
    return build[start:end]


def _run(tmp_path: Path, shipped: str, kept: str | None) -> str:
    meter, kept_path = tmp_path / "config.txt", tmp_path / "kept"
    meter.write_text(shipped)
    if kept is not None:
        kept_path.write_text(kept)
    block = (_restore_block()
             .replace("/opt/gexis-peppy/peppymeter/config.txt", str(meter))
             .replace("/var/lib/gexis/peppy-meter.kept", str(kept_path)))
    subprocess.run(["sh", "-ec", block], check=True)
    assert not kept_path.exists()
    return meter.read_text()


def test_the_devices_pack_and_smoothing_survive_and_new_keys_arrive(tmp_path):
    default = SHIPPED.read_text()
    device = re.sub(r"(?m)^base\.folder = .*$", f"base.folder = {PACK}", default)
    device = re.sub(r"(?m)^smooth\.buffer\.size = .*$", "smooth.buffer.size = 7", device)
    upgraded = _run(tmp_path, default + "new.key = 1\n", device)
    assert f"base.folder = {PACK}\n" in upgraded
    assert "smooth.buffer.size = 7\n" in upgraded
    assert "new.key = 1\n" in upgraded


def test_a_first_install_keeps_the_shipped_file(tmp_path):
    default = SHIPPED.read_text()
    assert _run(tmp_path, default, None) == default


def test_preinst_keeps_the_devices_copy():
    build = BUILD.read_text()
    preinst = build[build.index('cat > "$STAGE/DEBIAN/preinst"'):]
    assert "cp \"$METER\" /var/lib/gexis/peppy-meter.kept" in preinst


def test_it_restores_every_key_the_core_writes():
    """A key the core starts writing must join the list, or an upgrade
    resets it."""
    restored = set(re.search(r"for key in ([^;]+);", _restore_block()).group(1).split())
    written = set()
    for node in ast.walk(ast.parse(PEPPY.read_text())):
        if isinstance(node, ast.FunctionDef) and node.name == "set_meter_skins":
            for sub in ast.walk(node):
                if isinstance(sub, ast.Dict):
                    written |= {k.value for k in sub.keys if isinstance(k, ast.Constant)}
    # set_meter_smoothing's one key, which it compares as a literal.
    written |= set(re.findall(r'"(smooth\.buffer\.size)"', PEPPY.read_text()))
    assert written and written <= restored, written - restored
