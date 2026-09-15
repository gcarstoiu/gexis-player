<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!-- The drawer's volume glyph, shared so the now playing button matches it. -->
<script>
  let { percent = null, muted = false } = $props();

  const silent = $derived(muted || percent === 0);
  const arcs = $derived(percent == null ? 2 : silent ? 0 : percent < 34 ? 1 : percent < 67 ? 2 : 3);
</script>

<span class="icon">
  <span class="cone" class:is-dim={muted}></span>
  <span class="arc arc--1" class:is-lit={arcs >= 1}></span>
  <span class="arc arc--2" class:is-lit={arcs >= 2}></span>
  <span class="arc arc--3" class:is-lit={arcs >= 3}></span>
  {#if silent}<span class="slash"></span>{/if}
</span>

<style>
  .icon {
    position: relative;
    width: 30px;
    height: 30px;
    flex-shrink: 0;
    display: block;
  }
  .cone {
    position: absolute;
    left: 0;
    top: 50%;
    transform: translateY(-50%);
    width: 15px;
    height: 26px;
    background: rgba(233, 238, 242, 0.85);
    clip-path: polygon(0 27%, 42% 27%, 100% 0, 100% 100%, 42% 73%, 0 73%);
    display: block;
  }
  .cone.is-dim {
    background: rgba(233, 238, 242, 0.45);
  }
  .arc {
    position: absolute;
    top: 50%;
    border-radius: 50%;
    border: 2.5px solid rgba(233, 238, 242, 0.18);
    clip-path: polygon(50% 10%, 100% 0, 100% 100%, 50% 90%);
    display: block;
  }
  .arc.is-lit {
    border-color: rgba(233, 238, 242, 0.85);
  }
  .arc--1 { left: 5px; width: 16px; height: 16px; margin-top: -8px; }
  .arc--2 { left: 1px; width: 24px; height: 24px; margin-top: -12px; }
  .arc--3 { left: -2px; width: 30px; height: 30px; margin-top: -15px; }
  .slash {
    position: absolute;
    left: 1px;
    top: 50%;
    width: 28px;
    height: 3px;
    border-radius: 2px;
    transform: translateY(-50%) rotate(-38deg);
    background: var(--accent-warn);
    display: block;
  }
</style>
