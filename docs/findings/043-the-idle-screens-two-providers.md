# Finding 043 — The idle screen's two providers: what each offers, and what its terms allow

**Date:** 2026-09-21
**Question:** [ADR-0047](../decisions/0047-the-idle-screen-gains-backgrounds-and-weather.md)
is Proposed, and its own summary says the substance of it is *"two
third-party providers are unchosen"* — a weather service and an online
wallpaper service. George, 2026-09-21: *"Start with comparison and
recommendation for the services."*
**Status:** research for Phase 9 subphase 9g. **Nothing is decided here.**
ADR-0047 goes to Accepted on George's choice, not on this.

**Scope, stated up front:**

- **Terms read on 2026-09-21**, plus **live calls made from the device
  itself** — not from the dev machine — because the Pi is what will make
  them, on the network it will make them from. Every number below marked
  *measured* is from `gexis.local` on 2026-09-21.
- **Berlin's coordinates (52.52, 13.41) were used for every weather probe**,
  deliberately: this repository is public and the device's own location is
  not a fact it needs to carry.
- **No image was judged.** Nothing here says whether a museum painting or a
  stock photograph looks right behind a clock on a 1280×800 panel. That is
  George's call and it is the main thing this finding does not answer.
- **No provider was exercised over time.** One or three calls each. Nothing
  about reliability, seasonal load, or what any of these services does at
  3 a.m. in January.
- **Two pages could not be read.** `artic.edu/open-access/public-api`
  returned **403** to both the dev machine and the device, so the Art
  Institute's claims below come from its own API (`api.artic.edu/docs/`,
  reachable, 200) and from its responses' `info.license_text`. Where a
  claim rests on a search result rather than the provider's own page, it
  says so and is **not verified**.
- **Terms change, and these two prove it.** Unsplash and Pexels both now
  name wallpaper applications explicitly. Finding 030's closing warning —
  recheck when the work starts — applies again here.
- **Criteria used:** free; usable by every owner of a Gexis without handing
  a payment card to a third party; a licence that permits this use; and
  able to answer the rows the design actually draws.

## Result

**Both halves have a key-free answer, and for wallpapers the two obvious
names are ruled out by their own terms.**

### Weather

Measured from the device, 2026-09-21:

| Provider | key | measured | limits | licence |
|---|---|---|---|---|
| **Open-Meteo** | none | **200, 748 B, 0.12–0.14 s** (3 runs) | <10,000/day, 5,000/h, 600/min, non-commercial | CC BY 4.0, attribution link required |
| MET Norway | none | 200, **40,722 B**, 0.22 s | 20 req/s per application | CC BY 4.0, commercial use allowed |
| Bright Sky (DWD) | none | 200, 12,529 B, 0.15 s | none published | DWD's own terms |
| OpenWeatherMap One Call 3.0 | key | not called | 1,000/day free | proprietary |
| Pirate Weather | key | not called | 20,000/month free (search result, unverified) | proprietary |

**What decides it is not the weather — it is the four rows around it.**
The design draws `idle_days` (how many days), `idle_minmax` (both
temperatures), `idle_icons` (three icon sets) and `weather_location` (a
place typed by hand).

- **`idle_days` and `idle_minmax`:** Open-Meteo answers them as parameters —
  `forecast_days`, `temperature_2m_max`, `temperature_2m_min` — and returns
  **only the fields asked for**, which is why the same forecast is 748 B
  there and 40,722 B from MET Norway, whose `compact` endpoint returns every
  hour of everything and leaves the daily aggregation to us. Bright Sky is
  hourly records too.
- **`idle_icons`:** Open-Meteo returns a WMO code — a small enumerated set
  that maps cleanly onto three icon sets we draw ourselves. MET Norway
  returns `symbol_code` strings with day/night variants; Bright Sky returns
  its own `icon` field.
- **`weather_location` is the one that settles it.** Somebody has to turn
  "Hamburg" into coordinates. **Open-Meteo has a key-free geocoding API in
  the same house** — measured: 200, 1,247 B, 0.14 s, returning name,
  coordinates, country and IANA timezone. MET Norway and Bright Sky have
  none, so either would need a second provider (Nominatim, whose usage
  policy is strict) for a row the design already specifies.

**One documented behaviour did not reproduce.** MET Norway's terms say a
missing or prohibited User-Agent gets 403. A request from the device with an
empty User-Agent got **200** on 2026-09-21. Identify anyway — the terms
require it, and an enforcement that is off today is not a permission — but
the check is not evidence that our User-Agent is acceptable.

MET Norway also returns `Expires` and `Last-Modified` (measured: a
30-minute window) and its terms require honouring them, which is a real
obligation rather than a nicety.

### Wallpapers online

| Source | key | this use | measured |
|---|---|---|---|
| **Unsplash** | key | **forbidden by its guidelines** | not called |
| **Pexels** | key | **forbidden by its guidelines** | not called |
| Pixabay | key | allowed, with conditions | not called |
| Wallhaven | key (partly) | rights per image unverifiable | not called |
| NASA APOD | DEMO_KEY or free key | most images are copyrighted | 200, `copyright: "Piotr Czerski"` |
| **Art Institute of Chicago** | none | CC0 artworks, key-free | 200, 62,059 public-domain hits on one query |
| The Met | none | CC0 artworks, key-free | 200; `primaryImage` **8.3 MB**, `primaryImageSmall` 221 KB |

**The two obvious names are out, in their own words.** Unsplash: *"You
cannot replicate the core user experience of Unsplash (unofficial clients,
wallpaper applications, etc.)"* Pexels: *"You may not copy or replicate core
functionality of Pexels (including making Pexels content available as a
wallpaper app)."* An idle screen that shows a rotating photograph is the
named example in both. This is not a grey area to be argued; it is the
first thing to know about the row.

**Pixabay is the photographic option that permits it**, at a price in
mechanism: a key per owner, 100 requests per 60 s, *"Requests must be cached
for 24 hours"*, image URLs that expire in 24 hours, and **no permanent
hotlinking** — *"If you intend to use the images, please download them to
your server first."* That makes the device a cache with a size cap and an
eviction rule, not a `<img src>`.

**The museum sources need no key and no account.** The Art Institute's API
is anonymous at **60 requests/minute**, its responses declare CC0, and one
search for public-domain landscapes returned 62,059 of them with IIIF image
URLs at any width we ask for.

**And it carries a trap worth knowing before it costs a session.** The IIIF
image server **403s without an `AIC-User-Agent` header** — measured, with a
plain User-Agent *and* with a browser one. With the header: 200, 162 KB at
843 px, 353 KB at 1280 px. The JSON API answers fine without it, so the
failure appears only when an image is fetched, which is after everything
else looks right.

The Met is the same shape with one number to respect: `primaryImage` was
**8.3 MB** for a single object and `primaryImageSmall` 221 KB. A panel that
downloads the first of those every few minutes is a panel nobody measured.

**NASA APOD is not the public-domain source it is assumed to be.** The live
call on 2026-09-21 came back with a top-level `copyright` field naming a
photographer. Entries without that field are NASA's own and are free to use;
the rest are not, so the source needs filtering *and* a credit line for
what is left.

### Ruled out, and why

- **Unsplash, Pexels** — wallpaper applications named as forbidden in each
  provider's own guidelines.
- **OpenWeatherMap One Call 3.0** — a key and, per the subscription page, a
  payment card on file for the free tier. Every owner of a Gexis would have
  to give a card to a third party to see the weather on a screen they own.
- **Wallhaven** — user-uploaded wallpapers whose rights cannot be verified
  per image. Fine for a person choosing pictures; not something to ship as
  a default on somebody else's appliance.
- **Pirate Weather, WeatherAPI, Tomorrow.io, Visual Crossing** — keyed, and
  none offers anything the key-free options lack for this screen. Not
  researched in depth, which is itself a scope limit.
- **Bright Sky** — DWD data, so its strength is Germany, and it has no
  geocoding. A good second opinion for this device, a poor default for the
  product.

## Recommended, not decided

- **Weather: Open-Meteo.** Key-free, so it works on a device out of the box
  with nothing for the owner to register; 748 B for exactly the fields the
  design draws; geocoding for `weather_location` from the same provider;
  WMO codes for `idle_icons`. **MET Norway is the alternative** if the
  non-commercial clause ever matters — it permits commercial use — at the
  cost of 40 KB per refresh, our own daily aggregation, and a second
  provider for geocoding.
- **Wallpapers online: choose the kind of picture first.** For artwork,
  **the Art Institute of Chicago**, key-free and CC0, with the Met as a
  second source. For photographs, **Pixabay** is the only one of the three
  big stock sites whose terms permit this, and it brings a key and a local
  cache with it.

## Consequences for 9g (not decisions)

- **`weather_key` may have nothing left to gate.** ADR-0047 §2 says weather
  is off unless a key exists, and hangs `weather_location`, `idle_days`,
  `idle_minmax` and `idle_icons` off `onlyWhen: ['weather_key', ANY]`. With
  a key-free provider **there is no key**: the gate becomes `idle_weather`
  alone, and `weather_key` either leaves the registry or stays in it doing
  nothing — which is the state ADR-0022's amendment exists to prevent. The
  same question applies to `wallpaper_key` if the answer is a CC0 museum.
- **Attribution has to be drawn, and the design has nowhere to draw it.**
  Open-Meteo asks for `Weather data by Open-Meteo.com` as a link next to the
  data; MET Norway requires CC BY 4.0 credit; Pixabay asks that users be
  shown where images come from. The idle screen is a clock over a picture
  and carries no attribution element — the same gap Finding 030 recorded for
  enrichment, now on a screen that is up for hours.
- **A source that forbids hotlinking makes the device a cache** — a
  directory, a size cap, an eviction rule, the shape ADR-0012 already has
  for enrichment. Worth doing for the museum sources too: a panel that
  redraws every few minutes should not refetch a 353 KB JPEG each time.
- **Every path degrades to the clock**, which ADR-0047 already states as the
  rule (the region blanks, never the screen). It has to be built, not
  assumed — the device has no network at first boot by ADR-0031.
- **Open-Meteo's free tier is non-commercial.** A GPL appliance each owner
  runs at home fits its own examples; selling a Gexis would not, and that is
  a product question rather than a technical one.
- **Recheck both when the code starts** if that is not this week. Unsplash
  and Pexels both changed in the direction that matters here.

## Sources read

- **Open-Meteo:** open-meteo.com/en/terms, /en/licence, /en/features;
  api.open-meteo.com and geocoding-api.open-meteo.com test calls from the
  device
- **MET Norway:** api.met.no/doc/TermsOfService, api.met.no/doc/GettingStarted
  (search result), locationforecast/2.0 documentation; test calls from the
  device including the empty-User-Agent probe
- **Bright Sky / DWD:** brightsky.dev, brightsky.dev/docs; test call from the
  device
- **OpenWeatherMap:** openweathermap.org/api/one-call-3 and the One Call 3.0
  subscription page (via search result — the card requirement is **not**
  verified against the page itself)
- **Pirate Weather:** docs.pirateweather.net (via search result, unverified)
- **Unsplash:** help.unsplash.com API Guidelines (read directly),
  unsplash.com/api-terms
- **Pexels:** pexels.com/api/documentation (read directly)
- **Pixabay:** pixabay.com/api/docs (read directly)
- **Wallhaven:** wallhaven.cc/help/api (via search result, unverified)
- **NASA:** api.nasa.gov; live APOD call from the device
- **Art Institute of Chicago:** api.artic.edu/docs (read from the device),
  live search and IIIF calls including the 403/200 User-Agent comparison.
  artic.edu/open-access/public-api returned 403 to both machines
- **The Met:** metmuseum.org open-access pages (via search result); live
  object and image calls from the device
- **Wikimedia:** mediawiki.org/wiki/Wikimedia_APIs/Rate_limits (via search
  result); one live feed call from the device
