<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Settings, Phase 4 criterion 5 (ADR-0032, ADR-0035). Ported from
  design/source/Settings.dc.html. Rows come from the daemon's registry; the
  layout follows the component's own width, not the viewport, because it is
  standalone on a phone and will be embedded on the panel.
-->
<script>
  import { onMount } from 'svelte';
  import { pressing } from '../lib/press.svelte.js';
  import {
    settingsGroups,
    settingsDevice,
    settingsError,
    listAction,
    listItems,
    loadSettings,
    runSetting,
    writeSetting,
  } from '../lib/settings.js';

  // On the panel, Settings is a layer over the library and Back closes it
  // (source/Now Playing.dc.html passes the design's onBack). A phone has
  // nothing to go back to, so it passes none.
  //
  // `embedded` is the panel too: there the weave is drawn once for the whole
  // panel (PanelBackground.svelte). A phone gets its own, as before.
  let { onback = null, embedded = false } = $props();

  const WIDE_MIN = 720;

  //: Back says it was pressed, like the home screen's tiles (ADR-0066).
  const press = pressing();

  let width = $state(0);
  let cat = $state(null);
  let drilled = $state(null);
  let sheetKey = $state(null);
  // A full-screen chooser instead of a sheet, for a choice too large for
  // 560px (ADR-0044 §5). Holds the row's key, like `sheetKey`.
  let pickerKey = $state(null);
  //: Which row the pane is showing. **Not the value**: tapping a row in the
  //: picker previews it and nothing else, and the write happens on the
  //: button under the preview (design, 2026-09-22). On a wide screen the
  //: pane opens on the value in use; below 720px it opens on nothing,
  //: because there the pane covers the list.
  let pickerView = $state(null);
  // A list's labelled escape into typing (ADR-0044 §1's `manual`).
  let manual = $state(false);
  // A warned option that has been selected and not yet committed
  // (ADR-0044 §2). Null whenever nothing is being held back.
  let choicePending = $state(null);
  // A list's items, and whether they have been looked for yet (ADR-0044 §1).
  // A Wi-Fi scan and an LMS broadcast both take seconds, so `searching` is a
  // real state rather than a courtesy: showing "nothing found" before the
  // search has finished would be a different claim from the true one.
  let items = $state([]);
  let searching = $state(false);
  let listError = $state(null);
  // The network being joined, and how that is going.
  let joinItem = $state(null);
  let join = $state(null);
  let joinError = $state(null);
  // The first level of a grouped choice - the time zone's region.
  let region = $state(null);
  //: A write in flight. Even a fast one deserves saying so, and this one
  //: is not always fast: a rename writes four files and the refetch behind
  //: it took three seconds while the Wi-Fi read still sat on the request
  //: path. The sheet stayed open with nothing to show for it (George,
  //: 2026-09-21), which reads as a tap that did not land.
  let saving = $state(false);
  let toast = $state(null);
  let toastTimer;

  // Every group the API serves, filtered by nothing: `rowOf` and `valueOf`
  // read the whole inventory, including rows the screen never draws.
  const groups = $derived($settingsGroups);
  const loadError = $derived($settingsError);
  const wide = $derived((width || 1280) >= WIDE_MIN);
  // What the screen has: each group's drawable rows, and no group left
  // holding none of them. Every System row is `surfaced: false` after
  // George parked that category on 2026-09-20, so the design's six
  // categories are what remains of the registry's seven.
  const categories = $derived(
    groups
      .map((g) => ({ ...g, rows: drawable(g.rows) }))
      .filter((g) => g.rows.some((r) => r.type !== 'group'))
  );
  const current = $derived(
    categories.find((g) => g.id === (wide ? (cat ?? categories[0]?.id) : drilled)) ?? null
  );
  const rows = $derived(current?.rows ?? []);
  //: From the daemon, not derived here. The hostname is the system's own,
  //: so after a rename it still reads the old one until the restart - which
  //: is the truth, and the whole reason the sanitised host is shown beside
  //: the typed name (ADR-0022, ADR-0048 §5).
  const device = $derived($settingsDevice);
  const deviceName = $derived(device.name ?? valueOf('device_name') ?? 'gexis');
  const subtitle = $derived(
    [deviceName, device.hostname ? `${device.hostname}.local` : hostOf(deviceName), device.address]
      .filter(Boolean)
      .join('  \u00b7  ')
  );
  const sheet = $derived(sheetKey ? asSheet(rowOf(sheetKey)) : null);
  const picker = $derived(pickerKey ? rowOf(pickerKey) : null);

  // ADR-0044 §3 and §6: the API publishes every row and says of each whether
  // it belongs on the screen - `surfaced: false` permanently, `onlyWhen`
  // conditionally, and the second is transitive. The rule lives in the
  // registry, where it is tested once; here the panel only obeys it.
  //
  // A subhead whose whole section went with it goes too: a separator over
  // nothing announces a section that is not there.
  function drawable(all) {
    const kept = all.filter((r) => r.type === 'group' || r.visible !== false);
    return kept.filter((r, i) => r.type !== 'group' || (kept[i + 1] !== undefined && kept[i + 1].type !== 'group'));
  }

  // Typing an address is the same sheet a text row gets, on the same key -
  // not a second setting. A network's password is the same again: one sheet
  // pattern for every piece of text this screen takes.
  function asSheet(row) {
    if (!row) return row;
    if (joinItem) {
      return {
        ...row,
        type: 'text',
        label: joinItem.name,
        note: 'Enter the network password.',
        placeholder: 'Network password',
        secret: true,
        confirm: 'Join',
        wired: true,
      };
    }
    if (!manual) return row;
    return {
      ...row,
      type: 'text',
      note: 'Host and port, for a server discovery cannot reach.',
      placeholder: '192.168.1.10:9000',
      confirm: 'Save',
    };
  }

  // A grouped choice is two short lists rather than one long one: the zone
  // list is every zone this system knows, and `Europe/Berlin` splits at the
  // slash. Level one is the regions, level two the places in one of them.
  const grouped = $derived(sheet?.grouped ? (sheet.options ?? []) : []);
  const regions = $derived([...new Set(grouped.map((o) => o.split('/')[0]))].sort());
  const places = $derived(
    region === null ? [] : grouped.filter((o) => o.split('/')[0] === region)
  );
  const placeLabel = (option) => option.split('/').slice(1).join('/').replace(/_/g, ' ');

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
    saving = true;
    try {
      const result = await writeSetting(row.key, value);
      if (result.status === 409) flash(result.error || `${row.label} — not wired yet`);
      else if (!result.ok) flash(`${row.label}: ${result.error ?? `HTTP ${result.status}`}`);
      return result.ok;
    } finally {
      saving = false;
    }
  }

  function pending(row) {
    return (row.marks ?? '').includes('?');
  }

  const MINUS = '−';
  const BULLETS = '••••••••••';

  // One formatter for the row and the sheet, so a threshold does not read
  // "1.00 s" on one and "1 s" on the other: decimals follow the step, and a
  // word unit is spaced where % is not.
  function numeral(value, step) {
    const s = step ?? 1;
    if (s >= 1) return String(Math.round(value));
    // Snapping to the step in floating point leaves 0.30000000000000004
    // where 0.3 was meant; two places is past every step the registry has.
    return String(Number((Math.round(value / s) * s).toFixed(2)));
  }
  function withUnit(text, unit) {
    if (!unit) return text;
    return unit === '%' ? `${text}${unit}` : `${text} ${unit}`;
  }
  function shown(row) {
    const v = row.value;
    if (row.type === 'toggle') return '';
    // "Not set" is derived from an empty value, never stored as one, so it
    // can never be pre-filled into the field and saved as the real thing. A
    // secret that is set reports only that, never the value (ADR-0044).
    if (row.type === 'text') return !v ? 'Not set' : row.secret ? BULLETS : String(v);
    // ADR-0044 §7: a `multi` reads out what it holds, not how much. "4
    // topics" hides the thing the row exists to show; two names and a count
    // fits the row and still says which kind of pictures to expect.
    if (row.type === 'multi') {
      const held = Array.isArray(v) ? v : [];
      if (!held.length) return 'None';
      const shownNames = held.slice(0, 2).join(', ');
      return held.length > 2 ? `${shownNames} +${held.length - 2}` : shownNames;
    }
    if (row.type === 'list') {
      // A server list reads out which one is in use; a device list counts
      // what it holds. The design takes the count in both cases, which loses
      // the connected network's name on the Wi-Fi row - recorded in
      // docs/findings/042 §7 as one more place its prose and its literal
      // disagree.
      if (v) return String(v);
      // The items are on the row because the daemon seeds a list that does
      // not have to go looking (ADR-0044 §1, amended). A row counting only
      // what the *sheet* fetches reads "None" until someone opens it -
      // which is what it did with a phone paired (George, on the panel,
      // 2026-09-21).
      const n = (row.items ?? []).length;
      return n ? `${n} paired` : 'None';
    }
    if (v === null || v === undefined) return row.type === 'action' ? '' : '—';
    if (row.type === 'number') {
      return withUnit(numeral(Number(v), row.step).replace('-', MINUS), row.unit);
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
    // 84 visual things cannot be chosen from a 560px list, so a `picker` row
    // opens full screen instead of a sheet (ADR-0044 §5).
    else if (row.picker) {
      pickerKey = row.key;
      pickerView = null;
    }
    else openSheet(row);
  }

  async function chooseRegion(name) {
    region = name;
  }

  async function choose(option) {
    const row = sheet;
    if (String(row.value) === option) {
      // Back to what is stored. With something held back that is a change of
      // mind, not a choice, so the sheet stays open and lets go of it.
      if (choicePending !== null) {
        choicePending = null;
        return;
      }
      sheetKey = null;
      return;
    }
    // ADR-0044 §2: a warned option is selected first and committed second.
    // The warning is the whole point of the mechanic and "turn your
    // amplifier down before confirming" cannot be said after the write.
    if (row.warn?.[option]) {
      choicePending = option;
      return;
    }
    sheetKey = null;
    if (await write(row, option)) flash(`${row.label}: ${option}`);
  }

  //: ADR-0044 §7. Each tap is a write, because nothing on this screen has
  //: an unsaved state and a sheet that collected changes would be the first.
  //: **The last one cannot be turned off**: the daemon refuses an empty set
  //: and the sheet says so rather than sending a write it knows will fail.
  async function toggleOne(option) {
    const row = sheet;
    const held = Array.isArray(row.value) ? row.value : [];
    const on = held.includes(option);
    if (on && held.length === 1) {
      flash('At least one has to stay selected');
      return;
    }
    // Sent in the registry's order so the readout is stable; the daemon
    // sorts it the same way and the two agreeing is worth the sort here.
    const wanted = (row.options ?? []).filter((o) =>
      o === option ? !on : held.includes(o)
    );
    await write(row, wanted);
  }

  let draft = $state(null);

  function openSheet(row) {
    sheetKey = row.key;
    manual = false;
    choicePending = null;
    joinItem = null;
    join = null;
    joinError = null;
    listError = null;
    // A grouped choice opens on the region the current value is in, so the
    // zone in use is one tap away rather than two.
    region = row.grouped ? String(row.value ?? '').split('/')[0] || null : null;
    if (region !== null && !String(row.value ?? '').includes('/')) region = null;
    draft = row.type === 'text' ? (row.value ?? '') : row.type === 'number' ? (row.value ?? row.min) : null;
    // A seeded list is drawn from the row itself, so the sheet opens with
    // its devices on it rather than with a spinner for the 25 ms the read
    // takes (ADR-0044 §1, amended 2026-09-21).
    items = row.items ?? [];
    if (row.type === 'list') openList(row.key);
  }

  //: Fetched per opening, never cached: a scan is a picture of the room now.
  //: The key is captured so a slow answer cannot land in a sheet that has
  //: since been closed or replaced.
  //:
  //: **Only a list that has to go looking says it is looking** (ADR-0044 §1,
  //: amended). A seeded one is already drawn from the row and this refreshes
  //: behind it; a searching state there is three frames of spinner over a
  //: list that is right in front of you.
  async function openList(key) {
    searching = !!rowOf(key)?.discover;
    listError = null;
    const answer = await listItems(key);
    if (sheetKey !== key) return;
    items = answer.items;
    listError = answer.error;
    searching = false;
  }

  async function command(body, done) {
    const key = sheetKey;
    const answer = await listAction(key, body);
    if (sheetKey !== key) return answer;
    done(answer);
    return answer;
  }

  async function doJoin(name, password) {
    join = 'connecting';
    joinError = null;
    await command({ name, action: 'join', password: password ?? null }, (answer) => {
      if (!answer.ok) {
        join = 'error';
        joinError = answer.error;
        return;
      }
      join = 'ok';
      setTimeout(() => {
        if (join !== 'ok') return;
        closeSheet();
        flash(`Joined ${name}`);
      }, 1300);
    });
  }

  async function doForget(item) {
    const key = sheetKey;
    await command({ name: item.name, action: 'forget' }, (answer) => {
      flash(answer.ok ? `${item.name} forgotten` : (answer.error ?? 'Could not forget it'));
      if (answer.ok) openList(key);
    });
  }

  function enterManual() {
    manual = true;
    draft = String(rowOf(sheetKey)?.value ?? '');
  }

  async function chooseItem(item) {
    const row = rowOf(sheetKey);
    if (!row) return;
    // Choosing a server is a write; joining a network is a command. The row
    // that stores a value and the row that performs one are the same type,
    // and `kind` is what tells them apart (ADR-0044 §1).
    if (row.kind === 'server') {
      closeSheet();
      // Tapping the server already in use says "that one", so the sheet
      // closes and nothing is written.
      if (String(row.value ?? '') === item.name) return;
      // The daemon reads this at the next start: moving a running player to
      // another server means dropping its subscription, re-resolving the
      // player and re-arbitrating. Said plainly rather than left to be
      // discovered.
      if (await write(row, item.name)) flash(`${row.label} set — restart to use it`);
      return;
    }
    if (item.state === 'connected') return;
    if (item.state === 'locked') {
      joinItem = item;
      draft = '';
      return;
    }
    doJoin(item.name, null);
  }

  // '06G5_McIntosh' reads as 06 / McIntosh: the ordinal is how the corpus is
  // organised and the only way to scan a list that long. The stored value
  // stays the whole section name (ADR-0044 §4).
  //: What a `list` says while it is looking, per `kind` (ADR-0044 §1).
  //: A table rather than a ternary because a two-way branch has to send
  //: some kind somewhere it does not belong: `device` fell through to
  //: Wi-Fi's side of `kind === 'server'`, so the Bluetooth sheet said it
  //: was looking for networks and sweeping every channel. Only `discover`
  //: rows reach this now, and it is still theirs to get right.
  const SCAN = {
    server: { title: 'Searching the network', note: 'Servers answer within a few seconds.' },
    network: { title: 'Looking for networks', note: 'The adapter sweeps every channel.' },
    device: { title: 'Looking for devices', note: 'Paired devices answer straight away.' },
  };

  const ORDINAL = /^(\d+)G5_(.*)$/;
  function parts(name) {
    const m = ORDINAL.exec(String(name));
    return m ? { ord: m[1], label: m[2] } : { ord: '', label: String(name) };
  }

  //: The one write the picker makes, from the button under the preview.
  async function pick(name) {
    const row = picker;
    if (!name || String(row.value) === name) return;
    pickerKey = null;
    pickerView = null;
    if (await write(row, name)) flash(`${row.label}: ${parts(name).label}`);
  }

  async function saveNumber() {
    const row = sheet;
    if (Number(draft) === row.value) return;
    if (await write(row, Number(draft))) flash(`${row.label}: ${shown({ ...row, value: Number(draft) })}`);
  }

  async function confirmSheet() {
    const row = sheet;
    // A failed attempt returns to the field with the password still in it.
    if (join === 'error') {
      join = null;
      joinError = null;
      return;
    }
    if (joinItem) {
      doJoin(joinItem.name, draft);
      return;
    }
    // The escape out of a discovery list: type the address. It changes what
    // the sheet is, so it happens before anything is written.
    if (row.type === 'list' && row.manual) {
      enterManual();
      return;
    }
    // A warned option waited for this tap, and it is a write like any other.
    if (choicePending !== null) {
      const option = choicePending;
      choicePending = null;
      sheetKey = null;
      if (await write(row, option)) flash(`${row.label}: ${option}`);
      return;
    }
    if (!row.wired) {
      sheetKey = null;
      flash(`${row.label} — not wired yet`);
      return;
    }
    if (row.type === 'action') {
      sheetKey = null;
      const result = await runSetting(row.key);
      if (!result.ok) flash(`${row.label}: ${result.error ?? `HTTP ${result.status}`}`);
      return;
    }
    if (row.type === 'text') {
      if (await write(row, draft)) {
        sheetKey = null;
        // A row whose effect is deferred says so. "Saved" on its own reads
        // as "done", and the device is still advertising the old name
        // (ADR-0048 §2).
        flash(row.restart ? `${row.label} saved — restart to use it` : `${row.label} saved`);
      }
    }
  }

  function closeSheet() {
    // Inside a level, the same button steps back before it closes.
    if (joinItem && join !== 'connecting') {
      joinItem = null;
      join = null;
      joinError = null;
      draft = null;
      return;
    }
    if (region !== null && sheet?.grouped) {
      region = null;
      return;
    }
    sheetKey = null;
    choicePending = null;
    manual = false;
    joinItem = null;
    join = null;
    region = null;
  }

  function back() {
    if (!wide && drilled) {
      drilled = null;
      return;
    }
    onback?.();
  }
</script>

<div class="settings" class:is-embedded={embedded} bind:clientWidth={width}>
  {#if !embedded}
    <div class="weave"></div>
  {/if}
  <div class="veil"></div>

  <div class="frame">
    <div class="head" class:head--wide={wide}>
      {#if (wide && onback) || (!wide && drilled)}
        <button
          class="back"
          class:is-pressed={press.is('back')}
          type="button"
          aria-label="Back"
          onpointerdown={() => press.down('back')}
          onpointerup={press.up}
          onpointercancel={press.up}
          onclick={() => press.act(back)}
        ><span></span></button>
      {/if}
      <div class="head__text">
        <div class="title" class:title--wide={wide}>{!wide && current ? current.label : 'Settings'}</div>
        <!-- Shown at both widths: the panel is where someone types the
             name, so it is where the resolved host has to sit beside it. -->
        <div class="subtitle">{subtitle}</div>
      </div>
    </div>

    {#if loadError}
      <div class="error">Settings could not be loaded: {loadError}</div>
    {:else}
      <div class="body">
        {#if wide}
          <div class="rail" data-noscrollbar>
            {#each categories as g (g.id)}
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
            {#each categories as g (g.id)}
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
                <!-- A readonly row takes no tap and draws no chevron: there
                     is nothing to change, and a chevron promises a sheet that
                     only repeats the value already on the row. `disabled`
                     rather than a different element, so the row keeps its
                     layout and its 44px height. -->
                <button
                  class="row"
                  class:row--danger={r.danger}
                  class:row--readonly={r.type === 'readonly'}
                  type="button"
                  disabled={r.type === 'readonly'}
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
                    {:else if r.type !== 'readonly'}
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

  <!-- ADR-0044 §5: a chooser too large for a 560px sheet takes the screen.
       **A list with a preview beside it** (design, 2026-09-22) - the
       four-across grid it replaces made 84 tiles too small to judge and too
       large to scan, and drew every preview at once. Here one is fetched,
       when a row is tapped. -->
  {#if picker}
    {@const options = picker.options ?? []}
    {@const inUse = picker.value == null ? null : String(picker.value)}
    {@const viewing = pickerView ?? (wide ? inUse : null)}
    <div class="picker">
      <!-- Its own ground, embedded or not: it covers the rows, so the
           panel's weave behind the app cannot reach it. -->
      <div class="weave"></div>
      <div class="veil"></div>
      <div class="picker__head" class:head--wide={wide}>
        <button
          class="back"
          class:is-pressed={press.is('picker-back')}
          type="button"
          aria-label="Back"
          onpointerdown={() => press.down('picker-back')}
          onpointerup={press.up}
          onpointercancel={press.up}
          onclick={() => press.act(() => (pickerKey = null))}
        ><span></span></button>
        <div class="head__text">
          <div class="title" class:title--wide={wide}>{picker.label}</div>
          <div class="subtitle">{options.length} skins</div>
        </div>
      </div>

      <div class="picker__body">
        <div class="skins" class:skins--wide={wide} data-noscrollbar>
          {#each options as option (option)}
            {@const p = parts(option)}
            <button
              class="skin"
              class:is-viewing={option === viewing}
              class:is-inuse={option === inUse}
              type="button"
              aria-current={option === inUse ? 'true' : undefined}
              onclick={() => (pickerView = option)}
            >
              <span class="skin__ord">{p.ord}</span>
              <span class="skin__label">{p.label}</span>
              {#if option === inUse}<span class="skin__check"><span></span></span>{/if}
            </button>
          {/each}
          {#if !options.length}
            <div class="skins__empty">No skins are installed.</div>
          {/if}
        </div>

        {#if viewing}
          {@const p = parts(viewing)}
          {@const isCurrent = viewing === inUse}
          <div class="pane" class:pane--over={!wide}>
            {#if !wide}
              <div class="pane__back">
                <button
                  class="back back--small"
                  class:is-pressed={press.is('view-back')}
                  type="button"
                  aria-label="Back to list"
                  onpointerdown={() => press.down('view-back')}
                  onpointerup={press.up}
                  onpointercancel={press.up}
                  onclick={() => press.act(() => (pickerView = null))}
                ><span></span></button>
                <span class="pane__backlabel">Back to list</span>
              </div>
            {/if}
            <!-- ADR-0050: the preview is the skin's own `screen.bgr`, served
                 from where the image installed it. Nothing is rendered and
                 nothing is cached, so this is one file per tap. -->
            <div class="pane__art">
              <img src={`/skins/${encodeURIComponent(viewing)}/preview`} alt="" />
            </div>
            <div class="pane__text">
              <div class="pane__name">{p.label}</div>
              <div class="pane__meta">{viewing} &nbsp;·&nbsp; {isCurrent ? 'IN USE' : 'NOT IN USE'}</div>
            </div>
            <button
              class="pane__use"
              class:is-inert={isCurrent}
              type="button"
              disabled={isCurrent}
              onclick={() => pick(viewing)}
            >{isCurrent ? 'In use' : 'Use this skin'}</button>
          </div>
        {/if}
      </div>
    </div>
  {/if}

  <div class="scrim" class:is-open={sheet} role="presentation" onclick={closeSheet}></div>

  {#if sheet}
    <div class="sheet" role="dialog" aria-label={sheet.label}>
      <div class="sheet__head">
        <div class="sheet__title">{sheet.grouped && region !== null ? region : sheet.label}</div>
        {#if sheet.note && !joinItem}<div class="sheet__note">{sheet.note}</div>{/if}
        {#if joinItem && sheet.note}<div class="sheet__note">{sheet.note}</div>{/if}
      </div>

      <!-- ADR-0044 §2, both forms. A **string** warns about the row and is
           shown the whole time the sheet is open, because what it describes
           happens whatever is typed (`device_name`); an **object** warns
           about one option and waits until that option is picked. -->
      {#if typeof sheet.warn === 'string'}
        <div class="warn">
          <span class="warn__mark">!</span>
          <span class="warn__text">{sheet.warn}</span>
        </div>
      {:else if choicePending !== null && sheet.warn?.[choicePending]}
        <div class="warn">
          <span class="warn__mark">!</span>
          <span class="warn__text">{sheet.warn[choicePending]}</span>
        </div>
      {/if}

      <!-- A grouped choice, level one: the regions. ADR-0044 §4 - two short
           lists rather than one of several hundred. -->
      {#if sheet.grouped && region === null}
        <div class="options" data-noscrollbar>
          {#each regions as name (name)}
            {@const selected = String(sheet.value ?? '').split('/')[0] === name}
            <button class="option" class:is-selected={selected} type="button" onclick={() => chooseRegion(name)}>
              <span class="radio"><span></span></span>
              <span class="option__label">{name.replace(/_/g, ' ')}</span>
              <span class="chev"></span>
            </button>
          {/each}
        </div>
      {:else if sheet.grouped}
        <div class="options" data-noscrollbar>
          {#each places as option (option)}
            {@const selected = String(sheet.value) === option}
            <button class="option" class:is-selected={selected} type="button" onclick={() => choose(option)}>
              <span class="radio"><span></span></span>
              <span class="option__label">{placeLabel(option)}</span>
            </button>
          {/each}
        </div>
      {:else if sheet.type === 'multi'}
        <!-- The choice sheet with the radio replaced: tapping toggles, and
             nothing closes the sheet because there is no single answer that
             ends it (ADR-0044 §7). -->
        <div class="options" data-noscrollbar>
          {#each sheet.options ?? [] as option (option)}
            {@const selected = (sheet.value ?? []).includes(option)}
            <button
              class="option"
              class:is-selected={selected}
              type="button"
              disabled={saving}
              onclick={() => toggleOne(option)}
            >
              <span class="radio radio--box"><span></span></span>
              <span class="option__label">{option}</span>
            </button>
          {/each}
        </div>
      {:else if sheet.type === 'choice'}
        <div class="options" data-noscrollbar>
          {#each sheet.options ?? [] as option (option)}
            {@const selected = choicePending !== null ? choicePending === option : String(sheet.value) === option}
            {@const p = sheet.optionsFrom ? parts(option) : { ord: '', label: option }}
            {@const why = sheet.unavailable?.[option]}
            <!-- ADR-0044's `unavailable`: greyed, not hidden. George,
                 2026-09-23: "settings is different than the now playing
                 screen when it comes to capabilities" - a screen for
                 changing things should say what cannot be changed and
                 why, where a screen for listening should carry no dead
                 controls. -->
            <button
              class="option"
              class:is-selected={selected}
              class:is-unavailable={!!why}
              type="button"
              onclick={() => (why ? flash(why) : choose(option))}
            >
              <span class="radio"><span></span></span>
              {#if p.ord}<span class="option__ord">{p.ord}</span>{/if}
              <span class="option__label">{p.label}</span>
              {#if why}<span class="option__why">{why}</span>{/if}
            </button>
          {/each}
        </div>
      {/if}

      <!-- A list is navigation, not a value (ADR-0044 §1): items with a
           per-item action, and a plain sentence when there are none. All
           three sources are built now - a Wi-Fi scan, LMS discovery and
           BlueZ's paired devices - and only the two that go looking open
           on the searching state below. -->
      {#if sheet.type === 'list' && searching}
        <!-- "Nothing found" is only true once the search has finished. -->
        <div class="scan">
          <div class="scan__spin"></div>
          <div>
            <div class="scan__title">{SCAN[sheet.kind]?.title ?? 'Looking'}</div>
            <div class="scan__note">{SCAN[sheet.kind]?.note ?? ''}</div>
          </div>
        </div>
      {:else if sheet.type === 'list'}
        {#if items.length}
          <div class="items" data-noscrollbar>
            {#each items as item (item.name)}
              {@const joined = item.state === 'connected' || item.state === 'current'}
              <!-- Only the network in use takes no tap: there is nothing to
                   join. The server in use still does - tapping the one you
                   are on is how the sheet is dismissed, and refusing it
                   leaves the sheet looking stuck (George, on the panel,
                   2026-09-20). -->
              {@const inert = item.state === 'connected'}
              <button
                class="item"
                class:is-joined={joined}
                class:item--static={inert}
                type="button"
                disabled={inert}
                onclick={() => chooseItem(item)}
              >
                {#if item.bars}
                  <span class="bars" class:is-joined={joined}>
                    {#each [1, 2, 3, 4] as n (n)}
                      <span class="bars__b" class:is-on={item.bars >= n} style:--i={n}></span>
                    {/each}
                  </span>
                {/if}
                <span class="item__text">
                  <span class="item__title">
                    <span class="item__name">{item.name}</span>
                    {#if item.state === 'locked'}<span class="lock"><span></span><span></span></span>{/if}
                  </span>
                  {#if item.meta}<span class="item__meta" class:is-joined={joined}>{item.meta}</span>{/if}
                </span>
                {#if item.state === 'saved'}
                  <!-- **Saved only, never the network in use.** Forgetting
                       the one the device is reachable over drops the daemon
                       with it, from a screen that may itself be the phone on
                       that network. The row for the connected network is
                       also `disabled`, and a browser suppresses clicks
                       inside a disabled button - so a Forget drawn there
                       would look live and do nothing.

                       A `span`, not a `button`: a button inside a button is
                       invalid and the inner one never gets the tap. -->
                  <span
                    class="forget"
                    role="button"
                    tabindex="0"
                    onclick={(e) => { e.stopPropagation(); doForget(item); }}
                    onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); doForget(item); } }}
                  >Forget</span>
                {:else if item.state === 'locked'}
                  <span class="item__need">Password needed</span>
                {/if}
              </button>
            {/each}
            {#if sheet.hint}<div class="items__hint">{sheet.hint}</div>{/if}
          </div>
        {:else}
          <div class="empty">
            <span class="empty__ring"></span>
            <span class="empty__text">{listError ?? sheet.empty ?? 'Nothing here yet.'}</span>
          </div>
        {/if}
      {/if}

      <!-- Joining takes real seconds and can fail, so the sheet reports the
           attempt rather than closing and leaving the outcome unsaid. -->
      {#if join}
        <div class="joining">
          <div class="joining__mark" data-state={join}>
            {#if join === 'connecting'}<span class="joining__spin"></span>{/if}
            {#if join === 'ok'}<span class="joining__tick"></span>{/if}
            {#if join === 'error'}<span class="joining__bang"></span>{/if}
          </div>
          <div class="joining__text">
            <div class="joining__title" data-state={join}>
              {join === 'connecting' ? `Joining ${joinItem?.name ?? ''}` : join === 'ok' ? 'Connected' : 'Could not join'}
            </div>
            <div class="joining__note">
              {join === 'connecting'
                ? 'Checking the password and getting an address.'
                : join === 'ok'
                  ? 'This network is saved and will reconnect on its own.'
                  : (joinError ?? 'The password was not accepted.')}
            </div>
          </div>
        </div>
      {/if}

      {#if join === 'connecting' || join === 'ok'}
        <!-- Nothing to type into while the attempt is running. -->
      {:else if sheet.wired && sheet.type === 'number'}
        {@const pct = ((Number(draft) - sheet.min) / (sheet.max - sheet.min)) * 100}
        <div class="editor">
          <div class="editor__read">
            <span class="editor__n">{numeral(Number(draft), sheet.step).replace('-', MINUS)}</span>
            {#if sheet.unit}<span class="editor__unit">{sheet.unit}</span>{/if}
          </div>
          <input
            class="range"
            type="range"
            min={sheet.min}
            max={sheet.max}
            step={sheet.step ?? 1}
            style:--pct="{Math.min(100, Math.max(0, pct))}%"
            bind:value={draft}
            onchange={saveNumber}
            aria-label={sheet.label}
          />
          <div class="editor__ends">
            <span>{withUnit(String(sheet.min).replace('-', MINUS), sheet.unit)}</span>
            <span>{withUnit(String(sheet.max).replace('-', MINUS), sheet.unit)}</span>
          </div>
        </div>
      {:else if sheet.wired && sheet.type === 'text'}
        <!-- The panel and the phone take the same input; a panel without a
             keyboard attached reads every setting and changes every one that
             is not text (ADR-0044). -->
        <input
          class="field"
          type={sheet.secret ? 'password' : 'text'}
          placeholder={sheet.placeholder ?? ''}
          bind:value={draft}
          autocomplete="off"
          autocapitalize="off"
          spellcheck="false"
          aria-label={sheet.label}
        />
      {:else if sheet.type === 'readonly' || sheet.type === 'text' || sheet.type === 'number'}
        <div class="sheet__value">{shown(sheet)}</div>
      {/if}

      {#if join !== 'connecting' && join !== 'ok'}
      <div class="sheet__actions">
        <button class="btn" type="button" disabled={saving} onclick={closeSheet}>
          {#if join === 'error'}
            Give up
          {:else if joinItem || (sheet.grouped && region !== null)}
            Back
          {:else if choicePending === null && (sheet.type === 'choice' || sheet.type === 'multi' || sheet.grouped || (sheet.wired && sheet.type === 'number'))}
            Close
          {:else}
            Cancel
          {/if}
        </button>
        {#if join === 'error' || joinItem || choicePending !== null || sheet.type === 'action' || sheet.type === 'text' || (sheet.type === 'number' && !sheet.wired) || (sheet.type === 'list' && sheet.manual && !searching)}
          <button
            class="btn btn--confirm"
            class:btn--danger={sheet.danger || choicePending !== null}
            type="button"
            disabled={saving}
            onclick={confirmSheet}
          >
            {#if saving}
              <span class="btn__spin"></span>Saving
            {:else if join === 'error'}
              Try again
            {:else if joinItem}
              Join
            {:else if choicePending !== null}
              {sheet.confirm ?? 'Confirm'}
            {:else if sheet.type === 'list'}
              {sheet.manual}
            {:else}
              {sheet.confirm ?? (sheet.type === 'action' ? 'Continue' : sheet.wired ? 'Save' : 'Edit')}
            {/if}
          </button>
        {/if}
      </div>
      {/if}
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
  .settings.is-embedded {
    background: none;
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
  /* Shrinks rather than filling grey - see now playing's buttons. */
  /* Held long enough to be painted (ADR-0066). */
  .back:active,
  .back.is-pressed {
    transform: scale(0.95);
    background: rgba(233, 238, 242, 0.16);
  }
  /* The ink is what wants centring, not the box - see `.i-back` in
     Library.svelte. 13px here rather than 14, so the offset is smaller. */
  .back span {
    width: 13px;
    height: 13px;
    border-left: 3px solid var(--ink);
    border-bottom: 3px solid var(--ink);
    transform: translateX(3.9px) rotate(45deg);
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
  /* Not dimmed: the value is the point of the row and stays fully legible.
     Only the affordance goes. */
  .row--readonly { opacity: 1; }
  .row--readonly:active { transform: none; }

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
    /* No `backdrop-filter`: ADR-0041. A live blur of the screen behind a
       sheet costs this panel two thirds of its frames, whatever its radius
       and however small the sheet (Finding 037). The dimming is free. */
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
  /* A checkbox is the radio with corners: same size, same border, same
     accent, so a sheet that takes several answers is recognisably the one
     that takes one. */
  .radio--box {
    border-radius: 7px;
  }
  .radio--box span {
    border-radius: 2px;
    width: 12px;
    height: 12px;
  }
  .option.is-unavailable {
    opacity: 0.42;
  }

  .option__why {
    margin-left: auto;
    padding-left: 14px;
    font-size: 17px;
    color: var(--ink-dim, #9fb0bd);
    text-align: right;
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
  /* The 2026-09-20 drop draws both, where the one before it only described
     them: a reading above the travel, not beside it. The track is a real
     range input rather than the design's pointer maths - same geometry,
     and it keeps the keyboard and the accessible name. */
  .editor {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 18px;
  }
  .editor__read {
    display: flex;
    align-items: baseline;
    gap: 10px;
  }
  .editor__n {
    font-family: var(--font-mono);
    font-size: 38px;
    font-weight: 700;
    letter-spacing: -0.01em;
    line-height: 1;
  }
  .editor__unit {
    font-family: var(--font-mono);
    font-size: 17px;
    color: rgba(233, 238, 242, 0.6);
  }
  .range {
    width: 100%;
    height: 56px;
    margin: 0;
    background: none;
    -webkit-appearance: none;
    appearance: none;
    touch-action: none;
  }
  .range::-webkit-slider-runnable-track {
    height: 14px;
    border-radius: 999px;
    background: linear-gradient(
      to right,
      var(--accent-lms) 0 var(--pct),
      rgba(233, 238, 242, 0.13) var(--pct) 100%
    );
  }
  .range::-webkit-slider-thumb {
    -webkit-appearance: none;
    appearance: none;
    width: 34px;
    height: 34px;
    margin-top: -10px;
    border-radius: 50%;
    background: var(--ink);
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.45);
  }
  .editor__ends {
    display: flex;
    justify-content: space-between;
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.1em;
    color: rgba(233, 238, 242, 0.6);
  }
  /* ADR-0044 §2 - a warning the choice holds back until the option is
     chosen, in the same amber the danger rows use. */
  .warn {
    flex-shrink: 0;
    display: flex;
    align-items: flex-start;
    gap: 14px;
    padding: 16px 18px;
    border-radius: 14px;
    background: rgba(224, 167, 88, 0.12);
    border: 1px solid rgba(224, 167, 88, 0.42);
  }
  .warn__mark {
    width: 26px;
    height: 26px;
    border-radius: 50%;
    background: var(--accent-warn);
    color: var(--bg-panel);
    font-weight: 700;
    font-size: 17px;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
  }
  .warn__text {
    flex: 1;
    min-width: 0;
    font-size: 15px;
    line-height: 1.45;
    text-wrap: pretty;
  }
  .option__ord {
    flex-shrink: 0;
    width: 34px;
    font-family: var(--font-mono);
    font-size: 14px;
    letter-spacing: 0.06em;
    color: rgba(233, 238, 242, 0.5);
  }

  /* ADR-0044 §1 - a list's items. */
  .items {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .item {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 16px;
    min-height: 66px;
    padding: 12px 18px;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.045);
    border: 1px solid rgba(233, 238, 242, 0.1);
  }
  .item:active {
    transform: scale(0.95);
  }
  .item.is-joined {
    background: rgba(126, 214, 188, 0.12);
    border-color: rgba(126, 214, 188, 0.34);
  }
  /* A list whose items have no command behind them yet reads and does not
     act, so it takes no tap and gives no press feedback either. */
  .item--static:active {
    transform: none;
  }
  .bars {
    width: 26px;
    height: 20px;
    display: flex;
    align-items: flex-end;
    gap: 3px;
    flex-shrink: 0;
  }
  .bars__b {
    width: 4px;
    height: calc(2px + var(--i) * 4px);
    border-radius: 1px;
    background: rgba(233, 238, 242, 0.2);
  }
  .bars__b.is-on {
    background: rgba(233, 238, 242, 0.82);
  }
  .bars.is-joined .bars__b.is-on {
    background: var(--accent-lms);
  }
  .item__text {
    flex: 1;
    min-width: 0;
  }
  .item__title {
    display: flex;
    align-items: center;
    gap: 9px;
  }
  .item__name {
    font-size: 17px;
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .lock {
    width: 13px;
    height: 15px;
    position: relative;
    flex-shrink: 0;
  }
  .lock span:first-child {
    position: absolute;
    left: 0;
    bottom: 0;
    width: 13px;
    height: 9px;
    border-radius: 2px;
    background: rgba(233, 238, 242, 0.6);
  }
  .lock span:last-child {
    position: absolute;
    left: 3px;
    top: 0;
    width: 7px;
    height: 8px;
    border: 2px solid rgba(233, 238, 242, 0.6);
    border-bottom: none;
    border-radius: 4px 4px 0 0;
  }
  .item__meta {
    display: block;
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.04em;
    margin-top: 4px;
    color: rgba(233, 238, 242, 0.6);
  }
  .item__meta.is-joined {
    color: var(--accent-lms);
  }
  .items__hint {
    flex-shrink: 0;
    font-family: var(--font-mono);
    font-size: 13px;
    line-height: 1.5;
    letter-spacing: 0.02em;
    color: rgba(233, 238, 242, 0.6);
    padding: 14px 4px 2px;
    text-wrap: pretty;
  }
  .forget {
    flex-shrink: 0;
    display: inline-flex;
    align-items: center;
    height: 44px;
    padding: 0 18px;
    border-radius: 12px;
    background: rgba(224, 167, 88, 0.14);
    border: 1px solid rgba(224, 167, 88, 0.4);
    font-family: var(--font-mono);
    font-size: 13px;
    font-weight: 600;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--accent-warn);
  }
  .forget:active {
    transform: scale(0.95);
  }
  .item__need {
    flex-shrink: 0;
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: rgba(233, 238, 242, 0.6);
    max-width: 150px;
    text-align: right;
    text-wrap: pretty;
  }

  /* The search, while it is running. */
  .scan {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 14px 4px;
  }
  .scan__spin,
  .joining__spin {
    width: 30px;
    height: 30px;
    border-radius: 50%;
    box-sizing: border-box;
    border: 3px solid rgba(233, 238, 242, 0.14);
    border-top-color: var(--accent-lms);
    animation: setSpin 900ms linear infinite;
    flex-shrink: 0;
  }
  @keyframes setSpin {
    to {
      transform: rotate(360deg);
    }
  }
  .scan__title {
    font-size: 17px;
    font-weight: 600;
  }
  .scan__note {
    font-size: 14px;
    color: rgba(233, 238, 242, 0.6);
    margin-top: 4px;
    text-wrap: pretty;
  }

  /* The attempt: running, joined, refused. */
  .joining {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 18px;
    padding: 12px 0 4px;
  }
  .joining__mark {
    width: 64px;
    height: 64px;
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 50%;
    flex-shrink: 0;
  }
  .joining__mark[data-state='ok'] {
    background: rgba(126, 214, 188, 0.16);
    border: 1px solid rgba(126, 214, 188, 0.45);
  }
  .joining__mark[data-state='error'] {
    background: rgba(224, 167, 88, 0.16);
    border: 1px solid rgba(224, 167, 88, 0.45);
  }
  .joining__spin {
    width: 64px;
    height: 64px;
  }
  .joining__tick {
    width: 22px;
    height: 12px;
    border-left: 3px solid var(--accent-lms);
    border-bottom: 3px solid var(--accent-lms);
    transform: rotate(-45deg);
    margin-top: -4px;
  }
  .joining__bang {
    width: 4px;
    height: 30px;
    border-radius: 2px;
    background: var(--accent-warn);
  }
  .joining__text {
    text-align: center;
  }
  .joining__title {
    font-size: 19px;
    font-weight: 700;
  }
  .joining__title[data-state='ok'] {
    color: var(--accent-lms);
  }
  .joining__title[data-state='error'] {
    color: var(--accent-warn);
  }
  .joining__note {
    font-size: 15px;
    line-height: 1.4;
    color: rgba(233, 238, 242, 0.6);
    margin-top: 7px;
    text-wrap: pretty;
  }

  .empty {
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    padding: 34px 20px;
  }
  .empty__ring {
    width: 58px;
    height: 58px;
    border-radius: 50%;
    border: 2px dashed rgba(233, 238, 242, 0.28);
  }
  .empty__text {
    font-size: 16px;
    line-height: 1.45;
    color: rgba(233, 238, 242, 0.62);
    text-align: center;
    text-wrap: pretty;
    max-width: 36ch;
  }

  /* ADR-0044 §5 - the full-screen picker. */
  .picker {
    position: absolute;
    inset: 0;
    z-index: 30;
    background: var(--bg-base);
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }
  .picker__head {
    position: relative;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 14px 18px;
    min-height: 78px;
    border-bottom: 1px solid rgba(233, 238, 242, 0.09);
  }
  .picker__head.head--wide {
    padding: 0 36px;
    min-height: 92px;
  }
  /* The list and the pane beside it (design, 2026-09-22). */
  .picker__body {
    position: relative;
    flex: 1;
    min-height: 0;
    display: flex;
  }
  .skins {
    flex-shrink: 0;
    width: 100%;
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: 10px 0 24px;
    box-sizing: border-box;
  }
  .skins--wide {
    width: 380px;
    border-right: 1px solid rgba(233, 238, 242, 0.09);
  }
  .skin {
    display: flex;
    align-items: center;
    gap: 14px;
    width: 100%;
    min-height: 62px;
    padding: 0 26px;
    box-sizing: border-box;
    background: none;
    border: 0;
    /* The rail is always there and usually transparent, so a tap does not
       move the row by three pixels. */
    border-left: 3px solid transparent;
    text-align: left;
    color: var(--ink);
  }
  .skin:active {
    background: rgba(233, 238, 242, 0.1);
  }
  /* Being previewed is the Display group's own accent; being in use is the
     affirm accent, which is what the check is too. One row can be both. */
  .skin.is-viewing {
    background: rgba(200, 162, 216, 0.14);
    border-left-color: var(--accent-display);
  }
  .skin.is-inuse .skin__label {
    color: var(--accent-lms);
  }
  .skin__ord {
    flex-shrink: 0;
    width: 32px;
    font-family: var(--font-mono);
    font-size: var(--t-label);
    letter-spacing: 0.08em;
    color: rgba(233, 238, 242, 0.45);
  }
  .skin__label {
    flex: 1;
    min-width: 0;
    font-size: var(--t-body-sm);
    font-weight: 600;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .skin__check {
    flex-shrink: 0;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background: var(--accent-lms);
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .skin__check span {
    width: 7px;
    height: 4px;
    border-left: 2.5px solid var(--ink-on-accent);
    border-bottom: 2.5px solid var(--ink-on-accent);
    transform: rotate(-45deg);
    margin-top: -2px;
  }
  .skins__empty {
    padding: 18px 26px;
    font-size: var(--t-body-sm);
    color: var(--ink-quiet);
  }

  .pane {
    flex: 1;
    min-width: 0;
    min-height: 0;
    display: flex;
    flex-direction: column;
    gap: 20px;
    padding: 26px 28px 28px;
    box-sizing: border-box;
  }
  /* Below 720px there is no room for both, so the pane covers the list and
     carries its own way back to it. */
  .pane--over {
    position: absolute;
    inset: 0;
    background: var(--bg-base);
  }
  .pane__back {
    flex-shrink: 0;
    display: flex;
    align-items: center;
    gap: 14px;
  }
  .back--small {
    width: 46px;
    height: 46px;
  }
  .back--small span {
    width: 11px;
    height: 11px;
    border-left-width: 2.5px;
    border-bottom-width: 2.5px;
    margin-left: 8px;
  }
  .pane__backlabel {
    font-family: var(--font-mono);
    font-size: var(--t-label);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  /* **The picture is the frame, and it is never cropped.** The box was a
     16:10 rectangle at the full width of the pane with the picture `cover`ed
     into it, which is right on the panel and wrong everywhere else: on a
     laptop the pane is wide and short, `max-height` won the argument with
     `aspect-ratio`, and the box ended up wider than the skin - so the skin
     was cut and only its middle was shown (George, 2026-09-22). Now the box
     only says how much room there is; the picture takes what it needs of it
     and keeps its own shape, whatever the viewport. */
  .pane__art {
    flex: 0 1 auto;
    min-height: 0;
    max-height: 58%;
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
  }
  .pane__art img {
    max-width: 100%;
    max-height: 100%;
    width: auto;
    height: auto;
    object-fit: contain;
    border-radius: var(--r-lg);
    background: var(--bg-well);
    border: 1px solid rgba(233, 238, 242, 0.14);
    box-sizing: border-box;
  }
  .pane__text {
    flex: 1;
    min-height: 0;
  }
  .pane__name {
    font-size: var(--t-h3);
    font-weight: 700;
    letter-spacing: -0.01em;
    text-wrap: pretty;
  }
  .pane__meta {
    font-family: var(--font-mono);
    font-size: var(--t-label);
    letter-spacing: 0.06em;
    color: rgba(233, 238, 242, 0.55);
    margin-top: 8px;
    word-break: break-word;
  }
  .pane__use {
    flex-shrink: 0;
    min-height: 60px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    font-weight: 600;
    background: var(--accent-lms);
    color: var(--ink-on-accent);
    border: 1px solid var(--accent-lms);
  }
  .pane__use:active {
    opacity: 0.75;
  }
  /* The skin in use has no action left: an outline that says so rather than
     a button that would write what is already there. */
  .pane__use.is-inert {
    background: transparent;
    color: rgba(233, 238, 242, 0.5);
    border-color: rgba(233, 238, 242, 0.18);
  }

  .field {
    flex-shrink: 0;
    width: 100%;
    height: 62px;
    border-radius: 14px;
    background: rgba(8, 12, 16, 0.6);
    border: 1px solid rgba(126, 214, 188, 0.45);
    padding: 0 18px;
    font-family: var(--font-mono);
    font-size: 17px;
    letter-spacing: 0.02em;
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
  .btn:disabled {
    opacity: 0.7;
  }
  .btn__spin {
    width: 18px;
    height: 18px;
    margin-right: 10px;
    border-radius: 50%;
    box-sizing: border-box;
    border: 2px solid rgba(233, 238, 242, 0.2);
    border-top-color: currentColor;
    animation: setSpin 900ms linear infinite;
    flex-shrink: 0;
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
