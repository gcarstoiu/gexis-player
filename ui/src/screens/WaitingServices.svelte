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

  // Order, colours, labels and ring delays are the design's.
  const SERVICES = [
    { id: 'lms', name: 'Lyrion', status: 'Starts on play', size: 24, lead: true, delays: [0, 1400] },
    { id: 'spotify', name: 'Spotify', status: 'Listening', size: 24, lead: false, delays: [900, 2300] },
    { id: 'bluetooth', name: 'Bluetooth', status: 'Pairable', size: 26, lead: false, delays: [1800, 400] },
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
  .rings {
    position: relative;
    width: 72px;
    height: 72px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .ring {
    position: absolute;
    width: 72px;
    height: 72px;
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
    width: 58px;
    height: 58px;
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
