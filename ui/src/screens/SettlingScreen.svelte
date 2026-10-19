<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **The first start after setup, until the player has settled** (ADR-0128).
  What setup chose to download - the visualiser's skins, each plugin - with
  each one's progress, then *Ready*, which the core takes down a few seconds
  later. **A download that fails is left for Settings, and the owner is
  told** - the screen names it, says where to try again, and waits for OK.
  Sources are not refused while it settles (George: rather than blocking, say
  that music may be slow to start).

  **It can be put away from the start** (ADR-0128 amended 2026-10-10, George:
  "Otherwise it feels like being stuck"): the screen says the downloads go on
  and where to follow them, and comes back only if one fails.
-->
<script>
  let { settling, ondone, onhide } = $props();
  let hiding = $state(false);

  const failed = $derived(settling.items.filter((i) => i.state === 'failed'));
  const title = $derived(settling.phase === 'ready' ? 'Ready'
    : settling.phase === 'failed' ? 'Almost ready' : 'Getting the player ready');

  function mb(bytes) {
    return bytes == null ? null : Math.round(bytes / 1e6);
  }
  //: ADR-0149 decision 43: Lyrion after its download - starting, its
  //: add-ons, reading the music - in its own words, with how far it has read.
  const following = $derived(settling.items.some((i) => i.steps));
  function line(item) {
    if (item.step === 'after') return item.share != null ? `${item.label} · ${Math.round(item.share * 100)} %` : item.label;
    if (item.state === 'done') return 'Done';
    if (item.state === 'failed') return item.error ? `Did not finish: ${item.error}` : 'Did not finish';
    if (item.state === 'waiting') return 'Waiting to start…';
    // **Each step in words** (George, 2026-10-18: what happens in the
    // background should be transparent), as the phone's Getting ready and
    // Settings say them.
    if (item.step === 'preparing') return 'Starting the download…';
    if (item.step === 'verifying') return 'Checking the download…';
    // The download is in and the package is being put in place - minutes for
    // a skin pack, with nothing to count (2026-10-11).
    if (item.step === 'installing') return 'Downloaded · installing…';
    const got = mb(item.received), all = mb(item.total);
    const far = got != null && all ? `${got} of ${all} MB`
      // A skin pack says how far it is as a share, not in bytes.
      : item.share != null ? `${Math.round(item.share * 100)} %` : 'Downloading…';
    return item.step === 'retrying' ? `Retrying · ${far}` : far;
  }
  function share(item) {
    if (item.state === 'done') return 1;
    if (item.total) return Math.min(1, (item.received ?? 0) / item.total);
    return item.share != null ? Math.min(1, Math.max(0, item.share)) : 0;
  }
  function names(list) {
    const n = list.map((i) => i.name);
    return n.length < 2 ? n.join('') : `${n.slice(0, -1).join(', ')} and ${n.at(-1)}`;
  }
</script>

<div class="settle" role="dialog" aria-modal="true" aria-label={title}>
  <div class="card">
    <div class="title">{title}</div>
    <div class="note">
      {#if settling.phase === 'ready'}
        Everything you chose in setup is in place.
      {:else if settling.phase === 'failed'}
        {names(failed)} did not finish. Try again any time in <b>Settings → Plugins</b>; everything else is ready.
      {:else}
        {#if following}
          Lyrion starts, adds its add-ons and reads your music - a large library takes hours. The other sources play meanwhile.
          You can use the player now: Lyrion goes on, and Settings → Library shows how far it is.
        {:else}
          Downloading and installing what you chose in setup - a few minutes. Until it is done, music may be slow to start.
          You can use the player now: the downloads go on, and Settings shows how far they are.
        {/if}
      {/if}
    </div>
    <div class="items">
      {#each settling.items as item (item.id)}
        <div class="item" class:is-done={item.state === 'done'} class:is-failed={item.state === 'failed'}>
          <div class="item__head">
            <span class="item__name">{item.name}</span>
            <span class="item__state">{line(item)}</span>
          </div>
          {#if item.steps}
            <!-- The phone's numbered checklist, on the panel (George,
                 2026-10-19: "Make sure the plate shows the steps"). -->
            <ol class="steps">
              {#each item.steps as [text, at], n (n)}
                <li class="step step--{at}"><span class="step__n">{at === 'done' ? '✓' : n + 1}</span><span>{text}</span></li>
              {/each}
            </ol>
          {/if}
          {#if item.state === 'busy' || item.state === 'waiting' || item.state === 'done'}
            <div class="bar" class:bar--waiting={item.state === 'waiting' || item.step === 'preparing' || item.step === 'installing' || item.step === 'verifying' || (item.state === 'busy' && !item.total && item.share == null)}>
              <span style:width="{Math.round(share(item) * 100)}%"></span>
            </div>
          {/if}
          {#if item.step === 'after' && item.line}
            <!-- Lyrion's own words for its step: what it is reading, and how
                 many of how many (ADR-0115 decision 28). -->
            <div class="item__line">{item.line}</div>
          {/if}
        </div>
      {/each}
    </div>
    {#if settling.phase === 'failed'}
      <button class="ok" type="button" onclick={ondone}>OK</button>
    {:else if settling.phase === 'settling'}
      <button class="ok" type="button" disabled={hiding} onclick={async () => { hiding = true; try { await onhide(); } finally { hiding = false; } }}>Use the player now</button>
    {/if}
  </div>
</div>

<style>
  .settle {
    position: fixed;
    inset: 0;
    z-index: 85;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 22px;
    background: rgba(8, 12, 16, 0.86);
  }
  .card {
    width: 100%;
    max-width: 620px;
    max-height: 100%;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 20px;
    padding: 28px;
    border-radius: 22px;
    background: var(--bg-panel);
    border: 1px solid rgba(233, 238, 242, 0.14);
    box-shadow: 0 30px 70px rgba(0, 0, 0, 0.5);
    color: var(--ink);
  }
  .title {
    font-size: 26px;
    font-weight: 600;
  }
  .note {
    font-size: 17px;
    line-height: 1.45;
    color: var(--ink-dim, #9fb0bd);
  }
  .note b {
    color: var(--ink);
    font-weight: 600;
  }
  .items {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .item {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .item__head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 14px;
    flex-wrap: wrap;
  }
  .item__name {
    font-size: 18px;
    font-weight: 600;
  }
  .item__state {
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--ink-dim, #9fb0bd);
    font-variant-numeric: tabular-nums;
  }
  .item__line {
    font-size: 15px;
    line-height: 1.4;
    color: var(--ink-dim, #9fb0bd);
  }
  .item.is-done .item__state {
    color: #7ed6bc;
  }
  .item.is-failed .item__state {
    color: #e0a758;
  }
  .steps {
    list-style: none;
    margin: 2px 0 2px;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .step {
    display: flex;
    align-items: baseline;
    gap: 12px;
    font-size: 16px;
    line-height: 1.35;
    color: var(--ink-dim, #9fb0bd);
  }
  .step__n {
    flex-shrink: 0;
    width: 24px;
    height: 24px;
    border-radius: 50%;
    display: inline-grid;
    place-items: center;
    font-family: var(--font-mono);
    font-size: 13px;
    border: 1px solid rgba(233, 238, 242, 0.22);
    transform: translateY(-1px);
  }
  .step--done .step__n {
    color: #7ed6bc;
    border-color: rgba(126, 214, 188, 0.5);
  }
  .step--now {
    color: var(--ink);
    font-weight: 600;
  }
  .step--now .step__n {
    color: #101a21;
    background: #7ed6bc;
    border-color: #7ed6bc;
  }
  .step--next {
    opacity: 0.6;
  }
  .bar {
    height: 6px;
    border-radius: 3px;
    background: rgba(233, 238, 242, 0.1);
    overflow: hidden;
  }
  .bar span {
    display: block;
    height: 100%;
    border-radius: 3px;
    background: #7ed6bc;
    transition: width 400ms ease;
  }
  .bar--waiting span {
    width: 30% !important;
    animation: settleWait 1600ms ease-in-out infinite;
    background: rgba(126, 214, 188, 0.5);
  }
  @media (max-height: 480px) {
    .settle { padding: 10px; }
    .card { padding: 16px 22px; gap: 12px; }
    .title { font-size: 22px; }
    .note { font-size: 15px; line-height: 1.35; }
    .items { gap: 10px; }
    .ok { height: 46px; }
  }
  @keyframes settleWait {
    0% { transform: translateX(-100%); }
    100% { transform: translateX(340%); }
  }
  /* Stuck to the card's foot: on a 320 px bar the card scrolls, and the
     way out must not be below it. */
  .ok {
    position: sticky;
    bottom: 0;
    align-self: flex-end;
    min-width: 140px;
    padding: 0 22px;
    height: 54px;
    border-radius: 15px;
    font-size: 17px;
    font-weight: 600;
    color: #7ed6bc;
    background: rgba(126, 214, 188, 0.14);
    border: 1px solid rgba(126, 214, 188, 0.45);
  }
</style>
