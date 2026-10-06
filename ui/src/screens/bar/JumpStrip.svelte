<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  The bar's letter-pair strip (Bar States, lib-artists): `#` and thirteen
  two-letter steps, A–B … Y–Z. The Artists row and Lyrion's lettered lists
  (ADR-0118, Claude Design's handover §Frame — Bar) share it, so the two
  read as the same control (George, 2026-10-06).

  `have` says which letters the list holds - a step none of whose letters
  it holds is inert - `on` is the letter on screen, and `tint` the list's
  colour as an "r, g, b" triple for the current step.
-->
<script>
  let { have = () => true, on = null, tint = '159, 180, 232', onpick } = $props();

  //: Round 2's thirteen two-letter steps, and the "#" the panel's rail has
  //: (13b-round2-review.md §2: fourteen still fit at 51 px at 1200).
  const STEPS = [
    { label: '#', letters: ['#'] },
    ...Array.from({ length: 13 }, (_, i) => {
      const a = String.fromCharCode(65 + i * 2);
      const b = String.fromCharCode(66 + i * 2);
      return { label: `${a}–${b}`, letters: [a, b] };
    }),
  ];
</script>

<div class="jump" style:--tint={tint}>
  {#each STEPS as step (step.label)}
    {@const first = step.letters.find((l) => have(l))}
    <button
      class="jump__step"
      class:is-on={step.letters.includes(on)}
      type="button"
      disabled={!first}
      onclick={() => onpick?.(first)}>{step.label}</button>
  {/each}
</div>

<style>
  .jump {
    display: flex;
    gap: 6px;
  }
  .jump__step {
    flex: 1;
    min-width: 44px;
    height: 52px;
    border-radius: var(--r-md);
    display: flex;
    align-items: center;
    justify-content: center;
    text-align: center;
    box-sizing: border-box;
    padding: 0;
    font-family: var(--font-mono);
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0.06em;
    background: rgba(233, 238, 242, 0.05);
    border: 1px solid rgba(233, 238, 242, 0.1);
    color: rgba(233, 238, 242, 0.78);
    cursor: pointer;
  }
  .jump__step.is-on {
    background: rgba(var(--tint), 0.18);
    border-color: rgba(var(--tint), 0.5);
    color: rgb(var(--tint));
  }
  .jump__step:disabled {
    color: rgba(233, 238, 242, 0.3);
    cursor: default;
  }
  .jump__step:not(:disabled):active { transform: scale(0.96); }
</style>
