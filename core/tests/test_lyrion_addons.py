"""ADR-0115: Lyrion's add-ons, installed through its own plugin page."""
from __future__ import annotations

from gexis_core import lyrion_addons as la

PAGE = """<html><body>
<form name="settingsForm" id="settingsForm" method="post" action="/settings/server/plugins.html?playerid=x">
<input type="hidden" name="pageAntiCSRFToken" value="tok">
<input name="InternetRadio" id="InternetRadio" checked=checked type="checkbox" value="Radio" />
<input name="SongLyrics" id="SongLyrics" type="checkbox" value="Song Lyrics" />
<input name="MaterialSkin" id="MaterialSkin" type="checkbox" value="Material Skin" />
<input name="MusicArtistInfo" id="MusicArtistInfo" checked=checked type="checkbox" value="Music and Artist Information" />
<input name="RadioNowPlaying" id="RadioNowPlaying" type="checkbox" value="Radio Now Playing" />
<input type="submit" name="saveSettings" value="Apply">
</form></body></html>"""


def test_it_knows_which_of_ours_are_not_installed():
    assert la.missing(PAGE) == ["MaterialSkin", "RadioNowPlaying"]


def test_the_form_goes_back_with_everything_as_it_was_and_ours_ticked():
    """Saving the page disables an unticked plugin that is installed, so
    every other box must go back exactly as Lyrion drew it."""
    action, fields = la.submission(PAGE)
    assert action == "/settings/server/plugins.html?playerid=x"
    names = [n for n, _ in fields]
    assert ("pageAntiCSRFToken", "tok") in fields
    assert "InternetRadio" in names, "on before, on after"
    assert "SongLyrics" not in names, "off before, off after - the user's choice"
    assert {"MaterialSkin", "MusicArtistInfo", "RadioNowPlaying"} <= set(names)
    assert names.count("MusicArtistInfo") == 1
    assert "saveSettings" in names


def test_a_page_without_the_form_is_refused():
    import pytest
    with pytest.raises(ValueError):
        la.submission("<html>Server is starting</html>")
