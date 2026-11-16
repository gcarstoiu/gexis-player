# ADR-0182: packaging/upstream-bump.py, offline (downloads faked).
# Run: python -m pytest packaging/test_upstream_bump.py
import hashlib
import importlib.util
import io
import pathlib
import tarfile

import pytest

spec = importlib.util.spec_from_file_location(
    "upstream_bump", pathlib.Path(__file__).with_name("upstream-bump.py"))
ub = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ub)

INPUTS = (
    "# header\n"
    "aaaa\tGPL-3.0\tCamillaDSP, binary v4.1.2\thttps://github.com/HEnquist/camilladsp/releases/download/v4.1.2/camilladsp-linux-aarch64.tar.gz\n"
    "bbbb\tMIT\tsomething else\thttps://example.org/x.tar.gz\n"
    "cccc\tGPL-3.0\tCamillaDSP v4.1.2, source of the binary we ship\thttps://codeload.github.com/HEnquist/camilladsp/tar.gz/v4.1.2\n"
)


BINARY = b"\x7fELF"
CHECK = (
    "# ADR-0162 D1: CamillaDSP, the build its pin names (the binary's own checksum,\n"
    "# extracted from the pinned release, v4.1.2, 2026-10-25). Raise it with every\n"
    'CAMILLADSP_BINARY_SHA256="e04c"\n'
)


def tarball(member: str) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as t:
        data = BINARY
        info = tarfile.TarInfo(member)
        info.size = len(data)
        t.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def tree(tmp_path, inputs=INPUTS):
    (tmp_path / "packaging/camilladsp").mkdir(parents=True)
    (tmp_path / "packaging/camilladsp/pins.sh").write_text('CAMILLADSP_VERSION="v4.1.2"\n')
    (tmp_path / "packaging/inputs.tsv").write_text(inputs)
    (tmp_path / "image").mkdir()
    (tmp_path / "image/verify-image.sh").write_text(CHECK)
    return tmp_path


def fake_fetch(binary: bytes):
    def fetch(url, dest):
        data = binary if "/releases/download/" in url else b"source archive"
        dest.write_bytes(data)
        return hashlib.sha256(data).hexdigest()
    return fetch


def has_asset(repo, tag):
    return ["camilladsp-linux-aarch64.tar.gz", "other.zip"]


def test_moves_the_pin_and_both_lines_where_they_stand(tmp_path):
    root = tree(tmp_path)
    binary = tarball("camilladsp")
    keep = tmp_path / "keep"
    b, s = ub.bump("camilladsp", "v4.1.3", keep, root=root, fetch=fake_fetch(binary), assets=has_asset)
    assert b == hashlib.sha256(binary).hexdigest()
    pins = (root / "packaging/camilladsp/pins.sh").read_text()
    assert 'CAMILLADSP_VERSION="v4.1.3"\n' in pins
    assert f'CAMILLADSP_SHA256="{b}"\n' in pins
    assert 'releases/download/${CAMILLADSP_VERSION}/${CAMILLADSP_ASSET}' in pins
    lines = (root / "packaging/inputs.tsv").read_text().splitlines()
    assert lines[0] == "# header"
    assert lines[1] == (f"{b}\tGPL-3.0\tCamillaDSP, binary v4.1.3\thttps://github.com/HEnquist/camilladsp/"
                        "releases/download/v4.1.3/camilladsp-linux-aarch64.tar.gz")
    assert lines[2].startswith("bbbb\t")
    assert lines[3] == (f"{s}\tGPL-3.0\tCamillaDSP v4.1.3, source of the binary we ship\t"
                        "https://codeload.github.com/HEnquist/camilladsp/tar.gz/v4.1.3")
    assert sorted(p.name for p in keep.iterdir()) == sorted([b, s])
    check = (root / "image/verify-image.sh").read_text()
    assert f'CAMILLADSP_BINARY_SHA256="{hashlib.sha256(BINARY).hexdigest()}"\n' in check
    assert "the pinned release, v4.1.3, " in check


def test_a_build_pin_goes_back_to_a_release_pin(tmp_path):
    """ADR-0181's pin (a commit, the mirror's address) becomes a release's."""
    (tmp_path / "packaging/go-librespot").mkdir(parents=True)
    (tmp_path / "packaging/go-librespot/pins.sh").write_text(
        '# ADR-0181 ...\nGO_LIBRESPOT_VERSION="v0.10.5+git20261111.775ba58"\nGO_LIBRESPOT_COMMIT="775ba58"\n')
    (tmp_path / "packaging/inputs.tsv").write_text(
        "dddd\tGPL-3.0\tgo-librespot, binary of master\thttps://github.com/devgianlu/go-librespot/actions/runs/1\n"
        "eeee\tGPL-3.0\tgo-librespot 775ba5883, source of the binary we ship\thttps://codeload.github.com/devgianlu/go-librespot/tar.gz/775ba58\n")
    ub.bump("go-librespot", "v0.10.6", None, root=tmp_path, fetch=fake_fetch(tarball("go-librespot")),
            assets=lambda r, t: ["go-librespot_linux_arm64.tar.gz"])
    pins = (tmp_path / "packaging/go-librespot/pins.sh").read_text()
    assert "COMMIT" not in pins and "ADR-0181" not in pins
    assert 'GO_LIBRESPOT_VERSION="v0.10.6"\n' in pins
    assert "775ba58" not in (tmp_path / "packaging/inputs.tsv").read_text()


@pytest.mark.parametrize("why, assets, member, inputs", [
    ("no such asset", lambda r, t: ["camilladsp-linux-amd64.tar.gz"], "camilladsp", INPUTS),
    ("no binary in it", has_asset, "bin/camilladsp", INPUTS),
    ("no source line", has_asset, "camilladsp", INPUTS.splitlines(keepends=True)[1]),
])
def test_a_release_that_does_not_fit_changes_nothing(tmp_path, why, assets, member, inputs):
    root = tree(tmp_path, inputs)
    with pytest.raises(ub.NotSimple):
        ub.bump("camilladsp", "v4.1.3", None, root=root, fetch=fake_fetch(tarball(member)), assets=assets)
    assert (root / "packaging/camilladsp/pins.sh").read_text() == 'CAMILLADSP_VERSION="v4.1.2"\n'
    assert (root / "packaging/inputs.tsv").read_text() == inputs
    assert (root / "image/verify-image.sh").read_text() == CHECK
