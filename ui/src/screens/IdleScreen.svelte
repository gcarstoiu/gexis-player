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
  import { onMount, tick } from 'svelte';
  import { fade } from 'svelte/transition';
  import WeatherIcon from './WeatherIcon.svelte';
  import Backdrop from './Backdrop.svelte';
  import { screen } from '../lib/family.svelte.js';

  let { ondismiss, settings = {} } = $props();

  let page = $state(null);
  let pageLoaded = $state(false);
  let now = $state(new Date());
  // ADR-0109: the panel's shape, 1280 logical px by the screen's height.
  let panelHeight = $state(window.innerHeight || 800);
  let panelWidth = $state(window.innerWidth || 1280);
  let spot = $state(randomSpot());
  let weather = $state(null);
  let picture = $state(null);
  let shown = $state(null);

  const external = $derived(settings.idle_screen === 'External URL');
  const wantsWeather = $derived(settings.idle_weather !== false && !external);
  //: `idle_forecast` is two layouts, not a count (design, 2026-09-22):
  //: **3 days** puts a band across the bottom and lets the clock drift in
  //: the upper area; **Today only** ("None" until 2026-10-05) drops the band and brings the current
  //: conditions up under the clock, which then centres over them.
  const threeDays = $derived((settings.idle_forecast ?? '3 days') === '3 days');
  const iconSet = $derived(settings.idle_icons ?? 'Solid');
  //: `idle_clock`, George's row (2026-09-22): *"this way a user can
  //: actually use the panel as a photo frame only"*. The date goes with
  //: it - they are one block and one thought.
  const wantsClock = $derived(settings.idle_clock !== false && !external);
  //: George, 2026-09-28: a 12-hour clock drops the leading zero and says am
  //: or pm after the seconds, at their size.
  const twelve = $derived(settings.clock_format === '12 h');
  const background = $derived(settings.idle_background ?? 'Gexis wallpapers');
  const black = $derived(background === 'Black' || !shown);

  // The design's own two values, and the reasoning is in the header: the
  // stroke is what makes white type survive a photograph, so a screen with
  // no photograph does not want it.
  // The contour's colour; its *width* is per element, below. Transparent
  // rather than zero so the widths stay harmless when there is no picture.

  const stroke = $derived(black ? 'transparent' : 'rgba(46, 57, 66, 0.92)');
  const scrim = $derived(black ? 'rgba(11, 18, 24, 0.93)' : 'rgba(7, 11, 15, 0.06)');

  //: The design's own two drift boxes. With the band below, the clock group
  //: is about 640x226 and roams widely; with the weather riding along it is
  //: about 1180x400, so the box tightens to keep that off the edges.
  //: ADR-0109: the boxes were drawn at 800 tall. On another height the top
  //: of the box stays where it was and its bottom moves with the screen's
  //: bottom edge, so the group keeps the 800 margins (720 on the 13.3").
  function randomSpot() {
    const wide = (settings.idle_forecast ?? '3 days') === '3 days';
    const [top, bottom] = wide ? [17, 55] : [36, 56];
    const low = (top / 100) * 800;
    const high = (bottom / 100) * 800 + (panelHeight - 800);
    return {
      x: Math.round(wide ? 29 + Math.random() * 42 : 41 + Math.random() * 14),
      y: Math.round(((low + Math.random() * (high - low)) / panelHeight) * 100),
    };
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


  onMount(() => {
    fetch('/idle')
      .then((r) => (r.ok ? r.json() : null))
      .then((result) => (page = external && result?.embeddable ? result.url : null))
      .catch(() => (page = null));

    loadWeather();

    const tick = setInterval(() => {
      now = new Date();
      if (now.getSeconds() === 0) {
        spot = randomSpot();
        if (bar) drift = randomDrift();
      }
    }, 1000);
    const forecast = setInterval(loadWeather, 15 * 60 * 1000);
    return () => {
      clearInterval(tick);
      clearInterval(forecast);
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

  const forecastDays = $derived(threeDays ? (weather?.days ?? []).slice(0, 3) : []);
  //: Today's high and low ride with the current conditions in both layouts.
  const today = $derived((weather?.days ?? [])[0] ?? null);
  const drawsWeather = $derived(
    wantsWeather && weather && !weather.off && !weather.error && weather.now
  );
  const wind = $derived(
    weather?.now?.wind === null || weather?.now?.wind === undefined
      ? null
      : `${Math.round(weather.now.wind)} ${weather.wind_unit ?? 'km/h'}`
  );
  // **One line, along the bottom** (George, 2026-09-21). Two stacked lines
  // in a corner read as a block of small print; joined with the separator
  // this panel already uses between facts, they read as a footer.
  const credits = $derived(
    [
      shown && picture?.credit
        ? `${picture.by ? `Photo by ${picture.by} · ` : ''}${picture.credit}`
        : shown && picture?.by
          ? picture.by
          : null,
      wantsWeather && weather?.credit && !weather.off ? weather.credit.text : null,
    ]
      .filter(Boolean)
      .join(' · ')
  );

  //: **ADR-0109, Bar family** (design `Bar Panels` idle, idle-black,
  //: idle-frame; round 2 rules). One row, centred: the clock, a divider,
  //: today, and as many forecast days as the width holds. Feels-like, wind
  //: and the sun pair are dropped by design (review decision 11). The row
  //: drifts sideways only, ±24 px, inside 48 px of padding.
  const bar = $derived(screen.family === 'bar');
  function randomDrift() {
    return Math.round((Math.random() * 2 - 1) * 24);
  }
  let drift = $state(0);
  //: Round 2: days = clamp(floor((W − 1112) / 136), 0, 3) - the row is
  //: 1112 + 136 n wide. With the clock off the weather is alone and takes
  //: all three; with the forecast set to None there are none.
  const barDays = $derived.by(() => {
    if (!threeDays) return 0;
    if (!wantsClock) return 3;
    return Math.max(0, Math.min(3, Math.floor((screen.width - 1112) / 136)));
  });
  //: **The rule assumes today is 360 and a day 100 wide.** Two-digit
  //: negative temperatures make them about 401 and 138 (round-2 review §2),
  //: and a 12-hour clock is wider too. So the row is measured: first
  //: today's type steps down (to 0.8), then a day is dropped, until the row
  //: fits inside the padding and the drift. Nothing overlaps.
  let rowEl = $state(null);
  let todayScale = $state(1);
  let dropped = $state(0);
  const shownDays = $derived(drawsWeather ? (weather?.days ?? []).slice(0, Math.max(0, barDays - dropped)) : []);
  async function fitRow() {
    todayScale = 1;
    dropped = 0;
    await tick();
    const room = () => screen.width - 2 * 48 - 2 * 24;
    while (rowEl && rowEl.scrollWidth > room() && todayScale > 0.81) {
      todayScale = Math.round((todayScale - 0.05) * 100) / 100;
      await tick();
    }
    while (rowEl && rowEl.scrollWidth > room() && dropped < barDays) {
      dropped += 1;
      await tick();
    }
  }
  $effect(() => {
    if (!bar) return;
    // What the row's width depends on.
    weather; barDays; wantsClock; twelve; screen.width; rowEl;
    fitRow();
  });
  onMount(() => {
    if (!bar) return;
    drift = randomDrift();
    document.fonts?.ready.then(() => bar && fitRow());
  });
</script>

<!-- The same three facts in both layouts: feels-like, wind, and the sun
     pair. **Feels-like is always drawn**, even when it equals the reading
     (design, 2026-09-22). Sunrise and sunset carry a mark rather than a
     label - a half sun with rays above the horizon, and a sun below it. -->
{#snippet facts()}
  <div class="facts ink">
    <span class="facts__one">{degrees(weather?.now?.feels_like)}</span>
    <span class="facts__one">{wind ?? '—'}</span>
    <span class="facts__sun">
      <span class="sunline">
        <span class="sunmark sunmark--rise">
          <span class="sunmark__horizon"></span>
          <span class="sunmark__window"><span class="sunmark__disc"></span></span>
          <span class="sunmark__ray sunmark__ray--up"></span>
          <span class="sunmark__ray sunmark__ray--left"></span>
          <span class="sunmark__ray sunmark__ray--right"></span>
        </span>
        <span class="sunline__t sunline__t--rise">{weather?.sun?.rise ?? '—'}</span>
      </span>
      <span class="sunline">
        <span class="sunmark sunmark--set">
          <span class="sunmark__horizon"></span>
          <span class="sunmark__window"><span class="sunmark__disc"></span></span>
        </span>
        <span class="sunline__t sunline__t--set">{weather?.sun?.sets ?? '—'}</span>
      </span>
    </span>
  </div>
{/snippet}

<svelte:window bind:innerHeight={panelHeight} bind:innerWidth={panelWidth} />

<div class="idle" class:idle--bar={bar} transition:fade={{ duration: 520 }} style:--stroke={stroke}>
  <!-- The picture, shared with the waiting screen (ADR-0133). -->
  <Backdrop {settings} active={!external} bind:picture bind:shown />
  {#if !external}
    <div class="scrim" style:background={scrim}></div>

    {#if bar}
      {#if wantsClock || drawsWeather || (wantsWeather && weather?.error)}
        <div class="bi">
          <div class="bi__row" bind:this={rowEl} style:transform={`translateX(${drift}px)`}>
            {#if wantsClock}
              <div class="bi__clockblock">
                <div class="bi__clock">
                  {#if twelve}
                    <span class="bi__hm ink">{now.getHours() % 12 || 12}:{pad(now.getMinutes())}</span>
                    <span class="bi__s ink">{pad(now.getSeconds())} {now.getHours() < 12 ? 'am' : 'pm'}</span>
                  {:else}
                    <span class="bi__hm ink">{pad(now.getHours())}:{pad(now.getMinutes())}</span>
                    <span class="bi__s ink">{pad(now.getSeconds())}</span>
                  {/if}
                </div>
                <div class="bi__date ink">{date}</div>
              </div>
            {/if}
            {#if drawsWeather}
              {#if wantsClock}<span class="bi__divider"></span>{/if}
              <div class="bi__today ink" style:--k={todayScale}>
                <WeatherIcon condition={weather.now.condition} set={iconSet} size={100} />
                <div class="bi__todaytext">
                  <div class="bi__line">
                    <span class="bi__temp">{degrees(weather.now.temperature)}</span>
                    {#if today}
                      <span class="bi__mm">
                        <span class="bi__max">{degrees(today.max)}</span>
                        <span class="bi__min">{degrees(today.min)}</span>
                      </span>
                    {/if}
                  </div>
                  <div class="bi__cond">{WORDS[weather.now.condition] ?? ''}</div>
                </div>
              </div>
              {#if shownDays.length}
                <div class="bi__days">
                  {#each shownDays as day (day.date)}
                    <span class="bi__day">
                      <span class="bi__dayname ink">{short(day.date)}</span>
                      <WeatherIcon condition={day.condition} set={iconSet} size={80} />
                      <span class="bi__daymm ink">
                        <span class="bi__daymax">{degrees(day.max)}</span>
                        <span class="bi__daymin">{degrees(day.min)}</span>
                      </span>
                    </span>
                  {/each}
                </div>
              {/if}
            {:else if wantsWeather && weather?.error}
              {#if wantsClock}<span class="bi__divider"></span>{/if}
              <span class="bi__said ink">{weather.error}</span>
            {/if}
          </div>
        </div>
      {/if}
    {:else if wantsClock || (!threeDays && drawsWeather)}
      <div
        class="clockblock"
        class:clockblock--centred={!threeDays}
        style:left={`${spot.x}%`}
        style:top={`${spot.y}%`}
      >
        {#if wantsClock}
          <div class="clock">
            {#if twelve}
              <span class="clock__hm ink">{now.getHours() % 12 || 12}:{pad(now.getMinutes())}</span>
              <span class="clock__s ink">{pad(now.getSeconds())} {now.getHours() < 12 ? 'am' : 'pm'}</span>
            {:else}
              <span class="clock__hm ink">{pad(now.getHours())}:{pad(now.getMinutes())}</span>
              <span class="clock__s ink">{pad(now.getSeconds())}</span>
            {/if}
          </div>
          <div class="date ink">{date}</div>
        {/if}

        <!-- **The None layout**: no band, and the current conditions ride
             with the clock, which centres over them. -->
        {#if !threeDays && drawsWeather}
          {#if wantsClock}<div class="rule"></div>{/if}
          <div class="now now--big ink">
            <WeatherIcon condition={weather.now.condition} set={iconSet} size={150} />
            <div class="now__text">
              <div class="now__line">
                <span class="now__temp">{degrees(weather.now.temperature)}</span>
                {#if today}
                  <span class="now__mm">
                    <span class="now__max">{degrees(today.max)}</span>
                    <span class="now__min">{degrees(today.min)}</span>
                  </span>
                {/if}
              </div>
              <div class="now__label">{WORDS[weather.now.condition] ?? ''}</div>
            </div>
            <span class="rule rule--tall"></span>
            {@render facts()}
          </div>
        {/if}
      </div>
    {/if}

    {#if bar}
      <!-- The bar draws its weather in the row above. -->
    {:else if threeDays && drawsWeather}
      <div class="band">
        <div class="now ink">
          <WeatherIcon condition={weather.now.condition} set={iconSet} size={132} />
          <div class="now__text">
            <div class="now__line">
              <span class="now__temp">{degrees(weather.now.temperature)}</span>
              {#if today}
                <span class="now__mm">
                  <span class="now__max">{degrees(today.max)}</span>
                  <span class="now__min">{degrees(today.min)}</span>
                </span>
              {/if}
            </div>
            <div class="now__label">{WORDS[weather.now.condition] ?? ''}</div>
          </div>
        </div>
        <span class="rule rule--stretch"></span>
        {@render facts()}
        <!-- A flexing spacer with a floor, so the three days always read as
             their own group however wide the left side gets. -->
        <span class="band__gap"></span>
        <div class="band__days">
          {#each forecastDays as day (day.date)}
            <span class="day">
              <span class="day__name ink">{short(day.date)}</span>
              <WeatherIcon condition={day.condition} set={iconSet} size={100} />
              <span class="day__mm ink">
                <span class="day__max">{degrees(day.max)}</span>
                <span class="day__min">{degrees(day.min)}</span>
              </span>
            </span>
          {/each}
        </div>
      </div>
    {:else if wantsWeather && weather?.error}
      <div class="band band--said"><span class="ink">{weather.error}</span></div>
    {/if}

    {#if credits}
      <div class="credits ink" class:credits--bar={bar}>{credits}</div>
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
    height: 100vh;
    z-index: 20;
    overflow: hidden;
    background: #0b1218;
  }

  .scrim {
    position: absolute;
    inset: 0;
  }

  /* **The contour is what makes the type legible**, not a plate. Painted
     under the fill so the glyph keeps its own weight.

     **Its width is a proportion of the type, not the design's one number.**
     The drop puts 4px on every span that carries it, which is a rim on a
     132px numeral and most of a 21px letter - measured on the panel, the
     clock's ink came out 80% white and the day names 38%, which is why
     George saw them as grey. The stroke tapers with the size now, and the
     sizes the design did its contrast arithmetic for keep its 4px. */
  .ink {
    color: var(--ink);
    paint-order: stroke fill;
    -webkit-text-stroke: var(--stroke-w, 4px) var(--stroke);
    text-shadow: 0 2px 10px rgba(7, 11, 15, 0.55);
  }
  .date,
  .day__name {
    --stroke-w: 1.5px;
  }
  .wx__label,
  .wx__max,
  .wx__min,
  .day__max,
  .day__min {
    --stroke-w: 2px;
  }
  .credits {
    --stroke-w: 1px;
  }

  .clockblock {
    position: absolute;
    /* `max-content`, so the group is never squeezed by how near the right
       edge its drift takes it. */
    width: max-content;
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
  .clockblock--centred {
    align-items: center;
  }
  .date {
    font-family: var(--font-mono);
    font-size: 26px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    white-space: nowrap;
  }

  /* The forecast band, in the `3 days` layout only. It does not drift.
     Named `band`, not `wx`: `WeatherIcon`'s own root carries `wx`, and one
     name for two things read as the band still being there when it was an
     icon that had matched. */
  .band {
    position: absolute;
    left: 0;
    right: 0;
    bottom: 0;
    padding: 22px 28px 26px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    gap: 20px;
  }
  .band--said {
    justify-content: center;
    font-size: var(--t-body);
  }
  .band__gap {
    flex: 1;
    min-width: 64px;
  }

  /* Current conditions: the same block in both layouts, larger in `None`
     where it is the screen's subject rather than a band's left end. */
  .now {
    display: flex;
    align-items: center;
    gap: 28px;
    flex-shrink: 0;
  }
  .now--big {
    gap: 38px;
    margin-top: 24px;
  }
  .now__text {
    min-width: 0;
  }
  .now__line {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .now__temp {
    font-size: 100px;
    font-weight: 300;
    letter-spacing: -0.03em;
    line-height: 0.94;
  }
  .now--big .now__line {
    gap: 18px;
  }
  .now--big .now__temp {
    font-size: 116px;
  }
  /* Stacked, not side by side: the high over the low, left-aligned against
     the temperature. */
  .now__mm {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
    white-space: nowrap;
  }
  .now__max {
    font-size: 40px;
    font-weight: 700;
    color: var(--accent-artist);
  }
  .now__min {
    font-size: 30px;
    color: var(--accent-bluetooth);
  }
  .now--big .now__max {
    font-size: 42px;
  }
  .now--big .now__min {
    font-size: 32px;
  }
  .now__label {
    font-size: 30px;
    font-weight: 600;
    color: var(--accent-lms);
    margin-top: 8px;
    white-space: nowrap;
  }
  .now--big .now__label {
    font-size: 32px;
  }

  /* Hairlines: stretched in the band, a fixed 150px upright in `None`, and
     full-width under the date. */
  .rule {
    width: 100%;
    height: 1px;
    background: rgba(233, 238, 242, 0.32);
    margin-top: 24px;
  }
  .rule--stretch {
    width: 1px;
    height: auto;
    align-self: stretch;
    background: rgba(233, 238, 242, 0.26);
    margin-top: 0;
    flex-shrink: 0;
  }
  .rule--tall {
    width: 1px;
    height: 150px;
    background: rgba(233, 238, 242, 0.3);
    margin-top: 0;
    flex-shrink: 0;
  }

  /* Feels-like, wind, and the sun pair - one column, both layouts. */
  .facts {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 12px;
    flex-shrink: 0;
  }
  .facts__one {
    font-size: 30px;
    font-weight: 700;
    white-space: nowrap;
    align-self: center;
  }
  .facts__sun {
    display: flex;
    flex-direction: column;
    gap: 6px;
    margin-top: 4px;
    min-width: 0;
  }
  .sunline {
    display: flex;
    align-items: center;
    gap: 11px;
    min-width: 0;
  }
  .sunline__t {
    font-size: 30px;
    font-weight: 700;
    white-space: nowrap;
  }
  .sunline__t--rise {
    color: #f2c14f;
  }
  .sunline__t--set {
    color: var(--accent-artist);
  }

  /* The marks: a half sun with three rays standing on the horizon, and the
     same sun fallen below it. A label would say the same thing in two
     words and take four times the room. */
  .sunmark {
    position: relative;
    width: 36px;
    height: 36px;
    flex-shrink: 0;
    display: block;
  }
  .sunmark__horizon {
    position: absolute;
    left: 0;
    width: 36px;
    height: 3px;
    border-radius: 2px;
    background: var(--ink);
  }
  .sunmark--rise .sunmark__horizon {
    bottom: 7px;
  }
  .sunmark--set .sunmark__horizon {
    bottom: 16px;
  }
  /* A window the disc is drawn inside, so half of it shows and no arc has
     to be drawn. */
  .sunmark__window {
    position: absolute;
    left: 6px;
    width: 24px;
    height: 12px;
    overflow: hidden;
  }
  .sunmark--rise .sunmark__window {
    bottom: 10px;
  }
  .sunmark--set .sunmark__window {
    bottom: 2px;
  }
  .sunmark__disc {
    display: block;
    width: 24px;
    height: 24px;
    border-radius: 50%;
  }
  .sunmark--rise .sunmark__disc {
    background: #f2c14f;
  }
  .sunmark--set .sunmark__disc {
    background: var(--accent-artist);
    margin-top: -12px;
  }
  .sunmark__ray {
    position: absolute;
    top: 5px;
    width: 3px;
    height: 8px;
    border-radius: 2px;
    background: #f2c14f;
  }
  .sunmark__ray--up {
    left: 17px;
    top: 1px;
  }
  .sunmark__ray--left {
    left: 4px;
    transform: rotate(-42deg);
  }
  .sunmark__ray--right {
    right: 4px;
    transform: rotate(42deg);
  }

  .band__days {
    display: flex;
    align-items: flex-start;
    gap: 40px;
    flex-shrink: 0;
  }
  .day {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
    flex-shrink: 0;
    min-width: 106px;
  }
  .day__name {
    font-family: var(--font-mono);
    font-size: 26px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }
  .day__mm {
    display: flex;
    align-items: baseline;
    gap: 9px;
  }
  .day__max {
    font-size: 44px;
    font-weight: 700;
    color: var(--accent-artist);
  }
  .day__min {
    font-size: 34px;
    color: var(--accent-bluetooth);
  }

  /* Ours, not the design's. Mono and uppercase is how this panel already
     draws an attribution (now playing's, under a biography).

     **In the band the forecast bar leaves free.** That bar's padding ends
     its content 28px above the edge, so an 11px line sitting 7px up clears
     it without a measurement anyone has to remember - and when the weather
     is off, the footer is simply the only thing down there. */
  .credits {
    position: absolute;
    left: 56px;
    right: 56px;
    bottom: 7px;
    font-family: var(--font-mono);
    font-size: var(--t-micro);
    line-height: 14px;
    letter-spacing: var(--track-wide);
    text-transform: uppercase;
    text-align: center;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  /* ADR-0109, Bar family: the whole strip, W x 400 - the External URL page
     too (review decision 10). */
  .idle--bar {
    width: 100vw;
  }
  .bi {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 48px;
  }
  .bi__row {
    display: flex;
    align-items: center;
    gap: 40px;
    flex-shrink: 0;
    transition: transform 1400ms cubic-bezier(0.4, 0, 0.2, 1);
  }
  .bi__clockblock {
    flex-shrink: 0;
  }
  .bi__clock {
    display: flex;
    align-items: baseline;
    gap: 14px;
    font-family: var(--font-mono);
    font-weight: 300;
    letter-spacing: -0.02em;
    white-space: nowrap;
  }
  .bi__hm {
    font-size: 150px;
    line-height: 1;
  }
  .bi__s {
    font-size: 64px;
    line-height: 1;
    color: var(--accent-lms);
  }
  .bi__date {
    --stroke-w: 1.5px;
    margin-top: 18px;
    font-family: var(--font-mono);
    font-size: 26px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    white-space: nowrap;
  }
  .bi__divider {
    width: 1px;
    height: 220px;
    background: rgba(233, 238, 242, 0.3);
    flex-shrink: 0;
  }
  .bi__today {
    --k: 1;
    display: flex;
    align-items: center;
    gap: 20px;
    flex-shrink: 0;
  }
  .bi__todaytext {
    min-width: 0;
  }
  .bi__line {
    display: flex;
    align-items: flex-start;
    gap: 14px;
    white-space: nowrap;
  }
  .bi__temp {
    font-size: calc(100px * var(--k));
    font-weight: 300;
    letter-spacing: -0.03em;
    line-height: 0.94;
  }
  .bi__mm {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .bi__max {
    --stroke-w: 2px;
    font-size: calc(40px * var(--k));
    font-weight: 700;
    color: var(--accent-artist);
  }
  .bi__min {
    --stroke-w: 2px;
    font-size: calc(30px * var(--k));
    color: var(--accent-bluetooth);
  }
  /* Two lines at most, 240 wide, as round 2 draws it. */
  .bi__cond {
    --stroke-w: 2px;
    margin-top: 8px;
    max-width: 240px;
    font-size: calc(30px * var(--k));
    line-height: 1.15;
    font-weight: 600;
    color: var(--accent-lms);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
  /* A day is as wide as what it says, never under 100: "-12° -18°" is 138. */
  .bi__days {
    display: flex;
    gap: 36px;
    flex-shrink: 0;
  }
  .bi__day {
    min-width: 100px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;
    flex-shrink: 0;
  }
  .bi__dayname {
    --stroke-w: 1.5px;
    font-family: var(--font-mono);
    font-size: 24px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
  }
  .bi__daymm {
    display: flex;
    align-items: baseline;
    gap: 10px;
    white-space: nowrap;
  }
  .bi__daymax {
    --stroke-w: 2px;
    font-size: 36px;
    font-weight: 700;
    color: var(--accent-artist);
  }
  .bi__daymin {
    --stroke-w: 2px;
    font-size: 28px;
    color: var(--accent-bluetooth);
  }
  .bi__said {
    font-size: var(--t-body);
    max-width: 360px;
  }
  .credits--bar {
    left: 64px;
    right: 64px;
    bottom: 8px;
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
