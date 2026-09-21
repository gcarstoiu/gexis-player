# Finding 043 — The idle screen's two providers: what each offers, and what its terms allow

**Date:** 2026-09-21
**Question:** [ADR-0047](../decisions/0047-the-idle-screen-gains-backgrounds-and-weather.md)
is Proposed, and its own summary says the substance of it is *"two
third-party providers are unchosen"* — a weather service and an online
wallpaper service. George, 2026-09-21: *"Start with comparison and
recommendation for the services."*
**Status:** research for Phase 9 subphase 9g. **Nothing is decided here.**
ADR-0047 goes to Accepted on George's choice, not on this.

> **Corrected 2026-09-21, same day, after George asked "are you sure
> Unsplash is not viable? Please do a thorough check".** The first version
> of this finding ruled out **both Unsplash and Pexels** on one line of each
> provider's guidelines. **Both permit this use**, and each says so on a
> page dedicated to the question that the first pass did not open:
> Unsplash's *Guideline: Replicating Unsplash* names **Trello's board
> backgrounds** as an approved integration, and Pexels' *Can I use the API
> as a wallpaper app?* says a platform that serves a different purpose is
> *"absolutely welcome"* to include a background feature. The wallpaper
> section below is rewritten; `docs/LESSONS.md` case 12 records the shape of
> the mistake.

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
- **Terms change**, and a summary line is not the term. Finding 030's
  closing warning — recheck when the work starts — applies again here, and
  so does the correction above: where a provider has a page dedicated to the
  question being asked, that page is the source, not the bullet that
  mentions it in passing.
- **Criteria used:** free; usable by every owner of a Gexis without handing
  a payment card to a third party; a licence that permits this use; and
  able to answer the rows the design actually draws.

## Result

**Weather has a key-free answer that also solves the row next to it. Every
wallpaper service that matters permits this use** — what separates them is
what a publicly distributed appliance has to do to hold a credential, and
whether a key is wanted at all.

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

**The clause everyone quotes is not the rule.** Both big stock services
prohibit *wallpaper apps* and both, on their own dedicated pages, permit a
background feature inside a product that stands up without it.

**Unsplash's test**, from *Guideline: Replicating Unsplash*: does the
application *"offer more value than simply the Unsplash integration"*. Its
approved examples are Ghost (images in an editor), Medium (images in posts)
and **Trello — *"brings Unsplash images inside Trello's productivity app to
allow users to customize the backgrounds of their boards"***. Its
prohibited example is a wallpaper application that *"returns Unsplash images
for downloading. Without the integration, the app has no content and no
value to users."* A music player whose idle screen offers four backgrounds,
one of which is photographs, is on the Trello side of that line: remove the
integration and the product is unchanged.

**Pexels says it outright**, in *Can I use the API as a wallpaper app?*:
*"if your platform primarily serves a different purpose, you're absolutely
welcome to use our API to include a feature that allows your users to select
a background, header or wallpaper image… The Pexels API is intended to
enhance your user experience, not be the user experience."* It then names
this exact case as an exception: **"Using Pexels images as the default
wallpapers/backgrounds/screensavers within an operating system"**, with a
condition attached — *"If the images are automatically served to the user
without any alteration (eg. as a background or screensaver), the attribution
must be worked into the display."*

| Source | key | permitted for this | what it costs |
|---|---|---|---|
| **Pexels** | per owner | **yes, and the background/screensaver case is named** | 200/h, 20,000/month; credit worked into the display |
| **Unsplash** | see below | **yes by its own test** (Trello) | hotlinked URLs only, a download-event ping, credit **with links**; demo 50/h, production 1,000/h |
| Pixabay | per owner | yes | **no hotlinking** — download first; 24 h cache; 100 req/60 s |
| Art Institute of Chicago | none | yes (CC0) | an `AIC-User-Agent` header; 60 req/min |
| The Met | none | yes (CC0) | `primaryImageSmall`, not the 8.3 MB original |
| Wallhaven | key (partly) | rights per image unverifiable | — |
| NASA APOD | key | most images are copyrighted | measured: `copyright: "Piotr Czerski"` |

**Unsplash's real obstacle is distribution, not the wallpaper clause.** Its
guidelines say an application's keys *"must remain confidential"* and that
*"your users should not be required to create developer accounts"* — and a
GPL appliance whose source is public can satisfy neither by shipping a key
or by asking every owner to register one. Unsplash has an answer for exactly
this shape and names it: *"For decentralized applications, like open source
CMSs WordPress and Ghost, [we] added support for dynamic client
registration… This or the use of a proxy is required for applications where
a single API key can't be shared between all installations due to the code
being publicly distributed. Since this is not a typical use case, you should
reach out to the Unsplash Team."* So the route exists, is documented, and
**starts with an email rather than with code**. A proxy is the other route
and ADR-0028's no-cloud stance rules it out.

**Pexels and Pixabay have no equivalent statement about per-owner keys**,
which is not the same as permission — it is an absence. Each owner getting
their own key is what the design's `wallpaper_key` row already describes,
and for Pexels 200 requests an hour is far more than an idle screen can
spend.

### Ruled out, and why

- **Wallhaven** — user-uploaded wallpapers whose rights cannot be verified
  per image. Fine for a person choosing their own pictures; not something to
  ship as a default on somebody else's appliance.
- **NASA APOD** — the live call on 2026-09-21 came back with a top-level
  `copyright` field naming a photographer, so most days are not NASA's own
  work to give away. Usable only by filtering to entries without that field,
  which is a source that shrinks unpredictably.
- **OpenWeatherMap One Call 3.0** — a key and, per the subscription page, a
  payment card on file for the free tier. Every owner of a Gexis would have
  to give a card to a third party to see the weather on a screen they own.
- **Pirate Weather, WeatherAPI, Tomorrow.io, Visual Crossing** — keyed, and
  none offers anything the key-free options lack for this screen. Not
  researched in depth, which is itself a scope limit.
- **Bright Sky** — DWD data, so its strength is Germany, and it has no
  geocoding. A good second opinion for this device, a poor default for the
  product.

## The weather re-check, asked for the same day

George applied the same challenge to the weather half: *"Before deciding for
weather — same challenge. Do a thorough check again."* Three of the things
the first pass leaned on do not survive it.

**`weather_location` does not lock the choice.** The first pass called
Open-Meteo's geocoder *"the one that settles it"*. It does not: geocoding
happens **once**, when someone types a place, and the coordinates are what
gets stored. Open-Meteo's geocoding API can be called on its own, with any
forecast provider behind it — so this is a convenience, not a dependency.
The alternatives are worse but exist: Nominatim's policy caps regular use at
*"4 requests per minute"* and asks that results be cached; Komoot's Photon
is *"reasonable use only"* with no availability guarantee.

**The payload difference is real and small.** Measured: compact 40,224 B,
complete 62,906 B, against Open-Meteo's 748 B. But `Expires` on the same
response was **nine minutes ahead of the request** (and about thirty ahead
of `last-modified`), so this is one fetch every ten to thirty minutes on a
device that streams music all day. It is tidiness, not cost.

**The aggregation is confirmed and is not much.** Measured: 91 timeseries
entries, fields `instant`, `next_1_hours`, `next_6_hours`, `next_12_hours`,
**and no daily aggregate of any kind** — `idle_minmax` has to be computed
from the hourly values. That is a loop, not a project.

**What actually separates them, once those three are set aside:**

| | Open-Meteo | MET Norway |
|---|---|---|
| free tier | **non-commercial only** | no commercial restriction |
| who runs it | one person, GitHub-sponsor funded; **AGPL and self-hostable**, data mirrored on AWS Open Data | a national meteorological institute with a public mandate |
| obligations | CC BY 4.0 attribution link | CC BY 4.0, identifying User-Agent, honour `Expires` |
| icons | WMO codes, ours to draw | `symbol_code` **plus an MIT-licensed icon set** (`metno/weathericons`) |

**So the decision is a product question, not a technical one:** Open-Meteo's
terms permit *"personal home automation purposes"* and forbid *"integrating
our service into commercial products"*. A Gexis given away fits; a Gexis
sold does not, and it would not be one device breaching the terms but every
unit shipped. MET Norway carries no such clause.

**Everything else was re-checked and stays out.**

- **wttr.in** — key-free, but measured at **three days** of forecast, 39 KB,
  and it is one person's service with no terms page. `idle_days` alone rules
  it out.
- **OpenWeatherMap One Call 3.0** — the claim that a payment card is
  required could not be confirmed in the provider's own words; what *can* be
  said from its own pages is that the One Call subscription page is a
  billing form quoting a per-call price. That is a caution, not a finding.
- **Bright Sky, Pirate Weather, WeatherAPI, Tomorrow.io, Visual Crossing** —
  unchanged, and for WeatherAPI a further point: its free tier is documented
  as non-commercial too, so it trades Open-Meteo's restriction for a key
  without removing the restriction.

## Pixabay, chosen 2026-09-21

George, having looked at the pictures: *"Based on this and the pictures I am
seeing on their website we will go with pixabay."* What the API imposes on
the rows that have to be designed around it:

- **Twenty categories, and one per request.** `backgrounds, fashion, nature,
  science, education, feelings, health, people, religion, places, animals,
  industry, computer, food, sports, transportation, travel, buildings,
  business, music`. The parameter takes a single value, so "nature and
  space" is two requests, or one request per refresh with the topic chosen
  from those selected — the second, given 100 requests per 60 seconds and a
  24-hour caching rule.
- **Two of the four topics George named are not categories.** *Nature* and
  *animals* are; **space** and **landscape** are not — they are search
  terms. So a topic in our settings is **our vocabulary, not Pixabay's**,
  and each one maps to either a `category` or a `q`. That mapping is a
  decision, and it belongs in the ADR rather than in the code that happens
  to implement it.
- **`largeImageURL` is the usable one.** `fullHDURL` and `imageURL` are
  *"only available if your account has been approved for full API access"*,
  which a per-owner key will not be.
- **The device is the cache.** No permanent hotlinking, URLs expire in 24
  hours, requests must be cached for 24 hours — so the picture is fetched to
  disk and the sheet's own rules decide when it is replaced.
- Useful parameters the rows can set or hardcode: `image_type=photo`,
  `orientation=horizontal`, `min_width`/`min_height` for a 1280×800 panel,
  `safesearch`, `editors_choice`, `order=popular|latest`, `per_page` 3–200.

## Recommended, not decided

- **Weather: one question decides it — is a Gexis ever sold?** If no,
  **Open-Meteo**: key-free, 748 B for exactly the fields the design draws,
  geocoding in the same house, and its terms name personal home automation
  as a qualifying use. If yes, or if that is to stay open, **MET Norway**:
  an institute rather than one person, no commercial restriction, an
  MIT-licensed icon set, at the cost of a daily aggregation loop, an
  identifying User-Agent, honouring `Expires`, and a geocoder fetched from
  somewhere else — Open-Meteo's own, which works standalone.
- **Wallpapers online: decided — Pixabay** (George, 2026-09-21, on the
  pictures). The rest of this bullet is what the alternatives were: All
  three stock services permit this use; what separates them is what a
  publicly distributed appliance has to do to hold a credential.
  **Pexels** is the cleanest of them — it names the background/screensaver
  case, 200 requests an hour is far beyond what this screen spends, and a
  per-owner key is exactly what `wallpaper_key` already is. **Unsplash is
  equally permitted and needs an email first** (dynamic client registration,
  because our source is public). **The Art Institute of Chicago remains the
  only option that needs no key at all**, at the cost of showing paintings
  rather than photographs — which is a taste question, and George's.

## Consequences for 9g (not decisions)

- **`weather_key` may have nothing left to gate.** ADR-0047 §2 says weather
  is off unless a key exists, and hangs `weather_location`, `idle_days`,
  `idle_minmax` and `idle_icons` off `onlyWhen: ['weather_key', ANY]`. With
  a key-free provider **there is no key**: the gate becomes `idle_weather`
  alone, and `weather_key` either leaves the registry or stays in it doing
  nothing — which is the state ADR-0022's amendment exists to prevent. The
  same question applies to `wallpaper_key` **only** if the answer is a CC0
  museum. Under any of the three stock services `wallpaper_key` earns its
  place exactly as the design drew it: a secret row each owner fills in.
- **Attribution has to be drawn, and the design has nowhere to draw it.**
  Open-Meteo asks for `Weather data by Open-Meteo.com` as a link next to the
  data; MET Norway requires CC BY 4.0 credit; Pixabay asks that users be
  shown where images come from. **The stock services make it a condition of
  this particular use**: Pexels — *"If the images are automatically served
  to the user without any alteration (eg. as a background or screensaver),
  the attribution must be worked into the display"*; Unsplash — *"Photo by
  [name] on Unsplash"* with both names as links carrying utm parameters, and
  its attribution guideline offers no exemption for a screen nobody clicks.
  The idle screen is a clock over a picture and carries no attribution
  element — the same gap Finding 030 recorded for enrichment, now on a
  screen that is up for hours and, for two of the three sources, a condition
  of using them at all.
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
- **Unsplash:** help.unsplash.com API Guidelines, **Guideline: Replicating
  Unsplash**, Guideline: Attribution, "When should I apply for a higher rate
  limit" (all read directly), unsplash.com/api-terms, unsplash.com/documentation
- **Pexels:** pexels.com/api/documentation (read directly);
  help.pexels.com **"Can I use the API as a wallpaper app?"** — 403 to both
  machines, read in full through a reader proxy from the device, the same
  route Finding 030 used for Discogs
- **Pixabay:** pixabay.com/api/docs (read directly, twice — the second time
  for the category list and the image URL fields)
- **Wallhaven:** wallhaven.cc/help/api (via search result, unverified)
- **NASA:** api.nasa.gov; live APOD call from the device
- **Art Institute of Chicago:** api.artic.edu/docs (read from the device),
  live search and IIIF calls including the 403/200 User-Agent comparison.
  artic.edu/open-access/public-api returned 403 to both machines
- **The Met:** metmuseum.org open-access pages (via search result); live
  object and image calls from the device
- **Weather re-check (2026-09-21):** api.met.no locationforecast
  documentation, github.com/metno/weathericons (MIT),
  operations.osmfoundation.org Nominatim usage policy, open-meteo.com/en/terms
  re-read in full, github.com/open-meteo/open-meteo (AGPL, self-hosting),
  openweathermap.org One Call pages (the free-tier wording could **not** be
  confirmed), live wttr.in and met.no compact/complete calls from the device
- **Wikimedia:** mediawiki.org/wiki/Wikimedia_APIs/Rate_limits (via search
  result); one live feed call from the device
