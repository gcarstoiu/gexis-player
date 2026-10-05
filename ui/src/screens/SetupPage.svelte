<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  **First-time setup, on the phone** (design/source/Setup.dc.html,
  screens.md §13; ADR-0031 as amended; ADR-0104).

  The design's steps, with the changes the amendment made to them:
  - **Network** saves the choice and does not test it. With one radio the join
    can only happen after the setup network is down, which is after this page
    is gone. A wrong password brings setup back with the reason, and the page
    opens on this step again (amendment 5).
  - **Music** has no server discovery: over the setup network the player
    cannot see the home network (amendment 4). An optional address instead.
  - **Time** has no clock format: nothing in Settings stores one yet.
  - **Screen** (ADR-0109; Phase 13b) offers the model the screen and its
    touch controller suggest, or the list of every model gexis knows, or
    Headless (ADR-0077). Its answer is Settings' Attached screen.

  **The core keeps the answers.** Each Continue saves the step, so a page that
  drops (Finding 099 saw one) or a phone that comes back after a failed join
  resumes where it was. The password is never handed back.
-->
<script>
  import { onMount } from 'svelte';
  import mark from '../assets/gexis-mark.svg';

  let { setup } = $props();

  const STEPS = [
    ['wifi', 'Network', '#8fc4d8'],
    ['name', 'Name', '#e8a0b4'],
    ['tz', 'Time', '#c8a2d8'],
    ['out', 'Output', '#7ed6bc'],
    ['music', 'Music', '#9fb4e8'],
    ['display', 'Screen', '#8fd9a8'],
    ['visualiser', 'Visualiser', '#e8c27e'],
    ['review', 'Review', '#f2a48f']
  ];
  const last = STEPS.length;

  let step = $state(-1);
  let loaded = $state(false);
  let saving = $state(false);
  let problem = $state(null);

  // The answers, as the design names them.
  let ssid = $state(null);
  let hidden = $state(false);
  let manualSsid = $state('');
  let pw = $state('');
  let showPw = $state(false);
  let hasPassword = $state(false);
  let joinError = $state(null);
  //: Back after a failed join: only the network was wrong, so Continue on
  //: Network goes straight to Review (George, 2026-09-28).
  let retrying = $state(false);
  //: A step opened with Change from Review returns to Review on Continue
  //: (George, 2026-09-29: changing the name meant walking every step again).
  let fromReview = $state(false);
  let name = $state('gexis');
  let tz = $state(null);
  let tzMode = $state('auto');
  let tzRegion = $state(null);
  let clock24 = $state(true);
  let out = $state(null);
  let lms = $state('');
  //: George, 2026-09-29: Lyrion only with the user's say-so. `find`, `address`
  //: or `off`; nothing chosen blocks Continue.
  let lmsMode = $state(null);
  let spotify = $state(true);
  let bt = $state(true);
  let headless = $state(false);
  //: ADR-0111 decision 4: asked, never assumed. null until answered.
  let visualiser = $state(null);
  //: ADR-0109 as amended 2026-10-02: the restart will ask Keep this screen?
  //: on the panel, which this page says before the phone is put down.
  let keepQuestion = $state(false);
  //: ADR-0109's Screen step. `screenInfo` is `/setup/screen`: what the screen
  //: reports, the tested model that suggests, every model. `scPick` is a
  //: model's label ("Maker/Model", as Settings stores it).
  let screenInfo = $state(null);
  let screenRetrying = $state(false);

  //: The list comes from the player over the setup Wi-Fi. It fails only when
  //: the phone has dropped off that network for a moment, so the answer is
  //: Retry - never only Headless, where one tap turns the screen off
  //: (George, 2026-10-01).
  async function loadScreens() {
    try {
      screenInfo = await json('/setup/screen');
    } catch {
      screenInfo = { seen: { connected: false }, suggested: null, models: [], failed: true };
    }
  }

  async function retryScreens() {
    screenRetrying = true;
    await loadScreens();
    screenRetrying = false;
  }
  let scPick = $state(null);
  let scChoose = $state(false);
  let scConfirmed = $state(false);
  let scQuery = $state('');
  let scOpen = $state({});

  // What the device offers.
  let nets = $state([]);
  let scan = $state('scanning');
  let outputs = $state([]);
  let zones = $state([]);
  let tick = $state(new Date());
  let finished = $state(false);

  const id = $derived(step >= 0 && step < last ? STEPS[step][0] : null);
  const accent = $derived(step >= 0 && step < last ? STEPS[step][2] : '#7ed6bc');
  const overLan = $derived(setup?.network === 'online');
  const picked = $derived(ssid === '__other' ? manualSsid.trim() : ssid);
  const pickedNet = $derived(nets.find((n) => n.name === ssid) ?? null);
  const secured = $derived(ssid === '__other' ? true : (pickedNet?.secured ?? true));

  //: `device_name.sanitise`, as the address will be. Accents fold, case
  //: drops, the rest becomes hyphens; 63 is one DNS label.
  function slugOf(v) {
    return (v || '')
      .normalize('NFKD')
      .replace(/[̀-ͯ]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9-]+/g, '-')
      .replace(/^-+|-+$/g, '')
      .slice(0, 63);
  }
  const slug = $derived(slugOf(name) || 'gexis');
  const shownName = $derived((name || '').trim() || 'gexis');

  const wifiValid = $derived(
    (overLan && !ssid) ||
      (!!picked && (!secured || pw.length >= 8 || (hasPassword && !pw)))
  );
  function valid() {
    switch (id) {
      case 'wifi': return wifiValid;
      case 'name': return slugOf(name).length > 1;
      case 'tz': return !!tz;
      case 'music': return lmsMode === 'find' || lmsMode === 'off' || (lmsMode === 'address' && lms.trim().length > 2);
      // A choice, unless the screen was recognised: then that model is one.
      case 'display': return headless || !!chosen;
      case 'visualiser': return visualiser !== null;
      default: return true;
    }
  }

  async function json(url, opts) {
    const r = await fetch(url, opts);
    const body = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(body.error || `${url}: ${r.status}`);
    return body;
  }

  async function rescan() {
    scan = 'scanning';
    try {
      nets = (await json('/setup/networks')).items ?? [];
    } catch {
      nets = [];
    }
    scan = 'done';
  }

  function rowsOf(settings) {
    const rows = {};
    const walk = (o) => {
      if (Array.isArray(o)) o.forEach(walk);
      else if (o && typeof o === 'object') {
        if (o.key && o.type) rows[o.key] = o;
        Object.values(o).forEach(walk);
      }
    };
    walk(settings);
    return rows;
  }

  onMount(() => {
    const clock = setInterval(() => (tick = new Date()), 1000);
    (async () => {
      let saved = {};
      let rows = {};
      try { saved = await json('/setup/answers'); } catch { /* a fresh start */ }
      try { rows = rowsOf(await json('/settings')); } catch { /* defaults below */ }
      await loadScreens();
      outputs = rows.output_device?.options ?? [];
      zones = rows.timezone?.options ?? [];
      let phoneTz = null;
      try { phoneTz = Intl.DateTimeFormat().resolvedOptions().timeZone || null; } catch { /* none */ }
      // A new device starts from the phone's clock; one being set up again
      // from what it already has. Saved answers win over both.
      name = saved.name ?? rows.device_name?.value ?? 'gexis';
      tz = saved.timezone ?? (setup?.needed ? phoneTz : rows.timezone?.value) ?? phoneTz;
      if (tz && zones.length && !zones.includes(tz)) tz = null;
      tzMode = tz ? 'auto' : 'region';
      clock24 = (saved.clock ?? rows.clock_format?.value ?? '24 h') !== '12 h';
      out = saved.output ?? rows.output_device?.value ?? outputs[0] ?? null;
      lms = saved.lms ?? (setup?.needed ? '' : (rows.lms_server?.value ?? ''));
      // Set up again: start on what the device does now. New: nothing chosen.
      lmsMode = saved.lms_mode ?? (setup?.needed ? null
        : rows.lms_enabled?.value === false ? 'off' : (lms ? 'address' : null));
      spotify = saved.spotify ?? rows.spotify_enabled?.value ?? true;
      bt = saved.bluetooth ?? rows.bt_enabled?.value ?? true;
      // A new device chooses (Continue waits); one set up again starts on
      // what it has.
      headless = saved.headless ?? (setup?.needed ? false : !!rows.headless?.value);
      scPick = headless ? null : (saved.screen ?? (setup?.needed ? null : (rows.screen?.value ?? null)));
      if (scPick && scPick === screenInfo.suggested?.label) scConfirmed = true;
      else if (scPick && screenInfo.suggested) scChoose = true;
      // A device set up again opens on its own screen's maker.
      const had = scPick && screenInfo.models.find((m) => m.label === scPick);
      if (had) scOpen = { [had.maker]: true };
      // Set up again: what the device has (a kept gexis-skins counts).
      visualiser = saved.visualiser ?? (setup?.needed ? null : (rows.visualiser_skins?.value ?? null));
      hidden = !!saved.hidden;
      hasPassword = !!saved.has_password;
      joinError = saved.error ?? null;
      if (saved.ssid) {
        ssid = hidden ? '__other' : saved.ssid;
        if (hidden) manualSsid = saved.ssid;
      }
      const at = STEPS.findIndex((s) => s[0] === saved.step);
      retrying = !!joinError;
      step = joinError ? 0 : at >= 0 ? at : -1;
      loaded = true;
      rescan();
    })();
    return () => clearInterval(clock);
  });

  function answersFor(stepId) {
    switch (stepId) {
      case 'wifi': {
        const a = { ssid: picked || null, hidden: ssid === '__other' };
        if (pw) a.password = pw;
        else if (!secured) a.password = null;
        return a;
      }
      case 'name': return { name: (name || '').trim() };
      case 'tz': return { timezone: tz, clock: clock24 ? '24 h' : '12 h' };
      case 'out': return { output: out };
      case 'music': return { lms_mode: lmsMode, lms: lmsMode === 'address' ? (lms.trim() || null) : null, spotify, bluetooth: bt };
      case 'display': return headless ? { headless: true } : { headless: false, screen: chosen };
      case 'visualiser': return { visualiser };
      default: return {};
    }
  }

  async function saveStep(nextStep) {
    const a = answersFor(id);
    a.step = nextStep >= 0 && nextStep < last ? STEPS[nextStep][0] : 'review';
    saving = true;
    problem = null;
    try {
      const saved = await json('/setup/answers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(a)
      });
      hasPassword = saved.has_password;
      joinError = saved.error ?? null;
      if (id === 'wifi') pw = '';
      return true;
    } catch (err) {
      problem = err.message;
      return false;
    } finally {
      saving = false;
    }
  }

  async function next() {
    if (saving || !valid()) return;
    if (step < 0) {
      step = 0;
      return;
    }
    if (id === 'review') {
      await finish();
      return;
    }
    let to = fromReview || (retrying && id === 'wifi') ? last - 1 : step + 1;
    if (skipped(to)) to += 1;
    if (to === last - 1) fromReview = false;
    if (await saveStep(to)) step = to;
  }

  //: A headless player has no screen to draw on, and seven small screens
  //: (480 × 320 and the like) fit no pack: their Visualiser step is passed
  //: over, and the setting left as it is.
  const noVisualiser = $derived(headless || !chosenModel?.skins);
  function skipped(n) {
    return noVisualiser && STEPS[n]?.[0] === 'visualiser';
  }
  function back() {
    step -= skipped(step - 1) ? 2 : 1;
  }

  //: **The count is what this person meets** (George, 2026-10-03, reviewing
  //: the copy: "Should be dynamic based on what the user actually sees"):
  //: seven when the Visualiser step is skipped, eight otherwise.
  const shownSteps = $derived(STEPS.filter((_, n) => !skipped(n)).length);
  const shownAt = (n) => STEPS.slice(0, n + 1).filter((_, i) => !skipped(i)).length;
  //: The welcome card names no number: it shows before the screen is known
  //: (George: "Let's just use a few").

  async function finish() {
    saving = true;
    problem = null;
    try {
      const told = await json('/setup/finish', { method: 'POST' });
      keepQuestion = !!told?.keep_question;
      finished = true;
    } catch (err) {
      problem = err.message;
    } finally {
      saving = false;
    }
  }

  // -- the Screen step (ADR-0109) -------------------------------------------
  const models = $derived(screenInfo?.models ?? []);
  const suggested = $derived(screenInfo?.suggested ?? null);
  const seenScreen = $derived(screenInfo?.seen ?? { connected: false });
  const scState = $derived(suggested ? 'recognised' : seenScreen.connected ? 'uncertain' : 'none');
  const recOk = $derived(scState === 'recognised' && !scChoose);
  //: The model setup will set: a pick, or, recognised, the suggestion.
  const chosen = $derived(headless ? null : scPick ?? (recOk ? suggested.label : null));
  const chosenModel = $derived(models.find((m) => m.label === chosen) ?? (suggested?.label === chosen ? suggested : null));
  //: The pack the chosen screen gets (the core's skin_packs.for_screen).
  //: Non-breaking: "1280 ×" and "800" must not part at a line's end.
  const packSize = $derived(chosenModel?.skins?.replace('x', '\u00a0×\u00a0') ?? '');
  const packLabel = $derived(chosenModel?.skin_count ? `the ${chosenModel.skin_count} skins drawn for ${packSize} screens` : `the set for ${packSize} screens`);
  //: Two minutes, as every Keep waits since 2026-10-04 (SETUP_KEEP_S and
  //: KEEP_S in the core).
  const pickNote = $derived(
    (chosenModel && !chosenModel.tested ? 'This model has not been tested with gexis. ' : '') +
      'When setup finishes the player restarts on this screen and asks Keep this screen? on it. If nobody touches Keep within two minutes, it goes back.'
  );
  //: The preset names carry the panel's own resolution, which the row's note
  //: already gives the way the screen is used ("(400x1280)" on a bar).
  const shortOf = (m) => m.model.replace(/\s*\(\d+x\d+\)\s*$/, '') || m.model;
  const sizeOf = (m) => `${m.width} × ${m.height}`;
  const familyOf = (m) => (m.family === 'bar' ? 'Bar' : 'Standard');
  const aspectOf = (m) => {
    const r = m.width / m.height;
    if (m.family === 'bar') return `${r.toFixed(1).replace(/\.0$/, '')}:1`;
    const known = [[16, 9], [16, 10], [5, 3], [4, 3], [3, 2]];
    const [a, b] = known.reduce((best, k) => (Math.abs(k[0] / k[1] - r) < Math.abs(best[0] / best[1] - r) ? k : best));
    return `${a}:${b}`;
  };
  const reported = $derived.by(() => {
    const p = seenScreen.preferred ? seenScreen.preferred.split('x').map(Number) : null;
    return { size: p, usb: seenScreen.usb ?? [] };
  });
  const scGroups = $derived.by(() => {
    const q = scQuery.trim().toLowerCase();
    const hay = (m) => `${m.maker} ${m.model} ${m.width}x${m.height} ${sizeOf(m)} ${familyOf(m)} ${m.tested ? 'tested' : 'untested'}`.toLowerCase();
    const rows = q ? models.filter((m) => hay(m).includes(q)) : models;
    const out = [];
    // Uncertain: the models of the reported size first; nothing is hidden.
    const size = reported.size;
    if (scState === 'uncertain' && !scChoose && !q && size) {
      const match = rows.filter((m) => (m.width === size[0] && m.height === size[1]) || (m.width === size[1] && m.height === size[0]));
      // Tested first; rows from every maker, so each names its maker.
      match.sort((a, b) => Number(b.tested) - Number(a.tested));
      if (match.length) out.push({ key: '__match', title: `Matching ${size[0]} × ${size[1]}`, rows: match, fixed: true, makers: true });
    }
    for (const maker of [...new Set(rows.map((m) => m.maker))]) {
      out.push({ key: maker, title: maker, rows: rows.filter((m) => m.maker === maker), fixed: !!q });
    }
    return out;
  });
  const groupOpen = (g) => g.fixed || !!scOpen[g.key];
  function pickScreen(m) {
    scPick = m.label;
    headless = false;
    scConfirmed = false;
  }

  const fmt = (d, zone) => {
    try {
      return new Intl.DateTimeFormat('en-GB', { hour: '2-digit', minute: '2-digit', hour12: !clock24, timeZone: zone }).format(d);
    } catch {
      return '--:--';
    }
  };
  const regions = $derived([...new Set(zones.map((z) => (z.includes('/') ? z.split('/')[0] : z)))]);
  const cities = $derived(zones.filter((z) => (z.includes('/') ? z.split('/')[0] : z) === tzRegion));
  const tzLabel = $derived(
    tz ? `${tz.split('/').slice(-1)[0].replace(/_/g, ' ')} · ${tz.includes('/') ? tz.split('/')[0] : tz}` : 'Not detected'
  );

  const review = $derived([
    ['Network', picked || (overLan ? 'Ethernet only' : 'Not set'), 0],
    ['Name', `${shownName} · ${slug}.local`, 1],
    ['Time zone', `${tz || 'Not set'} · ${clock24 ? '24 h' : '12 h'}`, 2],
    ['Output', out || 'Not set', 3],
    ['Library', lmsMode === 'off' ? 'Not used' : lmsMode === 'address' ? lms.trim() : lmsMode === 'find' ? 'Found once on your network' : 'Not chosen', 4],
    ['Services', [spotify ? 'Spotify Connect' : null, bt ? 'Bluetooth' : null].filter(Boolean).join(' · ') || 'Lyrion only', 4],
    ['Screen', headless ? 'Headless' : chosenModel ? `${chosenModel.maker} ${shortOf(chosenModel)} · ${chosenModel.width} × ${chosenModel.height}` : 'Not chosen', 5],
    ...(noVisualiser ? [] : [['Visualiser', visualiser === true ? `Install · ${chosenModel?.skin_count ? `${chosenModel.skin_count} skins, ` : ''}${packSize}` : visualiser === false ? 'None' : 'Not chosen', 6]])
  ]);
</script>

<div class="page">
  <div class="shell">
    <header>
      <img class="mark" src={mark} alt="" width="34" height="34" />
      <span class="crumb">
        {step < 0 ? 'First-time setup' : step >= last || finished ? 'Almost done' : `Step ${shownAt(step)} of ${shownSteps} · ${STEPS[step][1]}`}
      </span>
      {#if setup?.ssid}<span class="over">Over {setup.ssid}</span>{/if}
    </header>

    {#if step >= 0 && step < last && !finished}
      <div class="progress"><div style="width:{Math.round(((shownAt(step) - 1 + (valid() ? 1 : 0.35)) / shownSteps) * 100)}%; background:{accent}"></div></div>
    {/if}

    <div class="grid" class:grid--rail={step >= 0 && step < last && !finished}>
      {#if step >= 0 && step < last && !finished}
        <nav class="rail">
          {#each STEPS as s, n}
            <button class="rail-item" class:cur={n === step} disabled={n > step || skipped(n)} onclick={() => (step = n)}>
              <span class="rail-bar" style="background:{s[2]}; opacity:{n <= step ? 1 : 0.45}"></span>
              <span class="rail-label">{s[1]}</span>
              {#if n < step}<span class="tick"></span>{/if}
            </button>
          {/each}
        </nav>
      {/if}

      <main>
        {#if !loaded}
          <div class="row-spin"><span class="spin" style="border-top-color:#8fc4d8"></span><span>Opening setup</span></div>
        {:else if finished}
          <section class="pane">
            <h1 class="hero">{shownName} is {picked ? 'joining your network' : 'set up'}</h1>
            {#if picked}
              <p class="lead">This page is served by the player over its own Wi-Fi, so it stops here. Check this phone is back on <strong>{picked}</strong>, then open the address below.</p>
            {/if}
            {#if keepQuestion}
              <div class="info info--warn"><span class="bar" style="background:#e0a758"></span><span><b>Then go to the player's screen</b><small>It restarts on the screen you chose and asks whether to keep it. Tap Keep on the screen within two minutes, or it goes back to how it was.</small></span></div>
            {/if}
            <div class="addr-card">
              <div class="label">Open in any browser</div>
              <div class="addr">http://{slug}.local:8090</div>
            </div>
            <!-- The password line only when there was a password to refuse: a
                 secured Wi-Fi was chosen - not over a cable with no Wi-Fi, nor
                 on an open network (George, 2026-10-04: "Agree"). -->
            {#if headless || (picked && secured)}
              <div class="note-card" style="--bar: {headless ? '#e0a758' : '#7ed6bc'}">
                <span class="bar"></span>
                <span>{headless
                  ? 'Nothing is drawn on the device, so this address is the only way in. Write it down before you close the page.'
                  : 'If the password is not accepted, the player opens its setup network again within about a minute. Join it, and this page picks up where you left off.'}</span>
              </div>
            {/if}
          </section>
        {:else if step < 0}
          <section class="pane">
            <h1 class="hero">Set up <span class="word">gexis</span></h1>
            <p class="lead">
              {overLan
                ? 'This page talks only to the player, over your network.'
                : "You are connected to the player's own Wi-Fi. This page talks only to the player."}
            </p>
            <div class="cards">
              <div class="info"><span class="bar" style="background:#8fc4d8"></span><span><b>About two minutes</b><small>A few questions. Every one of them can be changed later in Settings.</small></span></div>
              {#if !overLan}
                <div class="info"><span class="bar" style="background:#7ed6bc"></span><span><b>Keep this phone handy</b><small>When setup finishes, the player leaves its own Wi-Fi for yours and this page stops working. That is by design, not a fault.</small></span></div>
                <!-- George, 2026-09-29: the page would not load until he
                     turned mobile data off. The setup network has no
                     internet, so a phone may send the page's requests over
                     mobile data instead, where the player is not. -->
                <div class="info info--warn"><span class="bar" style="background:#e0a758"></span><span><b>Keep mobile data off</b><small>Until setup finishes. With it on, your phone may try to reach this page over mobile data, where the player cannot be found.</small></span></div>
              {/if}
            </div>
          </section>
        {:else}
          <div class="eyebrow" style="color:{accent}"><span class="dot" style="background:{accent}"></span>{STEPS[step][1]}<span class="rule"></span></div>

          {#if id === 'wifi'}
            <section class="pane">
              <div>
                <h1>Join your network</h1>
                <!-- Over the player's Wi-Fi, no line here (George, 2026-10-05:
                     "This text is not needed" - the welcome's "Keep this phone
                     handy" already says the page stops when the player moves). -->
                {#if overLan}
                  <p class="sub">The player is on your network by cable. Add Wi-Fi as well, or leave it on the cable.</p>
                {/if}
              </div>

              {#if joinError}
                <div class="warn"><span class="bang">!</span><span>Could not join {joinError.ssid}. {joinError.reason} Type the password again.</span></div>
              {/if}

              {#if !ssid}
                {#if scan === 'scanning'}
                  <div class="row-spin"><span class="spin" style="border-top-color:#8fc4d8"></span><span>Looking for networks</span></div>
                {:else}
                  {#if !nets.length}
                    <!-- George, 2026-10-03, reviewing the copy: "Add copy to cover this." -->
                    <div class="info"><span class="bar" style="background:#8fc4d8"></span><span><b>No networks found</b><small>Move the player closer to your router and tap Scan again, or choose Other network to type one in.</small></span></div>
                  {/if}
                  <div class="list">
                    {#each nets as n (n.name)}
                      <button class="net" onclick={() => { ssid = n.name; pw = ''; hasPassword = false; manualSsid = ''; }}>
                        <span class="bars">{#each [1, 2, 3, 4] as b}<span style="height:{2 + b * 4}px; background:{b <= n.bars ? '#8fc4d8' : 'rgba(233,238,242,0.22)'}"></span>{/each}</span>
                        <span class="grow"><span class="nm">{n.name}</span><span class="meta">{n.secured ? 'Secured' : 'Open'}</span></span>
                        <span class="chev"></span>
                      </button>
                    {/each}
                    <button class="net" onclick={() => { ssid = '__other'; pw = ''; hasPassword = false; }}>
                      <span class="grow"><span class="nm">Other network</span><span class="meta">A hidden network, typed by name</span></span>
                      <span class="chev"></span>
                    </button>
                    <button class="ghost" onclick={rescan}>Scan again</button>
                  </div>
                {/if}
              {:else}
                <div class="picked">
                  <span class="grow"><b>{ssid === '__other' ? 'Other network' : ssid}</b><small>{secured ? 'Secured' : 'Open'}</small></span>
                  <button class="chip" onclick={() => { ssid = null; pw = ''; hasPassword = false; }}>Change</button>
                </div>
                {#if ssid === '__other'}
                  <label class="field"><span class="label">Network name</span>
                    <input type="text" bind:value={manualSsid} placeholder="Exactly as your router spells it" autocomplete="off" spellcheck="false" />
                  </label>
                {/if}
                {#if secured}
                  <label class="field"><span class="label">Password</span>
                    <span class="pw">
                      <input type={showPw ? 'text' : 'password'} bind:value={pw} placeholder={hasPassword ? 'Saved — type to replace it' : 'Network password'} autocomplete="off" spellcheck="false" />
                      <button type="button" class="chip in" onclick={() => (showPw = !showPw)}>{showPw ? 'Hide' : 'Show'}</button>
                    </span>
                    <!-- No hint for a new password (George, 2026-10-05: "Not
                         needed"); the saved one's line waits on his answer. -->
                    {#if hasPassword && !pw}
                      <span class="hint">Saved. The player tries it at the end of setup.</span>
                    {/if}
                  </label>
                {:else}
                  <span class="hint">This network is open — no password needed.</span>
                {/if}
              {/if}
            </section>
          {:else if id === 'name'}
            <section class="pane">
              <div>
                <h1>Name the player</h1>
                <p class="sub">The player's name, and the name every service shows it under — Lyrion, Spotify Connect, Bluetooth and the rest. Pick one you will recognise in a list of speakers.</p>
              </div>
              <label class="field"><span class="label">Device name</span>
                <input type="text" bind:value={name} placeholder="Living room" autocomplete="off" spellcheck="false" style="border-color:{slugOf(name).length > 1 ? '' : 'rgba(224,167,88,0.55)'}" />
                <span class="hint" style="color:{slugOf(name).length > 1 ? '' : '#e0a758'}">{slugOf(name).length > 1
                  ? 'Letters, numbers and hyphens become the address; the name keeps its capitals everywhere else.'
                  : 'Needs at least two letters or numbers.'}</span>
              </label>
              <div class="table">
                <div class="thead">Becomes</div>
                {#each [['Address', `http://${slug}.local`], ['Lyrion player', shownName], ['Spotify Connect', shownName], ['Bluetooth', shownName]] as p}
                  <div class="trow"><span class="what">{p[0]}</span><span class="val">{p[1]}</span></div>
                {/each}
              </div>
            </section>
          {:else if id === 'tz'}
            <section class="pane">
              <div>
                <h1>Set the clock</h1>
              </div>
              {#if tzMode === 'auto'}
                <div class="tz">
                  <div class="grow"><div class="label">{setup?.needed ? 'Read from this phone' : 'The player’s time zone'}</div><div class="tz-name">{tzLabel}</div></div>
                  <div class="clock">{fmt(tick, tz || 'UTC')}</div>
                </div>
                <button class="ghost" onclick={() => { tzMode = 'region'; tzRegion = null; }}>Set manually</button>
              {:else if tzMode === 'region'}
                <div class="list">
                  <div class="back-row"><button class="back" aria-label="Back" onclick={() => (tzMode = 'auto')}><span></span></button><span class="label">Region</span></div>
                  {#each regions as r}
                    <button class="net" onclick={() => { tzRegion = r; tzMode = 'city'; }}><span class="grow nm">{r}</span><span class="chev"></span></button>
                  {/each}
                </div>
              {:else}
                <div class="list">
                  <div class="back-row"><button class="back" aria-label="Back" onclick={() => (tzMode = 'region')}><span></span></button><span class="label">{tzRegion}</span></div>
                  {#each cities as z}
                    <button class="net" class:sel={tz === z} onclick={() => { tz = z; tzMode = 'auto'; }}>
                      <span class="grow nm">{z.split('/').slice(1).join(' / ').replace(/_/g, ' ') || z}</span>
                      <span class="time">{fmt(tick, z)}</span>
                    </button>
                  {/each}
                </div>
              {/if}
              <div class="tz">
                <span class="grow nm">Clock format</span>
                <span class="seg">
                  <button class:on={clock24} onclick={() => (clock24 = true)}>24 h</button>
                  <button class:on={!clock24} onclick={() => (clock24 = false)}>12 h</button>
                </span>
              </div>
            </section>
          {:else if id === 'out'}
            <section class="pane">
              <div>
                <h1>Choose the output</h1>
              </div>
              {#if !outputs.length}
                <!-- George, 2026-10-03, reviewing the copy: "Add copy to cover this." -->
                <div class="info"><span class="bar" style="background:#7ed6bc"></span><span><b>No audio output found</b><small>Check that the DAC or HAT is connected, then restart the player. You can carry on and choose one later in Settings.</small></span></div>
              {/if}
              <div class="list">
                {#each outputs as o}
                  <button class="net" class:sel={out === o} onclick={() => (out = o)}>
                    <span class="radio" class:on={out === o}><span></span></span>
                    <span class="grow nm">{o}</span>
                  </button>
                {/each}
              </div>
            </section>
          {:else if id === 'music'}
            <section class="pane">
              <div>
                <h1>Find your library</h1>
                <p class="sub">Your own music comes through a Lyrion server on your local network or on the player itself.</p>
              </div>
              <div class="list">
                <div class="label pad">Lyrion (Logitech Media Server)</div>
                {#each [
                  ['find', 'Find my Lyrion server', overLan ? 'The player looks on your network when you finish.' : 'The player looks once it is on your network, and uses it if it finds one.'],
                  ['address', 'Enter an address', 'If you know where your server is.'],
                  ['off', "I don't use Lyrion", 'No library on the panel. Spotify Connect and Bluetooth work without it; switch it on in Settings any time.']
                ] as o}
                  <button class="net" class:sel={lmsMode === o[0]} onclick={() => (lmsMode = o[0])}>
                    <span class="radio" class:on={lmsMode === o[0]}><span></span></span>
                    <span class="grow"><span class="nm">{o[1]}</span><span class="meta plain">{o[2]}</span></span>
                  </button>
                {/each}
              </div>
              {#if lmsMode === 'address'}
                <label class="field"><span class="label">Server address</span>
                  <input type="text" bind:value={lms} placeholder="192.168.1.10:9000" autocomplete="off" spellcheck="false" inputmode="url" />
                </label>
              {/if}
              <div class="list">
                <div class="label pad">Also switch on</div>
                {#each [['Spotify Connect', `The player appears in Spotify as ${shownName}.`, spotify, () => (spotify = !spotify)], ['Bluetooth', 'Phones can pair and send audio directly.', bt, () => (bt = !bt)]] as v}
                  <button class="net" onclick={v[3]}>
                    <span class="grow"><span class="nm">{v[0]}</span><span class="meta plain">{v[1]}</span></span>
                    <span class="toggle" class:on={v[2]}><span></span></span>
                  </button>
                {/each}
              </div>
            </section>
          {:else if id === 'display'}
            <section class="pane">
              <div>
                <h1>{recOk ? 'Is this your screen?' : scState === 'none' ? 'Nothing on the screen yet?' : scChoose ? 'Choose your screen' : 'Which screen is this?'}</h1>
                <p class="sub">{recOk
                  ? 'What the screen reports matches this model.'
                  : scState === 'none' ? 'Some screens need their settings before they show anything. Choose yours and the player will try it.'
                  : scChoose ? 'Every model gexis knows, by maker.'
                  : 'The screen said who made it and its resolution, but not which model. Choose it from the list.'}</p>
              </div>

              {#if recOk}
                <div class="sc-rec" class:on={scConfirmed && !headless}>
                  <span class="sc-art" style="aspect-ratio:{suggested.width} / {suggested.height}"><span>{aspectOf(suggested)}</span></span>
                  <span class="grow">
                    <b>{suggested.maker} {shortOf(suggested)}</b>
                    <span class="sc-size">{sizeOf(suggested)} · {familyOf(suggested)} layout</span>
                    <span class="sc-why">Suggested from what the screen and its touch controller report</span>
                  </span>
                  <span class="tag" class:untested={!suggested.tested}>{suggested.tested ? 'Tested' : 'Untested'}</span>
                </div>
                <div class="sc-pair">
                  <button class="sc-btn" class:on={scConfirmed && !headless} onclick={() => { scPick = null; scConfirmed = true; headless = false; }}>This is right</button>
                  <button class="sc-btn other" onclick={() => { scChoose = true; scConfirmed = false; }}>Choose another</button>
                </div>
                {#if !headless}
                  <div class="warn"><span class="bang">!</span><span>{pickNote}</span></div>
                {/if}
              {:else}
                {#if scState === 'uncertain' && !scChoose}
                  <div class="sc-seen">
                    <div class="label">What the screen reported</div>
                    <div class="sc-grid">
                      <span>Maker</span><span class="mono">{seenScreen.edid_maker ?? 'Not reported'}</span>
                      <span>Name</span><span class="mono">{seenScreen.edid_name ?? 'Not reported'}</span>
                      <span>Resolution</span><span class="mono">{reported.size ? `${reported.size[0]} × ${reported.size[1]}` : 'Not reported'}</span>
                      <span>Touch</span><span class="mono">{reported.usb.length ? reported.usb.map((u) => `USB ${u}`).join(', ') : 'No USB device'}</span>
                    </div>
                  </div>
                {/if}
                {#if screenInfo?.failed}
                  <div class="warn"><span class="bang">!</span><span>Couldn't load the list of screens. Your phone may have dropped off the player's Wi-Fi for a moment.</span></div>
                  <button class="sc-btn" onclick={retryScreens} disabled={screenRetrying}>{screenRetrying ? 'Trying again…' : 'Retry'}</button>
                {:else}
                  <label class="field">
                    <input type="text" class="search" style="--c:#8fd9a8" bind:value={scQuery} placeholder="Search by maker, size or resolution" autocomplete="off" spellcheck="false" />
                  </label>
                  {#each scGroups as g (g.key)}
                    <div class="list">
                      {#if g.fixed}
                        <div class="label pad">{g.title}</div>
                      {:else}
                        <button class="sc-maker" aria-expanded={groupOpen(g)} onclick={() => (scOpen = { ...scOpen, [g.key]: !groupOpen(g) })}>
                          <span class="label grow">{g.title}</span>
                          <span class="sc-count">{g.rows.length} {g.rows.length === 1 ? 'model' : 'models'}</span>
                          <span class="chev" class:down={groupOpen(g)}></span>
                        </button>
                      {/if}
                      {#if groupOpen(g)}
                        {#each g.rows as m (m.id)}
                          {@const on = !headless && chosen === m.label}
                          <button class="net" class:sel={on} onclick={() => pickScreen(m)}>
                            <span class="radio" class:on><span></span></span>
                            <span class="grow"><span class="nm wrap">{g.makers ? `${m.maker} ${shortOf(m)}` : shortOf(m)}</span><span class="meta">{sizeOf(m)} · {familyOf(m)}</span></span>
                            <span class="tag" class:untested={!m.tested}>{m.tested ? 'Tested' : 'Untested'}</span>
                          </button>
                          {#if on}
                            <div class="warn"><span class="bang">!</span><span>{pickNote}</span></div>
                          {/if}
                        {/each}
                      {/if}
                    </div>
                  {:else}
                    <p class="hint">No model matches “{scQuery.trim()}”.</p>
                  {/each}
                {/if}
              {/if}

              <div class="list">
                <div class="label pad">Or</div>
                <button class="net" class:sel={headless} onclick={() => { headless = true; scConfirmed = false; scPick = null; }}>
                  <span class="radio" class:on={headless}><span></span></span>
                  <span class="grow"><span class="nm">Headless</span><span class="meta plain">No local screen. The display stays off and nothing is drawn.</span></span>
                </button>
                {#if headless}
                  <div class="warn"><span class="bang">!</span><span>Without a screen, the setup network always uses the password <b>gexis-setup</b>. If gexis starts and cannot reach your Wi-Fi, it opens that network again: join it from your phone, then open <b>10.42.0.1:8090</b>.</span></div>
                {/if}
              </div>
            </section>
          {:else if id === 'visualiser'}
            <section class="pane">
              <div>
                <h1>A visualiser for the screen?</h1>
                <p class="sub">While music plays, the screen can show VU meters and spectrum analysers instead of the cover. They are drawn for one screen size, so the player fetches {packLabel}.</p>
              </div>
              <div class="list">
                {#each [
                  [true, 'Install the visualiser', 'Downloaded once the player is on your home network. Remove it any time under Plugins.'],
                  [false, 'No visualiser', 'Nothing is downloaded. Plugins can install it later.']
                ] as o}
                  <button class="net" class:sel={visualiser === o[0]} onclick={() => (visualiser = o[0])}>
                    <span class="radio" class:on={visualiser === o[0]}><span></span></span>
                    <span class="grow"><span class="nm">{o[1]}</span><span class="meta plain">{o[2]}</span></span>
                  </button>
                {/each}
              </div>
              <div class="note-card" style="--bar: #e8c27e">
                <span class="bar"></span>
                <span>The designs are made by the PeppyMeter community, and many show the faces of real hi-fi equipment.</span>
              </div>
            </section>
          {:else if id === 'review'}
            <section class="pane">
              <div>
                <h1>Check it over</h1>
                <p class="sub">Finishing writes all of this to the player and moves it to your network.</p>
              </div>
              <div class="table">
                {#each review as r}
                  <div class="trow"><span class="what">{r[0]}</span><span class="val grow">{r[1]}</span><button class="chip" onclick={() => { fromReview = true; step = r[2]; }}>Change</button></div>
                {/each}
              </div>
            </section>
          {/if}
        {/if}

        {#if problem}
          <div class="warn"><span class="bang">!</span><span>{problem}</span></div>
        {/if}

        {#if loaded && !finished}
          <div class="foot">
            {#if step > 0}<button class="ghost" onclick={back}>Back</button>{/if}
            <button class="primary" style="--c:{accent}" disabled={!valid() || saving} onclick={next}>
              {step < 0 ? 'Start' : id === 'review' ? 'Finish and connect' : 'Continue'}
            </button>
          </div>
        {/if}
      </main>
    </div>
  </div>
</div>

<style>
  /* The design's backdrop: the diagonal weave **blurred by 70 px and scaled**,
     under the radial scrim (Setup.dc.html). Drawn unblurred it read as a
     "hash of colours" (George, 2026-09-28). The panel bans blur for its GPU
     (IMPLEMENTED-DIFFERENTLY, the whole panel); a phone does not have that
     limit, and this page is only ever on a phone. Fixed layers, so the page
     scrolls over them. */
  .page {
    min-height: 100%;
    color: var(--ink);
    background: var(--bg-base);
    position: relative;
    isolation: isolate;
  }
  .page::before,
  .page::after {
    content: '';
    position: fixed;
    pointer-events: none;
    z-index: -1;
  }
  .page::before {
    inset: -90px;
    background: repeating-linear-gradient(38deg, var(--bg-weave-a) 0 48px, var(--bg-weave-b) 48px 96px);
    filter: blur(70px);
    transform: scale(1.14);
  }
  /* The same overhang as the weave: a phone's browser bar hiding on scroll
     grows the viewport, and a tint cut at the old edge left a band of
     untinted weave across the bottom (George's screenshot, 2026-09-29). */
  .page::after {
    inset: -90px;
    background: radial-gradient(130% 105% at 20% 42%, rgba(20, 33, 42, 0.72), rgba(13, 21, 28, 0.96));
  }
  .shell {
    max-width: 1000px;
    margin: 0 auto;
    padding: 28px 20px 44px;
  }
  @media (min-width: 720px) {
    .shell { padding: 46px 40px 64px; }
  }
  header { display: flex; align-items: center; gap: 16px; min-width: 0; }
  .mark { width: 34px; height: 34px; flex-shrink: 0; }
  .crumb, .over, .label, .thead, .eyebrow {
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .crumb { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .over { display: none; letter-spacing: 0.14em; }
  @media (min-width: 720px) { .over { display: block; } }

  .progress { height: 3px; border-radius: 2px; background: var(--ink-line); margin-top: 22px; overflow: hidden; }
  .progress div { height: 100%; transition: width 260ms cubic-bezier(0.32, 0.72, 0, 1); }

  .grid { margin-top: 26px; display: grid; gap: 34px; grid-template-columns: minmax(0, 1fr); }
  .rail { display: none; }
  @media (min-width: 720px) {
    .grid--rail { grid-template-columns: 220px minmax(0, 1fr); }
    .rail { display: flex; flex-direction: column; gap: 2px; position: sticky; top: 34px; align-self: start; }
  }
  .rail-item {
    all: unset; display: flex; align-items: center; gap: 15px; min-height: 56px; padding: 0 15px;
    border-radius: 13px; cursor: pointer; color: rgba(233, 238, 242, 0.6);
  }
  .rail-item.cur { background: rgba(233, 238, 242, 0.08); color: var(--ink); }
  .rail-item:disabled { cursor: default; }
  .rail-bar { width: 4px; height: 30px; border-radius: 2px; flex-shrink: 0; }
  .rail-label { flex: 1; font-size: 16px; font-weight: 600; }
  .tick { width: 13px; height: 7px; border-left: 2.5px solid #7ed6bc; border-bottom: 2.5px solid #7ed6bc; transform: rotate(-45deg); margin-top: -3px; }

  main { min-width: 0; }
  .eyebrow { display: flex; align-items: center; gap: 11px; margin-bottom: 20px; font-size: 13px; }
  .dot { width: 9px; height: 9px; border-radius: 50%; }
  .rule { flex: 1; height: 1px; background: var(--ink-line); }

  .pane { display: flex; flex-direction: column; gap: 22px; animation: fade 260ms cubic-bezier(0.32, 0.72, 0, 1); }
  @keyframes fade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: none; } }
  @keyframes spin { to { transform: rotate(360deg); } }
  h1 { margin: 0; font-weight: 800; letter-spacing: -0.015em; line-height: 1.15; font-size: 26px; }
  .hero { font-size: 30px; letter-spacing: -0.02em; line-height: 1.1; }
  @media (min-width: 720px) { h1 { font-size: 32px; } .hero { font-size: 40px; } }
  .word { font-weight: 600; }
  .lead { margin: 0; font-size: 17px; line-height: 1.55; color: var(--ink-muted); max-width: 52ch; }
  .sub { margin: 10px 0 0; font-size: 16px; line-height: 1.5; color: rgba(233, 238, 242, 0.66); max-width: 50ch; }

  .cards, .list { display: flex; flex-direction: column; gap: 6px; }
  .cards { gap: 10px; }
  .info, .note-card {
    display: flex; align-items: flex-start; gap: 14px; padding: 16px 18px; border-radius: 16px;
    background: rgba(255, 255, 255, 0.05); border: 1px solid var(--ink-line);
  }
  .info b { display: block; font-size: 17px; font-weight: 600; }
  .info--warn { border-color: rgba(224, 167, 88, 0.45); background: rgba(224, 167, 88, 0.08); }
  .info small { display: block; font-size: 15px; line-height: 1.45; color: var(--ink-quiet); margin-top: 5px; }
  .bar { width: 4px; align-self: stretch; border-radius: 2px; flex-shrink: 0; background: var(--bar, #7ed6bc); }
  .note-card { font-size: 15px; line-height: 1.5; color: var(--ink-muted); }

  .net, .picked {
    all: unset; box-sizing: border-box; display: flex; align-items: center; gap: 16px; min-height: 66px;
    padding: 12px 18px; border-radius: 14px; background: rgba(255, 255, 255, 0.05);
    border: 1px solid var(--ink-line); cursor: pointer;
  }
  .net:active { transform: scale(0.99); background: rgba(233, 238, 242, 0.1); }
  .net.sel { background: rgba(126, 214, 188, 0.1); border-color: rgba(126, 214, 188, 0.45); }
  .picked { cursor: default; }
  .picked b { display: block; font-size: 17px; font-weight: 700; }
  .picked small, .meta { display: block; font-family: var(--font-mono); font-size: 13px; letter-spacing: 0.04em; margin-top: 4px; color: var(--ink-quiet); }
  .meta.plain { font-family: var(--font-ui); font-size: 14px; letter-spacing: 0; line-height: 1.4; }
  .grow { flex: 1; min-width: 0; }
  .nm { display: block; font-size: 17px; font-weight: 600; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .bars { width: 26px; height: 20px; display: flex; align-items: flex-end; gap: 3px; flex-shrink: 0; }
  .bars span { width: 4px; border-radius: 1px; display: block; }
  .chev { width: 11px; height: 11px; border-right: 2.5px solid rgba(233, 238, 242, 0.42); border-top: 2.5px solid rgba(233, 238, 242, 0.42); transform: rotate(45deg); flex-shrink: 0; }
  .time { font-family: var(--font-mono); font-size: 14px; color: var(--ink-quiet); }

  .field { display: flex; flex-direction: column; gap: 9px; }
  input {
    width: 100%; box-sizing: border-box; height: 58px; border-radius: 14px; background: rgba(8, 12, 16, 0.6);
    border: 1px solid rgba(233, 238, 242, 0.18); padding: 0 18px; font-family: var(--font-mono);
    font-size: 16px; color: var(--ink); outline: none;
  }
  input:focus { border-color: var(--c, #8fc4d8); }
  input::placeholder { color: rgba(233, 238, 242, 0.38); }
  .pw { position: relative; display: block; }
  .pw input { padding-right: 96px; }
  .hint { font-size: 14px; line-height: 1.45; color: var(--ink-quiet); }

  .chip, .ghost, .back {
    all: unset; box-sizing: border-box; cursor: pointer; border-radius: 999px; font-weight: 700;
    background: var(--ink-fill); border: 1px solid rgba(233, 238, 242, 0.16);
  }
  .chip { padding: 8px 16px; font-size: 14px; }
  .chip.in { position: absolute; right: 8px; top: 50%; transform: translateY(-50%); }
  .ghost { align-self: flex-start; padding: 12px 22px; font-size: 15px; }
  .back { width: 40px; height: 40px; display: flex; align-items: center; justify-content: center; }
  .back span { width: 10px; height: 10px; border-left: 2.5px solid var(--ink); border-bottom: 2.5px solid var(--ink); transform: rotate(45deg); margin-left: 4px; }
  .back-row { display: flex; align-items: center; gap: 14px; padding: 0 2px 6px; }
  .pad { padding: 8px 2px 4px; }

  .table { display: flex; flex-direction: column; gap: 1px; border-radius: 16px; overflow: hidden; border: 1px solid var(--ink-line); }
  .thead { padding: 14px 18px; background: rgba(255, 255, 255, 0.05); }
  .trow { display: flex; align-items: center; flex-wrap: wrap; gap: 16px; padding: 14px 18px; background: rgba(255, 255, 255, 0.03); min-height: 34px; }
  /* A phone: the label above its value, which then has the row's width
     rather than a column a few letters wide ("Wavesh / are"). */
  .what { flex: 0 0 100%; margin-bottom: -10px; font-size: 15px; color: var(--ink-quiet); }
  .val { font-size: 17px; font-weight: 600; overflow-wrap: break-word; }
  @media (min-width: 720px) { .what { flex: 0 0 132px; margin-bottom: 0; } }

  .tz { display: flex; align-items: center; flex-wrap: wrap; gap: 16px; padding: 20px; border-radius: 16px; background: rgba(255, 255, 255, 0.05); border: 1px solid var(--ink-line); }
  .tz-name { font-size: 22px; font-weight: 700; margin-top: 8px; word-break: break-word; }
  .clock { font-family: var(--font-mono); font-size: 28px; font-weight: 600; }

  .seg { display: flex; gap: 6px; flex-shrink: 0; }
  .seg button {
    all: unset; cursor: pointer; padding: 10px 18px; border-radius: 999px; font-size: 15px; font-weight: 700;
    background: var(--ink-fill); border: 1px solid rgba(233, 238, 242, 0.16);
  }
  .seg button.on { background: #c8a2d8; border-color: #c8a2d8; color: var(--ink-on-accent); }

  .radio, .toggle { flex-shrink: 0; display: flex; align-items: center; }
  .radio { width: 24px; height: 24px; border-radius: 50%; border: 2px solid rgba(233, 238, 242, 0.42); justify-content: center; }
  .radio.on { border-color: #7ed6bc; }
  .radio.on span { width: 11px; height: 11px; border-radius: 50%; background: #7ed6bc; }
  .toggle { width: 58px; height: 30px; border-radius: 999px; background: var(--ink-fill); border: 1px solid rgba(233, 238, 242, 0.18); position: relative; }
  .toggle span { position: absolute; left: 3px; width: 24px; height: 24px; border-radius: 50%; background: rgba(233, 238, 242, 0.55); transition: left 160ms; }
  .toggle.on { background: #7ed6bc; border-color: #7ed6bc; }
  .toggle.on span { left: 31px; background: #0d151c; }

  /* ADR-0109's Screen step (Setup.dc.html step 6). */
  .sc-rec {
    display: flex; align-items: center; gap: 18px; padding: 20px; border-radius: 16px;
    background: rgba(255, 255, 255, 0.05); border: 1px solid var(--ink-line);
  }
  .sc-rec.on { background: rgba(143, 217, 168, 0.1); border-color: rgba(143, 217, 168, 0.45); }
  .sc-rec b { display: block; font-size: 19px; font-weight: 700; }
  .sc-art {
    width: 96px; max-height: 64px; flex-shrink: 0; border-radius: 8px; background: rgba(8, 12, 16, 0.5);
    border: 2px solid #8fd9a8; box-sizing: border-box; display: flex; align-items: center; justify-content: center;
    font-family: var(--font-mono); font-size: 11px; color: #8fd9a8;
  }
  .sc-size { display: block; font-size: 15px; color: rgba(233, 238, 242, 0.72); margin-top: 4px; }
  .sc-why { display: block; font-family: var(--font-mono); font-size: 12px; color: rgba(233, 238, 242, 0.5); margin-top: 8px; }
  .tag {
    font-family: var(--font-mono); font-size: 11px; letter-spacing: 0.14em; text-transform: uppercase;
    padding: 4px 8px; border-radius: 6px; flex-shrink: 0; align-self: center;
    background: rgba(126, 214, 188, 0.14); color: #7ed6bc;
  }
  .sc-rec .tag { align-self: flex-start; }
  .tag.untested { background: rgba(224, 167, 88, 0.14); color: #e0a758; }
  .sc-pair { display: grid; gap: 10px; grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .sc-btn {
    all: unset; box-sizing: border-box; cursor: pointer; padding: 15px 18px; border-radius: 999px; text-align: center;
    font-size: 16px; font-weight: 800; background: var(--ink-fill); border: 1px solid rgba(233, 238, 242, 0.16);
  }
  .sc-btn.other { font-weight: 700; }
  .sc-btn.on { background: #8fd9a8; border-color: #8fd9a8; color: var(--ink-on-accent); }
  .sc-btn:active { transform: scale(0.98); }
  .sc-seen { padding: 16px 18px; border-radius: 16px; background: rgba(255, 255, 255, 0.05); border: 1px solid var(--ink-line); }
  .sc-seen .label { padding: 0 0 10px; }
  .sc-grid { display: grid; grid-template-columns: auto minmax(0, 1fr); gap: 6px 16px; font-size: 15px; }
  .sc-grid > span:nth-child(odd) { color: var(--ink-quiet); }
  .mono { font-family: var(--font-mono); word-break: break-word; }
  /* A maker's heading opens its models: 181 rows, all open, are some
     thirteen thousand pixels of phone between the search and Continue. */
  .sc-maker { all: unset; box-sizing: border-box; cursor: pointer; display: flex; align-items: center; gap: 12px; min-height: 48px; padding: 4px 6px 4px 2px; }
  .sc-maker .label { padding: 0; }
  .sc-count { font-family: var(--font-mono); font-size: 12px; color: var(--ink-quiet); }
  .chev.down { transform: rotate(135deg); margin-top: -4px; }
  .nm.wrap { white-space: normal; overflow: visible; }
  /* The design's search field is in the page's face, not the mono of the
     fields that take addresses and passwords. */
  input.search { font-family: var(--font-ui); }

  .warn {
    display: flex; align-items: flex-start; gap: 14px; padding: 14px 16px; border-radius: 14px;
    background: rgba(224, 167, 88, 0.1); border: 1px solid rgba(224, 167, 88, 0.4); font-size: 15px; line-height: 1.45;
  }
  .bang { width: 22px; height: 22px; border-radius: 50%; background: #e0a758; color: #0d151c; font-weight: 800; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }

  .row-spin { display: flex; align-items: center; gap: 16px; padding: 20px 4px; font-size: 17px; font-weight: 600; }
  .spin { width: 30px; height: 30px; border-radius: 50%; border: 3px solid rgba(233, 238, 242, 0.14); animation: spin 900ms linear infinite; flex-shrink: 0; }

  .addr-card { padding: 20px; border-radius: 16px; background: rgba(255, 255, 255, 0.05); border: 1px solid var(--ink-line); }
  .addr { font-family: var(--font-mono); font-size: 23px; font-weight: 600; margin-top: 10px; word-break: break-all; }
  @media (min-width: 720px) { .addr { font-size: 30px; } }

  .foot { display: flex; align-items: center; gap: 12px; margin-top: 30px; }
  .foot .ghost { align-self: center; }
  .primary {
    all: unset; box-sizing: border-box; flex: 1; text-align: center; cursor: pointer; padding: 17px 24px;
    border-radius: 999px; font-size: 17px; font-weight: 800; background: var(--c); color: var(--ink-on-accent);
  }
  .primary:disabled { opacity: 0.4; cursor: default; }
</style>
