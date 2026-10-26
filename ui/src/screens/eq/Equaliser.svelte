<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Settings → Audio → Equaliser (ADR-0162; design/source/20, Turn 1, look 3a
  "Ridge"): on or off, the setting in use and its ten bands, the presets and
  the owner's own, Save as…, Rename and Delete, and the headroom note - for
  the output in use, which keeps its own.

  Three surfaces from one state: the panel (1280 x 800 family), the bars
  (logical height 400) and the phone (rows for the bands, the setting in a
  sheet). Choosing a setting glides the bands to their new levels; the
  setting itself is chosen at once.
-->
<script>
  import {
    BandSender, Glide, deleteEqualiser, equaliser, note, outputPhrase, outputShort,
    renameEqualiser, saveEqualiser, setEqualiser,
  } from '../../lib/equaliser.svelte.js';
  import { pressing } from '../../lib/press.svelte.js';
  import EqCurve from './EqCurve.svelte';
  import EqGraph from './EqGraph.svelte';
  import EqRows from './EqRows.svelte';

  let { surface = 'panel', onback, onhome = null } = $props();

  const press = pressing();
  const glide = new Glide();
  let error = $state(null);
  const sender = new BandSender((e) => (error = e.message));
  //: The bands as the finger set them, until the core's catch up.
  let local = $state(null);
  let drag = $state(-1);
  //: null | 'save' | 'rename' | 'delete' | 'full' | 'pick'
  let sheet = $state(null);
  let draft = $state('');
  let busy = $state(false);

  const FLAT = Array(10).fill(0);
  const eq = $derived($equaliser);
  const own = $derived(eq?.own ?? []);
  const on = $derived(!!eq?.on);
  const custom = $derived(eq?.sel === 'custom');
  const isOwn = $derived(!!eq && own.some((o) => o.key === eq.sel));
  const full = $derived(own.length >= (eq?.own_max ?? 10));
  const levels = $derived(glide.drawn ?? local ?? eq?.gains ?? FLAT);
  const told = $derived(eq ? note(eq) : null);
  const selName = $derived(!eq ? '' : custom ? 'Custom' : (eq.name ?? 'Flat'));
  const selMeta = $derived(!eq ? '' : custom ? (eq.from_name ? `From ${eq.from_name} · not saved` : 'Not saved')
    : isOwn ? 'Yours' : 'Preset');
  const phone = $derived(surface === 'phone');
  const bar = $derived(surface === 'bar');
  const nextName = $derived(`My setting ${own.length + 1}`);

  //: The core's bands have caught up with the finger: they are the truth again.
  $effect(() => {
    const g = eq?.gains;
    if (local && drag === -1 && g && g.every((v, i) => v === local[i])) local = null;
  });
  let settleTimer;
  function settle() {
    clearTimeout(settleTimer);
    settleTimer = setTimeout(() => {
      if (drag === -1) local = null;
    }, 2000);
  }

  function setBand(i, g) {
    if (!on) return;
    glide.stop();
    drag = i;
    const base = (local ?? eq.gains).slice();
    if (base[i] === g) return;
    base[i] = g;
    local = base;
    sender.send(base);
  }
  function endDrag() {
    drag = -1;
    settle();
  }

  async function choose(key) {
    if (sheet === 'pick') sheet = null;
    if (!on || !eq || key === eq.sel || key === 'custom') return;
    const target = [...eq.presets, ...own].find((o) => o.key === key);
    if (!target) return;
    glide.to(levels.slice(), target.gains);
    local = null;
    try {
      await setEqualiser({ sel: key });
    } catch (e) {
      error = e.message;
      glide.stop();
    }
  }

  async function toggle() {
    if (!eq || busy) return;
    busy = true;
    error = null;
    try {
      await setEqualiser({ on: !eq.on });
    } catch (e) {
      error = e.message;
    } finally {
      busy = false;
    }
  }

  function openSheet(which) {
    error = null;
    if (which === 'save') {
      draft = nextName;
      sheet = full ? 'full' : 'save';
    } else {
      if (which === 'rename') draft = eq?.name ?? '';
      sheet = which;
    }
  }
  function closeSheet() {
    sheet = null;
    error = null;
  }
  async function confirm() {
    error = null;
    try {
      if (sheet === 'save') await saveEqualiser(draft.trim() || nextName);
      else if (sheet === 'rename') await renameEqualiser(eq.sel, draft.trim() || eq.name);
      else if (sheet === 'delete') {
        glide.to(levels.slice(), eq.presets[0].gains);
        await deleteEqualiser(eq.sel);
      }
      sheet = null;
    } catch (e) {
      error = e.message;
    }
  }

  const sheets = $derived({
    save: { title: 'Save as…', note: `Saved settings are shared by every output. ${own.length} of ${eq?.own_max ?? 10} used.`,
      input: true, confirm: 'Save' },
    rename: { title: `Rename “${eq?.name ?? ''}”`, input: true, confirm: 'Rename' },
    delete: { title: `Delete “${eq?.name ?? ''}”?`, note: 'Its bands go. An output that uses it goes back to Flat.',
      confirm: 'Delete', danger: true },
    full: { title: 'Ten saved already', note: 'Ten of your own is the most there can be. Delete one, then save this setting.',
      confirm: 'OK', single: true },
    pick: { title: 'Setting', pick: true },
  });
  const shown = $derived(sheet ? sheets[sheet] : null);

  //: The list: Custom first when there is one, the presets, then the owner's.
  const items = $derived.by(() => {
    if (!eq) return [];
    const out = [];
    if (custom) out.push({ key: 'custom', name: 'Custom', custom: true });
    out.push({ head: 'Presets' });
    for (const p of eq.presets) out.push(p);
    out.push({ head: `Yours · ${own.length} of ${eq.own_max}` });
    for (const o of own) out.push(o);
    return out;
  });

  //: The list keeps the setting in use in view: on opening, and when it
  //: changes (a setting saved lands below the presets).
  function scrollToSelected(node, sel) {
    const show = () => requestAnimationFrame(() => {
      const t = node.querySelector('[data-sel="1"]');
      if (!t) return;
      const top = t.getBoundingClientRect().top - node.getBoundingClientRect().top;
      if (top < 0 || top + t.offsetHeight > node.clientHeight) node.scrollTop += top - node.clientHeight / 2;
    });
    show();
    return { update: show };
  }
  const back = () => press.act(() => onback?.());
</script>

{#snippet toggleSwitch()}
  <span class="switch" class:is-on={on}><span></span></span>
{/snippet}

{#snippet list(inSheet)}
  {#each items as it, n (it.head ?? it.key)}
    {#if it.head}
      <div class="head" class:head--first={n === 0}>
        {#if !bar && !inSheet}<span class="head__dot"></span>{/if}
        <span class="head__text">{it.head}</span><span class="head__rule"></span>
      </div>
    {:else}
      {@const sel = eq.sel === it.key}
      <button type="button" class="item" class:is-sel={sel} data-sel={sel ? '1' : '0'}
              aria-pressed={sel} onclick={() => choose(it.key)}>
        <span class="ring"><span></span></span>
        <span class="item__name">{it.name}</span>
        {#if it.custom}
          {#if bar && !inSheet}<span class="item__dot"></span>{:else}<span class="item__meta">Not saved</span>{/if}
        {/if}
      </button>
    {/if}
  {/each}
{/snippet}

{#snippet actions()}
  <div class="actions" class:is-off={!on}>
    <button type="button" class="btn" class:btn--primary={custom && !full} class:is-dim={full}
            onclick={() => openSheet('save')}>Save as…</button>
    {#if isOwn}
      <button type="button" class="btn" onclick={() => openSheet('rename')}>Rename</button>
      <button type="button" class="btn btn--danger" onclick={() => openSheet('delete')}>Delete</button>
    {/if}
  </div>
{/snippet}

{#snippet badge()}
  <span class="badge" class:badge--amber={told.amber}>{told.badge}</span>
{/snippet}

<div class="eq" class:eq--bar={bar} class:eq--phone={phone} data-dpad-layer>
  {#if bar}
    <div class="ground ground--bar"></div>
  {:else}
    <div class="weave"></div>
  {/if}
  <div class="veil" class:veil--bar={bar}></div>

  {#if !eq}
    <div class="frame">
      <div class="top">
        <button class="back" class:is-pressed={press.is('back')} type="button" aria-label="Back" data-dpad-back
                onpointerdown={() => press.down('back')} onpointerup={press.up} onpointercancel={press.up}
                onclick={back}><span></span></button>
        <div class="top__text"><div class="title">Equaliser</div></div>
      </div>
      <p class="none">There is no output to set it for.</p>
    </div>
  {:else if bar}
    <div class="frame frame--bar">
      <div class="side">
        <div class="side__buttons">
          <button class="back back--bar" class:is-pressed={press.is('back')} type="button" aria-label="Back" data-dpad-back
                  onpointerdown={() => press.down('back')} onpointerup={press.up} onpointercancel={press.up}
                  onclick={back}><span></span></button>
          {#if onhome}
            <button class="home" class:is-pressed={press.is('home')} type="button" aria-label="Home"
                    onpointerdown={() => press.down('home')} onpointerup={press.up} onpointercancel={press.up}
                    onclick={() => press.act(onhome)}><span class="grid"><i></i><i></i><i></i><i></i></span></button>
          {/if}
        </div>
        <div class="title title--bar">Equaliser</div>
        <div class="crumb crumb--bar">Audio · {outputShort(eq.output)}</div>
        <div class="side__rest"></div>
        <button type="button" class="power power--bar" aria-pressed={on} onclick={toggle}>
          <span class="power__state" class:is-on={on}>{on ? 'On' : 'Off'}</span>
          {@render toggleSwitch()}
        </button>
      </div>
      <div class="list list--bar" class:is-off={!on} use:scrollToSelected={eq?.sel}>{@render list(false)}</div>
      <div class="content">
        <div class="content__top">
          <div class="content__text">
            <div class="namerow">
              <span class="selname">{selName}</span>
              <span class="selmeta" class:is-amber={custom}>{selMeta}</span>
            </div>
            <div class="barnote" class:is-amber={told.amber}>{told.text}</div>
          </div>
          {@render actions()}
        </div>
        <div class="card card--bar" class:is-off={!on} class:is-dsd={on && eq.dsd}>
          <EqGraph {levels} bands={eq.bands} surface="bar" {drag} disabled={!on}
                   onset={setBand} onend={endDrag} />
        </div>
      </div>
    </div>
  {:else if phone}
    <div class="frame">
      <div class="top top--phone">
        <button class="back" class:is-pressed={press.is('back')} type="button" aria-label="Back" data-dpad-back
                onpointerdown={() => press.down('back')} onpointerup={press.up} onpointercancel={press.up}
                onclick={back}><span></span></button>
        <div class="top__text">
          <div class="title title--phone">Equaliser</div>
          <div class="crumb">Settings · Audio</div>
        </div>
      </div>
      <div class="scroll">
        <button type="button" class="pcard" aria-pressed={on} onclick={toggle}>
          <span class="pcard__text">
            <span class="pcard__title">Equaliser</span>
            <span class="pcard__note">For {outputPhrase(eq.output)}. Each output keeps its own.</span>
          </span>
          {@render toggleSwitch()}
        </button>
        <button type="button" class="pcard pcard--setting" class:is-off={!on} onclick={() => openSheet('pick')}>
          <span class="pcard__text">
            <span class="pcard__title">Setting</span>
            <span class="pcard__note" class:is-amber={custom}>{selMeta}</span>
          </span>
          <span class="pcard__value">{selName}</span>
          <span class="chev"></span>
        </button>
        <div class="phone-actions">{@render actions()}</div>
        <div class="card card--phone" class:is-off={!on} class:is-dsd={on && eq.dsd}>
          <EqCurve {levels} bands={eq.bands} {drag} />
          <div class="pnote">
            <span class="badge badge--phone" class:badge--amber={told.amber}>{told.badge}</span>
            <span class="pnote__text">{told.text}</span>
          </div>
        </div>
        <div class="bandshead">
          <span>Bands</span><span class="head__rule"></span><span class="bandshead__range">{'−'}12 to +12 dB</span>
        </div>
        <div class:is-off={!on} class:is-dsd={on && eq.dsd} class="rowsbox">
          <EqRows {levels} bands={eq.bands} {drag} disabled={!on} onset={setBand} onend={endDrag} />
        </div>
      </div>
    </div>
  {:else}
    <div class="frame">
      <div class="top">
        <button class="back" class:is-pressed={press.is('back')} type="button" aria-label="Back" data-dpad-back
                onpointerdown={() => press.down('back')} onpointerup={press.up} onpointercancel={press.up}
                onclick={back}><span></span></button>
        <div class="top__text">
          <div class="title">Equaliser</div>
          <div class="crumb">Audio · for {outputPhrase(eq.output)} · each output keeps its own</div>
        </div>
        <button type="button" class="power" aria-pressed={on} onclick={toggle}>
          <span class="power__state" class:is-on={on}>{on ? 'On' : 'Off · bit-perfect'}</span>
          {@render toggleSwitch()}
        </button>
      </div>
      <div class="body">
        <div class="list" class:is-off={!on} use:scrollToSelected={eq?.sel}>{@render list(false)}</div>
        <div class="right">
          <div class="card" class:is-off={!on} class:is-dsd={on && eq.dsd}>
            <div class="namerow">
              <span class="selname">{selName}</span>
              <span class="selmeta" class:is-amber={custom}>{selMeta}</span>
            </div>
            <EqGraph {levels} bands={eq.bands} surface="panel" {drag} disabled={!on}
                     onset={setBand} onend={endDrag} />
          </div>
          <div class="foot">
            <div class="foot__note">
              {@render badge()}
              <span class="foot__text">{told.text}</span>
            </div>
            {@render actions()}
          </div>
        </div>
      </div>
    </div>
  {/if}

  {#if error && !sheet}
    <div class="toast" role="status">{error}</div>
  {/if}

  {#if shown}
    <div class="scrim" role="presentation" onclick={closeSheet}></div>
    <div class="sheet" role="dialog" aria-label={shown.title}
         ondpadback={(event) => { event.preventDefault(); closeSheet(); }}>
      <div class="sheet__head">
        <div class="sheet__title">{shown.title}</div>
        {#if shown.note}<div class="sheet__note">{shown.note}</div>{/if}
      </div>
      {#if shown.pick}
        <div class="sheet__list" use:scrollToSelected={eq?.sel}>{@render list(true)}</div>
      {/if}
      {#if shown.input}
        <!-- No on-screen keyboard on the panel: a keyboard on the player, or
             the phone's touchpad, types here (ADR-0121). -->
        <input class="field" type="text" bind:value={draft} maxlength="40" autocomplete="off"
               spellcheck="false" aria-label="Name"
               onkeydown={(event) => event.key === 'Enter' && confirm()} />
        {#if !phone}
          <div class="sheet__hint">Type with a keyboard on the player, or from the phone’s touchpad.</div>
        {/if}
      {/if}
      {#if error}<div class="sheet__error">{error}</div>{/if}
      <div class="sheet__actions">
        {#if !shown.single}
          <button type="button" class="sbtn" data-dpad-back onclick={closeSheet}>{shown.pick ? 'Close' : 'Cancel'}</button>
        {/if}
        {#if !shown.pick}
          <button type="button" class="sbtn sbtn--confirm" class:sbtn--danger={shown.danger}
                  onclick={() => (shown.single ? closeSheet() : confirm())}>{shown.confirm}</button>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .eq {
    position: absolute;
    inset: 0;
    z-index: 30;
    overflow: hidden;
    background: var(--bg-base);
    color: var(--ink);
    -webkit-tap-highlight-color: transparent;
  }
  /* On the phone, under the mini player (its scrim 19, its sheet 20), which
     stays over every page (ADR-0101). */
  .eq--phone {
    z-index: 18;
  }
  .weave {
    position: absolute;
    inset: -90px;
    background: repeating-linear-gradient(38deg, var(--bg-weave-a) 0 48px, var(--bg-weave-b) 48px 96px);
    filter: blur(70px);
    transform: scale(1.14);
  }
  .ground--bar {
    position: absolute;
    inset: 0;
    background: #37505f;
  }
  .veil {
    position: absolute;
    inset: 0;
    background: radial-gradient(130% 105% at 20% 42%, rgba(20, 33, 42, 0.72), rgba(13, 21, 28, 0.96));
  }
  .veil--bar {
    background: radial-gradient(130% 105% at 20% 42%, rgba(20, 33, 42, 0.62), rgba(13, 21, 28, 0.93));
  }
  .frame {
    position: relative;
    height: 100%;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }
  .frame--bar {
    flex-direction: row;
  }
  .none {
    padding: 40px 36px;
    font-size: 19px;
    color: rgba(233, 238, 242, 0.72);
  }

  /* -- the head -- */
  .top {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 0 36px;
    min-height: 92px;
    border-bottom: 1px solid rgba(233, 238, 242, 0.09);
  }
  .top--phone {
    gap: 16px;
    padding: 14px 18px;
    min-height: 78px;
  }
  .top__text {
    flex: 1;
    min-width: 0;
  }
  .title {
    font-size: 25px;
    font-weight: 700;
    letter-spacing: -0.01em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .title--phone {
    font-size: 23px;
  }
  .title--bar {
    font-size: 26px;
    margin-top: 8px;
    line-height: 1.15;
  }
  .crumb {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.06em;
    color: rgba(233, 238, 242, 0.6);
    margin-top: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .crumb--bar {
    font-size: 15px;
    margin-top: 0;
  }
  .back,
  .home {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    flex-shrink: 0;
    border: 0;
    padding: 0;
    background: rgba(233, 238, 242, 0.07);
    display: flex;
    align-items: center;
    justify-content: center;
    color: inherit;
  }
  .back span {
    width: 13px;
    height: 13px;
    border-left: 3px solid var(--ink);
    border-bottom: 3px solid var(--ink);
    transform: rotate(45deg);
    margin-left: 10px;
  }
  .back--bar,
  .home {
    width: 60px;
    height: 60px;
  }
  .back--bar span {
    width: 14px;
    height: 14px;
    margin-left: 11px;
  }
  .grid {
    width: 22px;
    height: 22px;
    display: grid;
    grid-template-columns: 1fr 1fr;
    grid-template-rows: 1fr 1fr;
    gap: 3.5px;
  }
  .grid i {
    border-radius: 2px;
    background: rgba(233, 238, 242, 0.85);
  }
  .back:active,
  .home:active,
  .is-pressed {
    transform: scale(0.95);
  }

  .power {
    display: flex;
    align-items: center;
    gap: 16px;
    height: 58px;
    padding: 0 14px 0 20px;
    border-radius: 15px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(233, 238, 242, 0.1);
    color: inherit;
    flex-shrink: 0;
  }
  .power:active {
    transform: scale(0.95);
  }
  .power--bar {
    gap: 12px;
    height: 60px;
    padding: 0 12px 0 16px;
  }
  .power__state {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    white-space: nowrap;
    color: rgba(233, 238, 242, 0.72);
  }
  .power--bar .power__state {
    flex: 1;
    min-width: 0;
    text-align: left;
    font-size: 15px;
  }
  .power__state.is-on {
    color: #7ed6bc;
  }
  .switch {
    width: 60px;
    height: 34px;
    border-radius: 17px;
    flex-shrink: 0;
    position: relative;
    box-sizing: border-box;
    display: block;
    background: rgba(233, 238, 242, 0.08);
    border: 1px solid rgba(233, 238, 242, 0.16);
    transition: background 140ms ease;
  }
  .switch span {
    position: absolute;
    top: 3px;
    left: 3px;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    display: block;
    background: rgba(233, 238, 242, 0.6);
    transition: left 140ms ease;
  }
  .switch.is-on {
    background: rgba(126, 214, 188, 0.32);
    border-color: rgba(126, 214, 188, 0.5);
  }
  .switch.is-on span {
    left: 29px;
    background: #7ed6bc;
  }

  /* -- the panel's body -- */
  .body {
    flex: 1;
    min-height: 0;
    display: flex;
    gap: 24px;
    padding: 22px 36px 26px;
  }
  .list {
    width: 300px;
    flex-shrink: 0;
    overflow-y: auto;
    scrollbar-width: none;
    display: flex;
    flex-direction: column;
    gap: 6px;
    transition: opacity 160ms ease;
  }
  .list::-webkit-scrollbar {
    display: none;
  }
  .is-off {
    opacity: 0.4;
    pointer-events: none;
  }
  .card.is-dsd,
  .rowsbox.is-dsd {
    opacity: 0.5;
  }
  .head {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 14px 2px 6px;
    flex-shrink: 0;
  }
  .head__dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    flex-shrink: 0;
    background: #7ed6bc;
  }
  .head__text {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: #7ed6bc;
    flex-shrink: 0;
    white-space: nowrap;
  }
  .head__rule {
    flex: 1;
    height: 1px;
    background: rgba(233, 238, 242, 0.1);
  }
  .item {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 14px;
    min-height: 56px;
    padding: 0 16px;
    border-radius: 14px;
    box-sizing: border-box;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(233, 238, 242, 0.1);
    color: rgba(233, 238, 242, 0.82);
    text-align: left;
    font: inherit;
  }
  .item.is-sel {
    background: rgba(126, 214, 188, 0.14);
    border-color: rgba(126, 214, 188, 0.4);
    color: var(--ink);
  }
  .ring {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    flex-shrink: 0;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 2px solid rgba(233, 238, 242, 0.3);
  }
  .ring span {
    width: 11px;
    height: 11px;
    border-radius: 50%;
    background: #7ed6bc;
    display: none;
  }
  .item.is-sel .ring {
    border-color: #7ed6bc;
  }
  .item.is-sel .ring span {
    display: block;
  }
  .item__name {
    flex: 1;
    min-width: 0;
    font-size: 17px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .item__meta {
    flex-shrink: 0;
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    white-space: nowrap;
    color: #e0a758;
  }
  .item__dot {
    flex-shrink: 0;
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: #e0a758;
  }

  .right {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }
  .card {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
    border-radius: 22px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(233, 238, 242, 0.1);
    padding: 20px 24px 14px;
    box-sizing: border-box;
    transition: opacity 160ms ease;
  }
  .namerow {
    display: flex;
    align-items: baseline;
    gap: 14px;
    flex-shrink: 0;
    min-width: 0;
  }
  .selname {
    font-size: 26px;
    font-weight: 700;
    letter-spacing: -0.01em;
    white-space: nowrap;
  }
  .selmeta {
    flex: 1 1 auto;
    min-width: 0;
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.06em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: rgba(233, 238, 242, 0.6);
  }
  .is-amber {
    color: #e0a758 !important;
  }
  .foot {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    min-height: 58px;
  }
  .foot__note {
    flex: 1;
    min-width: 0;
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .foot__text {
    flex: 1;
    min-width: 0;
    font-size: 15px;
    line-height: 1.4;
    color: rgba(233, 238, 242, 0.78);
    text-wrap: pretty;
  }
  .badge {
    flex-shrink: 0;
    min-width: 64px;
    height: 36px;
    padding: 0 10px;
    border-radius: 10px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: var(--font-mono);
    font-size: 15px;
    font-weight: 600;
    white-space: nowrap;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    color: var(--ink);
  }
  .badge--amber {
    background: rgba(224, 167, 88, 0.14);
    border-color: rgba(224, 167, 88, 0.4);
    color: #e0a758;
  }
  .badge--phone {
    min-width: 54px;
    height: 30px;
    padding: 0 8px;
    border-radius: 9px;
    font-size: 13px;
  }
  .actions {
    display: flex;
    gap: 10px;
    flex-shrink: 0;
  }
  .btn {
    height: 58px;
    padding: 0 24px;
    border-radius: 15px;
    box-sizing: border-box;
    display: flex;
    align-items: center;
    justify-content: center;
    font: inherit;
    font-size: 17px;
    font-weight: 600;
    white-space: nowrap;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    color: var(--ink);
  }
  .btn:active,
  .sbtn:active,
  .item:active {
    transform: scale(0.95);
  }
  .btn--primary {
    background: rgba(126, 214, 188, 0.16);
    border-color: rgba(126, 214, 188, 0.4);
    color: #7ed6bc;
    font-weight: 700;
  }
  .btn--danger {
    background: rgba(224, 167, 88, 0.14);
    border-color: rgba(224, 167, 88, 0.4);
    color: #e0a758;
  }
  .btn.is-dim {
    opacity: 0.5;
  }

  /* -- the bars -- */
  .side {
    width: 220px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 28px 24px 24px;
    box-sizing: border-box;
    border-right: 1px solid rgba(233, 238, 242, 0.09);
  }
  .side__buttons {
    display: flex;
    gap: 10px;
  }
  .side__rest {
    flex: 1;
  }
  .list--bar {
    width: clamp(250px, 18%, 340px);
    padding: 12px 20px 24px 24px;
    box-sizing: border-box;
    border-right: 1px solid rgba(233, 238, 242, 0.09);
    -webkit-mask-image: linear-gradient(180deg, #000 82%, transparent 100%);
    mask-image: linear-gradient(180deg, #000 82%, transparent 100%);
  }
  .list--bar .head {
    padding: 12px 2px 6px;
  }
  .list--bar .item__name {
    font-size: 18px;
  }
  .content {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 22px 32px 22px 24px;
    box-sizing: border-box;
  }
  .content__top {
    display: flex;
    align-items: center;
    gap: 20px;
    min-height: 60px;
    flex-shrink: 0;
  }
  .content__text {
    flex: 1;
    min-width: 0;
  }
  .eq--bar .selmeta {
    font-size: 15px;
  }
  .barnote {
    font-size: 16px;
    line-height: 1.3;
    margin-top: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    color: rgba(233, 238, 242, 0.72);
  }
  .eq--bar .btn {
    height: 60px;
    padding: 0 22px;
    font-size: 18px;
  }
  .card--bar {
    border-radius: 20px;
    padding: 8px 18px;
  }

  /* -- the phone -- */
  .scroll {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    scrollbar-width: none;
    padding: 14px 16px calc(24px + env(safe-area-inset-bottom, 0px));
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .scroll::-webkit-scrollbar {
    display: none;
  }
  .pcard {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 18px;
    border-radius: 15px;
    padding: 14px 20px;
    box-sizing: border-box;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(233, 238, 242, 0.1);
    color: inherit;
    text-align: left;
    font: inherit;
  }
  .pcard--setting {
    min-height: 78px;
  }
  .pcard__text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
  }
  .pcard__title {
    font-size: 18px;
    font-weight: 600;
  }
  .pcard__note {
    font-size: 14px;
    line-height: 1.36;
    color: rgba(233, 238, 242, 0.6);
    margin-top: 5px;
    text-wrap: pretty;
  }
  .pcard__value {
    font-family: var(--font-mono);
    font-size: 15px;
    flex-shrink: 0;
    color: rgba(233, 238, 242, 0.88);
  }
  .chev {
    width: 11px;
    height: 11px;
    border-right: 2.5px solid rgba(233, 238, 242, 0.42);
    border-top: 2.5px solid rgba(233, 238, 242, 0.42);
    transform: rotate(45deg);
    flex-shrink: 0;
  }
  .phone-actions .actions {
    flex-wrap: wrap;
    gap: 8px;
    padding: 4px 0 6px;
  }
  .phone-actions .btn {
    height: 44px;
    padding: 0 18px;
    border-radius: 12px;
    font-size: 15px;
  }
  .card--phone {
    flex: none;
    border-radius: 18px;
    padding: 14px 14px 10px;
  }
  .pnote {
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-top: 12px;
    padding-top: 12px;
    border-top: 1px solid rgba(233, 238, 242, 0.08);
  }
  .pnote__text {
    flex: 1;
    min-width: 0;
    font-size: 14px;
    line-height: 1.4;
    color: rgba(233, 238, 242, 0.78);
    text-wrap: pretty;
    padding-top: 5px;
  }
  .bandshead {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px 2px 4px;
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.6);
  }
  .bandshead__range {
    letter-spacing: 0.1em;
    text-transform: none;
    white-space: nowrap;
  }

  /* -- sheets -- */
  .scrim {
    position: absolute;
    inset: 0;
    z-index: 40;
    background: rgba(8, 12, 16, 0.62);
  }
  .sheet {
    position: absolute;
    z-index: 41;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: calc(100% - 44px);
    max-width: 560px;
    max-height: calc(100% - 24px);
    background: #16232c;
    border: 1px solid rgba(233, 238, 242, 0.14);
    border-radius: 22px;
    box-shadow: 0 30px 70px rgba(0, 0, 0, 0.5);
    box-sizing: border-box;
    padding: 26px;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }
  .sheet__title {
    font-size: 22px;
    font-weight: 700;
    text-wrap: pretty;
  }
  .sheet__note {
    font-size: 15px;
    line-height: 1.4;
    color: rgba(233, 238, 242, 0.6);
    margin-top: 8px;
    text-wrap: pretty;
  }
  .sheet__list {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    scrollbar-width: none;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .sheet__list .head {
    padding: 12px 2px 6px;
  }
  .sheet__list .head__text {
    font-size: 12px;
  }
  .sheet__list .item {
    gap: 16px;
    padding: 0 18px;
  }
  .field {
    flex-shrink: 0;
    width: 100%;
    box-sizing: border-box;
    height: 62px;
    border-radius: 14px;
    background: rgba(8, 12, 16, 0.6);
    border: 1px solid rgba(126, 214, 188, 0.45);
    padding: 0 18px;
    font-family: var(--font-mono);
    font-size: 17px;
    color: var(--ink);
    outline: none;
    user-select: text;
  }
  .field:focus {
    border-color: #7ed6bc;
  }
  .sheet__hint {
    flex-shrink: 0;
    font-family: var(--font-mono);
    font-size: 13px;
    line-height: 1.5;
    letter-spacing: 0.02em;
    color: rgba(233, 238, 242, 0.6);
    margin-top: -8px;
    text-wrap: pretty;
  }
  .sheet__error,
  .toast {
    font-size: 15px;
    line-height: 1.4;
    color: #e0a758;
  }
  .toast {
    position: absolute;
    z-index: 35;
    left: 50%;
    bottom: 28px;
    transform: translateX(-50%);
    background: rgba(22, 35, 44, 0.97);
    border: 1px solid rgba(224, 167, 88, 0.4);
    border-radius: 14px;
    padding: 14px 22px;
    max-width: calc(100% - 48px);
  }
  .sheet__actions {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .sbtn {
    flex: 1;
    height: 58px;
    border-radius: 15px;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    font: inherit;
    font-size: 17px;
    font-weight: 600;
    color: var(--ink);
  }
  .sbtn--confirm {
    font-weight: 700;
    background: rgba(126, 214, 188, 0.16);
    border-color: rgba(126, 214, 188, 0.4);
    color: #7ed6bc;
  }
  .sbtn--danger {
    background: rgba(224, 167, 88, 0.2);
    border-color: rgba(224, 167, 88, 0.5);
    color: #e0a758;
  }
</style>
