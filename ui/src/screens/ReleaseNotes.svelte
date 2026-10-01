<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  A release's notes as sections with bullet points (George, 2026-10-01: "one
  big blob of text ... separated by New feature and Fixes, and have bullet
  points"). The notes are plain text, written so they still read where they
  are not parsed: a heading on its own line (New, Fixed, Good to know), then
  lines that start with "•" (or "-"). Anything else is a paragraph.
-->
<script>
  let { text = '', large = false } = $props();

  const sections = $derived.by(() => {
    const out = [];
    let current = null;
    for (const raw of String(text ?? '').split('\n')) {
      const line = raw.trim();
      if (!line) continue;
      const bullet = line.match(/^[•\-*]\s+(.*)$/);
      if (bullet) {
        if (!current) out.push((current = { head: null, items: [] }));
        current.items.push(bullet[1]);
      } else if (line.length <= 40 && !/[.!?]$/.test(line)) {
        out.push((current = { head: line.replace(/^#+\s*/, '').replace(/:$/, ''), items: [] }));
      } else {
        out.push({ head: null, items: [], para: line });
        current = null;
      }
    }
    return out;
  });
</script>

<div class="notes" class:notes--large={large}>
  {#each sections as s, i (i)}
    {#if s.head}<div class="notes__head">{s.head}</div>{/if}
    {#if s.para}<p class="notes__para">{s.para}</p>{/if}
    {#if s.items.length}
      <ul class="notes__list">
        {#each s.items as item, j (j)}<li>{item}</li>{/each}
      </ul>
    {/if}
  {/each}
</div>

<style>
  .notes {
    display: flex;
    flex-direction: column;
    gap: 6px;
    text-align: left;
  }
  .notes__head {
    margin-top: 6px;
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--ink-muted);
  }
  .notes__head:first-child { margin-top: 0; }
  .notes__para {
    margin: 0;
    font-size: 15px;
    line-height: 1.45;
  }
  .notes__list {
    margin: 0;
    padding-left: 20px;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .notes__list li {
    font-size: 15px;
    line-height: 1.45;
  }
  .notes__list li::marker { color: var(--accent-lms); }

  .notes--large { gap: 10px; }
  .notes--large .notes__head { font-size: 20px; }
  .notes--large .notes__para,
  .notes--large .notes__list li { font-size: 26px; }
  .notes--large .notes__list { padding-left: 34px; gap: 8px; }
</style>
