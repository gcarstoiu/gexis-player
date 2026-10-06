<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  ADR-0118, Phase 13f: one level of Lyrion's own menus, as Claude Design drew
  it (design/source/13f/, "Lyrion Standard"). One rule carries every level -
  **what an entry opens decides its shape**: branches are a glyph in a
  tinted disc (Radio's, design/screens.md §8) and navigate; albums and
  playlists with covers are a cover grid; tracks and stations are leaf rows
  that reveal Play · Play next · Add on the first tap and play on the second
  (screens.md, *Row actions*); a search entry is a field the phone types
  into (ADR-0121).

  Library.svelte holds the path, the header and the mini strip; this draws
  the region between them, and the region alone blanks for a state.
-->
<script>
  import { tick } from 'svelte';
  import Disc from '../lib/Disc.svelte';
  import Glyph from '../lib/Glyph.svelte';
  import JumpStrip from './bar/JumpStrip.svelte';
  import { dragScroll } from './bar/sideways.svelte.js';
  import { rgba } from '../lib/glyphs.js';
  import { T, MY_MUSIC, MY_MUSIC_GROUPS, shapeFor, initials, railLetter, playCount, fact, levelLayout, hasCover, mmss } from '../lib/lyrionLooks.js';

  let {
    page = null,
    //: What led here: `opens` (My Music's word for its entry), `from` (the
    //: row that opened this level), `appTop` (an app's first level), `apps`,
    //: `favourites`, `app` (the app's name, for the states).
    ctx = {},
    letters = {},
    busy = null,
    loading = false,
    failed = null,
    onopen,
    onact,
    onsearchentry,
    onjump,
    onmore,
    onearlier,
    onretry,
    //: The Bar family (the handover's §Frame — Bar): lists run sideways
    //: where a 400 px screen has room for one row, the letter strip
    //: replaces the rail, and the bar's head column holds the title and
    //: Play all. `wide` is the 1850 layout.
    bar = false,
    wide = false,
  } = $props();
  const D = $derived(bar ? 42 : 46);

  const items = $derived(page?.items ?? []);
  const nonText = $derived(items.filter((r) => r.kind !== 'text'));

  const layout = $derived(levelLayout(page, ctx, { loading, failed }));

  // ── Leaf rows: one selected at a time ─────────────────────────────────
  let selected = $state(null);
  $effect(() => {
    page;
    selected = null;
  });
  function tapLeaf(row) {
    if (selected === row.handle) onact?.(row, 'play');
    else selected = row.handle;
  }
  function tap(row) {
    if (row.kind === 'play') tapLeaf(row);
    else if (row.kind === 'search') onsearchentry?.(row);
    else if (row.kind !== 'text') {
      selected = null;
      onopen?.(row);
    }
  }

  // ── Letters: headers in the list, and the rail ─────────────────────────
  //: `letters` is null while the index is on its way: the rail or strip is
  //: drawn already, its letters inert, so nothing moves when it lands.
  const alphabetical = $derived(letters === null || Object.keys(letters).length > 0);
  const known = $derived(letters ?? {});
  const RAIL = ['#', ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ'];
  const counts = $derived.by(() => {
    const at = Object.entries(known).sort((a, b) => a[1] - b[1]);
    const out = {};
    at.forEach(([letter, pos], i) => (out[letter] = (at[i + 1]?.[1] ?? page?.count ?? pos) - pos));
    return out;
  });
  //: Lyrion's own letter where it gives one (it sorts "Jon Lord" under L),
  //: the label's otherwise.
  const letterOf = (r) => r.letter ?? railLetter(r.label);
  //: The rail lights the letter whose header was last scrolled past.
  let seen = $state(null);
  const onLetter = $derived(seen ?? (items.length ? letterOf(items[0]) : null));
  let rowsBox = $state(null);
  let coversBox = $state(null);
  $effect(() => {
    page?.handle;
    seen = null;
  });
  /** A letter on the rail: that letter's rows, its header at the top. */
  async function jump(l) {
    await onjump?.(l, known[l]);
    await tick();
    const head = rowsBox?.querySelector(`[data-letter="${l}"]`);
    if (head) head.scrollIntoView({ block: 'start' });
    else if (coversBox) coversBox.scrollTop = coversBox.scrollLeft = 0;
    seen = l;
  }
  //: A mouse drags a bar's sideways lists (sideways.svelte.js); the
  //: Standard family's lists run down and are left alone.
  function across(node, on) {
    return on ? dragScroll(node) : {};
  }
  const STRIP_TINT = { genres: '242, 164, 143', artists: '159, 180, 232', covers: '126, 214, 188' };
  function scrollOf(node) {
    for (let n = node.parentElement; n; n = n.parentElement) {
      const st = getComputedStyle(n);
      if (/auto|scroll/.test(st.overflowY) || /auto|scroll/.test(st.overflowX)) return n;
    }
    return null;
  }
  function watchLetters(box) {
    const node = box;
    let queued = false;
    const look = () => {
      queued = false;
      const top = box.getBoundingClientRect().top + 8;
      let found = null;
      for (const h of node.querySelectorAll('[data-letter]')) {
        if (h.getBoundingClientRect().top > top) break;
        found = h.dataset.letter;
      }
      seen = found;
    };
    const onScroll = () => {
      if (!queued) (queued = true), requestAnimationFrame(look);
    };
    box.addEventListener('scroll', onScroll, { passive: true });
    return { destroy: () => box.removeEventListener('scroll', onScroll) };
  }

  /** Rows with a header where the letter changes - unnamed ones gathered
   *  last under their own (the handover's Genres). */
  function lettered(rows, tint) {
    if (!alphabetical) return rows.map((r) => ({ row: r }));
    const named = rows.filter((r) => r.label);
    const unnamed = rows.filter((r) => !r.label && r.kind !== 'text');
    const out = [];
    let last = null;
    for (const r of named) {
      const l = letterOf(r);
      if (l !== last) {
        out.push({ head: l, meta: counts[l] ?? '', tint, first: last === null });
        last = l;
      }
      out.push({ row: r });
    }
    if (unnamed.length) {
      out.push({ head: 'No name', meta: 'Lyrion gives these no label', tint: T.slate, first: !out.length });
      out.push({ row: { ...unnamed[0], _unnamed: unnamed.length } });
    }
    return out;
  }

  // ── Years by decade ───────────────────────────────────────────────────
  const decades = $derived.by(() => {
    const out = new Map();
    for (const r of nonText) {
      const y = Number(r.label);
      const key = Number.isFinite(y) && y > 0 ? `${Math.floor(y / 10) * 10}s` : 'Other';
      if (!out.has(key)) out.set(key, []);
      out.get(key).push(r);
    }
    return [...out.entries()];
  });

  // ── The app album page (the handover's §7) ─────────────────────────────
  const album = $derived.by(() => {
    if (layout !== 'album') return null;
    const isTrack = (r) => r.kind === 'play' || (r.unavailable && r.kind === 'folder' && !!r.subtitle);
    const tracks = items.filter(isTrack);
    // A library album's facts come from the core (its titles); an app's are
    // its own text lines.
    const facts = page.facts ?? items.filter((r) => r.kind === 'text').map((r) => fact(r.label)).filter(([k, v]) => k && v);
    const links = items.filter((r) => !isTrack(r) && (r.kind === 'folder' || r.kind === 'container')).map((r) => ({ row: r, kv: fact(r.label) }));
    const year = (facts.find(([k]) => /released|year/i.test(k))?.[1] ?? '').match(/\b(19|20)\d{2}\b/)?.[0] ?? '';
    const minutes = Math.round(tracks.reduce((n, r) => n + (r.duration ?? 0), 0) / 60);
    //: Nothing here plays: Qobuz streams none of it (not licensed here, or
    //: not yet released - its "* ").
    const none = !!ctx.from?.unavailable || (tracks.length > 0 && tracks.every((r) => r.unavailable && !r.can?.length));
    return { tracks, facts: facts.slice(0, 5), links, year, minutes, none };
  });

  // ── Cards at an app's first level: the search as a field-button, and
  //    several searches as one field with a chip per kind ─────────────────
  const searches = $derived(nonText.filter((r) => r.kind === 'search'));
  const others = $derived(nonText.filter((r) => r.kind !== 'search'));
  let kind = $state(0);
  $effect(() => {
    page;
    kind = 0;
  });

  // ── Loading: after a second, say who is being waited for ───────────────
  let slow = $state(false);
  $effect(() => {
    if (!loading) {
      slow = false;
      return;
    }
    const t = setTimeout(() => (slow = true), 1000);
    return () => clearTimeout(t);
  });

  function nearEnd(node) {
    const io = new IntersectionObserver((e) => e.some((x) => x.isIntersecting) && onmore?.(), { root: scrollOf(node), rootMargin: '600px' });
    io.observe(node);
    return { destroy: () => io.disconnect() };
  }
  //: Rows arriving above keep what is on screen where it is (a letter
  //: jumped to stays at the top).
  function nearStart(node) {
    const box = scrollOf(node);
    const io = new IntersectionObserver(async (e) => {
      if (!e.some((x) => x.isIntersecting) || !box) return;
      // A bar's sideways list keeps its place along x.
      const across = box.scrollWidth > box.clientWidth;
      const after = across ? box.scrollWidth - box.scrollLeft : box.scrollHeight - box.scrollTop;
      await onearlier?.();
      await tick();
      if (across) box.scrollLeft = box.scrollWidth - after;
      else box.scrollTop = box.scrollHeight - after;
    }, { root: box, rootMargin: '200px' });
    io.observe(node);
    return { destroy: () => io.disconnect() };
  }
  const more = $derived(page && (page.start ?? 0) + items.length < page.count);
  const earlier = $derived(page && (page.start ?? 0) > 0);
  const fmt = (n) => Number(n).toLocaleString('en-GB');
</script>

{#snippet actionsFor(row, short = false)}
  <span class="acts">
    {#if row.can?.includes('play')}<button class="act act--play" class:act--sq={short} type="button" aria-label="Play" onclick={(e) => { e.stopPropagation(); onact?.(row, 'play'); }}><span class="tri"></span>{#if !short}<span>Play</span>{/if}</button>{/if}
    {#if row.can?.includes('next')}<button class="act" type="button" onclick={(e) => { e.stopPropagation(); onact?.(row, 'next'); }}>{#if !short}<span class="nexti"><span class="tri tri--s"></span><b></b></span>{/if}<span>{short ? 'Next' : 'Play next'}</span></button>{/if}
    {#if row.can?.includes('add')}<button class="act" type="button" onclick={(e) => { e.stopPropagation(); onact?.(row, 'add'); }}>{#if !short}<span class="plus"></span>{/if}<span>Add</span></button>{/if}
  </span>
{/snippet}

{#snippet rowOf(r, lead, opts = {})}
  {@const isSel = r.kind === 'play' && selected === r.handle}
  {@const pc = opts.plays ? playCount(r.label) : { label: r.label, plays: null }}
  <button
    class="row"
    class:row--two={!!r.subtitle || opts.two}
    class:is-sel={isSel}
    class:is-busy={busy === r.handle}
    type="button"
    onclick={() => tap(r)}
  >
    {#if opts.num != null}<span class="num" class:num--top={opts.num <= 3 && opts.podium}>{opts.num}</span>{/if}
    {#if lead.disc}<Disc name={lead.disc} tint={lead.tint} size={D} />{:else if lead.thumb && !r.image}<Disc name={r.subtitle ? 'Note' : 'Rss'} tint={r.subtitle ? T.coral : T.amber} size={D} />{:else if lead.thumb}<span class="thumb"><img src={r.image} alt="" loading="lazy" /></span>{:else if lead.init}<span class="init">{initials(r.label)}</span>{/if}
    <span class="row__text">
      <span class="row__label" class:is-unnamed={!r.label}>{r._unnamed ? 'No name' : pc.label || 'No name'}</span>
      {#if r.subtitle}<span class="row__sub">{r.subtitle}</span>{/if}
    </span>
    {#if isSel}
      {@render actionsFor(r)}
    {:else if r._unnamed}
      <span class="row__meta">{r._unnamed}</span>
    {:else if pc.plays != null}
      <span class="row__meta">{pc.plays} plays</span>
    {:else if r.unavailable && !r.can?.length && r.kind !== 'folder'}
      <span class="row__meta">Not available</span>
    {:else if r.duration}
      <span class="row__meta">{mmss(r.duration)}</span>
    {:else if opts.meta}
      <span class="row__meta">{opts.meta}</span>
    {/if}
  </button>
{/snippet}

{#snippet heads(entry)}
  <div class="head" class:head--first={entry.first} data-letter={entry.head.length === 1 ? entry.head : null}>
    <span class="head__label" style:color={entry.tint}>{entry.head}</span>
    <span class="head__rule"></span>
    <span class="head__meta">{entry.meta}</span>
  </div>
{/snippet}

{#snippet rail()}
  {#if alphabetical && bar}
    <div class="strip"><JumpStrip have={(l) => l in known} on={onLetter} tint={STRIP_TINT[layout] ?? STRIP_TINT.artists} onpick={jump} /></div>
  {:else if alphabetical}
    <div class="rail">
      {#each RAIL as l (l)}
        {@const have = l in known}
        <button class="rail__l" class:is-on={l === onLetter} class:is-have={have} type="button" disabled={!have} onclick={() => jump(l)}>{l}</button>
      {/each}
    </div>
  {/if}
{/snippet}

{#snippet stateBlock(glyph, tint, title, body, retry)}
  <div class="state">
    <Disc name={glyph} {tint} size={bar ? 72 : 92} />
    <div class="state__text">
      <div class="state__title">{title}</div>
      <div class="state__body">{body}</div>
      {#if retry}<button class="retry" type="button" onclick={() => onretry?.()}>Retry</button>{/if}
    </div>
  </div>
{/snippet}

{#snippet albumFacts()}
  {#if album.facts.length}
    {#if !bar}<div class="sechead sechead--release"><span>Release</span><i></i></div>{/if}
    <div class="facts">
      {#each album.facts as [k, v] (k)}<div><div class="facts__k">{k}</div><div class="facts__v">{v}</div></div>{/each}
    </div>
  {/if}
  {#if album.links.length}
    <div class="links">
      {#each album.links as l (l.row.handle)}
        <button class="link" type="button" onclick={() => tap(l.row)}><span class="link__k">{l.kv[0]}</span>{#if l.kv[1]}<span class="link__v">{l.kv[1]}</span>{/if}<span class="chev"></span></button>
      {/each}
    </div>
  {/if}
{/snippet}

{#snippet playAll(label)}
  {#if !bar && ctx.from?.can?.includes('play')}
    <div class="playall">
      <button class="playall__go" type="button" onclick={() => onact?.(ctx.from, 'play')}><span class="tri tri--l"></span><span>{label}</span></button>
      <span class="playall__rule"></span>
      <span class="playall__meta">{fmt(page.count)} {page.count === 1 ? 'track' : 'tracks'}</span>
    </div>
  {/if}
{/snippet}

<div class="level" class:level--bar={bar} class:level--wide={wide}>
  {#if layout === 'loading'}
    <div class="pad loading">
      {#if ctx.opens === 'covers'}
        <div class="covers">
          {#each [1, 0.85, 0.7, 0.55, 0.4, 0.3, 0.6, 0.5, 0.4, 0.3, 0.22, 0.16] as o, i (i)}
            <div class="skel" style:opacity={o}><div class="skel__art"></div><div class="skel__l"></div><div class="skel__s"></div></div>
          {/each}
        </div>
      {:else}
        <div class="skelrows">
          {#each [1, 0.85, 0.7, 0.55, 0.4, 0.3, 0.22] as o, i (i)}<div class="skelrow" style:opacity={o}></div>{/each}
        </div>
      {/if}
      {#if slow}<div class="waiting"><span class="dot"></span>Waiting for {ctx.app ?? 'Lyrion'}</div>{/if}
    </div>
  {:else if layout === 'unreachable'}
    {@render stateBlock('Cloud', T.coral, `${ctx.app ?? 'Lyrion'} isn’t answering`, 'Lyrion could not reach the service. Your library and the other apps are unaffected.', true)}
  {:else if layout === 'nothing'}
    {@render stateBlock('Folder', T.slate, 'Nothing here', items[0]?.kind === 'text' && items[0].label && items.length === 1 ? items[0].label : `Lyrion has no entries under ${ctx.from?.label ?? page.title ?? 'this'}.`, false)}
  {:else if layout === 'favEmpty'}
    {@render stateBlock('Heart', T.pink, 'No favourites yet', 'Favourites you add in Lyrion, from any app or the library, appear here.', false)}
  {:else if layout === 'notSignedIn'}
    {@render stateBlock('Person', T.slate, `${ctx.app ?? 'This app'} isn’t signed in`, `Sign in to ${ctx.app ?? 'it'} in Lyrion’s own settings. Its menus appear here once it is.`, false)}
  {:else if layout === 'groups' && bar}
    <!-- My Music on a bar: the groups run sideways, five rows each. -->
    <div class="bgroups" use:across={bar}>
      {#each MY_MUSIC_GROUPS as g (g.key)}
        {@const entries = items.filter((r) => (MY_MUSIC[r.id]?.[0] ?? 'more') === g.key)}
        {#if entries.length}
          <div class="bgroup">
            <div class="group__head"><span style:color={g.ink}>{g.name}</span><i></i></div>
            <div class="bgroup__grid">
              {#each entries as r (r.handle)}
                {@const look = MY_MUSIC[r.id] ?? ['more', ...shapeFor(r.label, r.hint)]}
                <button class="entry" class:is-busy={busy === r.handle} type="button" onclick={() => tap(r)}>
                  <Disc name={look[1]} tint={look[2]} size={D} />
                  <span class="entry__label">{r.label}</span>
                </button>
              {/each}
            </div>
          </div>
        {/if}
      {/each}
    </div>
  {:else if layout === 'groups'}
    <!-- My Music: four columns, every entry visible from 711 to 853 tall. -->
    <div class="groups">
      {#each [0, 1, 2, 3] as column (column)}
        <div class="groups__col">
          {#each MY_MUSIC_GROUPS.filter((g) => g.column === column) as g (g.key)}
            {@const entries = items.filter((r) => (MY_MUSIC[r.id]?.[0] ?? 'more') === g.key)}
            {#if entries.length}
              <div class="group" style:flex={entries.length}>
                <div class="group__head"><span style:color={g.ink}>{g.name}</span><i></i></div>
                {#each entries as r (r.handle)}
                  {@const look = MY_MUSIC[r.id] ?? ['more', ...shapeFor(r.label, r.hint)]}
                  <button class="entry" class:is-busy={busy === r.handle} type="button" onclick={() => tap(r)}>
                    <Disc name={look[1]} tint={look[2]} size={46} />
                    <span class="entry__label">{r.label}</span>
                  </button>
                {/each}
              </div>
            {/if}
          {/each}
        </div>
      {/each}
    </div>
  {:else if layout === 'apps'}
    <div class="pad scroll">
      <div class="cards" style:--rows={2} use:across={bar}>
        {#each nonText as r (r.handle)}
          <button class="card" type="button" class:is-busy={busy === r.handle} onclick={() => tap(r)}>
            <span class="logo">{#if r.image}<img src={r.image} alt="" />{:else}{initials(r.label)}{/if}</span>
            <span class="card__text"><span class="card__label">{r.label}</span></span>
          </button>
        {/each}
      </div>
    </div>
  {:else if layout === 'cards'}
    <div class="pad scroll cardlevel">
      {#if searches.length}
        <!-- A search is a field-button; several are one field and a chip each. -->
        <button class="fieldbtn" type="button" onclick={() => onsearchentry?.(searches[kind] ?? searches[0])}>
          <Glyph name="Search" ink={T.ink} />
          <span class="fieldbtn__label">{searches.length >= 3 ? `Search ${ctx.app ?? ''} · ${searches[kind]?.label ?? ''}` : searches[0].label === 'Search' || /^search$/i.test(searches[0].label) ? `Search ${ctx.app ?? ''}` : searches[0].label}</span>
          <span class="fieldbtn__phone"><Glyph name="Phone" ink="rgba(233,238,242,0.62)" /><span>Type on your phone</span></span>
        </button>
        {#if searches.length >= 3}
          <div class="chips" use:across={bar}>
            {#each searches as s, i (s.handle)}
              <button class="chip" class:is-on={i === kind} type="button" onclick={() => (kind = i)}>{s.label}</button>
            {/each}
          </div>
        {/if}
      {/if}
      {#if others.length}
        {@const sections = searches.length >= 3 ? [['Lists', others]] : others.some((r) => r.kind === 'play') && others.some((r) => r.kind !== 'play') ? [['Mixes', others.filter((r) => r.kind !== 'play')], ['Streams', others.filter((r) => r.kind === 'play')]] : [[null, others]]}
        {#each sections as [headLabel, cards] (headLabel ?? 'all')}
          {#if headLabel}<div class="sechead"><span>{headLabel}</span><i></i></div>{/if}
          <div class="cards" style:--rows={searches.length >= 3 || sections.length > 1 ? 1 : 2} use:across={bar}>
            {#each cards as r, i (r.handle)}
              {@const look = r.kind === 'play' ? ['Rss', [T.amber, T.pink, T.sky, T.green][i % 4]] : headLabel === 'Mixes' ? ['Arcs', [T.mint, T.sky, T.coral, T.blue, T.lilac, T.green][i % 6]] : shapeFor(r.label, r.hint)}
              {@const isSel = r.kind === 'play' && selected === r.handle}
              <button class="card" class:is-sel={isSel} class:is-busy={busy === r.handle} type="button" onclick={() => tap(r)}>
                <Disc name={look[0]} tint={look[1]} size={bar ? 42 : 54} />
                <span class="card__text">
                  <span class="card__label">{r.label || 'No name'}</span>
                  {#if r.subtitle}<span class="card__sub">{r.subtitle}</span>{/if}
                </span>
                {#if isSel}
                  <span class="card__play" role="presentation" onclick={(e) => { e.stopPropagation(); onact?.(r, 'play'); }}><span class="tri"></span>Play</span>
                {/if}
              </button>
            {/each}
          </div>
        {/each}
      {/if}
      {#if more}<div class="more" use:nearEnd></div>{/if}
    </div>
  {:else if layout === 'covers'}
    <div class="withrail">
      <div class="pad scroll coversl" bind:this={coversBox} use:across={bar}>
        {#if earlier}<div class="more" use:nearStart></div>{/if}
        <div class="covers">
          {#each items as r, i (r.handle ?? `t${i}`)}
            {#if r.kind !== 'text'}
              <button class="cover" class:is-busy={busy === r.handle} class:is-off={r.unavailable} type="button" onclick={() => tap(r)}>
                <span class="cover__art">{#if hasCover(r)}<img src={r.image} alt="" loading="lazy" />{:else}{@const look = shapeFor(r.label, r.hint)}<Disc name={look[0]} tint={look[1]} size={bar ? 72 : 92} />{/if}</span>
                <span class="cover__t" class:is-unnamed={!r.label}>{r.label || 'No name'}</span>
                <span class="cover__s">{r.unavailable ? `Not available${r.subtitle ? ` · ${r.subtitle}` : ''}` : (r.subtitle ?? '')}</span>
              </button>
            {/if}
          {/each}
        </div>
        {#if more}<div class="more" use:nearEnd></div>{/if}
      </div>
      {@render rail()}
    </div>
  {:else if layout === 'years'}
    <div class="pad scroll years" use:across={bar}>
      {#each decades as [name, ys] (name)}
        <div class="decade">
          <div class="decade__label"><Disc name="Calendar" tint={T.amber} size={D} /><span>{name}</span></div>
          <div class="decade__years">
            {#each ys as r (r.handle)}
              <button class="year" type="button" class:is-busy={busy === r.handle} onclick={() => tap(r)}>{r.label}</button>
            {/each}
          </div>
        </div>
      {/each}
      {#if more}<div class="more" use:nearEnd></div>{/if}
    </div>
  {:else if layout === 'album' && album}
    <div class="albumpage">
      <div class="albumpage__side">
        <span class="albumpage__cover">{#if ctx.from?.image}<img src={ctx.from.image} alt="" />{/if}</span>
        {#if !bar}
          <div class="albumpage__title">{ctx.from?.label ?? page.title}</div>
          <div class="albumpage__by">
            {#if ctx.from?.subtitle}<span class="albumpage__artist">{ctx.from.subtitle}</span>{/if}
            {#if album.year}<span class="albumpage__year">· {album.year}</span>{/if}
          </div>
        {/if}
        <div class="albumpage__acts">
          {#if album.none}<div class="albumpage__none">{ctx.app ?? 'The service'} can’t stream this album</div>{/if}
          {#if ctx.from?.can?.includes('play')}<button class="big big--play" type="button" onclick={() => onact?.(ctx.from, 'play')}><span class="tri tri--l"></span>Play album</button>{/if}
          {#if ctx.from?.can?.includes('add')}<button class="big" type="button" onclick={() => onact?.(ctx.from, 'add')}><span class="plus plus--l"></span>Add to queue</button>{/if}
        </div>
      </div>
      <div class="albumpage__main scroll">
        {#if !bar}<div class="tracks__head"><span>Tracks</span><span>{album.tracks.length}{album.minutes ? ` · ${album.minutes} min` : ''}</span></div>{/if}
        {#each album.tracks as r, i (r.handle)}
          {@const isSel = selected === r.handle}
          {@const off = r.unavailable && !r.can?.length}
          <button class="trow" class:is-sel={isSel} class:is-off={off} type="button" disabled={off} onclick={() => tapLeaf(r)}>
            <span class="trow__n">{String(i + 1).padStart(2, '0')}</span>
            <span class="trow__t">{r.label}</span>
            {#if isSel}{@render actionsFor(r, bar)}{:else if off}<span class="trow__d">Not available</span>{:else if r.duration}<span class="trow__d">{mmss(r.duration)}</span>{/if}
          </button>
        {/each}
        {#if !bar}{@render albumFacts()}{/if}
      </div>
      {#if bar}<div class="albumpage__facts scroll">{@render albumFacts()}</div>{/if}
    </div>
  {:else}
    <!-- Rows: genres, artists, ranked, folders, tracks, favourites. -->
    {@const cols = layout === 'genres' || layout === 'artists' ? (wide ? 5 : 3) : layout === 'ranked' || layout === 'favourites' ? (wide ? 3 : 2) : wide ? 2 : 1}
    <div class="withrail">
      <div class="pad scroll rowsl" bind:this={rowsBox} use:watchLetters>
        {#if layout === 'folder'}{@render playAll(ctx.from?.hint === 'folder' || ctx.opens === 'folder' ? 'Play folder' : 'Play all')}{/if}
        {#if layout === 'tracks'}{@render playAll('Play all')}{/if}
        {#if earlier}<div class="more" use:nearStart></div>{/if}
        <div class="grid" style:grid-template-columns="repeat({cols}, minmax(0, 1fr))">
          {#each layout === 'genres' ? lettered(nonText, T.coral) : layout === 'artists' ? lettered(nonText, T.blue) : items.map((r) => ({ row: r })) as entry, i (entry.row?.handle ?? `h${i}-${entry.head ?? ''}`)}
            {#if entry.head}
              {@render heads(entry)}
            {:else if entry.row.kind === 'text'}
              <div class="textline">{entry.row.label}</div>
            {:else}
              {@const r = entry.row}
              {#if layout === 'genres'}
                {@render rowOf(r, { disc: 'Tag', tint: r.label ? T.coral : T.slate })}
              {:else if layout === 'artists'}
                {@render rowOf(r, { init: true })}
              {:else if layout === 'ranked'}
                {@render rowOf(r, { init: true }, { num: (page.start ?? 0) + i + 1, podium: true })}
              {:else if layout === 'tracks'}
                {@render rowOf(r, { thumb: true }, { num: ctx.opens === 'tracks' ? (page.start ?? 0) + i + 1 : null, plays: ctx.opens === 'tracks', two: true })}
              {:else if layout === 'favourites'}
                {@const look = r.kind === 'play' && !hasCover(r) ? ['Arcs', T.sky] : r.kind === 'container' && !hasCover(r) ? ['Lines', T.coral] : r.kind === 'folder' ? ['Folder', T.mint] : null}
                {#if look}{@render rowOf(r, { disc: look[0], tint: look[1] }, { two: true })}{:else}{@render rowOf(r, { thumb: true }, { two: true })}{/if}
              {:else}
                {@const look = r.kind === 'play' ? ['Note', T.coral] : r.kind === 'search' ? ['Search', T.ink] : r.kind === 'folder' && !r.hint ? ['Folder', T.mint] : shapeFor(r.label, r.hint)}
                {#if hasCover(r) && r.kind !== 'folder'}{@render rowOf(r, { thumb: true })}{:else}{@render rowOf(r, { disc: look[0], tint: look[1] })}{/if}
              {/if}
            {/if}
          {/each}
        </div>
        {#if more}<div class="more" use:nearEnd></div>{/if}
        {#if more && page.count > 1000}<div class="foot"><i></i>{fmt((page.start ?? 0) + 1)}–{fmt((page.start ?? 0) + items.length)} of {fmt(page.count)} · more as you scroll<i></i></div>{/if}
      </div>
      {@render rail()}
    </div>
  {/if}
</div>

<style>
  /* min-width 0: in a bar's row a sideways list must not widen the level. */
  .level { position: relative; flex: 1; min-height: 0; min-width: 0; display: flex; flex-direction: column; }
  .pad { padding: 22px 40px 24px; box-sizing: border-box; }
  .scroll { flex: 1; min-height: 0; overflow-y: auto; scrollbar-width: none; touch-action: pan-y; }
  .scroll::-webkit-scrollbar { display: none; }
  .withrail { flex: 1; min-height: 0; min-width: 0; display: flex; }
  .withrail > .scroll { min-width: 0; }
  .more { height: 1px; }
  button { font: inherit; color: inherit; background: none; border: 0; padding: 0; text-align: left; cursor: pointer; }
  button:active { transform: scale(0.95); }
  .is-busy { opacity: 0.6; }
  .is-unnamed { font-style: italic; color: rgba(233, 238, 242, 0.62); }

  /* Play, the triangle; Play next, the triangle and a bar; Add, a plus. */
  .tri { width: 0; height: 0; border-left: 12px solid #7ed6bc; border-top: 8px solid transparent; border-bottom: 8px solid transparent; display: block; }
  .tri--l { border-left-width: 14px; border-top-width: 9px; border-bottom-width: 9px; }
  .tri--s { border-left: 9px solid rgba(233, 238, 242, 0.9); border-top-width: 6px; border-bottom-width: 6px; }
  .nexti { display: flex; align-items: center; gap: 2px; }
  .nexti b { width: 2.5px; height: 12px; border-radius: 1px; background: rgba(233, 238, 242, 0.9); display: block; }
  .plus { width: 14px; height: 14px; position: relative; display: block; }
  .plus::before, .plus::after { content: ''; position: absolute; border-radius: 2px; background: rgba(233, 238, 242, 0.9); }
  .plus::before { left: 0; top: 5.75px; width: 14px; height: 2.5px; }
  .plus::after { left: 5.75px; top: 0; width: 2.5px; height: 14px; }
  .plus--l { width: 17px; height: 17px; }
  .plus--l::before { top: 7px; width: 17px; height: 3px; }
  .plus--l::after { left: 7px; width: 3px; height: 17px; }

  /* ── Rows ─────────────────────────────────────────────────────────── */
  .rowsl { display: flex; flex-direction: column; gap: 14px; }
  .grid { display: grid; column-gap: 16px; row-gap: 4px; align-content: start; }
  .row { min-width: 0; height: 60px; display: flex; align-items: center; gap: 16px; padding: 0 12px 0 8px; border-radius: 14px; box-sizing: border-box; }
  .row--two { height: 64px; }
  .row.is-sel { background: rgba(126, 214, 188, 0.16); }
  .row.is-sel .row__label { color: #7ed6bc; }
  .row__text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .row__label { font-size: 20px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .row__sub { font-size: 15px; color: rgba(233, 238, 242, 0.62); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .row__meta { font-family: var(--font-mono); font-size: 16px; color: rgba(233, 238, 242, 0.62); flex-shrink: 0; }
  .num { font-family: var(--font-mono); font-size: 15px; color: rgba(233, 238, 242, 0.62); width: 34px; text-align: right; flex-shrink: 0; }
  .num--top { color: #e0a758; }
  .thumb { width: 46px; height: 46px; border-radius: 9px; overflow: hidden; position: relative; flex-shrink: 0; background: #17242d; box-shadow: inset 0 0 0 1px rgba(233, 238, 242, 0.1); display: block; }
  .thumb img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
  .init { width: 46px; height: 46px; border-radius: 50%; flex-shrink: 0; background: rgba(159, 180, 232, 0.14); border: 1px solid rgba(159, 180, 232, 0.3); box-sizing: border-box; display: flex; align-items: center; justify-content: center; font-size: 16px; font-weight: 700; letter-spacing: 0.02em; color: #9fb4e8; }
  .acts { display: flex; align-items: center; gap: 8px; flex-shrink: 0; }
  .act { height: 48px; padding: 0 18px; border-radius: 14px; background: rgba(233, 238, 242, 0.06); border: 1px solid rgba(233, 238, 242, 0.14); box-sizing: border-box; display: flex; align-items: center; gap: 10px; font-size: 17px; font-weight: 700; white-space: nowrap; }
  .act--play { background: rgba(126, 214, 188, 0.14); border-color: rgba(126, 214, 188, 0.36); }
  .textline { grid-column: 1 / -1; font-size: 16px; color: rgba(233, 238, 242, 0.62); padding: 10px 8px; }
  .head { scroll-margin-top: 14px; grid-column: 1 / -1; display: flex; align-items: center; gap: 14px; padding-top: 14px; padding-bottom: 8px; }
  .head--first { padding-top: 0; }
  .head__label { font-family: var(--font-mono); font-size: 14px; font-weight: 700; letter-spacing: 0.18em; flex-shrink: 0; }
  .head__rule { flex: 1; height: 1px; background: rgba(233, 238, 242, 0.1); }
  .head__meta { font-family: var(--font-mono); font-size: 12px; letter-spacing: 0.1em; color: rgba(233, 238, 242, 0.6); flex-shrink: 0; }
  .playall { display: flex; align-items: center; gap: 12px; flex-shrink: 0; }
  .playall__go { height: 56px; padding: 0 26px; border-radius: 15px; background: rgba(126, 214, 188, 0.14); border: 1px solid rgba(126, 214, 188, 0.36); display: flex; align-items: center; gap: 13px; box-sizing: border-box; font-size: 19px; font-weight: 700; white-space: nowrap; }
  .playall__rule { flex: 1; height: 1px; background: rgba(233, 238, 242, 0.1); }
  .playall__meta { font-family: var(--font-mono); font-size: 13px; letter-spacing: 0.14em; text-transform: uppercase; color: rgba(233, 238, 242, 0.62); }
  .foot { height: 56px; flex-shrink: 0; display: flex; align-items: center; justify-content: center; gap: 12px; font-family: var(--font-mono); font-size: 13px; letter-spacing: 0.16em; text-transform: uppercase; color: rgba(233, 238, 242, 0.62); }
  .foot i { width: 40px; height: 4px; border-radius: 2px; background: rgba(233, 238, 242, 0.18); display: block; }

  /* ── The rail: letters the list has at 0.72, the rest at 0.28 and inert. */
  .rail { width: 58px; flex-shrink: 0; display: flex; flex-direction: column; align-items: center; justify-content: space-between; padding: 10px 0; box-sizing: border-box; border-left: 1px solid rgba(233, 238, 242, 0.07); }
  .rail__l { font-family: var(--font-mono); font-size: 13px; font-weight: 700; line-height: 1; color: rgba(233, 238, 242, 0.28); padding: 2px 14px; }
  .rail__l.is-have { color: rgba(233, 238, 242, 0.72); }
  .rail__l.is-on { color: #7ed6bc; }

  /* ── My Music ──────────────────────────────────────────────────────── */
  .groups { flex: 1; min-height: 0; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 24px; padding: 16px 40px; box-sizing: border-box; }
  .groups__col { min-width: 0; min-height: 0; display: flex; flex-direction: column; gap: 6px; }
  .group { display: flex; flex-direction: column; gap: 6px; min-height: 0; }
  .group__head { height: 30px; flex-shrink: 0; display: flex; align-items: center; gap: 12px; }
  .group__head span { font-family: var(--font-mono); font-size: 13px; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; white-space: nowrap; }
  .group__head i { flex: 1; height: 1px; background: rgba(233, 238, 242, 0.1); }
  .entry { flex: 1 1 0; min-height: 54px; max-height: 76px; border-radius: 18px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(233, 238, 242, 0.1); display: flex; align-items: center; gap: 14px; padding: 0 16px 0 10px; box-sizing: border-box; }
  .entry__label { flex: 1; font-size: 19px; font-weight: 700; line-height: 1.15; min-width: 0; }

  /* ── Cards (Radio's), the field-button, chips ──────────────────────── */
  .cardlevel { display: flex; flex-direction: column; gap: 16px; }
  .cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); grid-auto-rows: 96px; gap: 16px; }
  .card { min-width: 0; border-radius: 18px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(233, 238, 242, 0.1); box-sizing: border-box; display: flex; align-items: center; gap: 18px; padding: 0 22px 0 20px; }
  .card.is-sel { background: rgba(126, 214, 188, 0.16); }
  .card__text { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .card__label { font-size: 21px; font-weight: 700; line-height: 1.15; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .card__sub { font-family: var(--font-mono); font-size: 13px; letter-spacing: 0.06em; color: rgba(233, 238, 242, 0.62); margin-top: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .card__play { height: 48px; padding: 0 18px; border-radius: 14px; background: rgba(126, 214, 188, 0.14); border: 1px solid rgba(126, 214, 188, 0.36); display: flex; align-items: center; gap: 10px; font-size: 17px; font-weight: 700; }
  .logo { width: 60px; height: 60px; border-radius: 14px; overflow: hidden; position: relative; flex-shrink: 0; background: rgba(233, 238, 242, 0.12); display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 800; }
  .logo img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
  .fieldbtn { height: 72px; flex-shrink: 0; border-radius: 18px; background: rgba(233, 238, 242, 0.07); border: 1px solid rgba(233, 238, 242, 0.16); box-sizing: border-box; display: flex; align-items: center; gap: 16px; padding: 0 22px; }
  .fieldbtn__label { font-size: 21px; font-weight: 600; color: rgba(233, 238, 242, 0.72); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; flex: 1; }
  .fieldbtn__phone { display: flex; align-items: center; gap: 10px; font-family: var(--font-mono); font-size: 13px; letter-spacing: 0.2em; text-transform: uppercase; color: rgba(233, 238, 242, 0.62); flex-shrink: 0; }
  .chips { display: flex; flex-wrap: wrap; gap: 10px; flex-shrink: 0; }
  .chip { height: 52px; padding: 0 20px; border-radius: 999px; display: flex; align-items: center; gap: 10px; box-sizing: border-box; background: rgba(233, 238, 242, 0.06); border: 1px solid rgba(233, 238, 242, 0.14); font-size: 18px; font-weight: 700; white-space: nowrap; }
  .chip.is-on { background: rgba(126, 214, 188, 0.16); border-color: rgba(126, 214, 188, 0.4); color: #7ed6bc; }
  .sechead { display: flex; align-items: center; gap: 12px; padding-top: 6px; }
  .sechead span { font-family: var(--font-mono); font-size: 13px; font-weight: 700; letter-spacing: 0.2em; text-transform: uppercase; color: rgba(233, 238, 242, 0.62); }
  .sechead i { flex: 1; height: 1px; background: rgba(233, 238, 242, 0.1); }

  /* ── Covers ────────────────────────────────────────────────────────── */
  .covers { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 26px 22px; }
  .cover { min-width: 0; display: block; }
  .cover__art { width: 100%; aspect-ratio: 1; border-radius: 16px; overflow: hidden; position: relative; background: #17242d; box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1); display: flex; align-items: center; justify-content: center; }
  .cover__art img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
  .cover__t { display: block; font-size: 17px; font-weight: 600; margin-top: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .cover__s { display: block; font-size: 15px; color: rgba(233, 238, 242, 0.62); margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-height: 1.2em; }

  /* ── Years ─────────────────────────────────────────────────────────── */
  .years { display: flex; flex-direction: column; gap: 18px; padding-top: 18px; }
  .decade { display: grid; grid-template-columns: 132px minmax(0, 1fr); gap: 20px; align-items: start; }
  .decade__label { height: 64px; display: flex; align-items: center; gap: 12px; font-family: var(--font-mono); font-size: 17px; font-weight: 700; letter-spacing: 0.08em; color: #e0a758; }
  .decade__years { display: grid; grid-template-columns: repeat(10, minmax(0, 1fr)); gap: 8px; }
  .year { height: 64px; border-radius: 14px; background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(233, 238, 242, 0.1); display: flex; align-items: center; justify-content: center; box-sizing: border-box; font-family: var(--font-mono); font-size: 21px; font-weight: 600; text-align: center; }

  /* ── An app's album page ───────────────────────────────────────────── */
  .albumpage { flex: 1; min-height: 0; display: flex; gap: 36px; padding: 24px 40px; box-sizing: border-box; }
  .albumpage__side { width: 264px; flex-shrink: 0; display: flex; flex-direction: column; gap: 12px; }
  .albumpage__cover { width: 264px; height: 264px; border-radius: 16px; overflow: hidden; position: relative; flex-shrink: 0; background: #17242d; box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.1); display: block; }
  /* A short panel: the cover gives way, not the artist line. */
  @media (max-height: 760px) { .albumpage__cover { width: 200px; height: 200px; } }
  .albumpage__cover img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; }
  .albumpage__title { flex-shrink: 0; font-size: 24px; font-weight: 700; line-height: 1.2; margin-top: 4px; }
  .albumpage__by { flex-shrink: 0; display: flex; align-items: baseline; gap: 8px; font-size: 17px; white-space: nowrap; overflow: hidden; }
  .albumpage__artist { color: #f2a48f; font-weight: 600; overflow: hidden; text-overflow: ellipsis; }
  .albumpage__year { font-family: var(--font-mono); font-size: 15px; color: rgba(233, 238, 242, 0.62); }
  .albumpage__acts { margin-top: auto; display: flex; flex-direction: column; gap: 10px; }
  .big { height: 58px; border-radius: 16px; background: rgba(233, 238, 242, 0.06); border: 1px solid rgba(233, 238, 242, 0.16); display: flex; align-items: center; justify-content: center; gap: 14px; box-sizing: border-box; font-size: 19px; font-weight: 700; white-space: nowrap; }
  .big--play { background: rgba(126, 214, 188, 0.14); border-color: rgba(126, 214, 188, 0.36); }
  .albumpage__main { flex: 1; min-width: 0; display: flex; flex-direction: column; }
  .tracks__head { height: 36px; flex-shrink: 0; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid rgba(233, 238, 242, 0.08); margin-bottom: 8px; font-family: var(--font-mono); font-size: 13px; letter-spacing: 0.2em; text-transform: uppercase; color: rgba(233, 238, 242, 0.62); }
  .trow { height: 60px; flex-shrink: 0; display: flex; align-items: center; gap: 18px; padding: 0 12px 0 16px; border-radius: 14px; box-sizing: border-box; margin-bottom: 2px; }
  .trow.is-sel { background: rgba(126, 214, 188, 0.16); }
  .trow.is-sel .trow__t, .trow.is-sel .trow__n { color: #7ed6bc; }
  .trow__n { font-family: var(--font-mono); font-size: 15px; color: rgba(233, 238, 242, 0.62); width: 26px; flex-shrink: 0; }
  .trow__d { font-family: var(--font-mono); font-size: 15px; color: rgba(233, 238, 242, 0.62); flex-shrink: 0; }
  .trow.is-off { opacity: 0.5; cursor: default; }
  .trow.is-off:active { transform: none; }
  .cover.is-off .cover__art { opacity: 0.45; }
  .albumpage__none { font-size: 16px; line-height: 1.4; color: rgba(233, 238, 242, 0.72); padding: 12px 14px; border-radius: 14px; background: rgba(233, 238, 242, 0.05); border: 1px solid rgba(233, 238, 242, 0.1); }
  .trow__t { flex: 1; min-width: 0; font-size: 20px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .sechead--release { margin: 28px 0 14px; padding-top: 0; }
  .facts { display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px; }
  .facts__k { font-family: var(--font-mono); font-size: 12px; letter-spacing: 0.18em; text-transform: uppercase; color: rgba(233, 238, 242, 0.62); }
  .facts__v { font-size: 19px; font-weight: 600; margin-top: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .links { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 20px; padding-bottom: 8px; }
  .link { height: 52px; padding: 0 16px 0 20px; border-radius: 999px; background: rgba(233, 238, 242, 0.06); border: 1px solid rgba(233, 238, 242, 0.14); box-sizing: border-box; display: flex; align-items: center; gap: 10px; }
  .link__k { font-family: var(--font-mono); font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; color: rgba(233, 238, 242, 0.62); }
  .link__v { font-size: 18px; font-weight: 700; }
  .chev { width: 9px; height: 9px; border-right: 2.5px solid rgba(233, 238, 242, 0.72); border-top: 2.5px solid rgba(233, 238, 242, 0.72); transform: rotate(45deg); margin: 0 4px 0 2px; display: block; }

  /* ── States: the region blanks, never the screen ───────────────────── */
  .state { flex: 1; min-height: 0; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 18px; padding: 24px 40px; box-sizing: border-box; text-align: center; }
  .state__title { font-size: 30px; font-weight: 700; letter-spacing: -0.01em; margin-top: 6px; white-space: nowrap; }
  .state__body { font-size: 19px; line-height: 1.5; color: rgba(233, 238, 242, 0.72); width: 560px; max-width: 100%; text-wrap: pretty; }
  .retry { height: 56px; padding: 0 30px; border-radius: 999px; background: rgba(159, 180, 232, 0.14); border: 1px solid rgba(159, 180, 232, 0.36); box-sizing: border-box; display: flex; align-items: center; margin-top: 8px; font-size: 19px; font-weight: 700; }
  .loading { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 22px; overflow: hidden; }
  .skel__art { width: 100%; aspect-ratio: 1; border-radius: 16px; background: rgba(233, 238, 242, 0.07); }
  .skel__l { height: 14px; width: 78%; border-radius: 7px; background: rgba(233, 238, 242, 0.08); margin-top: 14px; }
  .skel__s { height: 12px; width: 52%; border-radius: 6px; background: rgba(233, 238, 242, 0.06); margin-top: 9px; }
  .skel, .skelrow { animation: pulse 1500ms ease-in-out infinite; }
  .skelrows { display: flex; flex-direction: column; gap: 8px; }
  .skelrow { height: 60px; border-radius: 14px; background: rgba(233, 238, 242, 0.05); }
  @keyframes pulse { 50% { filter: opacity(0.55); } }
  .waiting { display: flex; align-items: center; justify-content: center; gap: 12px; font-family: var(--font-mono); font-size: 13px; letter-spacing: 0.2em; text-transform: uppercase; color: rgba(233, 238, 242, 0.62); }
  .dot { width: 8px; height: 8px; border-radius: 50%; background: #7ed6bc; display: block; }
  /* ── The Bar family (the handover's §Frame — Bar): 400 tall ─────────── */
  .level--bar .pad { padding: 22px 28px 22px; }
  .level--bar .withrail { flex-direction: column; }
  .strip { flex-shrink: 0; padding: 0 28px 22px; }
  .level--bar .row { height: 52px; border-radius: 12px; gap: 14px; }
  .level--bar .row--two { height: 60px; }
  .level--bar .row__label { font-size: 19px; }
  .level--bar .row__sub { font-size: 14px; }
  .level--bar .thumb, .level--bar .init { width: 42px; height: 42px; }
  .level--bar .init { font-size: 15px; }
  .level--bar .act { height: 46px; }
  .act--sq { width: 46px; padding: 0; justify-content: center; }
  .level--bar .head { padding-top: 10px; padding-bottom: 6px; }
  .level--bar .head--first { padding-top: 0; }
  /* Sideways: a finger pans them natively, the phone's touchpad scrolls x. */
  .level--bar .bgroups, .level--bar .coversl, .level--bar .years, .level--bar .cards, .level--bar .chips {
    overflow-x: auto; overflow-y: hidden; touch-action: pan-x; scrollbar-width: none; overscroll-behavior-x: contain;
  }
  .level--bar .bgroups::-webkit-scrollbar, .level--bar .coversl::-webkit-scrollbar, .level--bar .years::-webkit-scrollbar,
  .level--bar .cards::-webkit-scrollbar, .level--bar .chips::-webkit-scrollbar { display: none; }
  /* My Music: groups sideways, five 56 px rows in 250 px columns. */
  .bgroups { flex: 1; min-height: 0; display: flex; gap: 28px; padding: 22px 28px; box-sizing: border-box; }
  .bgroup { flex-shrink: 0; display: flex; flex-direction: column; gap: 8px; }
  .bgroup__grid { display: grid; grid-auto-flow: column; grid-template-rows: repeat(5, 56px); grid-auto-columns: 250px; gap: 6px 10px; }
  .bgroup .entry { max-height: none; min-height: 0; border-radius: 14px; gap: 12px; padding: 0 12px 0 7px; }
  .bgroup .entry__label { font-size: 17px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  /* Cards: 300 px columns flowing sideways, one or two rows. */
  .level--bar .cardlevel { overflow: hidden; gap: 12px; }
  .level--bar .cards { grid-template-columns: none; grid-auto-flow: column; grid-auto-columns: 300px; grid-template-rows: repeat(var(--rows, 2), 96px); gap: 14px; flex-shrink: 0; }
  .level--bar .card { gap: 14px; padding: 0 18px 0 16px; }
  .level--bar .card__label { font-size: 19px; }
  .level--bar .logo { width: 54px; height: 54px; }
  .level--bar .fieldbtn { height: 60px; border-radius: 16px; }
  .level--bar .fieldbtn__label { font-size: 19px; }
  .level--bar .chips { flex-wrap: nowrap; }
  .level--bar .chip { height: 48px; font-size: 17px; }
  /* Covers: one sideways row of 200 px covers above the strip. */
  .level--bar .coversl { display: flex; align-items: flex-start; }
  .level--bar .coversl > .more { width: 1px; height: 1px; flex-shrink: 0; }
  .level--bar .covers { display: flex; gap: 22px; }
  .level--bar .cover { width: 200px; flex-shrink: 0; }
  .level--bar .cover__t { font-size: 16px; margin-top: 8px; }
  .level--bar .cover__s { font-size: 14px; }
  .level--bar .loading .covers { overflow: hidden; }
  .level--bar .loading .skel { width: 200px; flex-shrink: 0; }
  /* Years: decades sideways, each five rows of 112 x 56 chips. */
  .level--bar .years { flex-direction: row; gap: 28px; padding-top: 18px; }
  .level--bar .decade { display: flex; flex-direction: column; gap: 8px; flex-shrink: 0; }
  .level--bar .decade__label { height: 42px; font-size: 15px; }
  .level--bar .decade__years { grid-template-columns: none; grid-auto-flow: column; grid-template-rows: repeat(5, 56px); grid-auto-columns: 112px; gap: 6px; }
  .level--bar .year { height: 56px; font-size: 19px; }
  /* The app album page: a 180 px cover column, the tracks, the facts. */
  .level--bar .albumpage { gap: 24px; padding: 22px 28px; }
  .level--bar .albumpage__side { width: 180px; gap: 10px; }
  .level--bar .albumpage__cover { width: 180px; height: 180px; border-radius: 14px; }
  .level--bar .big { height: 52px; font-size: 17px; border-radius: 14px; }
  .level--bar .trow { height: 50px; gap: 14px; }
  .level--bar .trow__t { font-size: 18px; }
  .albumpage__facts { width: 250px; flex-shrink: 0; padding-left: 24px; border-left: 1px solid rgba(233, 238, 242, 0.08); }
  .level--wide .albumpage__facts { width: 420px; }
  .level--bar .facts { grid-template-columns: 1fr; gap: 10px; }
  .level--bar .facts > div { display: grid; grid-template-columns: 96px minmax(0, 1fr); align-items: baseline; gap: 10px; }
  .level--bar .facts__k { font-size: 11px; }
  .level--bar .facts__v { font-size: 16px; margin-top: 0; }
  .level--bar .links { margin-top: 16px; gap: 8px; }
  .level--bar .link { height: 44px; padding: 0 12px 0 16px; }
  .level--bar .link__v { font-size: 16px; }
  /* States: the disc on the left, the text on the right. */
  .level--bar .state { flex-direction: row; text-align: left; gap: 28px; }
  .level--bar .state__title { font-size: 28px; margin-top: 0; }
  .level--bar .state__body { font-size: 18px; width: 520px; margin-top: 8px; }
  .level--bar .retry { height: 52px; margin-top: 14px; }
  .state__text { display: flex; flex-direction: column; align-items: flex-start; }
  .level:not(.level--bar) .state__text { align-items: center; gap: 18px; }
</style>
