"""ADR-0152: the API's description and the API itself stay one.

The OpenAPI file is written by hand (aiohttp generates none); this is what
keeps it honest. A route the core registers and the file does not describe,
or one the file describes and the core no longer has, fails here.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from gexis_core.state import StateStore
from gexis_core.wsserver import StateServer

SPEC_PATH = Path(__file__).resolve().parents[1] / "src" / "gexis_core" / "api" / "openapi.json"
METHODS = {"get", "put", "post", "delete", "patch"}
#: Served by the same web server but not part of the API: the UI's own files
#: and the API's documentation page itself.
NOT_API = re.compile(r"^/$|^/assets|^/api(/|$)")


@pytest.fixture(scope="module")
def spec() -> dict:
    return json.loads(SPEC_PATH.read_text())


def _routes() -> set[tuple[str, str]]:
    app = StateServer(StateStore({})).make_app()
    out = set()
    for route in app.router.routes():
        if route.method in ("HEAD", "*") or route.resource is None:
            continue
        info = route.resource.get_info()
        path = info.get("formatter") or info.get("path")
        if path is None or NOT_API.search(path) or route.handler.__name__ == "_handle_app_file":
            continue
        out.add((route.method.lower(), path))
    return out


def _described(spec: dict) -> set[tuple[str, str]]:
    return {(m, p) for p, item in spec["paths"].items() for m in item if m in METHODS}


def test_every_route_is_described_and_every_description_is_a_route(spec):
    registered, described = _routes(), _described(spec)
    assert len(registered) >= 90, "the route listing came out short; the test would prove nothing"
    assert not sorted(registered - described), f"routes with no description: {sorted(registered - described)}"
    assert not sorted(described - registered), f"descriptions of routes that are gone: {sorted(described - registered)}"


def test_every_operation_says_what_it_is(spec):
    ids = []
    for path, item in spec["paths"].items():
        for method, op in item.items():
            if method not in METHODS:
                continue
            where = f"{method.upper()} {path}"
            assert op.get("operationId"), where
            ids.append(op["operationId"])
            assert op.get("summary") and len(op["summary"]) <= 80, where
            assert op.get("tags"), where
            assert op.get("x-gexis-stability") in ("stable", "internal"), where
            assert op.get("responses"), where
            for name in re.findall(r"{(\w+)}", path):
                params = [p for p in item.get("parameters", []) + op.get("parameters", []) if p.get("in") == "path"]
                assert any(p["name"] == name and p.get("required") for p in params), f"{where}: {{{name}}}"
    assert len(ids) == len(set(ids)), sorted({i for i in ids if ids.count(i) > 1})


def test_every_reference_resolves(spec):
    text = json.dumps(spec)
    schemas = spec.get("components", {}).get("schemas", {})
    missing = sorted({r for r in re.findall(r'"#/components/schemas/([^"]+)"', text) if r not in schemas})
    assert not missing, missing


def test_it_names_no_one_and_no_network(spec):
    """The file is published: no device of the project's, no home address."""
    text = json.dumps(spec).lower()
    for word in ("sofapi", "shelvespi", "guestpi", "bedroompi", "r2d2", "fritz.box", "qobuz"):
        assert word not in text, word
    assert not re.search(r"192\.168\.|\b10\.\d+\.\d+\.\d+|([0-9a-f]{2}:){5}[0-9a-f]{2}", text.replace("10.42.0.1", ""))
