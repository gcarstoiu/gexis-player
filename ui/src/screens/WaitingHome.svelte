<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The panel's root with LMS off** (ADR-0079), **as ADR-0133 draws it**.
  George, 2026-10-10, on three options: *"I kind of like all three. Can you
  mix all three into one design? A bit less text, but with the clock and
  wallpaper."*

  - **The background is its own** (`Backdrop` with `screen="home"`, the
    Home screen section's rows since 2026-10-11): the player's own
    wallpapers by default.
  - **The clock, the date and the player's name** sit in the top left,
    smaller than the idle screen's (*Clock on the waiting screen*).
  - **Each waiting source pulses at the foot** - the marks, names and
    states of the library's waiting footer (`WaitingServices`), straight on
    the picture without its plate (George, 2026-10-18); no other text (its
    hint line went the same day). On a bar, the clock is a column on the left
    and the marks stand beside it.
  - **Settings stays the button in the corner** (ADR-0079), and a screen
    with every source switched off says so.

-->
<script>
  import { onMount } from 'svelte';
  import Backdrop from './Backdrop.svelte';
  import WaitingServices from './WaitingServices.svelte';
  import { pressing } from '../lib/press.svelte.js';
  import { sources } from '../lib/state.js';
  import { settingsDevice } from '../lib/settings.js';
  import { screen } from '../lib/family.svelte.js';

  // `reading`: the Lyrion server's stage while a new player's library is
  // still being read (George, 2026-10-18, option A: the waiting screen stays
  // until the first scan is done, and says so plainly enough to read from
  // across the room).
  let { availability = {}, onsettings, settings = {}, reading = null } = $props();
  const readingShare = $derived(reading?.share ?? null);

  const press = pressing();
  let picture = $state(null);
  let shown = $state(null);
  let now = $state(new Date());

  // ADR-0086: whatever is installed, not a list written here.
  const waiting = $derived(
    Object.values($sources).filter((s) => s.kind === 'renderer' && availability[s.id]),
  );
  // Every source switched off is reachable now that the rows work (ADR-0077),
  // and an empty screen with no way off it would be the panel bricking itself.
  const none = $derived(waiting.length === 0);

  const bar = $derived(screen.family === 'bar');
  const wantsClock = $derived(settings.waiting_clock !== false);
  const twelve = $derived(settings.clock_format === '12 h');
  const name = $derived($settingsDevice.name || '');

  const pad = (n) => String(n).padStart(2, '0');
  const DAYS = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
  const MONTHS = [
    'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
  ];
  const time = $derived(
    twelve
      ? `${now.getHours() % 12 || 12}:${pad(now.getMinutes())}`
      : `${pad(now.getHours())}:${pad(now.getMinutes())}`,
  );
  const meridiem = $derived(twelve ? (now.getHours() < 12 ? 'am' : 'pm') : '');
  const date = $derived(`${DAYS[now.getDay()]} ${now.getDate()} ${MONTHS[now.getMonth()]}`);

  // The picture's credit, as the idle screen draws it: Pixabay's terms ask
  // that people be shown where a picture comes from, and the player's own
  // carry their authors.
  const credit = $derived(
    shown && picture?.credit
      ? `${picture.by ? `Photo by ${picture.by} · ` : ''}${picture.credit}`
      : shown && picture?.by
        ? picture.by
        : null,
  );

  onMount(() => {
    const tick = setInterval(() => (now = new Date()), 1000);
    return () => clearInterval(tick);
  });
</script>

<div class="waithome" class:waithome--bar={bar} class:waithome--plain={!shown}>
  <Backdrop {settings} screen="home" bind:picture bind:shown />
  <div class="veil"></div>

  <button
    class="corner"
    class:is-pressed={press.is('settings')}
    type="button"
    aria-label="Settings"
    onpointerdown={() => press.down('settings')}
    onpointerup={press.up}
    onpointercancel={press.up}
    onclick={() => press.act(onsettings)}
  >
    <span class="i-sliders"><i></i><b></b><i></i><b></b></span>
  </button>

  {#if wantsClock}
    <div class="clock">
      <div class="clock__time">{time}{#if meridiem}<span class="clock__ampm">{meridiem}</span>{/if}</div>
      <div class="clock__date">{date}</div>
      {#if name}<div class="clock__name">{name}</div>{/if}
    </div>
  {/if}

  {#if reading}
    <div class="reading">
      <div class="reading__head">{reading.phase === 'scanning' ? 'Lyrion is reading your music' : 'Lyrion is getting ready'}</div>
      <div class="reading__meter">
        <span class="reading__bar" class:reading__bar--busy={readingShare == null}>
          <span style:width={`${Math.round((readingShare ?? 0) * 100)}%`}></span>
        </span>
        {#if readingShare != null}<span class="reading__pct">{Math.round(readingShare * 100)} %</span>{/if}
      </div>
      <div class="reading__line">Your library appears here once Lyrion has read it all. The other sources play meanwhile.</div>
      <div class="reading__step">{reading.phase === 'scanning' ? reading.line.split('. Music shows up')[0] : reading.label}</div>
    </div>
  {/if}

  {#if none}
    <div class="none">
      <div class="none__head">No sources</div>
      <div class="none__note">Every source is switched off. Settings, top right.</div>
    </div>
  {:else}
    <div class="foot">
      <!-- The marks the library's footer shows, pulsing straight on the
           picture (George, 2026-10-18). -->
      <WaitingServices {availability} bare />
    </div>
  {/if}

  {#if credit}<div class="credit">{credit}</div>{/if}
</div>

<style>
  .reading {
    position: absolute;
    left: 50%;
    top: 52%;
    transform: translate(-50%, -50%);
    width: min(860px, calc(100% - 96px));
    padding: 26px 40px 28px;
    border-radius: 26px;
    background: rgba(10, 16, 22, 0.72);
    border: 1px solid rgba(233, 238, 242, 0.12);
    display: flex;
    flex-direction: column;
    gap: 14px;
    color: #e9eef2;
  }
  .reading__head {
    font-size: 46px;
    font-weight: 800;
    line-height: 1.1;
    letter-spacing: -0.01em;
  }
  .reading__meter {
    display: flex;
    align-items: center;
    gap: 22px;
  }
  .reading__bar {
    flex: 1;
    height: 16px;
    border-radius: 999px;
    background: rgba(233, 238, 242, 0.14);
    overflow: hidden;
  }
  .reading__bar > span {
    display: block;
    height: 100%;
    border-radius: 999px;
    background: #9fb4e8;
  }
  .reading__bar--busy > span {
    width: 30% !important;
    animation: readingBusy 1600ms ease-in-out infinite;
  }
  @keyframes readingBusy {
    from { transform: translateX(-100%); }
    to { transform: translateX(340%); }
  }
  .reading__pct {
    font-size: 40px;
    font-weight: 800;
    font-variant-numeric: tabular-nums;
    min-width: 3.4ch;
    text-align: right;
  }
  .reading__line {
    font-size: 26px;
    line-height: 1.35;
    color: rgba(233, 238, 242, 0.88);
  }
  .reading__step {
    font-family: var(--font-mono);
    font-size: 18px;
    letter-spacing: 0.04em;
    color: rgba(233, 238, 242, 0.6);
  }
  .waithome {
    position: absolute;
    inset: 0;
    z-index: 10;
    overflow: hidden;
    background: var(--bg-base);
  }
  /* Darker toward the foot and the clock's corner, so white type and the
     tiles hold on a bright picture; the picture's own dimming is the
     Background brightness row's, in Backdrop. */
  .veil {
    position: absolute;
    inset: 0;
    background:
      linear-gradient(180deg, rgba(10, 16, 22, 0.42) 0%, rgba(10, 16, 22, 0) 38%),
      linear-gradient(0deg, rgba(10, 16, 22, 0.62) 0%, rgba(10, 16, 22, 0) 45%);
    pointer-events: none;
  }
  .waithome--plain .veil {
    display: none;
  }

  /* The tile's glyph at the tile's own size, in the corner the tile is not in
     any more. Inset matches the panel's other edge controls. */
  .corner {
    position: absolute;
    top: 26px;
    right: 26px;
    z-index: 2;
    width: 64px;
    height: 64px;
    border-radius: 18px;
    border: 1px solid rgba(233, 238, 242, 0.14);
    background: rgba(16, 26, 33, 0.6);
    color: var(--ink);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    cursor: pointer;
    transition: transform 120ms ease, background 120ms ease;
  }
  .corner.is-pressed {
    transform: scale(0.94);
    background: rgba(233, 238, 242, 0.16);
  }
  .i-sliders {
    position: relative;
    width: 26px;
    height: 18px;
    display: block;
  }
  .i-sliders i,
  .i-sliders b {
    position: absolute;
    display: block;
  }
  .i-sliders i {
    left: 0;
    width: 26px;
    height: 2px;
    border-radius: 1px;
    background: currentColor;
    opacity: 0.55;
  }
  .i-sliders i:first-child {
    top: 4px;
  }
  .i-sliders i:nth-child(3) {
    top: 12px;
  }
  .i-sliders b {
    width: 7px;
    height: 7px;
    border-radius: 50%;
    background: currentColor;
  }
  .i-sliders b:nth-child(2) {
    top: 1.5px;
    left: 6px;
  }
  .i-sliders b:nth-child(4) {
    top: 9.5px;
    left: 15px;
  }

  /* ---- the clock ---- */
  .clock {
    position: absolute;
    left: 56px;
    top: 46px;
    z-index: 1;
    color: var(--ink);
    text-shadow: 0 1px 14px rgba(0, 0, 0, 0.35);
  }
  .clock__time {
    font-size: 120px;
    font-weight: 300;
    line-height: 1;
    letter-spacing: -0.03em;
    font-variant-numeric: tabular-nums;
  }
  .clock__ampm {
    font-size: 36px;
    font-weight: 400;
    margin-left: 12px;
    letter-spacing: 0;
  }
  .clock__date {
    margin-top: 10px;
    font-size: 26px;
    font-weight: 600;
    color: var(--ink-strong);
  }
  .clock__name {
    margin-top: 14px;
    font-family: var(--font-mono);
    font-size: 14px;
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--ink-strong);
  }

  /* ---- the sources ---- */
  .foot {
    position: absolute;
    left: 56px;
    right: 56px;
    bottom: 52px;
    z-index: 1;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .credit {
    position: absolute;
    right: 56px;
    bottom: 18px;
    z-index: 1;
    max-width: 70%;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.06em;
    color: var(--ink-quiet);
    text-align: right;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .none {
    position: absolute;
    inset: 0;
    z-index: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 0 40px;
  }
  .none__head {
    font-size: 30px;
    font-weight: 700;
    color: var(--ink);
  }
  .none__note {
    margin-top: 12px;
    font-size: 17px;
    color: var(--ink-quiet);
  }

  /* ---- the bar (ADR-0109): the clock a column on the left, the tiles
     beside it, no hint ---- */
  .waithome--bar .clock {
    left: 40px;
    top: 50%;
    transform: translateY(-50%);
  }
  .waithome--bar .clock__time {
    font-size: 104px;
  }
  .waithome--bar .clock__date {
    font-size: 20px;
  }
  .waithome--bar .clock__name {
    font-size: 12px;
    margin-top: 10px;
  }
  .waithome--bar .foot {
    left: 410px;
    right: 116px;
    top: 50%;
    bottom: auto;
    transform: translateY(-50%);
  }
  .waithome--bar .credit {
    right: 116px;
    bottom: 10px;
  }
</style>
