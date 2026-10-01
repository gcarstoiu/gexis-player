"""ADR-0107 (George, 2026-09-30): an image names no LMS server. The address
comes from setup or Settings; with none, LMS is off."""
from __future__ import annotations

import tomllib
from pathlib import Path

from gexis_core.config import Config

CORE_TOML = Path(__file__).resolve().parents[2] / "image/stage-gexis/03-core/files/core.toml"


def test_the_code_default_names_no_server():
    assert Config().lms_host == ""


def test_the_shipped_config_names_no_server():
    shipped = tomllib.loads(CORE_TOML.read_text())
    assert "lms_host" not in shipped, "one household's server in every image"
