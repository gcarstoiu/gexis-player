<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0118: one of the 46 glyphs (lib/glyphs.js), in one ink, drawn in its
  26 px box and scaled to `size` - as the handover's glyph() does.
-->
<script>
  import { SHAPES } from './glyphs.js';

  let { name = 'Folder', ink = '#e9eef2', size = 26 } = $props();

  const parts = $derived(SHAPES[name] ?? SHAPES.Folder);
  const k = $derived(size / 26);

  function css(part) {
    const [left, top, width, height, style] = part;
    let out = `left:${left}px;top:${top}px;width:${width}px;height:${height}px;`;
    for (const [key, value] of Object.entries(style)) {
      const prop = key.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);
      const v = typeof value === 'string' ? value.replace(/\bI\b/g, ink) : typeof value === 'number' && !['opacity'].includes(key) ? `${value}px` : value;
      out += `${prop}:${v};`;
    }
    return out;
  }
</script>

<span class="glyph" style:transform={k !== 1 ? `scale(${k})` : null} style:margin={k !== 1 ? `${13 * (k - 1)}px` : null} aria-hidden="true">
  {#each parts as part, i (i)}<i style={css(part)}></i>{/each}
</span>

<style>
  .glyph {
    position: relative;
    width: 26px;
    height: 26px;
    display: block;
    flex-shrink: 0;
  }
  .glyph i {
    position: absolute;
    display: block;
  }
</style>
