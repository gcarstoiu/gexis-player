<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Idle screen (ADR-0019, ADR-0033, ADR-0047). An overlay: whatever was
  underneath stays mounted, so dismissing it returns there.

  **`idle_screen: External URL` replaces all of it** with that page, which is
  ADR-0033's answer kept as one option rather than as the answer. Otherwise
  this is the built-in screen: a clock that moves so the panel does not burn
  in, over whichever background `idle_background` names, carrying the
  forecast when `idle_weather` is on.

  **Everything drawn moves with the clock.** A forecast pinned to a corner
  for six hours a night is the burn-in this screen exists to avoid, so the
  weather and the credits ride in the same block and drift with it. It is
  also why the background is a picture that changes: a still image is the
  same problem more slowly.

  **The credits are a licence condition, not decoration** (ADR-0047 §2c):
  Open-Meteo asks for its line beside the data, Pixabay asks that users be
  shown where the pictures come from. They are drawn whenever the thing they
  credit is on screen.
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

  // The clock never sits in the same place twice in a row, and never near
  // enough to an edge for the forecast under it to fall off the panel.
  function randomSpot() {
    return { x: Math.round(30 + Math.random() * 40), y: Math.round(26 + Math.random() * 40) };
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

  // **Loaded before it is shown.** Swapping `src` on a visible image paints
  // the gap; this holds the new picture until the browser has it, then
  // crosses to it, so a slow fetch is invisible rather than a black flash.
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
    // Open-Meteo's own models update hourly and the daemon holds a forecast
    // for fifteen minutes, so this is a redraw asking for what is already
    // there rather than a call.
    const forecast = setInterval(loadWeather, 15 * 60 * 1000);
    // `wallpaper_interval` is minutes, and it is the only timer on this
    // screen the user chose.
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
  const weekday = (iso) =>
    new Date(`${iso}T12:00:00`).toLocaleDateString(undefined, { weekday: 'short' });

  // Today is "Today", because a row that says "Mon" next to a clock showing
  // Monday afternoon reads as a forecast for a week away.
  const forecastDays = $derived(
    (weather?.days ?? []).slice(0, Math.max(1, days)).map((day, i) => ({
      ...day,
      label: i === 0 ? 'Today' : weekday(day.date),
    }))
  );
</script>

<div class="idle" transition:fade={{ duration: 520 }}>
  {#if shown && !external}
    <!-- Two layers, not one: the picture, then a wash that keeps white type
         legible over a photograph nobody chose for its contrast. -->
    {#key shown}
      <div class="picture" style:background-image={`url("${shown}")`} in:fade={{ duration: 900 }}></div>
    {/key}
    <div class="wash"></div>
  {/if}

  <div class="block" style:left={`${spot.x}%`} style:top={`${spot.y}%`}>
    <div class="clock">
      <span class="clock__hm">{pad(now.getHours())}:{pad(now.getMinutes())}</span>
      <span class="clock__s">{pad(now.getSeconds())}</span>
    </div>

    {#if wantsWeather && weather && !weather.off}
      {#if weather.error}
        <div class="weather weather--said">{weather.error}</div>
      {:else if weather.now}
        <div class="weather">
          <div class="now">
            <WeatherIcon condition={weather.now.condition} set={iconSet} size={52} />
            <span class="now__t">{degrees(weather.now.temperature)}</span>
            <span class="now__where">{weather.place}</span>
          </div>
          <div class="days">
            {#each forecastDays as day (day.date)}
              <div class="day">
                <span class="day__name">{day.label}</span>
                <WeatherIcon condition={day.condition} set={iconSet} size={30} />
                <span class="day__max">{degrees(day.max)}</span>
                {#if minmax}<span class="day__min">{degrees(day.min)}</span>{/if}
              </div>
            {/each}
          </div>
        </div>
      {/if}
    {/if}

    <!-- ADR-0047 §2c. Two credits, each drawn only while what it credits is
         on screen: the photographer where a wallpaper came from a service,
         and Open-Meteo wherever its data is shown.

         An artist picture carries neither - it came from the owner's own
         server - but it does carry **who it is**. A face on the idle screen
         of a music player with no name under it is a question the screen
         could have answered. -->
    {#if (picture?.by && shown) || (wantsWeather && weather?.credit && !weather.off)}
      <div class="credits">
        {#if picture?.credit && shown}
          <span>{picture.by ? `Photo by ${picture.by} · ` : ''}{picture.credit}</span>
        {:else if picture?.by && shown}
          <span class="credits--who">{picture.by}</span>
        {/if}
        {#if wantsWeather && weather?.credit && !weather.off}
          <span>{weather.credit.text}</span>
        {/if}
      </div>
    {/if}
  </div>

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
    background: rgba(11, 18, 24, 0.93);
  }

  .picture {
    position: absolute;
    inset: 0;
    background-size: cover;
    background-position: center;
  }
  /* An even, gentle darkening so the picture stays a picture. What makes
     the type legible is the scrim under the block itself, below - a fixed
     dark patch cannot do it, because the block moves and the patch does
     not. Seen on the panel: a clock over a sunlit flower. */
  .wash {
    position: absolute;
    inset: 0;
    background: rgba(6, 10, 14, 0.34);
  }

  .block {
    position: absolute;
    transform: translate(-50%, -50%);
    display: flex;
    flex-direction: column;
    gap: 22px;
    max-width: 620px;
    isolation: isolate;
    transition:
      left 1400ms cubic-bezier(0.4, 0, 0.2, 1),
      top 1400ms cubic-bezier(0.4, 0, 0.2, 1);
  }
  /* The scrim rides with the type. A gradient, not a blur: ADR-0041 - a
     backdrop-filter reads the screen back every frame and costs 24.5 ms
     against a 16.7 ms budget, and this screen is up for hours. */
  .block::before {
    content: '';
    position: absolute;
    /* **Far wider than it looks.** The gradient has to reach zero inside
       its own box, or the box's own edges draw as a rectangle over the
       picture - which is exactly what the first version did, plainly
       visible over a white petal. */
    inset: -170px -260px -140px -220px;
    z-index: -1;
    background: radial-gradient(
      46% 46% at 44% 48%,
      rgba(6, 10, 14, 0.88) 0%,
      rgba(6, 10, 14, 0.7) 40%,
      rgba(6, 10, 14, 0.34) 68%,
      rgba(6, 10, 14, 0) 88%
    );
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
    color: rgba(233, 238, 242, 0.92);
  }
  .clock__s {
    font-size: 58px;
    line-height: 1;
    color: rgba(126, 214, 188, 0.55);
  }

  .weather {
    display: flex;
    flex-direction: column;
    gap: 16px;
    color: rgba(233, 238, 242, 0.88);
  }
  .weather--said {
    font-size: 17px;
    color: rgba(233, 238, 242, 0.55);
  }

  .now {
    display: flex;
    align-items: center;
    gap: 16px;
  }
  .now__t {
    font-family: var(--font-mono);
    font-size: 52px;
    font-weight: 300;
    line-height: 1;
  }
  .now__where {
    font-size: 19px;
    font-weight: 600;
    color: rgba(233, 238, 242, 0.62);
    padding-top: 6px;
  }

  .days {
    display: flex;
    gap: 26px;
  }
  .day {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 6px;
    min-width: 62px;
  }
  .day__name {
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.55);
  }
  .day__max {
    font-family: var(--font-mono);
    font-size: 21px;
    color: rgba(233, 238, 242, 0.92);
  }
  .day__min {
    font-family: var(--font-mono);
    font-size: 16px;
    color: rgba(233, 238, 242, 0.5);
  }

  .credits--who {
    font-size: 15px;
    font-weight: 600;
    color: rgba(233, 238, 242, 0.62);
  }
  .credits {
    display: flex;
    flex-wrap: wrap;
    gap: 6px 18px;
    font-size: 12px;
    letter-spacing: 0.02em;
    color: rgba(233, 238, 242, 0.42);
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
