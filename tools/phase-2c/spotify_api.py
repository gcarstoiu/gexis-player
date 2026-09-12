"""Spotify Web API driver for the Phase 2c test harness - triggers Spotify
Connect acquisition ("transfer playback") without a phone.

Credentials come from spotify.local.env (gitignored - see
spotify.env.example), obtained via a one-time PKCE authorization
(docs/DEVELOPMENT.md / HANDOFF.md record how). Reads that file if present;
otherwise falls back to the SPOTIFY_* environment variables.
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

ENV_PATH = os.path.join(os.path.dirname(__file__), "spotify.local.env")


def _load_env():
    env = dict(os.environ)
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH) as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                env[k] = v.strip('"')
    return env


_ENV = _load_env()
CLIENT_ID = _ENV.get("SPOTIFY_CLIENT_ID")
REFRESH_TOKEN = _ENV.get("SPOTIFY_REFRESH_TOKEN")
GEXIS_DEVICE_ID = _ENV.get("SPOTIFY_GEXIS_DEVICE_ID")

_access_token = None
_access_token_expiry = 0


def get_access_token():
    """Refreshes lazily; a token is reused until ~60s before its expiry."""
    global _access_token, _access_token_expiry
    if _access_token and time.monotonic() < _access_token_expiry:
        return _access_token

    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
    }).encode()
    req = urllib.request.Request(
        "https://accounts.spotify.com/api/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        body = json.load(resp)
    _access_token = body["access_token"]
    _access_token_expiry = time.monotonic() + body.get("expires_in", 3600) - 60
    return _access_token


def _api(method, path, body=None, expect_json=True, best_effort=False):
    """best_effort=True swallows HTTPError instead of raising - confirmed
    on gexis (2026-09-10) that PUT /me/player against a librespot-based
    Connect device returns a spurious 500 while the transfer still takes
    effect (gexis-core's own "will_play (acquisition)" log line fires
    right when the call is made, regardless of the HTTP status). Same
    "don't trust the self-reported status" shape as this project's other
    verification-ran-against-the-wrong-reality incidents - the caller
    should confirm the real effect (device list, PCM holder, arbitration
    log), not this call's return value."""
    token = get_access_token()
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        f"https://api.spotify.com/v1{path}",
        data=data,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method=method,
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if not expect_json or resp.status == 204:
                return None
            raw = resp.read()
            return json.loads(raw) if raw else None
    except urllib.error.HTTPError as e:
        detail = e.read().decode()
        if best_effort:
            print(f"warning: Spotify API {method} {path} -> {e.code}: {detail} (ignored, best_effort)")
            return None
        raise RuntimeError(f"Spotify API {method} {path} -> {e.code}: {detail}")


def list_devices():
    return _api("GET", "/me/player/devices")["devices"]


def resolve_gexis_device_id():
    """Looks up by name every call rather than trusting a cached id -
    go-librespot generates a fresh zeroconf device id on every reflash
    (state doesn't survive a rootfs replacement), so a stale id in
    spotify.local.env would silently start failing exactly like the
    card-index and ephemeral-port issues Finding 005 and HANDOFF.md
    already record for this project. Falls back to the env value only if
    the name lookup fails (e.g. Spotify's device cache lagging right
    after a fresh pairing)."""
    for d in list_devices():
        if d["name"] == "gexis":
            return d["id"]
    if GEXIS_DEVICE_ID:
        return GEXIS_DEVICE_ID
    raise RuntimeError("no Spotify Connect device named 'gexis' found, and no fallback id configured")


def transfer_to_gexis(play=True):
    """Acquisition trigger: 'device selected in the app', per ADR-0010's
    table. play=True also starts/resumes playback on the device."""
    return _api(
        "PUT", "/me/player", {"device_ids": [resolve_gexis_device_id()], "play": play},
        expect_json=False, best_effort=True,
    )


def transfer_away(other_device_id, play=False):
    """Moves Spotify Connect off gexis onto a different registered device -
    the release-equivalent action for racing takeovers without a phone."""
    return _api(
        "PUT", "/me/player", {"device_ids": [other_device_id], "play": play},
        expect_json=False, best_effort=True,
    )


def pause():
    return _api("PUT", "/me/player/pause", expect_json=False, best_effort=True)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "devices":
        for d in list_devices():
            print(d["id"], d["name"], d["type"], "active" if d["is_active"] else "")
    elif len(sys.argv) > 1 and sys.argv[1] == "transfer":
        transfer_to_gexis()
        print("transferred to gexis")
    else:
        print("usage: spotify_api.py [devices|transfer]")
