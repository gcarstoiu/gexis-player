<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<script>
  // ADR-0166, design/source/22: the group's glyph, two speakers, as each
  // design file draws it (24 viewBox, stroke 2).
  let { size = 20, ink = 'currentColor' } = $props();
</script>

<svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke={ink} stroke-width="2"
     stroke-linejoin="round" aria-hidden="true">
  <rect x="2.5" y="4" width="8" height="16" rx="2" />
  <rect x="13.5" y="4" width="8" height="16" rx="2" />
  <circle cx="6.5" cy="14.5" r="2" />
  <circle cx="17.5" cy="14.5" r="2" />
</svg>

<style>
  svg { flex-shrink: 0; display: block; }
</style>
