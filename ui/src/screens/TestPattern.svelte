<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The hardware report's screen check** (ADR-0126 decision 2: *"shows a test
  pattern with the edges marked - 'Is all of it visible?'; asks for four taps
  in the corners - touch accuracy is measured, not asked"*). Asked for from a
  phone; drawn here, over everything but the update lock and Keep this
  screen.

  A coloured line along each edge, one colour per edge, so "the right edge is
  missing" can be said and checked. Then a circle in each corner in turn; a
  tap anywhere moves to the next. Where each tap landed and where its circle
  was go to the core in the screen's own pixels (CSS pixels times the scale),
  and the phone shows how far off each was. Only real touches count: a
  phone's pointer (ADR-0121) dispatches its own events, and those are not
  the touch screen.
-->
<script>
  let { check, onresult } = $props();

  const CORNERS = ['top left', 'top right', 'bottom right', 'bottom left'];
  //: In from the corner by this much, so a bezel cannot hide the circle.
  const INSET = 56;

  let taps = $state([]);
  let width = $state(window.innerWidth);
  let height = $state(window.innerHeight);
  let sent = $state(false);

  const step = $derived(taps.length);
  const target = $derived(step < CORNERS.length ? circle(CORNERS[step]) : null);

  function circle(corner) {
    return {
      x: corner.endsWith('left') ? INSET : width - INSET,
      y: corner.startsWith('top') ? INSET : height - INSET,
    };
  }

  function tap(e) {
    if (!e.isTrusted || !check.touch || !target || sent) return;
    e.preventDefault();
    e.stopPropagation();
    taps = [...taps, { corner: CORNERS[step], x: e.clientX, y: e.clientY, tx: target.x, ty: target.y }];
    if (taps.length === CORNERS.length) {
      sent = true;
      const dpr = window.devicePixelRatio || 1;
      const px = (v) => Math.round(v * dpr);
      onresult({
        seq: check.seq,
        width: px(width),
        height: px(height),
        taps: taps.map((t) => ({ corner: t.corner, x: px(t.x), y: px(t.y), tx: px(t.tx), ty: px(t.ty) })),
      });
    }
  }
</script>

<svelte:window bind:innerWidth={width} bind:innerHeight={height} />

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="pattern" onpointerdown={tap}>
  <div class="edge edge--top"></div>
  <div class="edge edge--right"></div>
  <div class="edge edge--bottom"></div>
  <div class="edge edge--left"></div>
  <div class="grid"></div>

  <div class="words">
    <div class="words__title">Test pattern</div>
    <div class="words__text">
      A coloured line should run along every edge: red at the top, green on the
      right, blue at the bottom, yellow on the left. Answer on the phone.
    </div>
    {#if check.touch && target}
      <div class="words__text words__text--ask">Tap the circle - {CORNERS[step]} ({step + 1} of 4).</div>
    {:else if check.touch}
      <div class="words__text words__text--ask">Done - the result is on the phone.</div>
    {/if}
    <div class="words__size">{Math.round(width * (window.devicePixelRatio || 1))} × {Math.round(height * (window.devicePixelRatio || 1))}</div>
  </div>

  {#if check.touch && target}
    <div class="target" style:left="{target.x}px" style:top="{target.y}px"></div>
  {/if}
</div>

<style>
  .pattern {
    position: fixed;
    inset: 0;
    z-index: 90;
    background: #000;
    color: #fff;
    touch-action: none;
  }
  .edge {
    position: absolute;
  }
  .edge--top { top: 0; left: 0; right: 0; height: 4px; background: #ff3b30; }
  .edge--right { top: 0; right: 0; bottom: 0; width: 4px; background: #34c759; }
  .edge--bottom { bottom: 0; left: 0; right: 0; height: 4px; background: #0a84ff; }
  .edge--left { top: 0; left: 0; bottom: 0; width: 4px; background: #ffd60a; }
  .grid {
    position: absolute;
    inset: 4px;
    background-image:
      linear-gradient(rgba(255, 255, 255, 0.14) 1px, transparent 1px),
      linear-gradient(90deg, rgba(255, 255, 255, 0.14) 1px, transparent 1px);
    background-size: 10% 10%;
    background-position: center;
  }
  .words {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: min(560px, calc(100% - 2 * 120px));
    display: flex;
    flex-direction: column;
    gap: 12px;
    text-align: center;
    background: #000;
    padding: 18px;
  }
  .words__title {
    font-size: 26px;
    font-weight: 600;
  }
  .words__text {
    font-size: 18px;
    line-height: 1.4;
    color: rgba(255, 255, 255, 0.82);
  }
  .words__text--ask {
    color: #fff;
    font-weight: 600;
  }
  .words__size {
    font-size: 14px;
    color: rgba(255, 255, 255, 0.5);
    font-variant-numeric: tabular-nums;
  }
  .target {
    position: absolute;
    width: 44px;
    height: 44px;
    margin: -22px 0 0 -22px;
    border-radius: 50%;
    border: 3px solid #fff;
    box-shadow: 0 0 0 6px rgba(255, 255, 255, 0.18);
  }
  .target::after {
    content: '';
    position: absolute;
    left: 50%;
    top: 50%;
    width: 6px;
    height: 6px;
    margin: -3px 0 0 -3px;
    border-radius: 50%;
    background: #fff;
  }
</style>
