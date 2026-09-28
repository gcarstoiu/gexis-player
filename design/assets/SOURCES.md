# Where these files come from

Recorded 2026-09-27, after George asked for every mark and sample to be
sourced (ADR-0099, finding 5). The copies in `design/source/`, `ui/src/assets/`,
`image/stage-gexis/05-peppy/files/icons/` and the built-in plugins' `mark.png`
are byte-identical to these.

## Sample photos (design prototypes only; not in the player)

| File | What | Source | Licence |
|---|---|---|---|
| `album-art.webp` | Wassily Kandinsky, *Several Circles* (1926), cropped square, 720 px | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Vassily_Kandinsky,_1926_-_Several_Circles,_Gugg_0910_25.jpg) | Public domain (the artist died in 1944) |
| `artist-photo.webp` | Charlie Parker, Tommy Potter, Miles Davis, Duke Jordan, Max Roach at the Three Deuces, New York, c. August 1947, by William P. Gottlieb; cropped square, 720 px | [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Charlie_Parker,_Tommy_Potter,_Miles_Davis,_Duke_Jordan,_Max_Roach_(Gottlieb_06851).jpg), Library of Congress, Music Division (gottlieb.06851) | Public domain, dedicated by the Library of Congress in 2010 |

They replace two photographs of real, identifiable people that arrived through
Claude Design with no recorded source. Those are still in the repository's history.

## Marks (trademarks, used only to name what they belong to)

| File | Whose | Source | Notes |
|---|---|---|---|
| `icon-spotify.png` | Spotify AB | Spotify's 2024 icon, [developer.spotify.com/documentation/design](https://developer.spotify.com/documentation/design) (`2024-spotify-logo-icon.zip`) | A raster of the official green icon: under 1 % of pixels differ, all on edges. Spotify's guidelines ask for the green icon only on black or white. |
| `icon-lyrion.svg` | Lyrion Music Server | [LMS-Community/lms-community.github.io @ 07325bf](https://github.com/LMS-Community/lms-community.github.io/blob/07325bf6c9b8db4bd1409de29706d0a56f7034c2/assets/icon/Lyrion%20-%20logo%20-%20lime.svg), the lime logo | The official file, minified: all ten path starts match. Lyrion's terms (§6b) allow its digital assets in combination with its software. |
| `icon-bluetooth.png` | **Gexis's own**, not Bluetooth SIG's mark | Drawn 2026-09-27 from `design/marks/bluetooth.svg` (George: option B1, a phone sending sound), in the panel's `--accent-bluetooth` | Replaces a redraw of Bluetooth SIG's figure mark, which it licenses only to members' qualified products. |

## Gexis's own marks

`design/marks/` holds the SVG sources of marks drawn for the player, GPL-3.0
like the rest of it: `bluetooth.svg` (B1).
