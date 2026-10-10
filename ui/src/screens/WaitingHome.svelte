<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The panel's root with LMS off** (ADR-0079), **as ADR-0133 draws it**.
  George, 2026-10-10, on three options: *"I kind of like all three. Can you
  mix all three into one design? A bit less text, but with the clock and
  wallpaper."*

  - **The background is the idle screen's** (`Backdrop`, the same
    *Background*): the player's own wallpapers by default.
  - **The clock, the date and the player's name** sit in the top left,
    smaller than the idle screen's (*Clock on the waiting screen*).
  - **Each waiting source is a tile** along the foot - its mark, its name,
    its state - and one line above them is the only other text (*Hint on the
    waiting screen*). On a bar, the clock is a column on the left and the
    tiles stand beside it, with no hint.
  - **Settings stays the button in the corner** (ADR-0079), and a screen
    with every source switched off says so.

  The tiles are a translucent plate, not frosted glass as the mock-up drew
  them: ADR-0041 bans live backdrop blur on the Pi 4 (24.5 ms a frame).
-->
<script>
  import { onMount } from 'svelte';
  import Backdrop from './Backdrop.svelte';
  import SourceMark from '../lib/SourceMark.svelte';
  import { pressing } from '../lib/press.svelte.js';
  import { sources } from '../lib/state.js';
  import { settingsDevice } from '../lib/settings.js';
  import { screen } from '../lib/family.svelte.js';

  let { availability = {}, onsettings, settings = {} } = $props();

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
  const wantsHint = $derived(settings.waiting_hint !== false && !bar);
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

  // The picture's credit, as the idle screen draws it: Pixabay, NASA's and
  // ESA's licences all ask that people be shown where a picture comes from.
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
  <Backdrop {settings} bind:picture bind:shown />
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

  {#if none}
    <div class="none">
      <div class="none__head">No sources</div>
      <div class="none__note">Every source is switched off. Settings, top right.</div>
    </div>
  {:else}
    <div class="foot">
      {#if wantsHint}<div class="hint">Start music from your phone</div>{/if}
      <div class="tiles" style:--count={waiting.length}>
        {#each waiting as s (s.id)}
          <div class="tile" class:is-lead={s.id === 'lms'}>
            <div class="mark">
              <SourceMark
                source={s.id}
                mark={s.mark}
                size={bar ? 30 : 38}
                color={s.id === 'lms' ? 'var(--accent-lms)' : 'var(--ink)'}
                opacity={s.id === 'lms' ? 1 : 0.8}
              />
            </div>
            <div class="tile__text">
              <div class="tile__name">{s.name}</div>
              <div class="tile__status">{s.status}</div>
            </div>
          </div>
        {/each}
      </div>
    </div>
  {/if}

  {#if credit}<div class="credit">{credit}</div>{/if}
</div>

<style>
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
  .hint {
    font-size: 19px;
    color: var(--ink-strong);
    text-shadow: 0 1px 12px rgba(0, 0, 0, 0.45);
  }
  .tiles {
    display: grid;
    grid-template-columns: repeat(var(--count), minmax(0, 1fr));
    gap: 16px;
  }
  .tile {
    height: 132px;
    box-sizing: border-box;
    border-radius: var(--r-card);
    padding: 0 22px;
    display: flex;
    align-items: center;
    gap: 18px;
    min-width: 0;
    background: rgba(16, 26, 33, 0.72);
    border: 1px solid rgba(233, 238, 242, 0.14);
  }
  .tile.is-lead {
    border-color: rgba(126, 214, 188, 0.5);
  }
  .mark {
    width: 72px;
    height: 72px;
    flex-shrink: 0;
    border-radius: 50%;
    display: grid;
    place-items: center;
    background: rgba(233, 238, 242, 0.08);
  }
  .tile.is-lead .mark {
    background: rgba(126, 214, 188, 0.1);
  }
  .tile__text {
    min-width: 0;
  }
  .tile__name {
    font-size: 25px;
    font-weight: 700;
    color: var(--ink);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .tile__status {
    margin-top: 8px;
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--ink-quiet);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .tile.is-lead .tile__status {
    color: var(--accent-lms);
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
  .waithome--bar .tile {
    height: 170px;
    flex-direction: column;
    align-items: flex-start;
    justify-content: center;
    gap: 12px;
    padding: 0 18px;
    border-radius: 20px;
  }
  .waithome--bar .mark {
    width: 56px;
    height: 56px;
  }
  .waithome--bar .tile__name {
    font-size: 21px;
  }
  .waithome--bar .credit {
    right: 116px;
    bottom: 10px;
  }
</style>
