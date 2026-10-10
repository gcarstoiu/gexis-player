# SPDX-License-Identifier: GPL-3.0-or-later
"""**Space pictures, downloaded** (ADR-0133, George 2026-10-10: *"Yes. Record
it that way"*): new pictures from NASA and ESA as the player runs, kept on
the device, with `gexis-wallpapers`' built-in set while none has arrived.

**Only sources where every picture's licence is known:**

- **ESA/Webb's picture of the month and ESA/Hubble's of the week**, from
  their feeds. Both sites release their pictures under CC BY 4.0; a
  picture is kept only if its own page's credit line starts with "ESA",
  because the sites also mirror NASA-led releases (the rule the candidates
  were chosen by). The credit is drawn with the picture.
- **NASA's image library** (`images-api.nasa.gov`, no key), only items from
  a NASA centre whose credit names no partner - the image library carries
  ESA, university and agency pictures beside NASA's own, and those are not
  public domain. Pictures from missions that usually credit partners
  (Hubble, Webb, Cassini, the rovers...) are passed over unless their own
  credit line says NASA alone.
- **Not the Astronomy Picture of the Day**, which carries photographers'
  copyrighted pictures.

**How it runs** - as the Pixabay downloader does (ADR-0047 §2a): a
catalogue asked for at most once a day and kept on disk, each picture
downloaded the first time it is shown, the newest `keep` kept. The
renditions are ESA's 1920-pixel wallpaper and NASA's large preview, so
nothing is resized on the device.
"""
from __future__ import annotations

import asyncio
import html
import json
import logging
import random
import re
import time
from pathlib import Path

import aiohttp

from gexis_core.providers import USER_AGENT

logger = logging.getLogger("gexis_core.space_pictures")

KEEP = 40
DAY_S = 24 * 3600
#: After a refresh that found nothing (no network), when to try again.
RETRY_S = 3600
TIMEOUT_S = 30.0
#: A picture larger than this is not a wallpaper rendition and is skipped.
MAX_BYTES = 8_000_000

ESA_FEEDS = (
    ("esawebb.org", "https://esawebb.org/images/potm/feed/"),
    ("esahubble.org", "https://esahubble.org/images/potw/feed/"),
)
NASA_API = "https://images-api.nasa.gov/search"
#: Two of these are asked each day, so the catalogue grows slowly and varies.
NASA_QUERIES = (
    "earth from international space station", "earth limb", "blue marble", "earthrise",
    "aurora from space station", "sunrise from space station", "city lights at night from space",
    "clouds from space station", "ocean from space", "crescent earth", "full moon",
    "artemis earth", "earth observation from orbit",
)
NASA_CENTRES = frozenset({"GSFC", "JSC", "JPL", "KSC", "MSFC", "ARC", "HQ", "LARC", "LaRC", "GRC", "AFRC", "SSC"})
#: A partner named anywhere in the credit, the photographer or the title.
NOT_NASA_ALONE = re.compile(
    r"\bESO\b|\bESA\b|\bCSA\b|STScI|JAXA|Roscosmos|Univ|Institut|SwRI|MSSS|\bASU\b|\bCXC\b|\bSAO\b|"
    r"Space Science Inst|\bSSI\b|DLR|Johns Hopkins|\bAPL\b|Carnegie|NOAA|USGS|Cornell|Arizona|"
    r"Max Planck|Southwest|Malin|Keck|Gemini|NSF|NOIRLab|Getty|Reuters|\bAP\b|processed by",
    re.I)
#: **A scene, not people** (found on the first real refresh, 2026-10-10: a
#: former vice-president visiting Goddard came back for "hurricane"): the
#: title or keywords must name a place in space, and nothing about people
#: or events.
SCENE = re.compile(
    r"\bEarth\b|Moon|lunar|planet|Mars|Jupiter|Saturn|nebula|galaxy|galaxies|aurora|sunrise|sunset|"
    r"hurricane|typhoon|cyclone|storm|cloud|ocean|sea\b|coast|island|desert|mountain|volcano|"
    r"city lights|night lights|Blue Marble|Earthrise|limb|horizon|star|comet|eclipse|Sun\b",
    re.I)
PEOPLE = re.compile(
    r"astronaut|crew|cosmonaut|portrait|visit|vice president|\bVP\b|president|administrator|"
    r"employee|team|ceremony|students|press|conference|briefing|award|selfie|spacewalk|EVA\b|"
    r"training|launch|rollout|engineer|technician|official|family|people|member",
    re.I)
#: Missions whose pictures usually credit partners: kept only with a credit.
PARTNER_MISSIONS = re.compile(
    r"Hubble|Cassini|Juno|Chandra|Spitzer|Webb|Voyager|HiRISE|Reconnaissance|Galileo|\bLRO\b|"
    r"rover|Perseverance|Curiosity|Opportunity",
    re.I)


# ---- what the sources say ------------------------------------------------

def esa_feed(body: str, host: str) -> list[dict]:
    """The pictures an ESA feed lists: id, title, page and the wallpaper
    rendition's address."""
    items = []
    for item in re.findall(r"<item>(.*?)</item>", body, re.S):
        link = re.search(r"<link>\s*(https://[^<\s]+)\s*</link>", item)
        if not link:
            continue
        found = re.search(r"/images/([a-z0-9_-]+)/?$", link.group(1).strip())
        if not found:
            continue
        pid = found.group(1)
        title = re.search(r"<title>(.*?)</title>", item, re.S)
        items.append({
            "id": f"esa-{host.split('.')[0]}-{pid}",
            "title": html.unescape(title.group(1)).strip() if title else pid,
            "page": link.group(1).strip(),
            "url": f"https://cdn.{host}/archives/images/wallpaper2/{pid}.jpg",
        })
    return items


def esa_credit(page: str) -> str | None:
    """The credit line an ESA picture page gives, or None."""
    text = re.sub(r"<script.*?</script>", " ", page, flags=re.S)
    text = html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text)))
    found = re.search(r"Credit:\s*(.+?)\s+(?:More Information|Usage of|About the Image|Release date|$)", text)
    return found.group(1).strip() if found else None


def nasa_items(body: dict) -> list[dict]:
    """The pictures an image-library search answered that are NASA's alone,
    landscape and at least 1920 pixels wide."""
    out = []
    for item in ((body or {}).get("collection") or {}).get("items") or []:
        try:
            data = item["data"][0]
        except (KeyError, IndexError, TypeError):
            continue
        links = {link["href"].rsplit("~", 1)[-1].split(".")[0]: link
                 for link in item.get("links") or [] if "~" in link.get("href", "")}
        large = links.get("large") or {}
        orig = links.get("orig") or {}
        width = orig.get("width") or large.get("width")
        height = orig.get("height") or large.get("height")
        if not large.get("href") or not width or not height or width < 1920 or width / height < 1.3:
            continue
        description = html.unescape(re.sub(r"<[^>]+>", " ", data.get("description") or ""))
        lines = re.findall(r"(?:image|photo)?\s*credits?\s*:\s*([^\n]{0,160})", description, re.I)
        credit = re.split(r"\s{2,}", lines[-1])[0].strip().rstrip(".") if lines else ""
        people = " ".join(filter(None, [data.get("secondary_creator") or "", data.get("photographer") or ""]))
        title = data.get("title") or ""
        if data.get("center") not in NASA_CENTRES:
            continue
        if NOT_NASA_ALONE.search(f"{credit} {people} {title}"):
            continue
        everything = f"{description} {title} {' '.join(data.get('keywords') or [])}"
        if not credit and PARTNER_MISSIONS.search(everything):
            continue
        if credit and "NASA" not in credit.upper():
            continue
        named = f"{title} {' '.join(data.get('keywords') or [])}"
        if not SCENE.search(named) or PEOPLE.search(f"{named} {description[:400]}"):
            continue
        nid = re.sub(r"[^A-Za-z0-9_-]", "_", data.get("nasa_id") or "")
        if not nid:
            continue
        out.append({
            "id": f"nasa-{nid}",
            "title": title,
            "page": f"https://images.nasa.gov/details/{data.get('nasa_id')}",
            "url": large["href"],
            "by": credit or f"NASA ({data.get('center')})",
            "licence": "Public domain",
        })
    return out


# ---- the downloader --------------------------------------------------------

class SpacePictures:
    """The downloaded Space pictures, and the catalogue they come from."""

    def __init__(self, session: aiohttp.ClientSession, directory: Path, *, keep: int = KEEP,
                 rng: random.Random | None = None, clock=time.time) -> None:
        self._session = session
        self._dir = Path(directory)
        self._keep = keep
        self._rng = rng or random.Random()
        self._clock = clock
        self._state_path = self._dir / "state.json"
        self._state = self._load()
        self._lock = asyncio.Lock()
        self._refreshing: asyncio.Task | None = None
        self._tried: float | None = None   # never, until the first refresh
        #: The last request found no network: until one succeeds, only what
        #: is on the device is shown, so a dead network costs no timeouts.
        self._offline = False

    def _load(self) -> dict:
        try:
            state = json.loads(self._state_path.read_text())
            if isinstance(state, dict):
                return {"at": float(state.get("at") or 0), "catalogue": dict(state.get("catalogue") or {}),
                        "credits": dict(state.get("credits") or {}), "files": dict(state.get("files") or {}),
                        "shown": list(state.get("shown") or [])}
        except (OSError, ValueError, TypeError):
            pass
        return {"at": 0.0, "catalogue": {}, "credits": {}, "files": {}, "shown": []}

    def _save(self) -> None:
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            part = self._state_path.with_suffix(".part")
            part.write_text(json.dumps(self._state))
            part.replace(self._state_path)
        except OSError as exc:
            logger.warning("space pictures: state not saved: %s", exc)

    async def _get(self, url: str, **params) -> tuple[int, bytes]:
        try:
            async with self._session.get(url, params=params or None, headers={"User-Agent": USER_AGENT},
                                         timeout=aiohttp.ClientTimeout(total=TIMEOUT_S)) as response:
                self._offline = False
                if response.status != 200:
                    return response.status, b""
                # Chunk by chunk to the end: `read(n)` answers with whatever
                # has arrived (found against ESA, 2026-10-10: 3 kB of a
                # picture), and a body past the cap is not a wallpaper.
                body = bytearray()
                async for chunk in response.content.iter_chunked(65536):
                    body += chunk
                    if len(body) > MAX_BYTES:
                        break
                return 200, bytes(body)
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            logger.info("space pictures: %s unreachable: %s", url, exc)
            self._offline = True
            return 0, b""

    def _due(self) -> bool:
        now = self._clock()
        if self._tried is not None and now - self._tried < RETRY_S:
            return False
        return now - self._state["at"] >= DAY_S or not self._state["catalogue"]

    def refresh_soon(self) -> asyncio.Task | None:
        """**In the background**, never on the screen's request: the first
        refresh reads every ESA picture's page once, a minute's work, and the
        screen shows the built-in set meanwhile."""
        if self._refreshing is None or self._refreshing.done():
            if self._due():
                self._refreshing = asyncio.ensure_future(self._refresh())
        return self._refreshing

    async def _refresh(self) -> None:
        """Ask the sources again."""
        self._tried = self._clock()
        found: dict[str, dict] = {}
        for host, feed in ESA_FEEDS:
            status, body = await self._get(feed)
            if status != 200:
                continue
            for item in esa_feed(body.decode("utf-8", "replace"), host):
                credit = self._state["credits"].get(item["id"])
                if credit is None:
                    status, page = await self._get(item["page"])
                    if status != 200:
                        continue
                    credit = esa_credit(page.decode("utf-8", "replace")) or ""
                    self._state["credits"][item["id"]] = credit
                if credit.startswith("ESA"):
                    found[item["id"]] = {**item, "by": None, "credit": credit, "licence": "CC BY 4.0"}
        for query in self._rng.sample(NASA_QUERIES, 2):
            status, body = await self._get(NASA_API, q=query, media_type="image", page_size="40")
            if status != 200:
                continue
            try:
                answer = json.loads(body)
            except ValueError:
                continue
            for item in nasa_items(answer)[:8]:
                found[item["id"]] = {**item, "credit": None}
        if found:
            # Kept, not replaced: yesterday's NASA queries were different.
            self._state["catalogue"].update(found)
            self._state["at"] = self._clock()
            self._save()

    async def _download(self, entry: dict) -> str | None:
        name = f"{entry['id']}.jpg"
        if name in self._state["files"] and (self._dir / name).is_file():
            return name
        status, body = await self._get(entry["url"])
        if status != 200 or not body or len(body) > MAX_BYTES or not body.startswith(b"\xff\xd8"):
            return None
        self._dir.mkdir(parents=True, exist_ok=True)
        (self._dir / name).write_bytes(body)
        self._state["files"][name] = {"at": self._clock(), "id": entry["id"]}
        self._evict()
        return name

    def _evict(self) -> None:
        files = sorted(self._state["files"].items(), key=lambda kv: kv[1]["at"], reverse=True)
        for name, _ in files[self._keep:]:
            (self._dir / name).unlink(missing_ok=True)
            del self._state["files"][name]

    async def next(self, avoid: str | None = None) -> dict | None:
        """A Space picture to draw, or None when none can be had - the
        caller then shows the built-in set."""
        self.refresh_soon()
        async with self._lock:
            catalogue = self._state["catalogue"]
            shown = self._state["shown"]
            ids = [i for i in catalogue if f"{i}.jpg" != avoid]
            fresh = [i for i in ids if i not in shown]
            if not fresh:
                shown.clear()
                fresh = ids
            self._rng.shuffle(fresh)
            for pid in ([] if self._offline else fresh[:3]):
                name = await self._download(catalogue[pid])
                if name is None:
                    continue
                shown.append(pid)
                self._save()
                return self.answer(name)
            # Nothing reachable: what is already on the device.
            kept = [n for n in self._state["files"] if n != avoid and (self._dir / n).is_file()]
            if kept:
                return self.answer(self._rng.choice(kept))
            return None

    def answer(self, name: str) -> dict:
        entry = self._state["catalogue"].get(self._state["files"][name]["id"], {})
        if entry.get("credit"):
            by, credit = None, f"{entry['credit']} · {entry.get('licence') or 'CC BY 4.0'}"
        else:
            by, credit = entry.get("by") or "NASA", "Public domain"
        return {"url": f"/idle/wallpaper/space/{name}", "file": name, "by": by,
                "page": entry.get("page") or "", "credit": credit, "error": None}

    def path_of(self, name: str) -> Path | None:
        """A downloaded picture's file, by a name this class handed out."""
        if name != Path(name).name or name not in self._state["files"]:
            return None
        path = self._dir / name
        return path if path.is_file() else None
