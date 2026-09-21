<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The pairing request (ADR-0045), ported from the design's inline pair frame.

  **The countdown here is a display, not a decision.** The design's own demo
  runs a 30s `setTimeout` and flips itself to `expired`; ours must not. The
  agent is holding BlueZ's handshake open and it is the one that lets go, so
  the frame's state comes from `/state` and the number below the buttons only
  says what the agent is already doing. Two clocks would eventually disagree,
  and the frame that outlived its request would be offering an Accept that
  trusts a device whose request no longer exists (ADR-0045's load-bearing
  paragraph).

  So: no timer decides anything. One interval ticks the text down, and it
  stops at zero rather than acting.
-->
<script>
  import { onDestroy } from 'svelte';
  import SourceMark from '../lib/SourceMark.svelte';
  import { answerPairing } from '../lib/state.js';

  let { request } = $props();

  //: Whether the question is still open. Every other state is the outcome.
  const asking = $derived(request?.state === 'asking');
  const accepted = $derived(request?.state === 'accepted');
  const label = $derived(
    request?.state === 'expired'
      ? 'Request expired'
      : request?.state === 'rejected'
        ? 'Not paired'
        : 'Paired'
  );

  //: `418 205` reads as a code; `418205` reads as a number. The design
  //: groups it in three and so does every phone showing the other half.
  const grouped = $derived(
    (request?.code ?? '').length === 6
      ? `${request.code.slice(0, 3)} ${request.code.slice(3)}`
      : (request?.code ?? '')
  );

  //: Counted from when this arrived, which is within a frame of the agent
  //: starting its own. It never reaches a conclusion - see the file header.
  let left = $state(0);
  let ticker;
  $effect(() => {
    clearInterval(ticker);
    if (!asking) return;
    const window = request.window ?? 30;
    const started = Date.now();
    left = Math.ceil(window);
    ticker = setInterval(() => {
      left = Math.max(0, Math.ceil(window - (Date.now() - started) / 1000));
    }, 1000);
    return () => clearInterval(ticker);
  });
  onDestroy(() => clearInterval(ticker));

  //: The button is disabled the moment it is tapped: the answer takes a
  //: round trip, and a second tap would land on nothing or on the next
  //: request.
  let answering = $state(false);
  async function answer(accept) {
    if (answering) return;
    answering = true;
    try {
      await answerPairing(accept);
    } catch (err) {
      console.info('pairing:', err.message);
    }
  }
  $effect(() => {
    if (asking) answering = false;
  });
</script>

<div class="pair" role="dialog" aria-label="Pairing request">
  <div class="pair__kicker">Pairing request</div>

  <div class="pair__who">
    <div class="pair__disc">
      {#if asking}
        <span class="pair__ring"></span>
        <span class="pair__ring pair__ring--late"></span>
      {/if}
      <span class="pair__face">
        <SourceMark source="bluetooth" size={52} color="var(--accent-bluetooth)" />
      </span>
    </div>
    <span class="pair__device">{request?.device ?? ''}</span>
  </div>

  {#if asking}
    {#if grouped}
      <div class="pair__code">
        <span class="pair__codelabel">Code on your phone</span>
        <span class="pair__digits">{grouped}</span>
      </div>
    {/if}

    <div class="pair__actions">
      <button class="pair__btn" type="button" disabled={answering} onclick={() => answer(false)}>
        Reject
      </button>
      <button
        class="pair__btn pair__btn--accept"
        type="button"
        disabled={answering}
        onclick={() => answer(true)}
      >
        Accept
      </button>
    </div>

    <div class="pair__countdown">Expires in {left}s</div>
  {:else}
    <div class="pair__done">
      {#if accepted}
        <span class="pair__tick"><i></i><i></i></span>
      {:else}
        <span class="pair__cross"><i></i><i></i></span>
      {/if}
      <span class="pair__donelabel" class:is-paired={accepted}>{label}</span>
    </div>
  {/if}
</div>

<style>
  .pair {
    position: absolute;
    inset: 0;
    /* Above the handoff and the idle screen: a request that cannot be seen
       cannot be answered, and it lapses in thirty seconds either way. */
    z-index: 32;
    background: rgba(13, 21, 27, 0.95);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 40px;
    color: var(--ink);
    user-select: none;
  }
  .pair__kicker {
    font-family: var(--font-mono);
    font-size: 15px;
    letter-spacing: 0.34em;
    text-transform: uppercase;
    color: var(--ink-tab-off);
  }
  .pair__who {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 22px;
  }
  .pair__disc {
    position: relative;
    width: 132px;
    height: 132px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .pair__face {
    width: 132px;
    height: 132px;
    border-radius: 50%;
    box-sizing: border-box;
    border: 2px solid var(--accent-bluetooth);
    background: rgba(159, 180, 232, 0.14);
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 0 46px rgba(159, 180, 232, 0.2);
  }
  .pair__ring {
    position: absolute;
    width: 132px;
    height: 132px;
    border-radius: 50%;
    box-sizing: border-box;
    border: 2px solid var(--accent-bluetooth);
    animation: pairRing 2800ms ease-out infinite;
  }
  .pair__ring--late {
    animation-delay: 1400ms;
  }
  @keyframes pairRing {
    0% {
      transform: scale(1);
      opacity: 0.5;
    }
    70% {
      opacity: 0;
    }
    100% {
      transform: scale(1.6);
      opacity: 0;
    }
  }
  .pair__device {
    font-size: 30px;
    font-weight: 700;
    white-space: nowrap;
    max-width: 90vw;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .pair__code {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 12px;
  }
  .pair__codelabel {
    font-family: var(--font-mono);
    font-size: 14px;
    letter-spacing: 0.22em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .pair__digits {
    font-family: var(--font-mono);
    font-size: 72px;
    font-weight: 700;
    letter-spacing: 0.16em;
    color: var(--accent-bluetooth);
    line-height: 1;
  }

  .pair__actions {
    display: flex;
    align-items: center;
    gap: 20px;
  }
  .pair__btn {
    height: 74px;
    padding: 0 44px;
    border-radius: 18px;
    background: var(--ink-fill);
    border: 1px solid rgba(233, 238, 242, 0.16);
    font: inherit;
    font-size: 21px;
    font-weight: 700;
    color: var(--ink);
    display: flex;
    align-items: center;
  }
  .pair__btn:active {
    transform: scale(0.95);
  }
  .pair__btn:disabled {
    opacity: 0.55;
  }
  .pair__btn--accept {
    background: rgba(159, 180, 232, 0.2);
    border-color: rgba(159, 180, 232, 0.5);
    color: var(--accent-bluetooth);
  }
  .pair__countdown {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }

  .pair__done {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 18px;
  }
  .pair__tick,
  .pair__cross {
    width: 84px;
    height: 84px;
    border-radius: 50%;
    position: relative;
    box-sizing: border-box;
  }
  .pair__tick {
    background: rgba(159, 180, 232, 0.18);
    border: 2px solid var(--accent-bluetooth);
  }
  .pair__tick i {
    position: absolute;
    border-radius: 2px;
    background: var(--accent-bluetooth);
    height: 3px;
    display: block;
  }
  .pair__tick i:first-child {
    left: 26px;
    top: 38px;
    width: 16px;
    transform: rotate(45deg);
    transform-origin: left center;
  }
  .pair__tick i:last-child {
    left: 37px;
    top: 49px;
    width: 28px;
    transform: rotate(-50deg);
    transform-origin: left center;
  }
  .pair__cross {
    background: rgba(233, 238, 242, 0.08);
    border: 2px solid rgba(233, 238, 242, 0.4);
  }
  .pair__cross i {
    position: absolute;
    left: 26px;
    top: 40.5px;
    width: 32px;
    height: 3px;
    border-radius: 2px;
    background: var(--ink-body);
    display: block;
  }
  .pair__cross i:first-child {
    transform: rotate(45deg);
  }
  .pair__cross i:last-child {
    transform: rotate(-45deg);
  }
  .pair__donelabel {
    font-family: var(--font-mono);
    font-size: 17px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-muted);
  }
  .pair__donelabel.is-paired {
    color: var(--accent-bluetooth);
  }
</style>
