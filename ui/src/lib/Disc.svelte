<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0118 / design/screens.md §8: a glyph on its tint - ground at 14 %,
  a 1 px border at 30 %, the glyph at full strength. 46 px on rows, 54 on
  cards, 42 on bars, 92 on the state screens.
-->
<script>
  import Glyph from './Glyph.svelte';
  import { rgba } from './glyphs.js';
  import { theme } from './theme.js';
  import { tone } from './themeRule.js';

  let { name = 'Folder', tint = '#8fc4d8', size = 46 } = $props();

  //: ADR-0171: a tint from the data, as the theme has it.
  const toned = $derived(tone(tint, $theme));
</script>

<span
  class="disc"
  style:width="{size}px"
  style:height="{size}px"
  style:background={rgba(toned, 0.14)}
  style:border-color={rgba(toned, 0.3)}
>
  <Glyph {name} ink={tint} size={size > 80 ? 40 : size > 50 ? 28 : 26} />
</span>

<style>
  .disc {
    border-radius: 50%;
    border: 1px solid;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
</style>
