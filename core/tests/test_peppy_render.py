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
from gexis_peppy_render import MetadataLayer, parse_colour, parse_point, remaining_time  # noqa: E402

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
        ({"position": 30.0, "duration": 200.0, "transport": "paused", "written_at": 0}, "-2:50"),
        ({"position": None, "duration": 200.0, "transport": "playing"}, None),
        ({"position": 30.0, "duration": None, "transport": "playing"}, None),
        ({"position": 300.0, "duration": 200.0, "transport": "paused", "written_at": 0}, "-0:00"),
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
