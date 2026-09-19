"""Phase 5 criterion 7: a field with nothing behind it draws nothing.

The renderer ships in the image stage rather than the core package (it runs
in the meter process, on system Python with pygame), so this reaches into
that directory to import it. Runs headless via SDL's dummy driver.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

pygame = pytest.importorskip("pygame")

STAGE = Path(__file__).parents[2] / "image" / "stage-gexis" / "05-peppy" / "files"
sys.path.insert(0, str(STAGE))

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
from gexis_peppy_render import (  # noqa: E402
    FINAL_SECONDS_COLOUR,
    MetadataLayer,
    parse_colour,
    parse_point,
    parse_size,
    remaining_time,
)

#: The shipped corpus: its config files are in this repository even though its
#: 82MB of images are fetched at build time, so the geometry is checkable here.
CORPUS_DIR = Path(__file__).parents[2] / "skins" / "templates"


def corpus_skins() -> list[dict]:
    skins, current = [], None
    for line in (CORPUS_DIR / "meters.txt").read_text().splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            current = {"name": line[1:-1]}
            skins.append(current)
        elif "=" in line and current is not None:
            key, value = line.split("=", 1)
            current[key.strip()] = value.strip()
    return skins

SKIN = {
    "screen.bgr": "bgr.png",
    "playinfo.title.pos": "100,400,bold",
    "playinfo.artist.pos": "100,450,regular",
    "playinfo.album.pos": "100,500,light",
    "time.remaining.pos": "900,500",
    "playinfo.type.pos": "600,550",
    "playinfo.maxwidth": "700",
    "playinfo.samplerate.pos": "110,570,bold",
    "albumart.pos": "560,70",
    "albumart.dimension": "170,170",
    "font.size.regular": "20",
    "font.size.bold": "20",
    "font.size.light": "20",
    "font.color": "180,180,180",
}


@pytest.fixture(scope="module")
def screen():
    # Some pygame builds ship without a working font module (the dev box's
    # Python 3.14 wheel is one). The device's is fine, and that is where this
    # file has to pass; here it skips rather than reporting a false failure.
    try:
        pygame.display.init()
        pygame.font.init()
    except (NotImplementedError, pygame.error) as exc:
        pytest.skip(f"pygame display/font unavailable: {exc}")
    yield pygame.display.set_mode((1280, 800))
    pygame.display.quit()


@pytest.fixture
def layer(screen, tmp_path):
    background = pygame.Surface((1280, 800))
    background.fill((10, 20, 30))
    pygame.image.save(background, str(tmp_path / "bgr.png"))
    made = MetadataLayer(screen, tmp_path)
    made.set_skin(SKIN)
    return made


def full(**kw):
    base = {
        "source": "lms",
        "title": "Title",
        "artist": "Artist",
        "album": "Album",
        "artwork": None,
        "position": 30.0,
        "duration": 200.0,
        "transport": "playing",
        "written_at": 0,
    }
    base.update(kw)
    return base


def test_it_draws_the_fields_it_has(layer):
    dirty = layer.draw(full())
    assert len(dirty) == 5  # title, artist, album, remaining, source


def test_a_field_with_nothing_behind_it_is_not_drawn(layer):
    """Bluetooth: no album, no position, no artwork."""
    dirty = layer.draw(full(album=None, position=None, duration=None, source="bluetooth"))

    assert len(dirty) == 3  # title, artist, source label only


def test_sample_rate_never_renders_even_though_the_skin_places_it(layer):
    """ADR-0036: no sample rate and no codec anywhere. The skin keeps the
    position; nothing ever fills it."""
    before = layer.draw(full())
    again = layer.draw(full())

    assert before and not again  # nothing changed, so nothing redrawn
    assert "samplerate" not in str(layer._last_drawn)


def test_a_field_that_disappears_is_erased_back_to_the_background(layer):
    layer.draw(full())
    painted_with_album = len(layer._painted)

    layer.draw(full(album=None))

    assert len(layer._painted) == painted_with_album - 1


def test_nothing_playing_draws_nothing(layer):
    layer.draw(full())

    layer.draw({"source": None, "title": None, "artist": None, "album": None, "artwork": None,
                "position": None, "duration": None, "transport": None, "written_at": 0})

    assert layer._painted == []


def test_a_skin_without_a_background_draws_nothing_rather_than_smearing(screen, tmp_path):
    made = MetadataLayer(screen, tmp_path)
    made.set_skin({k: v for k, v in SKIN.items() if k != "screen.bgr"})

    assert made.draw(full()) == []


def test_long_text_is_trimmed_to_the_skins_width(layer):
    wide = layer.draw(full(title="x" * 400))
    assert wide[0].width <= 700 + 40  # the skin's playinfo.maxwidth, plus the ellipsis


@pytest.mark.parametrize(
    ("metadata", "expected"),
    [
        ({"position": 30.0, "duration": 200.0, "transport": "paused", "written_at": 0}, "02:50"),
        ({"position": None, "duration": 200.0, "transport": "playing"}, None),
        ({"position": 30.0, "duration": None, "transport": "playing"}, None),
        ({"position": 300.0, "duration": 200.0, "transport": "paused", "written_at": 0}, "00:00"),
        ({"position": 0.0, "duration": 725.0, "transport": "paused", "written_at": 0}, "12:05"),
    ],
)
def test_remaining_time(metadata, expected):
    assert remaining_time(metadata) == expected


def test_parsers():
    assert parse_point("100,400,bold") == (100, 400, "bold")
    assert parse_point("100,400") == (100, 400, "regular")
    assert parse_point("nonsense") is None
    assert parse_point(None) is None
    assert parse_colour("1,2,3") == (1, 2, 3)
    assert parse_colour(None, (9, 9, 9)) == (9, 9, 9)


def test_artwork_is_drawn_before_the_text_over_it(layer):
    """dash-spectrum places title, artist and album inside its artwork well;
    the art has to go down first or it covers them (George, 2026-09-16)."""
    layer._artwork_url = "http://art/"
    layer._artwork_source = pygame.Surface((640, 640))

    layer.draw(full(artwork="http://art/"))

    artwork_rect = pygame.Rect(560, 70, 170, 170)
    assert layer._painted[0] == artwork_rect
    text_rects = layer._painted[2:]  # after artwork and badge
    assert text_rects, "text must still be drawn"


def test_each_renderer_gets_its_badge(layer):
    for source in ("lms", "spotify", "bluetooth"):
        badge = layer._badge(source, (50, 50))
        assert badge is not None, source
        assert badge.get_width() <= 50 and badge.get_height() <= 50


def test_the_lyrion_badge_is_tinted_not_black(layer):
    badge = layer._badge("lms", (50, 50))
    opaque = [
        badge.get_at((x, y))
        for x in range(badge.get_width())
        for y in range(badge.get_height())
        if badge.get_at((x, y)).a > 200
    ]
    assert opaque, "the mark has visible pixels"
    assert all(pixel.g > 150 for pixel in opaque)  # the LMS accent is green-teal


def test_an_unknown_source_draws_no_badge(layer):
    assert layer._badge_rect("airplay") is None


def test_the_badge_icons_are_the_uis_own():
    """Copied into the image stage; they must not drift from the UI's."""
    ui_assets = Path(__file__).parents[2] / "ui" / "src" / "assets"
    for name in ("icon-spotify.png", "icon-bluetooth.png", "icon-lyrion.svg"):
        assert (STAGE / "icons" / name).read_bytes() == (ui_assets / name).read_bytes(), name



def test_centred_text_is_centred_inside_its_box_not_around_the_position(screen, tmp_path):
    """The wrapper centres inside a box that STARTS at the position and is as
    wide as the skin's maxwidth. Centring around the position slid the text
    left by half its width, onto the artwork (George, dash-spectrum)."""
    background = pygame.Surface((1280, 800))
    pygame.image.save(background, str(tmp_path / "bgr.png"))
    layer = MetadataLayer(screen, tmp_path)
    layer.set_skin({**SKIN, "playinfo.title.pos": "770,100,bold", "playinfo.maxwidth": "480", "playinfo.center": "True"})

    layer.draw(full(title="Alpenglow"))

    title = layer._painted[1]  # after the badge
    assert title.left >= 770, "never left of where the box starts"
    assert abs((title.left - 770) - (770 + 480 - title.right)) <= 1, "equal space either side"


def test_remaining_time_is_drawn_top_left_at_its_position(layer):
    layer.draw(full(position=30.0, duration=200.0, transport="paused"))

    time_rect = next(r for r in layer._painted if (r.x, r.y) == (900, 500))
    assert time_rect is not None


def test_remaining_time_turns_red_for_the_last_ten_seconds(layer):
    fields = layer._fields(full(position=195.0, duration=200.0, transport="paused"))
    remaining = next(f for f in fields if f[1][:2] == (900, 500))
    assert remaining[2] == FINAL_SECONDS_COLOUR

    fields = layer._fields(full(position=100.0, duration=200.0, transport="paused"))
    remaining = next(f for f in fields if f[1][:2] == (900, 500))
    assert remaining[2] != FINAL_SECONDS_COLOUR


def test_the_badge_is_the_mark_alone(layer):
    """George, 2026-09-18, reversing his 2026-09-16 call: no name beside it.
    The name was the only thing drawn outside the square the skin reserves."""
    plain = layer._badge("spotify", (50, 50))
    rect = layer._badge_rect("spotify")
    assert rect.size == plain.get_size(), "the badge is the mark and nothing else"


@pytest.mark.parametrize("source", ["lms", "spotify", "bluetooth"])
def test_no_skin_draws_the_source_outside_the_box_it_reserved(screen, source):
    """Tier 4, against the real 71 skins rather than a fixture: every pixel of
    the source mark sits inside `playinfo.type.pos`/`.dimension`, which is the
    skin author\'s own reservation, and therefore on screen.

    This is the check that made the label untenable: it was placed beside the
    box with no bounds test, and on 7 skins it left the 1280px screen."""
    layer = MetadataLayer(screen, CORPUS_DIR)
    offenders = []
    for skin in corpus_skins():
        position = parse_size(skin.get("playinfo.type.pos"))
        if position is None:
            continue
        box = parse_size(skin.get("playinfo.type.dimension")) or (50, 50)
        layer._skin = skin
        rect = layer._badge_rect(source)
        if rect is None:
            continue
        reserved = pygame.Rect(position[0], position[1], box[0], box[1])
        if not reserved.contains(rect) or not screen.get_rect().contains(rect):
            offenders.append((skin["name"], tuple(rect), tuple(reserved)))
    assert not offenders, f"{len(offenders)} skins draw the source outside their box: {offenders[:5]}"



def test_the_same_artwork_is_rescaled_when_the_skin_changes(screen, tmp_path):
    """Same track, new skin: the art must take the new skin's size, not keep
    the previous one's (found on the panel after a rotation onto
    dash-spectrum)."""
    pygame.image.save(pygame.Surface((1280, 800)), str(tmp_path / "bgr.png"))
    layer = MetadataLayer(screen, tmp_path)
    layer._artwork_url = "http://art/"
    layer._artwork_source = pygame.Surface((640, 640))

    layer.set_skin({**SKIN, "albumart.pos": "560,70", "albumart.dimension": "170,170"})
    layer.draw(full(artwork="http://art/"))
    assert layer._painted[0].size == (170, 170)

    layer.set_skin({**SKIN, "albumart.pos": "0,15", "albumart.dimension": "770,770"})
    layer.draw(full(artwork="http://art/"))
    assert layer._painted[0].size == (770, 770)
