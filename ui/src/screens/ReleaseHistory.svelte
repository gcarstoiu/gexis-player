<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  What a waiting update brings: every release it skips, newest first, each
  under its number and date (ADR-0110 amended 2026-10-07, George: "the update
  screen should show all until the current one"). One release - or an updater
  too old to send the list - reads as before: that release's notes alone.
-->
<script>
  import ReleaseNotes from './ReleaseNotes.svelte';

  let { update = null, large = false } = $props();

  const releases = $derived(
    Array.isArray(update?.whats_new_all) ? update.whats_new_all.filter((e) => e && (e.release || e.earlier)) : []
  );
  const several = $derived(releases.filter((e) => e.release).length > 1);

  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function day(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso ?? '');
    return m ? `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}` : '';
  }
</script>

{#if several}
  <div class="history" class:history--large={large}>
    {#each releases as e, i (e.release ?? `earlier-${i}`)}
      {#if e.release}
        <section class="history__release">
          <div class="history__head">
            <span class="history__num">{e.release}</span>
            {#if day(e.date)}<span class="history__date">{day(e.date)}</span>{/if}
          </div>
          <ReleaseNotes text={e.notes} {large} />
        </section>
      {:else}
        <p class="history__earlier">
          And {e.earlier} earlier {e.earlier === 1 ? 'release' : 'releases'}: their notes are under
          Settings → System → Change logs once this update is installed, and on GitHub.
        </p>
      {/if}
    {/each}
  </div>
{:else if update?.whats_new}
  <ReleaseNotes text={update.whats_new} {large} />
{/if}

<style>
  .history {
    display: flex;
    flex-direction: column;
    gap: 18px;
  }
  .history__release {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .history__release + .history__release {
    padding-top: 16px;
    border-top: 1px solid rgba(233, 238, 242, 0.1);
  }
  .history__head {
    display: flex;
    align-items: baseline;
    gap: 10px;
  }
  .history__num {
    font-size: 17px;
    font-weight: 700;
    color: var(--ink);
  }
  .history__date {
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--ink-quiet);
  }
  .history__earlier {
    margin: 0;
    font-size: 14px;
    line-height: 1.45;
    color: var(--ink-quiet);
  }
  .history--large .history__num { font-size: 22px; }
</style>
