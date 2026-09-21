<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Idle screen (ADR-0019, ADR-0033, ADR-0047).

  **The design draws this screen and I did not look for it.** It is in
  `design/source/Now Playing.dc.html`, not in a file of its own -
  `screens.md` says so in its first paragraph: *"the rest are described here
  so the shape is known, and are all in `source/Now Playing.dc.html` except
  Settings"*. The first version of this screen was invented against that
  file's prose summary. What follows is the drawing.

  **Two things it settles that were guessed wrong:**

  - **The clock and the date drift; the weather does not.** The forecast is a
    bar pinned across the bottom, 24/56/28 of padding, the current conditions
    at the left and the days at the right. Only the clock block moves, and it
    moves by `left`/`top` over 1400ms, which is the design's own transition.
  - **There is no plate behind the type.** The design rejects one in a
    comment and says why: at `brightness(0.62)` a white region of the photo
    reaches 158, where ink-on-field is ~2.6:1, so **legibility comes from a
    contour on the glyphs** - a 4px slate stroke painted under the fill,
    which holds 10.1:1 against the ink and 4.4:1 against the brightest field.
    Black is the exception: no stroke, and a 0.93 scrim instead.

  The credits are ours, not the design's (ADR-0047 §2c): Open-Meteo's licence
  asks for a line beside the data and Pixabay asks that people be shown where
  the pictures come from. They take the same contour, and the mono uppercase
  treatment this panel already uses for an attribution.
-->
<script>
  import { onMount } from 'svelte';
  import { fade } from 'svelte/transition';
  import WeatherIcon from './WeatherIcon.svelte';

  let { ondismiss, settings = {} } = $props();

  let page = $state(null);
  let pageLoaded = $state(false);
  let now = $state(new Date());
  let spot = $state(randomSpot());
  let weather = $state(null);
  let picture = $state(null);
  let shown = $state(null);

  const external = $derived(settings.idle_screen === 'External URL');
  const wantsWeather = $derived(settings.idle_weather !== false && !external);
  const days = $derived(Number(settings.idle_days ?? 4));
  const minmax = $derived(settings.idle_minmax !== false);
  const iconSet = $derived(settings.idle_icons ?? 'Solid');
  const background = $derived(settings.idle_background ?? 'Artist pictures');
  const black = $derived(background === 'Black' || !shown);

  // The design's own two values, and the reasoning is in the header: the
  // stroke is what makes white type survive a photograph, so a screen with
  // no photograph does not want it.
  const stroke = $derived(black ? '0' : '4px rgba(46, 57, 66, 0.92)');
  const scrim = $derived(black ? 'rgba(11, 18, 24, 0.93)' : 'rgba(7, 11, 15, 0.06)');

  // Kept clear of the forecast bar below and the credits above.
  function randomSpot() {
    return { x: Math.round(30 + Math.random() * 40), y: Math.round(26 + Math.random() * 22) };
  }

  async function loadWeather() {
    if (!wantsWeather) return;
    try {
      const response = await fetch('/idle/weather');
      weather = response.ok ? await response.json() : null;
    } catch {
      weather = null;
    }
  }

  // **Loaded before it is shown.** Swapping the source on a visible picture
  // paints the gap; this holds the new one until the browser has it.
  async function loadPicture() {
    if (external || background === 'Black') return;
    let answer;
    try {
      const response = await fetch('/idle/wallpaper');
      answer = response.ok ? await response.json() : null;
    } catch {
      answer = null;
    }
    if (!answer?.url) {
      picture = answer ?? null;
      return;
    }
    const image = new Image();
    image.onload = () => {
      picture = answer;
      shown = answer.url;
    };
    image.onerror = () => (picture = { error: 'That picture could not be loaded.' });
    image.src = answer.url;
  }

  onMount(() => {
    fetch('/idle')
      .then((r) => (r.ok ? r.json() : null))
      .then((result) => (page = external && result?.embeddable ? result.url : null))
      .catch(() => (page = null));

    loadWeather();
    loadPicture();

    const tick = setInterval(() => {
      now = new Date();
      if (now.getSeconds() === 0) spot = randomSpot();
    }, 1000);
    const forecast = setInterval(loadWeather, 15 * 60 * 1000);
    const every = Math.max(1, Number(settings.wallpaper_interval ?? 15)) * 60 * 1000;
    const pictures = setInterval(loadPicture, every);
    return () => {
      clearInterval(tick);
      clearInterval(forecast);
      clearInterval(pictures);
    };
  });

  const pad = (n) => String(n).padStart(2, '0');
  const degrees = (value) =>
    value === null || value === undefined ? '—' : `${Math.round(value)}°`;

  // The design's date line: "Monday · 21 September", uppercased by the
  // stylesheet rather than by the string.
  const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ];
  const date = $derived(`${DAYS[now.getDay()]} · ${now.getDate()} ${MONTHS[now.getMonth()]}`);

  // The design's columns are short weekdays - "Fri", "Sat" - and today is
  // named like any other, because the bar is read across rather than down.
  const short = (iso) =>
    new Date(`${iso}T12:00:00`).toLocaleDateString(undefined, { weekday: 'short' });

  // The word under the temperature. The design shows "Partly cloudy"; this
  // is the same sentence for every condition a forecast can return.
  const WORDS = {
    'clear': 'Clear',
    'mostly-clear': 'Mostly clear',
    'partly-cloudy': 'Partly cloudy',
    'overcast': 'Overcast',
    'fog': 'Fog',
    'drizzle': 'Drizzle',
    'freezing-drizzle': 'Freezing drizzle',
    'rain': 'Rain',
    'heavy-rain': 'Heavy rain',
    'freezing-rain': 'Freezing rain',
    'showers': 'Showers',
    'heavy-showers': 'Heavy showers',
    'snow': 'Snow',
    'heavy-snow': 'Heavy snow',
    'snow-grains': 'Snow grains',
    'snow-showers': 'Snow showers',
    'thunderstorm': 'Thunderstorm',
    'thunderstorm-hail': 'Thunderstorm, hail',
    'unknown': '',
  };

  const forecastDays = $derived((weather?.days ?? []).slice(0, Math.max(3, Math.min(5, days))));
  const credits = $derived(
    [
      shown && picture?.credit
        ? `${picture.by ? `Photo by ${picture.by} · ` : ''}${picture.credit}`
        : shown && picture?.by
          ? picture.by
          : null,
      wantsWeather && weather?.credit && !weather.off ? weather.credit.text : null,
    ].filter(Boolean)
  );
</script>

<div class="idle" transition:fade={{ duration: 520 }} style:--stroke={stroke}>
  {#if shown && !external}
    {#key shown}
      <img class="bg" src={shown} alt="" in:fade={{ duration: 900 }} />
    {/key}
  {/if}
  {#if !external}
    <div class="scrim" style:background={scrim}></div>

    <div class="clockblock" style:left={`${spot.x}%`} style:top={`${spot.y}%`}>
      <div class="clock">
        <span class="clock__hm ink">{pad(now.getHours())}:{pad(now.getMinutes())}</span>
        <span class="clock__s ink">{pad(now.getSeconds())}</span>
      </div>
      <div class="date ink">{date}</div>
    </div>

    {#if wantsWeather && weather && !weather.off && !weather.error && weather.now}
      <div class="wx">
        <div class="wx__now">
          <WeatherIcon condition={weather.now.condition} set={iconSet} size={124} />
          <div class="wx__text">
            <div class="wx__line">
              <span class="wx__temp ink">{degrees(weather.now.temperature)}</span>
              {#if minmax && forecastDays[0]}
                <span class="wx__mm ink">
                  <span class="wx__max">{degrees(forecastDays[0].max)}</span>
                  <span class="wx__min">{degrees(forecastDays[0].min)}</span>
                </span>
              {/if}
            </div>
            <div class="wx__label ink">{WORDS[weather.now.condition] ?? ''}</div>
          </div>
        </div>
        <span class="wx__gap"></span>
        <div class="wx__days">
          {#each forecastDays as day (day.date)}
            <span class="day">
              <span class="day__name ink">{short(day.date)}</span>
              <WeatherIcon condition={day.condition} set={iconSet} size={80} />
              <span class="day__mm ink">
                <span class="day__max">{degrees(day.max)}</span>
                {#if minmax}<span class="day__min">{degrees(day.min)}</span>{/if}
              </span>
            </span>
          {/each}
        </div>
      </div>
    {:else if wantsWeather && weather?.error}
      <div class="wx wx--said"><span class="ink">{weather.error}</span></div>
    {/if}

    {#if credits.length}
      <div class="credits ink">
        {#each credits as line (line)}<span>{line}</span>{/each}
      </div>
    {/if}
  {/if}

  {#if page}
    <!-- No allow-top-navigation: a page that frame-busts must not navigate the kiosk away from this UI. -->
    <iframe
      class="page"
      class:page--loaded={pageLoaded}
      src={page}
      title="Idle page"
      sandbox="allow-scripts allow-same-origin"
      onload={() => (pageLoaded = true)}
    ></iframe>
  {/if}

  <!-- Above the iframe, which would otherwise swallow the touch. -->
  <div class="touch" role="presentation" onpointerdown={ondismiss}></div>
</div>

<style>
  .idle {
    position: fixed;
    top: 0;
    left: 0;
    width: 1280px;
    height: 800px;
    z-index: 20;
    overflow: hidden;
    background: #0b1218;
  }

  /* The design's own treatment: the picture is dimmed and slightly
     desaturated in the image itself, not under a dark sheet. */
  .bg {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    filter: brightness(0.62) saturate(0.9);
  }
  .scrim {
    position: absolute;
    inset: 0;
  }

  /* **The contour is what makes the type legible**, not a plate. Painted
     under the fill so the glyph keeps its own weight. */
  .ink {
    color: var(--ink);
    paint-order: stroke fill;
    -webkit-text-stroke: var(--stroke);
    text-shadow: 0 2px 10px rgba(7, 11, 15, 0.55);
  }

  .clockblock {
    position: absolute;
    transform: translate(-50%, -50%);
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
    transition:
      left 1400ms cubic-bezier(0.4, 0, 0.2, 1),
      top 1400ms cubic-bezier(0.4, 0, 0.2, 1);
  }
  .clock {
    display: flex;
    align-items: baseline;
    gap: 14px;
    font-family: var(--font-mono);
    font-weight: 300;
    letter-spacing: -0.02em;
    white-space: nowrap;
  }
  .clock__hm {
    font-size: var(--t-hero);
    line-height: 1;
  }
  .clock__s {
    font-size: 58px;
    line-height: 1;
    color: var(--accent-lms);
  }
  .date {
    font-family: var(--font-mono);
    font-size: 21px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    white-space: nowrap;
  }

  /* The forecast is a bar across the bottom, and it does not drift. */
  .wx {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    padding: 24px 56px 28px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 52px;
  }
  .wx--said {
    justify-content: center;
    font-size: var(--t-body);
  }
  .wx__now {
    display: flex;
    align-items: center;
    gap: 24px;
    flex-shrink: 0;
  }
  .wx__text {
    min-width: 0;
  }
  .wx__line {
    display: flex;
    align-items: baseline;
    gap: 16px;
  }
  .wx__temp {
    font-size: 104px;
    font-weight: 300;
    letter-spacing: -0.03em;
    line-height: 0.94;
  }
  .wx__mm,
  .day__mm {
    display: flex;
    align-items: baseline;
    gap: 9px;
    white-space: nowrap;
  }
  /* The high carries the warm accent and the low the cool one, which is how
     the design tells them apart without a label. */
  .wx__max,
  .day__max {
    font-size: 36px;
    font-weight: 700;
    color: var(--accent-artist);
  }
  .wx__min,
  .day__min {
    font-size: 26px;
    color: var(--accent-bluetooth);
  }
  .wx__label {
    font-size: 26px;
    font-weight: 600;
    color: var(--accent-lms);
    margin-top: 6px;
    white-space: nowrap;
  }
  .wx__gap {
    flex: 1;
    min-width: 0;
  }
  .wx__days {
    display: flex;
    align-items: flex-start;
    gap: 32px;
    flex-shrink: 0;
  }
  .day {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
    min-width: 104px;
  }
  .day__name {
    font-family: var(--font-mono);
    font-size: 21px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }

  /* Ours, not the design's. Mono and uppercase is how this panel already
     draws an attribution (now playing's, under a biography). Top right,
     clear of the clock's drift and of the forecast bar. */
  .credits {
    position: absolute;
    top: 24px;
    right: 56px;
    display: flex;
    flex-direction: column;
    align-items: flex-end;
    gap: 4px;
    font-family: var(--font-mono);
    font-size: var(--t-label-sm);
    letter-spacing: var(--track-wide);
    text-transform: uppercase;
    text-align: right;
  }

  .page {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: 0;
    opacity: 0;
    transition: opacity 520ms ease;
  }
  .page--loaded {
    opacity: 1;
  }

  .touch {
    position: absolute;
    inset: 0;
  }
</style>
