<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The player's screen, in miniature** (ADR-0149; Claude Design's
  `Panel Mini`): what part 2's choices will look like on the panel, beside
  each question. Drawn here rather than shot from the real screens: the
  page must follow a choice as it is made, before anything is written.

  `kind`: lib (Extended), simple, now (only what plays), wait (the waiting
  home, with `marks` its sources), clock (the idle screen), off (standby),
  and the visualiser's vu, viz, vs, turn, tape, all.
-->
<script>
  import calm from '../../assets/personalise/calm.webp';
  import colourful from '../../assets/personalise/colourful.webp';
  import psychedelic from '../../assets/personalise/psychedelic.webp';
  import lyrion from '../../assets/icon-lyrion.svg';
  import spotify from '../../assets/icon-spotify.png';
  import bluetooth from '../../assets/icon-bluetooth.png';

  let {
    kind = 'lib', head = '', time = '21:04', player = '', place = '', marks = [],
    clock = true, weather = false, black = false, bg = 'wall', style = 'Calm', rpm = 33, animate = true
  } = $props();

  const WALLS = { Calm: calm, Colourful: colourful, Psychedelic: psychedelic };
  const wall = $derived(WALLS[style] ?? calm);
  const SRC = {
    lyr: { label: 'Lyrion', icon: lyrion, line: 'Starts on play' },
    plex: { label: 'Plexamp', icon: null, line: 'Listening' },
    spo: { label: 'Spotify', icon: spotify, line: 'Listening' },
    bt: { label: 'Bluetooth', icon: bluetooth, line: 'Pairable' }
  };
  const date = new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' });
  const turnS = $derived(rpm === 45 ? 1.33 : 1.8);
</script>

<figure class="pv">
  {#if head}<figcaption class="pv__head">{head}</figcaption>{/if}
  <div class="pv__screen" class:pv__screen--black={black}>
    {#if kind === 'wait' || kind === 'clock'}
      {#if !black}
        {#if bg === 'artist' && kind === 'clock'}
          <div class="pv__artist"></div>
        {:else}
          <img class="pv__wall" src={wall} alt="" />
        {/if}
        <div class="pv__shade"></div>
      {/if}
    {/if}

    {#if kind === 'lib' || kind === 'simple'}
      <div class="lib">
        <div class="lib__rail">{#each [0, 1, 2, 3] as i (i)}<span></span>{/each}</div>
        <div class="lib__main">
          <div class="lib__chips">
            {#each kind === 'lib' ? ['My Music', 'Favourites', 'Apps', 'Radio'] : ['Artists', 'Albums', 'Playlists', 'Radio'] as c (c)}<span>{c}</span>{/each}
          </div>
          <div class="lib__grid">{#each Array(8) as _, i (i)}<span style="--h:{(i * 47) % 360}"></span>{/each}</div>
        </div>
      </div>
    {:else if kind === 'now'}
      <div class="now">
        <span class="now__cover"></span>
        <div class="now__text"><b></b><i></i><i class="short"></i><span class="now__bar"><span></span></span></div>
      </div>
    {:else if kind === 'wait'}
      {#if clock}
        <div class="wait__top"><b>{time}</b><span>{date} · {player}</span></div>
      {/if}
      <div class="wait__mid">
        <span class="wait__title">Start music from your phone</span>
        <div class="wait__tiles">
          {#each marks as m (m)}
            {@const s = SRC[m]}
            <span class="tile" class:tile--lead={m === 'lyr'}>
              {#if s.icon}<img src={s.icon} alt="" />{:else}<b class="tile__p">P</b>{/if}
              <span>{s.label}</span><small>{s.line}</small>
            </span>
          {/each}
        </div>
      </div>
    {:else if kind === 'clock'}
      {#if clock}<div class="clock__time">{time}</div><div class="clock__date">{date}</div>{/if}
      {#if weather}<div class="clock__wx">☀ 18° · {place || 'Your town'}</div>{/if}
    {:else if kind === 'off'}
      <div class="off">Standby</div>
    {:else}
      <div class="viz">
        {#if kind === 'vu' || kind === 'vs' || kind === 'all'}
          <div class="vu">
            {#each [0, 1] as i (i)}
              <span class="vu__face"><span class="vu__needle" class:vu__needle--b={i === 1}></span></span>
            {/each}
          </div>
        {/if}
        {#if kind === 'viz' || kind === 'vs'}
          <div class="bars" class:bars--low={kind === 'vs'}>{#each Array(18) as _, i (i)}<span style="--d:{(i * 137) % 900}ms"></span>{/each}</div>
        {/if}
        {#if kind === 'turn'}
          <div class="turn"><span class="disc" class:spin={animate} style="--s:{turnS}s"><span></span></span><span class="arm"></span></div>
        {/if}
        {#if kind === 'tape'}
          <div class="tape">{#each [0, 1] as i (i)}<span class="reel" class:spin={animate} style="--s:2.4s"></span>{/each}</div>
        {/if}
      </div>
    {/if}
  </div>
</figure>

<style>
  .pv {
    margin: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .pv__head {
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.55);
  }
  .pv__screen {
    position: relative;
    aspect-ratio: 16 / 10;
    max-width: 100%;
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid rgba(233, 238, 242, 0.14);
    background: radial-gradient(120% 100% at 20% 30%, #1c2a33, #0d151c);
    color: #e9eef2;
  }
  .pv__screen--black { background: #000; }
  .pv__wall, .pv__artist, .pv__shade { position: absolute; inset: 0; width: 100%; height: 100%; }
  .pv__wall { object-fit: cover; }
  .pv__artist { background: radial-gradient(80% 90% at 70% 40%, #6d5a4a, #1d1712); }
  .pv__shade { background: linear-gradient(180deg, rgba(0, 0, 0, 0.25), rgba(0, 0, 0, 0.55)); }

  .lib { position: absolute; inset: 0; display: flex; }
  .lib__rail { width: 12%; display: flex; flex-direction: column; gap: 9%; padding: 8% 3%; border-right: 1px solid rgba(233, 238, 242, 0.08); }
  .lib__rail span { aspect-ratio: 1; border-radius: 30%; background: rgba(233, 238, 242, 0.14); }
  .lib__main { flex: 1; padding: 5%; display: flex; flex-direction: column; gap: 6%; }
  .lib__chips { display: flex; gap: 4px; flex-wrap: wrap; }
  .lib__chips span { font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 999px; background: rgba(233, 238, 242, 0.1); }
  .lib__grid { flex: 1; display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
  .lib__grid span { border-radius: 5px; background: linear-gradient(140deg, hsl(var(--h) 35% 38%), hsl(var(--h) 30% 18%)); }

  .now { position: absolute; inset: 0; display: flex; align-items: center; gap: 7%; padding: 0 9%; }
  .now__cover { width: 38%; aspect-ratio: 1; border-radius: 8px; background: linear-gradient(140deg, #8a6e9e, #2a2140); }
  .now__text { flex: 1; display: flex; flex-direction: column; gap: 9px; }
  .now__text b, .now__text i { height: 9px; border-radius: 5px; background: rgba(233, 238, 242, 0.8); width: 80%; }
  .now__text i { background: rgba(233, 238, 242, 0.35); width: 60%; height: 7px; }
  .now__text i.short { width: 40%; }
  .now__bar { height: 3px; border-radius: 2px; background: rgba(233, 238, 242, 0.15); margin-top: 8px; }
  .now__bar span { display: block; width: 42%; height: 100%; background: #7ed6bc; border-radius: 2px; }

  .wait__top { position: absolute; top: 6%; left: 5%; display: flex; flex-direction: column; }
  .wait__top b { font-size: 20px; font-weight: 800; }
  .wait__top span { font-size: 9px; color: rgba(233, 238, 242, 0.75); }
  .wait__mid { position: absolute; left: 5%; right: 5%; bottom: 9%; display: flex; flex-direction: column; gap: 8px; }
  .wait__title { font-size: 12px; font-weight: 800; }
  .wait__tiles { display: flex; gap: 6px; }
  .tile {
    flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; padding: 6px;
    border-radius: 8px; background: rgba(13, 21, 28, 0.55); border: 1px solid rgba(233, 238, 242, 0.12);
    font-size: 9px; font-weight: 700;
  }
  .tile img, .tile__p { width: 14px; height: 14px; object-fit: contain; }
  .tile__p { display: grid; place-items: center; border-radius: 50%; border: 1px solid currentColor; font-size: 8px; }
  .tile small { font-size: 7.5px; font-weight: 600; color: rgba(233, 238, 242, 0.65); }
  .tile--lead { border-color: #7ed6bc; }
  .tile--lead small { color: #7ed6bc; }

  .clock__time { position: absolute; left: 7%; top: 18%; font-size: 40px; font-weight: 800; letter-spacing: -0.02em; }
  .clock__date { position: absolute; left: 7%; top: 44%; font-size: 11px; color: rgba(233, 238, 242, 0.8); }
  .clock__wx { position: absolute; left: 7%; bottom: 10%; font-size: 11px; font-weight: 700; }
  .off { position: absolute; inset: 0; display: grid; place-items: center; font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.25em; text-transform: uppercase; color: rgba(233, 238, 242, 0.22); }

  .viz { position: absolute; inset: 0; display: flex; flex-direction: column; justify-content: center; gap: 8%; padding: 6%; background: #0b0f12; }
  .vu { display: flex; gap: 6%; justify-content: center; }
  .vu__face { position: relative; width: 42%; aspect-ratio: 1.6; border-radius: 8px; background: linear-gradient(180deg, #efe3c4, #d2c29c); overflow: hidden; }
  .vu__needle { position: absolute; left: 50%; bottom: -10%; width: 2px; height: 85%; background: #1b1b1b; transform-origin: 50% 100%; animation: needle 1.7s ease-in-out infinite alternate; }
  .vu__needle--b { animation-duration: 1.3s; }
  @keyframes needle { from { transform: rotate(-38deg); } to { transform: rotate(22deg); } }
  .bars { display: flex; align-items: flex-end; gap: 3px; height: 55%; }
  .bars--low { height: 26%; }
  .bars span { flex: 1; height: 100%; background: linear-gradient(0deg, #7ed6bc, #9fb4e8); border-radius: 2px; transform-origin: 50% 100%; animation: bar 1s ease-in-out var(--d) infinite alternate; }
  @keyframes bar { from { transform: scaleY(0.15); } to { transform: scaleY(1); } }
  .turn { position: relative; display: grid; place-items: center; height: 100%; }
  .disc { width: 62%; aspect-ratio: 1; border-radius: 50%; background: repeating-radial-gradient(#111 0 2px, #1b1b1b 2px 4px); display: grid; place-items: center; }
  .disc span { width: 30%; aspect-ratio: 1; border-radius: 50%; background: #c8a2d8; }
  .arm { position: absolute; right: 16%; top: 12%; width: 3px; height: 52%; background: #b8b8b8; transform: rotate(24deg); transform-origin: 50% 0; border-radius: 2px; }
  .tape { display: flex; justify-content: center; gap: 16%; padding: 8% 0; border-radius: 10px; background: #2a2420; }
  .reel { width: 26%; aspect-ratio: 1; border-radius: 50%; background: conic-gradient(#d9cfc0 0 20deg, #3a332d 20deg 120deg, #d9cfc0 120deg 140deg, #3a332d 140deg 240deg, #d9cfc0 240deg 260deg, #3a332d 260deg); }
  .spin { animation: spin var(--s) linear infinite; }
  @keyframes spin { to { transform: rotate(360deg); } }
  @media (prefers-reduced-motion: reduce) {
    .spin, .vu__needle, .bars span { animation: none; }
  }
</style>
