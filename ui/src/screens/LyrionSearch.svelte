<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0118 E and the handover's note 4: a search from Lyrion's menus. The
  field is in Library's header and the phone types into it (ADR-0121); this
  runs every search the entry offers - My Music's five together, or one
  app's - when typing pauses, and shows what came back grouped by kind, with
  a chip per kind to narrow it.
-->
<script>
  import Disc from '../lib/Disc.svelte';
  import Glyph from '../lib/Glyph.svelte';
  import { T, initials, shapeFor } from '../lib/lyrionLooks.js';
  import { menuSearch } from '../lib/menus.js';

  //: On a bar the field is the content's own, at its top (the handover's
  //: §9: "the field sits at the top of the content, chips under it");
  //: the Standard family's is in Library's header.
  let { rows = [], text = $bindable(''), ctx = {}, onopen, onact, bar = false, wide = false } = $props();

  //: The designer's tints for the five, by the order Lyrion lists them.
  const KIND_TINT = { artists: T.blue, albums: T.mint, works: T.lilac, songs: T.coral, playlists: T.sky };
  const tintOf = (label) => KIND_TINT[(label || '').toLowerCase()] ?? T.sky;

  let results = $state([]);
  let searched = $state('');
  let running = $state(false);
  let only = $state(null);
  let selected = $state(null);

  $effect(() => {
    const words = text.trim();
    if (!words) {
      results = [];
      searched = '';
      return;
    }
    const timer = setTimeout(async () => {
      running = true;
      const got = await Promise.all(
        rows.map((row) => menuSearch(row.handle, words).then((page) => ({ row, page })).catch(() => ({ row, page: null })))
      );
      if (text.trim() !== words) return;
      results = got.filter((g) => g.page);
      searched = words;
      running = false;
      selected = null;
    }, 500);
    return () => clearTimeout(timer);
  });

  const shown = $derived(results.filter((g) => !only || g.row.handle === only));
  const total = $derived(results.reduce((n, g) => n + (g.page.items.filter((r) => r.kind !== 'text').length ? g.page.count : 0), 0));
  const hasCover = (r) => !!r.image && !/\/html\//.test(r.image);

  function tap(row) {
    if (row.kind === 'play') {
      if (selected === row.handle) onact?.(row, 'play');
      else selected = row.handle;
    } else if (row.kind !== 'text') onopen?.(row);
  }
</script>

<div class="search" class:search--bar={bar} class:search--wide={wide}>
  {#if bar}
    <label class="field">
      <Glyph name="Search" ink="#e9eef2" />
      <input class="field__in" type="search" placeholder="Type on your phone" bind:value={text} autocomplete="off" />
      <span class="field__phone"><Glyph name="Phone" ink="#7ed6bc" /><span>Typing on phone</span></span>
    </label>
  {/if}
  {#if !text.trim() || (!searched && running)}
    <div class="state">
      <Disc name="Phone" tint={T.mint} size={bar ? 72 : 92} />
      <div class="state__text">
        <div class="state__title">Type on your phone</div>
        <div class="state__body">
          {bar ? 'Results arrive as you type' : 'The panel has no keyboard. Your phone types into this field; results arrive as you type'}{rows.length > 1 ? `, across all ${rows.length === 5 ? 'five' : rows.length} searches` : ''}.
        </div>
      </div>
    </div>
  {:else if searched && !total}
    <div class="state">
      <Disc name="Search" tint={T.slate} size={bar ? 72 : 92} />
      <div class="state__text">
        <div class="state__title">Nothing for “{searched}”</div>
        <div class="state__body">
          {rows.length > 1 ? `No ${rows.map((r) => r.label.toLowerCase().replace(/s$/, '')).join(', ').replace(/, ([^,]*)$/, ' or $1')} matches.` : 'Nothing matches.'} Check the spelling on your phone.
        </div>
      </div>
    </div>
  {:else}
    <div class="scroll">
      {#if rows.length > 1}
        <div class="chips">
          <button class="chip" class:is-on={!only} type="button" onclick={() => (only = null)}>All<span class="chip__n">{total}</span></button>
          {#each results as g (g.row.handle)}
            {@const n = g.page.items.filter((r) => r.kind !== 'text').length ? g.page.count : 0}
            <button class="chip" class:is-on={only === g.row.handle} class:is-none={!n} type="button" onclick={() => (only = g.row.handle)}>{g.row.label}<span class="chip__n">{n}</span></button>
          {/each}
        </div>
      {/if}
      <div class="grid">
        {#each shown as g (g.row.handle)}
          {@const found = g.page.items.filter((r) => r.kind !== 'text')}
          {#if found.length}
            <div class="head"><span style:color={tintOf(g.row.label)}>{g.row.label}</span><i></i><b>{g.page.count}</b></div>
            {#each found as r (r.handle)}
              {@const isSel = r.kind === 'play' && selected === r.handle}
              <button class="row" class:is-sel={isSel} class:row--two={!!r.subtitle} type="button" onclick={() => tap(r)}>
                {#if r.hint === 'artist'}<span class="init">{initials(r.label)}</span>
                {:else if hasCover(r)}<span class="thumb"><img src={r.image} alt="" loading="lazy" /></span>
                {:else}{@const look = shapeFor(r.label, r.hint)}<Disc name={look[0]} tint={look[1]} size={bar ? 42 : 46} />{/if}
                <span class="row__text"><span class="row__label">{r.label}</span>{#if r.subtitle}<span class="row__sub">{r.subtitle}</span>{/if}</span>
                {#if isSel}
                  <span class="acts">
                    {#if r.can?.includes('play')}<span class="act act--play" role="presentation" onclick={(e) => { e.stopPropagation(); onact?.(r, 'play'); }}><span class="tri"></span>Play</span>{/if}
                    {#if r.can?.includes('next')}<span class="act" role="presentation" onclick={(e) => { e.stopPropagation(); onact?.(r, 'next'); }}>Play next</span>{/if}
                    {#if r.can?.includes('add')}<span class="act" role="presentation" onclick={(e) => { e.stopPropagation(); onact?.(r, 'add'); }}>Add</span>{/if}
                  </span>
                {/if}
              </button>
            {/each}
          {/if}
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .search { flex: 1; min-height: 0; min-width: 0; display: flex; flex-direction: column; }
  .scroll { flex: 1; min-height: 0; overflow-y: auto; padding: 22px 40px 24px; box-sizing: border-box; display: flex; flex-direction: column; gap: 14px; scrollbar-width: none; touch-action: pan-y; }
  button { font: inherit; color: inherit; background: none; border: 0; padding: 0; text-align: left; cursor: pointer; }
  button:active { transform: scale(0.95); }
  .chips { display: flex; flex-wrap: wrap; gap: 10px; flex-shrink: 0; }
  .chip { height: 52px; padding: 0 20px; border-radius: 999px; display: flex; align-items: center; gap: 10px; box-sizing: border-box; background: rgba(233, 238, 242, 0.06); border: 1px solid rgba(233, 238, 242, 0.14); font-size: 18px; font-weight: 700; white-space: nowrap; }
  .chip.is-on { background: rgba(126, 214, 188, 0.16); border-color: rgba(126, 214, 188, 0.4); color: #7ed6bc; }
  .chip.is-none { color: rgba(233, 238, 242, 0.62); }
  .chip__n { font-family: var(--font-mono); font-size: 14px; font-weight: 400; color: rgba(233, 238, 242, 0.62); }
  .grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 16px; row-gap: 4px; align-content: start; }
  .head { grid-column: 1 / -1; display: flex; align-items: center; gap: 14px; padding: 14px 0 8px; }
  .head span { font-family: var(--font-mono); font-size: 14px; font-weight: 700; letter-spacing: 0.18em; }
  .head i { flex: 1; height: 1px; background: rgba(233, 238, 242, 0.1); }
  .head b { font-family: var(--font-mono); font-size: 12px; font-weight: 400; letter-spacing: 0.1em; color: rgba(233, 238, 242, 0.6); }
  .row { min-width: 0; height: 60px; display: flex; align-items: center; gap: 16px; padding: 0 12px 0 8px; border-radius: 14px; box-sizing: border-box; }
  .row--two { height: 64px; }
  .row.is-sel { background: rgba(126, 214, 188, 0.16); grid-column: 1 / -1; }
  .row.is-sel .row__label { color: #7ed6bc; }
  .row__text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .row__label { font-size: 20px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .row__sub { font-size: 15px; color: rgba(233, 238, 242, 0.62); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .thumb { width: 46px; height: 46px; border-radius: 9px; overflow: hidden; position: relative; flex-shrink: 0; background: #17242d; display: block; }
  .thumb img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
  .init { width: 46px; height: 46px; border-radius: 50%; flex-shrink: 0; background: rgba(159, 180, 232, 0.14); border: 1px solid rgba(159, 180, 232, 0.3); box-sizing: border-box; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 700; color: #9fb4e8; }
  .acts { display: flex; gap: 8px; flex-shrink: 0; }
  .act { height: 48px; padding: 0 18px; border-radius: 14px; background: rgba(233, 238, 242, 0.06); border: 1px solid rgba(233, 238, 242, 0.14); box-sizing: border-box; display: flex; align-items: center; gap: 10px; font-size: 17px; font-weight: 700; white-space: nowrap; }
  .act--play { background: rgba(126, 214, 188, 0.14); border-color: rgba(126, 214, 188, 0.36); }
  .tri { width: 0; height: 0; border-left: 12px solid #7ed6bc; border-top: 8px solid transparent; border-bottom: 8px solid transparent; display: block; }
  .state { flex: 1; min-height: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 18px; padding: 24px 40px; box-sizing: border-box; text-align: center; }
  .state__title { font-size: 30px; font-weight: 700; letter-spacing: -0.01em; margin-top: 6px; white-space: nowrap; }
  .state__body { font-size: 19px; line-height: 1.5; color: rgba(233, 238, 242, 0.72); width: 560px; max-width: 100%; }
  .state__text { display: flex; flex-direction: column; align-items: center; gap: 18px; }
  /* ── A bar: the field on top, results four across (five at 1850). ── */
  .field { flex-shrink: 0; height: 60px; margin: 22px 28px 0; box-sizing: border-box; display: flex; align-items: center; gap: 16px; padding: 0 20px; border-radius: 16px; background: rgba(233, 238, 242, 0.07); border: 1.5px solid #7ed6bc; }
  .field__in { flex: 1; min-width: 0; appearance: none; background: none; border: 0; outline: none; padding: 0; font: inherit; font-size: 22px; font-weight: 600; color: #e9eef2; caret-color: #7ed6bc; }
  .field__in::placeholder { color: rgba(233, 238, 242, 0.4); }
  .field__in::-webkit-search-cancel-button { display: none; }
  .field__phone { display: flex; align-items: center; gap: 10px; flex-shrink: 0; font-family: var(--font-mono); font-size: 13px; letter-spacing: 0.2em; text-transform: uppercase; color: rgba(126, 214, 188, 0.9); }
  .search--bar .scroll { padding: 14px 28px 22px; gap: 10px; }
  .search--bar .chips { flex-wrap: nowrap; overflow-x: auto; scrollbar-width: none; touch-action: pan-x; }
  .search--bar .chip { height: 48px; font-size: 17px; }
  .search--bar .grid { grid-template-columns: repeat(4, minmax(0, 1fr)); }
  .search--wide .grid { grid-template-columns: repeat(5, minmax(0, 1fr)); }
  .search--bar .head { padding: 8px 0 4px; }
  .search--bar .row { height: 52px; border-radius: 12px; gap: 12px; }
  .search--bar .row--two { height: 58px; }
  .search--bar .row__label { font-size: 17px; }
  .search--bar .row__sub { font-size: 13px; }
  .search--bar .thumb, .search--bar .init { width: 42px; height: 42px; }
  .search--bar .act { height: 46px; }
  .search--bar .state { flex-direction: row; text-align: left; gap: 28px; }
  .search--bar .state__text { align-items: flex-start; gap: 8px; }
  .search--bar .state__title { font-size: 28px; margin-top: 0; }
  .search--bar .state__body { font-size: 18px; width: 520px; }
</style>
