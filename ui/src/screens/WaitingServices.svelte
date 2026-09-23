<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The library root's footer while no renderer is connected (design/screens.md
  §3): a pulsing mark for each service waiting to be used. Ported from
  source/Now Playing.dc.html. A service the daemon reports unavailable is not
  drawn - the design only draws ones that are waiting.
-->
<script>
  import SourceMark from '../lib/SourceMark.svelte';

  let { availability = {} } = $props();

  // Order, colours, labels, sizes and ring delays are the design's.
  //
  // The marks are 38/38/41, not the 24/24/26 shipped until 2026-09-20: the
  // design calls them `waitIcon…Lg` and sizes them
  // `sourceIcon('lms', '#7ed6bc', 38, 1)`, `('spotify', '#e9eef2', 38, 0.72)`
  // and `('bluetooth', '#e9eef2', 41, 0.72)`. Bluetooth is the odd one
  // because its glyph is taller than it is wide, so matching it by height
  // would leave it visibly smaller than the other two.
  const SERVICES = [
    { id: 'lms', name: 'Lyrion', status: 'Starts on play', size: 38, lead: true, delays: [0, 1400] },
    { id: 'spotify', name: 'Spotify', status: 'Listening', size: 38, lead: false, delays: [900, 2300] },
    { id: 'bluetooth', name: 'Bluetooth', status: 'Pairable', size: 41, lead: false, delays: [1800, 400] },
  ];
  const shown = $derived(SERVICES.filter((s) => availability[s.id]));
</script>

<div class="waiting">
  <div class="row">
    {#each shown as s (s.id)}
      <div class="service" class:is-lead={s.lead}>
        <div class="rings">
          {#each s.delays as delay}
            <div class="ring" style:animation-delay={`${delay}ms`}></div>
          {/each}
          <div class="disc">
            <SourceMark
              source={s.id}
              size={s.size}
              color={s.lead ? 'var(--accent-lms)' : 'var(--ink)'}
              opacity={s.lead ? 1 : 0.72}
            />
          </div>
        </div>
        <div class="label">
          <div class="name">{s.name}</div>
          <div class="status">{s.status}</div>
        </div>
      </div>
    {/each}
  </div>
</div>

<style>
  .waiting {
    position: relative;
    height: 186px;
    flex-shrink: 0;
    border-top: 1px solid rgba(159, 180, 232, 0.24);
    background: rgba(20, 31, 40, 0.78);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 40px;
    box-sizing: border-box;
  }
  .row {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 30px;
  }
  .service {
    width: 172px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 13px;
  }
  /* 100px rings around a 90px disc, per the design's notice footer. The
     whole cluster shipped undersized - 72px rings around a 58px disc - which
     is what made the marks inside look small (George, 2026-09-20). */
  .rings {
    position: relative;
    width: 100px;
    height: 100px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .ring {
    position: absolute;
    width: 100px;
    height: 100px;
    border-radius: 50%;
    border: 2px solid rgba(233, 238, 242, 0.6);
    animation: ring 2800ms ease-out infinite;
    box-sizing: border-box;
  }
  .is-lead .ring {
    border-color: var(--accent-lms);
  }
  @keyframes ring {
    0% { transform: scale(0.82); opacity: 0.55; }
    100% { transform: scale(1.75); opacity: 0; }
  }
  .disc {
    width: 90px;
    height: 90px;
    border-radius: 50%;
    background: var(--ink-fill);
    border: 1px solid rgba(233, 238, 242, 0.16);
    display: flex;
    align-items: center;
    justify-content: center;
    box-sizing: border-box;
  }
  .is-lead .disc {
    background: rgba(126, 214, 188, 0.14);
    border-color: rgba(126, 214, 188, 0.4);
  }
  .label {
    text-align: center;
  }
  .name {
    font-size: 16px;
    font-weight: 700;
    color: var(--ink);
    white-space: nowrap;
  }
  .status {
    font-family: var(--font-mono);
    font-size: var(--t-micro);
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--ink-quiet);
    margin-top: 4px;
    white-space: nowrap;
  }
  .is-lead .status {
    color: var(--accent-lms);
  }
</style>
