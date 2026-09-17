<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Settings, Phase 4 criterion 5 (ADR-0032, ADR-0035). Ported from
  design/source/Settings.dc.html. Rows come from the daemon's registry; the
  layout follows the component's own width, not the viewport, because it is
  standalone on a phone and will be embedded on the panel.
-->
<script>
  import { onMount } from 'svelte';
  import { settingsGroups, settingsError, loadSettings, writeSetting } from '../lib/settings.js';

  // On the panel, Settings is a layer over the library and Back closes it
  // (source/Now Playing.dc.html passes the design's onBack). A phone has
  // nothing to go back to, so it passes none.
  let { onback = null } = $props();

  const WIDE_MIN = 720;

  let width = $state(0);
  let cat = $state(null);
  let drilled = $state(null);
  let sheetKey = $state(null);
  let toast = $state(null);
  let toastTimer;

  const groups = $derived($settingsGroups);
  const loadError = $derived($settingsError);
  const wide = $derived((width || 1280) >= WIDE_MIN);
  const current = $derived(groups.find((g) => g.id === (wide ? (cat ?? groups[0]?.id) : drilled)) ?? null);
  const rows = $derived(current?.rows ?? []);
  const deviceName = $derived(valueOf('device_name') ?? 'gexis');
  const build = $derived(valueOf('image_build'));
  const sheet = $derived(sheetKey ? rowOf(sheetKey) : null);

  function rowOf(key) {
    for (const g of groups) for (const r of g.rows) if (r.key === key) return r;
    return null;
  }

  function valueOf(key) {
    for (const g of groups) for (const r of g.rows) if (r.key === key) return r.value;
    return undefined;
  }

  onMount(loadSettings);

  function flash(text) {
    clearTimeout(toastTimer);
    toast = text;
    toastTimer = setTimeout(() => (toast = null), 1900);
  }

  async function write(row, value) {
    const result = await writeSetting(row.key, value);
    if (result.status === 409) flash(`${row.label} — not wired yet`);
    else if (!result.ok) flash(`${row.label}: ${result.error ?? `HTTP ${result.status}`}`);
    return result.ok;
  }

  function pending(row) {
    return (row.marks ?? '').includes('?');
  }

  const MINUS = '−';
  function shown(row) {
    const v = row.value;
    if (row.type === 'toggle') return '';
    if (v === null || v === undefined) return row.type === 'action' ? '' : '—';
    if (row.type === 'number') {
      const n = row.step && row.step < 1 ? Number(v).toFixed(2) : String(v);
      const text = n.replace('-', MINUS);
      if (!row.unit) return text;
      return row.unit === '%' ? `${text}%` : `${text} ${row.unit}`;
    }
    return String(v);
  }

  function hostOf(name) {
    return (
      (String(name || '')
        .normalize('NFD')
        .replace(/[̀-ͯ]/g, '')
        .toLowerCase()
        .replace(/[^a-z0-9-]+/g, '-')
        .replace(/^-+|-+$/g, '')
        .slice(0, 63) || 'gexis') + '.local'
    );
  }

  function tap(row) {
    if (row.type === 'toggle') write(row, !row.value);
    else openSheet(row);
  }

  async function choose(option) {
    const row = sheet;
    sheetKey = null;
    if (String(row.value) === option) return;
    if (await write(row, option)) flash(`${row.label}: ${option}`);
  }

  let draft = $state(null);

  function openSheet(row) {
    sheetKey = row.key;
    draft = row.type === 'text' ? (row.value ?? '') : row.type === 'number' ? (row.value ?? row.min) : null;
  }

  async function saveNumber() {
    const row = sheet;
    if (Number(draft) === row.value) return;
    if (await write(row, Number(draft))) flash(`${row.label}: ${shown({ ...row, value: Number(draft) })}`);
  }

  async function confirmSheet() {
    const row = sheet;
    if (!row.wired) {
      sheetKey = null;
      flash(`${row.label} — not wired yet`);
      return;
    }
    if (row.type === 'text') {
      if (await write(row, draft)) {
        sheetKey = null;
        flash(`${row.label} saved`);
      }
    }
  }

  function back() {
    if (!wide && drilled) {
      drilled = null;
      return;
    }
    onback?.();
  }
</script>

<div class="settings" bind:clientWidth={width}>
  <div class="weave"></div>
  <div class="veil"></div>

  <div class="frame">
    <div class="head" class:head--wide={wide}>
      {#if (wide && onback) || (!wide && drilled)}
        <button class="back" type="button" aria-label="Back" onclick={back}><span></span></button>
      {/if}
      <div class="head__text">
        <div class="title" class:title--wide={wide}>{!wide && current ? current.label : 'Settings'}</div>
        {#if !wide}
          <div class="subtitle">{deviceName} &nbsp;·&nbsp; {hostOf(deviceName)}</div>
        {/if}
      </div>
      {#if wide && build}
        <span class="build">{build}</span>
      {/if}
    </div>

    {#if loadError}
      <div class="error">Settings could not be loaded: {loadError}</div>
    {:else}
      <div class="body">
        {#if wide}
          <div class="rail" data-noscrollbar>
            {#each groups as g (g.id)}
              <button
                class="cat"
                class:is-active={g.id === current?.id}
                type="button"
                onclick={() => (cat = g.id)}
              >
                <span class="bar" style:background={g.accent}></span>
                <span class="cat__name">{g.label}</span>
                {#if g.rows.some(pending)}<span class="dot"></span>{/if}
              </button>
            {/each}
          </div>
        {/if}

        {#if !wide && !drilled}
          <div class="list" class:list--wide={wide} data-noscrollbar>
            {#each groups as g (g.id)}
              <button class="card" type="button" onclick={() => (drilled = g.id)}>
                <span class="bar bar--tall" style:background={g.accent}></span>
                <span class="card__text">
                  <span class="card__title">
                    <span class="card__name">{g.label}</span>
                    {#if g.rows.some(pending)}<span class="dot dot--sm"></span>{/if}
                  </span>
                  <span class="card__blurb">{g.subtitle}</span>
                </span>
                <span class="chev"></span>
              </button>
            {/each}
          </div>
        {:else}
          <div class="list" class:list--wide={wide} data-noscrollbar>
            {#each rows as r, i (r.key ?? `group-${i}`)}
              {#if r.type === 'group'}
                <div class="subhead">
                  <span class="subhead__dot" style:background={r.accent}></span>
                  <span class="subhead__label" style:color={r.accent}>{r.label}</span>
                  <span class="subhead__rule"></span>
                </div>
              {:else}
                <button
                  class="row"
                  class:row--danger={r.danger}
                  type="button"
                  data-unwired={r.wired ? undefined : 'settings'}
                  onclick={() => tap(r)}
                >
                  <span class="row__body">
                    <span class="row__text">
                      <span class="row__label">
                        <span class="row__name">{r.label}</span>
                        {#if pending(r)}<span class="dot dot--sm"></span>{/if}
                      </span>
                      {#if r.note}<span class="row__note">{r.note}</span>{/if}
                    </span>
                    {#if r.type !== 'toggle' && shown(r)}
                      <span class="row__value" class:is-pending={pending(r)}>{shown(r)}</span>
                    {/if}
                    {#if r.type === 'toggle'}
                      <span class="toggle" class:is-on={!!r.value}><span></span></span>
                    {:else}
                      <span class="chev"></span>
                    {/if}
                  </span>
                </button>
              {/if}
            {/each}
          </div>
        {/if}
      </div>
    {/if}
  </div>

  <div class="scrim" class:is-open={sheet} role="presentation" onclick={() => (sheetKey = null)}></div>

  {#if sheet}
    <div class="sheet" role="dialog" aria-label={sheet.label}>
      <div class="sheet__head">
        <div class="sheet__title">{sheet.label}</div>
        {#if sheet.note}<div class="sheet__note">{sheet.note}</div>{/if}
      </div>

      {#if sheet.type === 'choice'}
        <div class="options" data-noscrollbar>
          {#each sheet.options as option (option)}
            {@const selected = String(sheet.value) === option}
            <button class="option" class:is-selected={selected} type="button" onclick={() => choose(option)}>
              <span class="radio"><span></span></span>
              <span class="option__label">{option}</span>
            </button>
          {/each}
        </div>
      {/if}

      {#if sheet.wired && sheet.type === 'number'}
        <div class="editor">
          <input
            class="range"
            type="range"
            min={sheet.min}
            max={sheet.max}
            step={sheet.step ?? 1}
            bind:value={draft}
            onchange={saveNumber}
            aria-label={sheet.label}
          />
          <span class="editor__value">{shown({ ...sheet, value: Number(draft) })}</span>
        </div>
      {:else if sheet.wired && sheet.type === 'text'}
        <input
          class="field"
          type="text"
          bind:value={draft}
          autocomplete="off"
          autocapitalize="off"
          spellcheck="false"
          aria-label={sheet.label}
        />
      {:else if sheet.type === 'readonly' || sheet.type === 'text' || sheet.type === 'number'}
        <div class="sheet__value">{shown(sheet)}</div>
      {/if}

      <div class="sheet__actions">
        <button class="btn" type="button" onclick={() => (sheetKey = null)}>
          {sheet.type === 'choice' || (sheet.wired && sheet.type === 'number') ? 'Close' : 'Cancel'}
        </button>
        {#if sheet.type === 'action' || sheet.type === 'text' || (sheet.type === 'number' && !sheet.wired)}
          <button class="btn btn--confirm" class:btn--danger={sheet.danger} type="button" onclick={confirmSheet}>
            {sheet.confirm ?? (sheet.type === 'action' ? 'Continue' : sheet.wired ? 'Save' : 'Edit')}
          </button>
        {/if}
      </div>
    </div>
  {/if}

  <div class="toast" class:is-shown={toast}>{toast ?? ''}</div>
</div>

<style>
  .settings {
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 100%;
    overflow: hidden;
    font-family: var(--font-ui);
    color: var(--ink);
    background: var(--bg-base);
    -webkit-tap-highlight-color: transparent;
  }
  .weave {
    position: absolute;
    inset: -90px;
    background: repeating-linear-gradient(38deg, var(--bg-weave-a) 0 48px, var(--bg-weave-b) 48px 96px);
    filter: blur(70px);
    transform: scale(1.14);
  }
  .veil {
    position: absolute;
    inset: 0;
    background: radial-gradient(130% 105% at 20% 42%, rgba(20, 33, 42, 0.72), rgba(13, 21, 28, 0.96));
  }
  .frame {
    position: relative;
    height: 100%;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  button {
    font: inherit;
    color: inherit;
    text-align: inherit;
    border: 0;
    margin: 0;
    background: none;
    padding: 0;
  }
  [data-noscrollbar] {
    scrollbar-width: none;
  }

  .head {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 16px;
    border-bottom: 1px solid rgba(233, 238, 242, 0.09);
    padding: 14px 18px;
    min-height: 78px;
  }
  .head--wide {
    padding: 0 36px;
    min-height: 92px;
  }
  .back {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    background: rgba(233, 238, 242, 0.07);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .back:active {
    background: rgba(233, 238, 242, 0.2);
  }
  .back span {
    width: 13px;
    height: 13px;
    border-left: 3px solid var(--ink);
    border-bottom: 3px solid var(--ink);
    transform: rotate(45deg);
    margin-left: 10px;
  }
  .head__text {
    flex: 1;
    min-width: 0;
  }
  .title {
    font-weight: 700;
    letter-spacing: -0.01em;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 23px;
  }
  .title--wide {
    font-size: 25px;
  }
  .subtitle {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.06em;
    color: rgba(233, 238, 242, 0.5);
    margin-top: 4px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .build {
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.6);
    flex-shrink: 0;
  }

  .error {
    position: relative;
    padding: 36px;
    color: var(--accent-warn);
    font-family: var(--font-mono);
    font-size: 15px;
  }

  .body {
    position: relative;
    flex: 1;
    min-height: 0;
    display: flex;
  }

  .rail {
    width: 290px;
    flex-shrink: 0;
    border-right: 1px solid rgba(233, 238, 242, 0.09);
    padding: 18px 16px;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .cat {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 15px;
    height: 72px;
    padding: 0 16px;
    border-radius: 14px;
  }
  .cat:active {
    background: rgba(233, 238, 242, 0.13);
  }
  .cat.is-active {
    background: rgba(233, 238, 242, 0.1);
  }
  .bar {
    width: 4px;
    height: 30px;
    border-radius: 2px;
    flex-shrink: 0;
    display: block;
  }
  .bar--tall {
    height: auto;
    align-self: stretch;
  }
  .cat__name {
    flex: 1;
    min-width: 0;
    font-size: 19px;
    font-weight: 600;
    color: rgba(233, 238, 242, 0.76);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .cat.is-active .cat__name {
    color: var(--ink);
  }
  .dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    background: var(--accent-warn);
    flex-shrink: 0;
    display: block;
  }
  .dot--sm {
    width: 8px;
    height: 8px;
  }

  .list {
    flex: 1;
    min-width: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: 14px 16px 30px;
  }
  .list--wide {
    padding: 20px 36px 36px;
  }

  .card {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 16px;
    min-height: 78px;
    padding: 16px 18px;
    border-radius: 16px;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(233, 238, 242, 0.1);
  }
  .card:active {
    background: rgba(233, 238, 242, 0.13);
  }
  .card__text {
    flex: 1;
    min-width: 0;
    display: block;
  }
  .card__title {
    display: flex;
    align-items: center;
    gap: 9px;
  }
  .card__name {
    font-size: 19px;
    font-weight: 600;
  }
  .card__blurb {
    display: block;
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.05em;
    color: rgba(233, 238, 242, 0.55);
    margin-top: 6px;
  }
  .chev {
    width: 11px;
    height: 11px;
    border-right: 2.5px solid rgba(233, 238, 242, 0.42);
    border-top: 2.5px solid rgba(233, 238, 242, 0.42);
    transform: rotate(45deg);
    flex-shrink: 0;
    display: block;
  }

  .subhead {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 14px;
    padding: 22px 2px 8px;
  }
  .subhead__dot {
    width: 9px;
    height: 9px;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .subhead__label {
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    flex-shrink: 0;
  }
  .subhead__rule {
    flex: 1;
    height: 1px;
    background: rgba(233, 238, 242, 0.1);
  }

  .row {
    flex-shrink: 0;
    width: 100%;
    container-type: inline-size;
    container-name: srow;
    border-radius: 15px;
    padding: 14px 20px;
    display: block;
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(233, 238, 242, 0.1);
  }
  .row:active {
    background: rgba(233, 238, 242, 0.12);
  }
  .row--danger {
    border-color: rgba(224, 167, 88, 0.3);
  }
  .row__body {
    display: flex;
    align-items: center;
    gap: 18px;
    min-width: 0;
    min-height: 50px;
  }
  .row__text {
    flex: 1;
    min-width: 0;
    display: block;
  }
  .row__label {
    display: flex;
    align-items: center;
    gap: 9px;
  }
  .row__name {
    font-size: 18px;
    font-weight: 600;
  }
  .row--danger .row__name {
    color: var(--accent-warn);
  }
  .row__note {
    display: block;
    font-size: 14px;
    line-height: 1.36;
    color: rgba(233, 238, 242, 0.55);
    margin-top: 5px;
    text-wrap: pretty;
  }
  .row__value {
    font-family: var(--font-mono);
    font-size: 15px;
    line-height: 1.35;
    flex-shrink: 0;
    max-width: 100%;
    text-align: right;
    word-break: break-all;
    color: rgba(233, 238, 242, 0.72);
  }
  .row__value.is-pending {
    color: var(--accent-warn);
  }
  /* Below 520px the value drops under the label instead of squeezing it. */
  @container srow (max-width: 520px) {
    .row__body {
      flex-wrap: wrap;
    }
    .row__value {
      order: 9;
      width: 100%;
      text-align: left;
      padding-top: 8px;
    }
  }

  .toggle {
    width: 60px;
    height: 34px;
    border-radius: 17px;
    flex-shrink: 0;
    position: relative;
    transition: background 140ms ease;
    background: rgba(233, 238, 242, 0.08);
    border: 1px solid rgba(233, 238, 242, 0.16);
  }
  .toggle span {
    position: absolute;
    top: 3px;
    left: 3px;
    width: 26px;
    height: 26px;
    border-radius: 50%;
    transition: left 140ms ease;
    background: rgba(233, 238, 242, 0.6);
  }
  .toggle.is-on {
    background: rgba(126, 214, 188, 0.32);
    border-color: rgba(126, 214, 188, 0.5);
  }
  .toggle.is-on span {
    left: 29px;
    background: var(--accent-lms);
  }

  .scrim {
    position: absolute;
    inset: 0;
    background: rgba(8, 12, 16, 0.62);
    backdrop-filter: blur(3px);
    transition: opacity 180ms ease;
    opacity: 0;
    pointer-events: none;
  }
  .scrim.is-open {
    opacity: 1;
    pointer-events: auto;
  }

  .sheet {
    position: absolute;
    left: 50%;
    top: 50%;
    transform: translate(-50%, -50%);
    width: calc(100% - 44px);
    max-width: 560px;
    max-height: 82%;
    background: var(--bg-panel);
    border: 1px solid rgba(233, 238, 242, 0.14);
    border-radius: 22px;
    box-shadow: 0 30px 70px rgba(0, 0, 0, 0.5);
    padding: 26px;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }
  .sheet__head {
    flex-shrink: 0;
    min-width: 0;
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
  .options {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .option {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 16px;
    min-height: 62px;
    padding: 12px 18px;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(233, 238, 242, 0.1);
  }
  .option:active {
    background: rgba(233, 238, 242, 0.14);
  }
  .option.is-selected {
    background: rgba(126, 214, 188, 0.14);
    border-color: rgba(126, 214, 188, 0.4);
  }
  .radio {
    width: 22px;
    height: 22px;
    border-radius: 50%;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 2px solid rgba(233, 238, 242, 0.3);
  }
  .option.is-selected .radio {
    border-color: var(--accent-lms);
  }
  .radio span {
    width: 11px;
    height: 11px;
    border-radius: 50%;
    background: var(--accent-lms);
    display: none;
  }
  .option.is-selected .radio span {
    display: block;
  }
  .option__label {
    flex: 1;
    min-width: 0;
    font-size: 17px;
    font-weight: 600;
    color: rgba(233, 238, 242, 0.82);
    text-wrap: pretty;
  }
  .option.is-selected .option__label {
    color: var(--ink);
  }
  .sheet__value {
    flex-shrink: 0;
    border-radius: 14px;
    background: rgba(8, 12, 16, 0.5);
    border: 1px solid rgba(233, 238, 242, 0.12);
    padding: 16px 18px;
    font-family: var(--font-mono);
    font-size: 15px;
    line-height: 1.5;
    color: rgba(233, 238, 242, 0.9);
    word-break: break-all;
  }
  /* Not in the design yet: number and text editing (design/settings.md
     describes them, Settings.dc.html does not draw them). */
  .editor {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 18px;
  }
  .range {
    flex: 1;
    min-width: 0;
    height: 44px;
    accent-color: var(--accent-lms);
  }
  .editor__value {
    font-family: var(--font-mono);
    font-size: 20px;
    font-weight: 600;
    min-width: 80px;
    text-align: right;
  }
  .field {
    flex-shrink: 0;
    width: 100%;
    min-height: 56px;
    border-radius: 14px;
    background: rgba(8, 12, 16, 0.5);
    border: 1px solid rgba(126, 214, 188, 0.4);
    padding: 14px 18px;
    font-family: var(--font-mono);
    font-size: 16px;
    color: var(--ink);
    outline: none;
  }
  .field:focus {
    border-color: var(--accent-lms);
  }

  .sheet__actions {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .btn {
    flex: 1;
    height: 58px;
    border-radius: 15px;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 17px;
    font-weight: 600;
  }
  .btn:active {
    background: rgba(233, 238, 242, 0.2);
  }
  .btn--confirm {
    font-weight: 700;
    background: rgba(126, 214, 188, 0.16);
    border-color: rgba(126, 214, 188, 0.4);
    color: var(--accent-lms);
  }
  .btn--danger {
    background: rgba(224, 167, 88, 0.2);
    border-color: rgba(224, 167, 88, 0.5);
    color: var(--accent-warn);
  }

  .toast {
    position: absolute;
    left: 50%;
    bottom: 26px;
    transform: translateX(-50%);
    max-width: calc(100% - 48px);
    padding: 14px 22px;
    border-radius: var(--r-pill);
    background: rgba(8, 12, 16, 0.9);
    border: 1px solid rgba(233, 238, 242, 0.16);
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    transition: opacity 200ms ease;
    opacity: 0;
    pointer-events: none;
  }
  .toast.is-shown {
    opacity: 1;
  }
</style>
