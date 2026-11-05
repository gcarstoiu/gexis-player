<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The panel and the bars while the room is measured (ADR-0175; design/source/29
  N08-N12, B05, B06, B08): display only - the run is followed on the phone.
  What it is doing, a progress bar, the five positions, and that sources can
  play again when it ends.
-->
<script>
  let { run, bar = false } = $props();

  const head = $derived(run.checking ? 'Checking the room' : 'Measuring the room');
  const speaker = (k) => (k === 'L' ? 'Left' : 'Right');
  const line = $derived.by(() => {
    const at = `Position ${run.position} of 5`;
    switch (run.step) {
      case 'level': return 'Finding the level · soft noise, getting louder';
      case 'place':
      case 'move': return `${at} · Moving the microphone`;
      case 'countdown': return `${at} · Sweeps in ${run.count}`;
      case 'measure':
      case 'checking': return `${at} · ${speaker(run.speaker ?? 'L')} speaker`;
      default: return 'Waiting for the phone';
    }
  });
  const pct = $derived(`${Math.round((run.progress ?? 0) * 100)}%`);
  const track = $derived([1, 2, 3, 4, 5].map((i) => ({
    n: i, state: i < run.position ? 'done' : i === run.position ? 'now' : 'next',
  })));
</script>

{#snippet phoneGlyph(size)}
  <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="7" y="2.5" width="10" height="19" rx="2.5"></rect><path d="M11 18.5h2"></path></svg>
{/snippet}

<div class="run" class:run--bar={bar} role="status" aria-live="polite">
  {#if bar}<div class="ground"></div>{:else}<div class="weave"></div>{/if}
  <div class="veil"></div>
  {#if bar}
    <div class="row">
      <div class="left">
        <span class="mark">Room correction</span>
        <div class="head">{head}</div>
        <div class="quiet">Please keep quiet</div>
      </div>
      <div class="right">
        <div class="line">{line}</div>
        <div class="bar"><div class="bar__fill" style="width:{pct}"></div></div>
        <div class="follow">{@render phoneGlyph(22)}<span>Follow it on the phone. Sources can play again when it ends.</span></div>
      </div>
    </div>
  {:else}
    <div class="stack">
      <span class="mark">Room correction</span>
      <div class="head">{head}</div>
      <div class="quiet">Please keep quiet</div>
      <div class="block">
        <div class="line">{line}</div>
        <div class="bar"><div class="bar__fill" style="width:{pct}"></div></div>
        <div class="track">
          {#each track as t (t.n)}
            <span class="pos pos--{t.state}"><span class="pos__seg"></span>{t.n}</span>
          {/each}
        </div>
      </div>
      <div class="follow">{@render phoneGlyph(24)}<span>Follow it on the phone. Sources can play again when it ends.</span></div>
    </div>
  {/if}
</div>

<style>
  .run {
    position: absolute;
    inset: 0;
    z-index: 60;
    overflow: hidden;
    background: var(--bg-base);
    color: var(--ink);
    user-select: none;
  }
  .weave {
    position: absolute;
    inset: -90px;
    background: repeating-linear-gradient(var(--weave-angle), var(--bg-weave-a) 0 48px, var(--bg-weave-b) 48px 96px);
    filter: blur(70px);
    transform: scale(1.14);
  }
  .ground {
    position: absolute;
    inset: 0;
    background: var(--c-weave-m);
  }
  .veil {
    position: absolute;
    inset: 0;
    background: var(--cover-veil-deep);
  }
  .stack {
    position: relative;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 22px;
    padding: 0 120px;
    box-sizing: border-box;
    text-align: center;
  }
  .mark {
    font-family: var(--font-mono);
    font-size: 15px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    white-space: nowrap;
    color: var(--accent-lms);
  }
  .head {
    font-size: 64px;
    font-weight: 800;
    letter-spacing: -0.02em;
    line-height: 1.05;
  }
  .quiet {
    font-size: 26px;
    font-weight: 600;
    white-space: nowrap;
    color: var(--ink-body);
  }
  .block {
    display: flex;
    flex-direction: column;
    gap: 14px;
    width: 640px;
    margin-top: 18px;
  }
  .line {
    font-family: var(--font-mono);
    font-size: 22px;
    letter-spacing: 0.04em;
    color: var(--ink);
  }
  .bar {
    position: relative;
    height: 12px;
    border-radius: 6px;
    background: var(--rc-run-track);
  }
  .bar__fill {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    border-radius: 6px;
    background: var(--accent-lms);
    transition: width 300ms ease;
  }
  .track {
    display: flex;
    gap: 6px;
  }
  .pos {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--ink-quiet);
  }
  .pos--now {
    color: var(--ink);
  }
  .pos__seg {
    width: 100%;
    height: 4px;
    border-radius: 2px;
    display: block;
    background: var(--c-ink-12);
  }
  .pos--done .pos__seg {
    background: var(--accent-lms);
  }
  .pos--now .pos__seg {
    background: var(--c-lms-50);
  }
  .follow {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 26px;
    font-size: 20px;
    color: var(--ink-muted);
  }
  .follow span {
    white-space: nowrap;
  }
  .follow svg {
    flex-shrink: 0;
  }

  /* -- the bars: one row -- */
  .row {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    gap: 56px;
    padding: 0 64px;
    box-sizing: border-box;
  }
  .left {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .run--bar .head {
    font-size: 48px;
    white-space: nowrap;
  }
  .run--bar .quiet {
    font-size: 22px;
  }
  .right {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 14px;
  }
  .run--bar .line {
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .run--bar .follow {
    margin-top: 0;
    font-size: 19px;
  }
  .run--bar .follow span {
    overflow: hidden;
    text-overflow: ellipsis;
  }
</style>
