<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
<!--
  Settings, Phase 4 criterion 5 (ADR-0032, ADR-0035). Ported from
  design/source/Settings.dc.html. Rows come from the daemon's registry; the
  layout follows the component's own width, not the viewport, because it is
  standalone on a phone and will be embedded on the panel.
-->
<script>
  import PlayerSwitcher from './PlayerSwitcher.svelte';
  import CableSheet from './CableSheet.svelte';
  import SendStep from './SendStep.svelte';
  import { onMount, untrack } from 'svelte';
  import { pressing } from '../lib/press.svelte.js';
  import { components, update, screenCheck, showScreenCheck, resetting, metadata, fixedOutput } from '../lib/state.js';
  import UpdateModal from './UpdateModal.svelte';
  import ReleaseNotes from './ReleaseNotes.svelte';
  import ReleaseHistory from './ReleaseHistory.svelte';
  import NoteText from '../lib/NoteText.svelte';
  import Equaliser from './eq/Equaliser.svelte';
  import { screen } from '../lib/family.svelte.js';
  import {
    settingsGroups,
    settingsDevice,
    settingsError,
    listAction,
    listItems,
    loadSettings,
    runSetting,
    writeSetting,
    ask as askPlayer,
    UNREACHED,
    LONG_REQUEST_TIMEOUT_MS,
  } from '../lib/settings.js';

  // On the panel, Settings is a layer over the library and Back closes it
  // (source/Now Playing.dc.html passes the design's onBack). A phone has
  // nothing to go back to, so it passes none.
  //
  // `embedded` is the panel too: there the weave is drawn once for the whole
  // panel (PanelBackground.svelte). A phone gets its own, as before.
  //: `switcher`: ADR-0136's player switcher in the title, left out inside the
  //: phone's remote, whose picker is above Settings (ADR-0164).
  //: `flat`: inside the remote, every screen of Settings on the modals'
  //: solid grey, with no weave or veil (George, 2026-10-27).
  let { onback = null, embedded = false, openRow = null, onrowopened = null, switcher = true, flat = false } = $props();

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
  // ADR-0099: a `document` row opens a page to read (Legal, Credits).
  let docKey = $state(null);
  //: ADR-0162: Audio -> Equaliser opens the equaliser's own page.
  let eqPage = $state(false);
  let docPage = $state(null);
  let docError = $state(null);
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
  //: **ADR-0083.** The backup chosen for restoring, held until it is
  //: confirmed. A restore replaces everything and reboots, so it is the one
  //: item action on this screen that cannot happen on a single tap - and a
  //: `danger` confirm is the shape the screen already has for that
  //: (`factory_reset`).
  let restorePending = $state(null);
  // A list's items, and whether they have been looked for yet (ADR-0044 §1).
  // A Wi-Fi scan and an LMS broadcast both take seconds, so `searching` is a
  // real state rather than a courtesy: showing "nothing found" before the
  // search has finished would be a different claim from the true one.
  let items = $state([]);
  let searching = $state(false);
  let listError = $state(null);
  // The network being joined, and how that is going.
  let joinItem = $state(null);
  //: ADR-0123: the connected network's details, unfolded under its line and
  //: read again every 5 s while they are open - signal and speed move.
  let netOpen = $state(false);
  let netLive = $state(null);
  // A speed never breaks between its number and its unit ("325 / Mb/s").
  const keepUnit = (meta) => meta.replace(/(\d) ([GMk]b\/s)/, '$1\u00a0$2');
  $effect(() => {
    if (!netOpen) return;
    let stop = false;
    const read = async () => {
      try {
        const { response: r, body: answer } = await askPlayer('/network/wifi');
        const body = r.ok ? answer : null;
        if (!stop) netLive = body?.connected ? body : null;
      } catch {
        // A missed read keeps the last one on screen.
      }
    };
    read();
    const timer = setInterval(read, 5000);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  });
  let join = $state(null);
  let joinError = $state(null);
  // The backup being restored, while the shared progress card shows it -
  // so the card speaks of a backup, not a network.
  let restoring = $state(null);
  // The first level of a grouped choice - the time zone's region.
  let region = $state(null);
  //: A write in flight. Even a fast one deserves saying so, and this one
  //: is not always fast: a rename writes four files and the refetch behind
  //: it took three seconds while the Wi-Fi read still sat on the request
  //: path. The sheet stayed open with nothing to show for it (George,
  //: 2026-09-21), which reads as a tap that did not land.
  let saving = $state(false);
  //: What the buttons show: disabled, and "Saving", only once a save has
  //: taken longer than SHOW_SAVING_MS. A save that answers sooner - nearly
  //: all, since 2026-10-05 - made Close blink off and on (George). Taps are
  //: still refused for the whole save, by `saving`.
  let busy = $state(false);
  let busyTimer;
  const SHOW_SAVING_MS = 400;
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
  const facts = $derived(
    [deviceName, device.hostname ? `${device.hostname}.local` : hostOf(deviceName), device.address]
      .filter(Boolean)
  );
  const sheet = $derived(sheetKey ? asSheet(rowOf(sheetKey)) : null);
  //: ADR-0125: the problem report - built on the player, sent from here.
  //: The panel has nowhere to save a file, so there the sheet says where to
  //: open it instead. ADR-0125 decision 5: an address for people without a
  //: GitHub account (George, 2026-10-07).
  const REPORT_EMAIL = 'george.carstoiu@gexis.net';
  //: **ADR-0138: three steps** - what happened, Preparing (the checklist the
  //: player works down), Send (`SendStep`, shared with hardware feedback).
  const REPORT_OFTEN = ['Every time', 'Sometimes', 'Once so far'];
  const REPORT_STEP_NAMES = { what: 'What happened', preparing: 'Preparing', send: 'Send' };
  let reportStep = $state('what');
  let reportNote = $state('');
  let reportOften = $state(null);
  let reportStatus = $state(null);
  let reportIssue = $state(null);
  let reportError = $state(null);
  let reportOpening = 0;
  let reportPoll = null;
  const reportReady = $derived(reportStatus?.state === 'ready');
  const onPanel = () => document.documentElement.classList.contains('on-panel');
  $effect(() => {
    if (sheet?.kind !== 'report') {
      reportStep = 'what';
      reportNote = '';
      reportOften = null;
      reportStatus = null;
      reportIssue = null;
      reportError = null;
      clearTimeout(reportPoll);
      reportOpening += 1;
    }
  });
  //: ADR-0126: a hardware report - what the device reads, the owner's
  //: answers, then GitHub's form filled in. The options are the words the
  //: form's text fields expect (GitHub fills no dropdown from a link, so
  //: they are text fields since 2026-10-11).
  const HW_QUESTIONS = [
    { id: 'sound', q: 'Did the music sound right?', options: ['Yes', 'No', 'Not tried'] },
    { id: 'volume', q: 'Did the volume change with the slider?', options: ['Yes', 'No', 'Not tried'] },
    { id: 'clicks', q: 'Any clicks or gaps between tracks?', options: ['No', 'Yes', 'Not tried'] },
    { id: 'picture', q: 'Is the whole picture visible on the screen?', options: ['Yes', 'No', 'No screen'], screen: true },
    { id: 'touch', q: 'Does a tap land where the finger is?', options: ['Yes', 'No', 'No touch'], touch: true },
  ];
  let hw = $state(null);
  let hwAnswers = $state({});
  let hwNotes = $state('');
  let hwUrl = $state(null);
  let hwBusy = $state(false);
  let hwError = $state(null);
  let hwTones = $state(null);
  //: George, 2026-10-07: two steps - the screen, then the sound; the screen's
  //: skipped when there is none to look at (headless, or none connected).
  let hwStep = $state('screen');
  //: **Hardware feedback in steps** (George, 2026-10-09: the free text
  //: "should have its own step in the modal as otherwise it's too tight on a
  //: phone"): Screen (with a screen), Sound, then Anything else - with what
  //: the player puts in the report itself, so it is seen before it is sent.
  const HW_STEP_NAMES = { screen: 'Screen', sound: 'Sound', notes: 'Anything else' };
  const hwSteps = $derived(hw?.display ? ['screen', 'sound', 'notes'] : ['sound', 'notes']);
  const hwAt = $derived(Math.max(0, hwSteps.indexOf(hwStep)));
  const hwLast = $derived(hwAt === hwSteps.length - 1);
  let hwTonesBusy = $state(false);
  //: **Which opening of the sheet an answer belongs to** (review,
  //: 2026-10-11): tones take ten seconds, and a sheet closed and opened again
  //: meanwhile took the old tones as its own.
  let hwOpening = 0;
  async function playHardwareTones() {
    if (hwTonesBusy) return;
    const opening = hwOpening;
    hwTonesBusy = true;
    hwError = null;
    try {
      const { response: r, body } = await askPlayer('/hardware-report/tones', { method: 'POST' });
      if (opening !== hwOpening) return;
      if (!r.ok) throw new Error(body?.error ?? `HTTP ${r.status}`);
      hwTones = body.tones;
    } catch (e) {
      if (opening === hwOpening) hwError = plainly(e?.message, 'The tones could not be played. Try again.');
    } finally {
      hwTonesBusy = false;
    }
  }
  // ADR-0126: the test pattern this sheet asked for (its `seq`), so a result
  // left from an earlier check is not shown as this one's.
  let hwCheckSeq = $state(null);
  //: **Up as soon as the player says so** (George, 2026-10-11: the pattern
  //: "didn't work" the first time). The button followed only the state
  //: socket, and a phone back from the background had none for seconds; the
  //: player's own answer now counts until the socket catches up.
  let hwAsked = $state(null); // { seq, showing } from the player's answer
  const hwCheck = $derived(
    hwCheckSeq !== null && $screenCheck?.seq === hwCheckSeq ? $screenCheck
      : hwAsked !== null && hwAsked.seq === hwCheckSeq ? { seq: hwAsked.seq, showing: hwAsked.showing, result: null }
        : null,
  );
  const hwCheckLines = $derived(hwCheck?.result ? [
    `The panel draws ${hwCheck.result.size.replace('x', ' × ')}.`,
    ...hwCheck.result.taps.map((t) => `${t.corner}: ${t.off} px from the circle`),
    hwCheck.result.landed ? `All four within ${hwCheck.result.limit} px.` : `Not all within ${hwCheck.result.limit} px.`,
  ] : null);
  async function toggleScreenCheck() {
    hwError = null;
    try {
      if (hwCheck?.showing) {
        await showScreenCheck(false);
        if (hwAsked) hwAsked = { ...hwAsked, showing: false };
      } else {
        // A new check answers touch anew: the last one's answer does not
        // outlive it (review, 2026-10-11).
        const { touch: _, ...rest } = hwAnswers;
        hwAnswers = rest;
        const { seq } = await showScreenCheck(true);
        hwAsked = { seq, showing: true };
        hwCheckSeq = seq;
      }
    } catch (e) {
      hwError = plainly(e?.message, 'The test pattern could not be shown. Try again.');
    }
  }
  // Touch accuracy is measured, not asked: the taps answer it.
  let hwAnsweredSeq = null;
  $effect(() => {
    if (hwCheck?.result?.taps?.length && hwAnsweredSeq !== hwCheck.seq) {
      hwAnsweredSeq = hwCheck.seq;
      hwAnswers = { ...untrack(() => hwAnswers), touch: hwCheck.result.landed ? 'Yes' : 'No' };
    }
  });
  $effect(() => {
    if (sheet?.kind !== 'hardware') {
      if (untrack(() => hwCheck?.showing)) showScreenCheck(false).catch(() => {});
      hw = null; hwAnswers = {}; hwNotes = ''; hwUrl = null; hwError = null; hwTones = null; hwCheckSeq = null;
      hwAsked = null; hwAnsweredSeq = null; hwBusy = false;
      hwStep = 'screen';
      hwOpening += 1;
      return;
    }
    if (hw === null && !onPanel() && untrack(() => !hwError)) {
      const ready = hwPreloaded;
      hwPreloaded = null;
      if (ready) {
        hw = ready;
        hwStep = ready.display ? 'screen' : 'sound';
      } else if (ready === false) {
        hwError = 'The player could not read its hardware. Try again.';
      } else {
        loadHardware();
      }
    }
  });
  function loadHardware() {
    const opening = hwOpening;
    hwError = null;
    askPlayer('/hardware-report').then(({ response: r, body }) => (r.ok ? body : Promise.reject(r.status)))
      .then((body) => { if (opening === hwOpening) { hw = body; hwStep = body?.display ? 'screen' : 'sound'; } })
      .catch(() => { if (opening === hwOpening) hwError = 'The player could not read its hardware. Try again.'; });
  }
  // ADR-0126 decision 1: one line on the System page, a week after a board
  // or screen that is not Tested arrived; dismissed for good with one tap.
  let hwPrompt = $state(null);
  $effect(() => {
    if (current?.id !== 'system') return;
    askPlayer('/hardware-report/prompt').then(({ response: r, body }) => (r.ok ? body : null))
      .then((body) => (hwPrompt = body?.text ?? null))
      .catch(() => (hwPrompt = null));
  });
  //: ADR-0126 amended 2026-10-11 (George): the last feedback, kept until
  //: the sound card or screen changes - sent again or started over from
  //: the System row.
  let hwKept = $state(null);
  function loadHardwareKept() {
    askPlayer('/hardware-report/kept').then(({ response: r, body }) => (r.ok ? body : null))
      .then((body) => (hwKept = body?.kept ?? null))
      .catch(() => (hwKept = null));
  }
  $effect(() => {
    if (current?.id === 'system' && !sheet) loadHardwareKept();
  });
  function hardwareKeptLine(kept) {
    let day = '';
    try {
      day = new Date(kept.at * 1000).toLocaleDateString(undefined, { day: 'numeric', month: 'short' });
    } catch {
      day = '';
    }
    return day ? `Ready since ${day}` : 'Ready';
  }
  async function startHardwareOver(row) {
    hwKept = null;
    await askPlayer('/hardware-report/kept/clear', { method: 'POST' }).catch(() => {});
    openSheet(row);
  }
  function dismissHardwarePrompt() {
    hwPrompt = null;
    fetch('/hardware-report/prompt/dismiss', { method: 'POST' }).catch(() => {});
  }

  async function prepareHardwareReport() {
    if (hwBusy) return;
    // GitHub's form will not take feedback without it.
    if (!hwAnswers.sound) {
      hwStep = 'sound';
      hwError = 'Answer "Did the music sound right?" first: GitHub needs it.';
      return;
    }
    const opening = hwOpening;
    hwBusy = true;
    hwError = null;
    // A screen without touch says so; without a screen, neither is asked.
    const answers = !hw?.display ? { ...hwAnswers, picture: 'No screen', touch: 'No touch' }
      : !hw?.touch ? { ...hwAnswers, touch: 'No touch' } : hwAnswers;
    try {
      const { response: r, body } = await askPlayer('/hardware-report/issue', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          answers, notes: hwNotes, tones: hwTones ?? [],
          // The check this feedback ran, and no other (review, 2026-10-11).
          check_seq: hwCheck?.result ? hwCheckSeq : null,
        }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      if (opening === hwOpening) hwUrl = body.url;
    } catch (e) {
      if (opening === hwOpening) hwError = plainly(e?.message, 'The report could not be prepared. Try again.');
    } finally {
      hwBusy = false;
    }
  }

  //: ADR-0083 as amended 2026-10-08: the file itself, by its own name - a
  //: link, so a large backup goes straight to the browser's downloads.
  //: **ADR-0083 as amended 2026-10-17: a backup added from this phone or
  //: computer** (George: "It should stay in the restore list"). Sent as the
  //: request's body, as setup sends one; checked by the player and added to
  //: the list, never restored by itself.
  let adding = $state(null); // the share sent, 0..1, while one goes up
  let addError = $state(null);
  function addBackup(input) {
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    addError = null;
    adding = 0;
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `/backups?name=${encodeURIComponent(file.name)}`);
    xhr.setRequestHeader('Content-Type', 'application/octet-stream');
    xhr.upload.onprogress = (e) => { if (e.lengthComputable) adding = e.loaded / e.total; };
    xhr.onload = () => {
      let body = {};
      try { body = JSON.parse(xhr.responseText); } catch { /* not JSON */ }
      adding = null;
      if (body.ok) {
        flash(body.already ? `${body.name} is already in the list` : `${body.name} added`, 3500);
        openList('restore');
      } else addError = body.error ?? 'The file did not reach the player. Try again.';
    };
    xhr.onerror = () => {
      adding = null;
      addError = 'The file did not reach the player. Try again.';
    };
    xhr.send(file);
  }

  function downloadBackup(item) {
    const a = Object.assign(document.createElement('a'), { href: `/backups/${encodeURIComponent(item.name)}`, download: item.name });
    document.body.append(a);
    a.click();
    a.remove();
    flash(`Saving ${item.name}`);
  }

  async function prepareReport() {
    // GitHub's form will not take a report without it.
    if (!reportNote.trim()) {
      reportError = 'Say what happened first: GitHub needs it.';
      return;
    }
    const opening = reportOpening;
    clearTimeout(reportPoll);
    reportError = null;
    reportStatus = null;
    reportIssue = null;
    reportStep = 'preparing';
    try {
      // Its start gathers what the report is built from before it answers
      // (George, 2026-10-12, answer 10: one of the long requests).
      const { response: r } = await askPlayer('/report/prepare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ what: reportNote, often: reportOften }),
      }, LONG_REQUEST_TIMEOUT_MS);
      if (!r.ok) throw new Error(r.status === 409 ? 'A report is already being prepared. Try again in a minute.' : `HTTP ${r.status}`);
    } catch (e) {
      if (opening === reportOpening) reportError = plainly(e?.message, 'The report could not be prepared. Try again.');
      return;
    }
    followReport(opening);
  }

  //: The checklist, read every 0.4 s while the player works down it.
  async function followReport(opening) {
    if (opening !== reportOpening) return;
    try {
      const { body: status } = await askPlayer('/report/status');
      if (opening !== reportOpening) return;
      reportStatus = status;
      if (status.state === 'ready') {
        askPlayer('/report/issue').then(({ response: r, body }) => (r.ok ? body : null))
          .then((body) => { if (opening === reportOpening) reportIssue = body?.url ?? null; })
          .catch(() => {});
        return;
      }
      if (status.state === 'failed' || status.state === 'idle') {
        reportError = 'The report could not be prepared. Try again.';
        return;
      }
    } catch {
      // The player is busy or restarting: the next look says.
    }
    reportPoll = setTimeout(() => followReport(opening), 400);
  }

  function sizeSaid(bytes) {
    if (bytes == null) return '';
    return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
  }
  const picker = $derived(pickerKey ? rowOf(pickerKey) : null);

  //: **A password can be shown while it is typed** (George, 2026-10-18: "Had
  //: to rewrite the password multiple times because i was afraid I
  //: misspelled"). Hidden again for each sheet.
  let pwShown = $state(false);
  $effect(() => {
    sheet;
    untrack(() => (pwShown = false));
  });

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
    if (shareLogin) {
      return {
        ...row,
        type: 'share-login',
        label: `Sign in to ${shareLogin.name}`,
        note: 'It shows its shares only to a user it knows. The same user and password are used to mount the one you choose.',
        confirm: 'Show shares',
        wired: true,
      };
    }
    if (shareFolder) {
      return { ...row, label: shareFolder.title, note: 'Tick the folders Lyrion reads, at any level; tap a folder to open it.', discover: false, manual: null, hint: null };
    }
    if (shareBrowse) {
      return { ...row, label: `Shares on ${shareBrowse.server.name}`, note: 'Tick a share to add all of it, or tap it to see its folders.', discover: false, manual: null, hint: null };
    }
    if (usbBrowse) {
      return { ...row, label: usbBrowse.title, note: 'Tick the folders Lyrion reads, at any level; tap a folder to open it.', discover: false, manual: null, hint: null };
    }
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
    // ADR-0115: a network share is three fields, not one value.
    if (row.kind === 'share') {
      return {
        ...row,
        type: 'share',
        label: 'Add a share',
        note: 'A folder on a NAS or a computer. SMB needs a user and password; NFS needs only the address.',
        confirm: 'Add',
        wired: true,
      };
    }
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
  // An option with no `/` is a choice of its own, above the groups - Sound
  // card board's *Found by itself* (ADR-0117).
  const loose = $derived(grouped.filter((o) => !o.includes('/')));
  const regions = $derived([...new Set(grouped.filter((o) => o.includes('/')).map((o) => o.split('/')[0]))].sort());
  const places = $derived(
    region === null ? [] : grouped.filter((o) => o.split('/')[0] === region)
  );
  const placeLabel = (option) => option.split('/').slice(1).join('/').replace(/_/g, ' ');

  //: **ADR-0106: uploading a plugin, from a phone or computer only** - the
  //: panel has no file picker. George's wording, 2026-09-29.
  const UPLOAD_NOTICE =
    'This plugin is not part of Gexis Player. It is installed and run at your own risk and responsibility.';
  let pluginFile = $state(null);
  //: One confirm for both upload and remove: a title, what it means, and
  //: what happens on yes.
  let ask = $state(null);
  //: ADR-0110: the update modal - `check`, `available` or `progress` - and
  //: whether the user hid a running install's. A running install reopens
  //: it until hidden (closing it on the phone leaves the update running).
  let updateModal = $state(null);
  let updateHidden = $state(false);
  $effect(() => {
    if ($update?.active && !updateHidden && !updateModal) updateModal = 'progress';
    if (!$update?.active) updateHidden = false;
  });
  function closeUpdate() {
    if ($update?.active) updateHidden = true;
    updateModal = null;
  }
  function pickPlugin() {
    pluginFile?.click();
  }
  //: **What an upload or a removal is doing, until it is over** (George,
  //: 2026-09-30: "no feedback given on the upload itself"). `sending` has a
  //: share of the bytes; `checking` and `restarting` have none to give.
  let task = $state(null);
  function send(file) {
    // XMLHttpRequest, not fetch: only it reports an upload's progress.
    return new Promise((resolve) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/plugins/upload');
      xhr.setRequestHeader('Content-Type', 'application/gzip');
      // George, 2026-10-12 (answer 10): an upload that stalls ends. Not a
      // limit on the whole request - a large file over a slow link may take
      // longer than that - but on silence: no bytes going out, or no answer
      // once they are all sent, for LONG_REQUEST_TIMEOUT_MS.
      let late;
      const arm = () => {
        clearTimeout(late);
        late = setTimeout(() => xhr.abort(), LONG_REQUEST_TIMEOUT_MS);
      };
      xhr.upload.onprogress = (e) => {
        arm();
        if (e.lengthComputable && task) task.share = e.loaded / e.total;
      };
      xhr.upload.onload = () => {
        arm();
        if (task) task.phase = 'checking';
      };
      xhr.onloadend = () => clearTimeout(late);
      xhr.onabort = () => resolve({ ok: false, status: 0, body: { error: UNREACHED } });
      xhr.onload = () => {
        let body = {};
        try { body = JSON.parse(xhr.responseText); } catch { /* not JSON */ }
        resolve({ ok: xhr.status >= 200 && xhr.status < 300, status: xhr.status, body });
      };
      xhr.onerror = () => resolve({ ok: false, status: 0, body: { error: 'The upload did not reach the player.' } });
      arm();
      xhr.send(file);
    });
  }
  //: The core restarts 1.5 s after it answers. Back is a `/settings` that
  //: answers after one that did not - or, if the restart was never seen,
  //: after 10 s.
  async function waitForRestart() {
    const started = Date.now();
    let seenDown = false;
    while (Date.now() - started < 90000) {
      await new Promise((r) => setTimeout(r, 1000));
      const up = await askPlayer('/settings', { cache: 'no-store' }).then(({ response: r }) => r.ok, () => false);
      if (!up) seenDown = true;
      else if (seenDown || Date.now() - started > 10000) {
        await loadSettings();
        return true;
      }
    }
    return false;
  }
  async function restarted(done) {
    task.phase = 'restarting';
    const back = await waitForRestart();
    task = back
      ? { ...task, phase: 'done', text: done }
      : { ...task, phase: 'failed', text: 'The player has not come back yet. Reload this page in a minute.' };
  }
  function onPluginPicked(event) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    ask = {
      title: `Install ${file.name}?`,
      text: UPLOAD_NOTICE,
      confirm: 'Install',
      run: async () => {
        task = { title: file.name, phase: 'sending', share: 0 };
        const res = await send(file);
        if (!res.ok) {
          task = { ...task, phase: 'failed', text: res.body.error ?? `The player answered HTTP ${res.status}.` };
          return;
        }
        task.title = `${res.body.installed} ${res.body.version}`;
        const b = res.body;
        await restarted(
          !b.previous
            ? 'Installed, and switched off. Its switch is on this page.'
            : b.enabled
              ? `Updated from ${b.previous}, and restarted with the new version.`
              : `Updated from ${b.previous}. It stays switched off.`
        );
      }
    };
  }
  function uninstallPlugin(row) {
    const id = row.key.replace(/\.(enabled|missing)$/, '');
    ask = {
      title: `Remove ${row.label}?`,
      text: row.catalogue
        ? 'Its package, its data and its settings are deleted. Install it again from More plugins to have it back.'
        : 'Its package, its data and its settings are deleted. Upload it again to reinstall it.',
      confirm: 'Remove',
      danger: true,
      run: async () => {
        task = { title: row.label, phase: 'checking' };
        // A request that never arrives fails the card, as an upload's does:
        // a rejection left it on *Checking* with no OK (code review,
        // 2026-10-12).
        // A removal takes the package off, as an upload puts one on: long.
        const got = await askPlayer(`/plugins/${encodeURIComponent(id)}/uninstall`, { method: 'POST' },
                              LONG_REQUEST_TIMEOUT_MS).catch(() => null);
        if (!got) {
          task = { ...task, phase: 'failed', text: UNREACHED };
          return;
        }
        const { response: res, body } = got;
        if (!res.ok) {
          task = { ...task, phase: 'failed', text: body.error ?? `The player answered HTTP ${res.status}.` };
          return;
        }
        await restarted('Removed.');
      }
    };
  }
  async function answerAsk(yes) {
    const pending = ask;
    ask = null;
    if (yes && pending) await pending.run();
  }

  //: **ADR-0168: More plugins** - other authors' plugins from the plugin
  //: catalogue. On every screen, the panel's and the bars' too: installing
  //: from it needs no file. `catalogue` is what `/plugins/catalogue` last
  //: said; null before it answers and on a core without it.
  const CATALOGUE_NOTICE =
    'This plugin is not part of Gexis Player. It was checked before it was listed, and is installed and run at your own risk and responsibility.';
  let catalogue = $state(null);
  let catalogueOpen = $state(false);
  let catalogueReading = $state(false);
  //: Installs started here, by id, until they end: `{ version, previous, since }`.
  let catalogueStarted = $state({});
  //: What each ended with, said on its row until the page closes:
  //: `{ done: true, version, previous }` or `{ error }`.
  let catalogueSaid = $state({});
  let catalogueAsking = null;
  const listedOf = (id) => catalogue?.plugins?.find((p) => p.id === id) ?? null;
  const jobOf = (id) => catalogue?.jobs?.[id] ?? null;
  const pluginIdOf = (row) => row.key.replace(/\.(enabled|missing)$/, '');
  //: Something from the catalogue is on its way to this row's plugin: no
  //: Remove until it is over.
  const arriving = (row) => { const job = jobOf(pluginIdOf(row)); return !!job && job.phase !== 'failed'; };
  const catalogueUpdates = $derived((catalogue?.plugins ?? []).filter((p) => p.state === 'update').length);
  //: A job the core is still on - or, once installed, the restart that
  //: follows (ADR-0106), until the core is back without it.
  const catalogueMoving = $derived(
    Object.values(catalogue?.jobs ?? {}).some((j) => j.phase !== 'failed') || Object.keys(catalogueStarted).length > 0
  );

  async function readCatalogue(refresh = false) {
    if (catalogueAsking && !refresh) return catalogueAsking;
    const asking = (async () => {
      const asked = Date.now();
      const got = await askPlayer(`/plugins/catalogue${refresh ? '?refresh=1' : ''}`, { cache: 'no-store' },
                                  refresh ? LONG_REQUEST_TIMEOUT_MS : undefined).catch(() => null);
      // Not reached - a restart, a dropped link: the last answer stands.
      if (!got) return;
      // A core without the catalogue (404, 503) has nothing to offer.
      catalogue = got.response.ok ? got.body : null;
      if (got.response.ok) settle(got.body, asked);
    })();
    catalogueAsking = asking;
    try {
      await asking;
    } finally {
      if (catalogueAsking === asking) catalogueAsking = null;
    }
  }
  //: An install started here ends in a line on its row: failed with the
  //: core's reason, or - once the core answers without the job, which only
  //: a restart takes away - done, or lost if its version is not there. A
  //: read asked before the install started says nothing about it.
  function settle(view, asked) {
    for (const [id, s] of Object.entries(catalogueStarted)) {
      if (asked < s.since) continue;
      const job = view.jobs?.[id];
      const listed = view.plugins?.find((p) => p.id === id);
      if (job?.phase === 'failed') {
        delete catalogueStarted[id];
      } else if (!job) {
        catalogueSaid[id] = listed?.installed === s.version
          ? { done: true, version: s.version, previous: s.previous }
          : { error: `${s.version} was not installed. Try again.` };
        delete catalogueStarted[id];
      }
    }
  }
  $effect(() => {
    // Read with the settings: a restart, or a plugin put on or taken off.
    groups;
    untrack(() => readCatalogue());
  });
  $effect(() => {
    if (!catalogueMoving) return;
    const timer = setInterval(() => readCatalogue(), 1000);
    return () => clearInterval(timer);
  });
  // What an install ended with belongs to the visit that saw it: another
  // group opened, and it goes (found on sofapi, 2026-10-30: a panel left on
  // Plugins still said "just now" hours later).
  $effect(() => {
    cat;
    drilled;
    untrack(() => (catalogueSaid = {}));
  });
  //: The line on a plugin's own row: a first install's "switched off" no
  //: longer holds once its switch is on.
  function saidOnRow(r, id) {
    const said = catalogueSaid[id];
    return said && !(said.done && !said.previous && toggleOn(r)) ? said : null;
  }
  async function openCatalogue() {
    catalogueOpen = true;
    catalogueSaid = {};
    catalogueReading = true;
    await readCatalogue(true);
    catalogueReading = false;
  }
  function installListed(p, { asked = false } = {}) {
    const go = async () => {
      delete catalogueSaid[p.id];
      const got = await askPlayer('/plugins/catalogue/install', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: p.id }),
      }).catch(() => null);
      if (!got || !got.response.ok) {
        catalogueSaid[p.id] = { error: got ? (got.body.error ?? `The player answered HTTP ${got.response.status}.`) : UNREACHED };
        return;
      }
      catalogueStarted[p.id] = { version: got.body.version, previous: p.installed, since: Date.now() };
      catalogue = { ...catalogue, jobs: { ...(catalogue?.jobs ?? {}), [p.id]: got.body } };
    };
    // The notice comes once, before the first install (George, 2026-10-29);
    // an update and a Retry go straight on.
    if (asked || p.installed) return go();
    ask = { title: `Install ${p.name}?`, text: CATALOGUE_NOTICE, confirm: 'Install', run: go };
  }
  //: The line under a listed plugin, or on its own row in Plugins: its
  //: download while one runs, else where it stands on this player.
  function listedLine(p, job, said) {
    if (job?.phase === 'downloading') {
      const share = job.total ? job.done / job.total : null;
      return `Downloading ${job.version}` + (share != null ? ` · ${Math.round(share * 100)}%` : '…');
    }
    if (job?.phase === 'installing' || job?.phase === 'installed') return `Installing ${job.version}. The player restarts to finish.`;
    if (job?.phase === 'failed') return `${job.version} was not installed: ${job.error}.`;
    if (said?.error) return said.error;
    if (said?.done) {
      return said.previous
        ? `Updated just now from ${said.previous} · ${said.version}`
        : `Installed just now · ${said.version}. It is switched off: its switch is on the Plugins page.`;
    }
    if (!p) return '';
    switch (p.state) {
      case 'available': return `Not installed · ${p.version} · ${sizeSaid(p.size)}`;
      case 'installed': return `Installed · ${p.installed}`;
      case 'update': return `Installed · ${p.installed}${p.reason ? ` · withdrawn: ${p.reason}` : ''} · ${p.version} is listed`;
      case 'withdrawn': return `Installed · ${p.installed} · Withdrawn: ${p.reason}`;
      case 'blocked': return `Blocked, and switched off: ${p.reason}`;
      case 'uploaded': return `Uploaded here · ${p.installed}. The catalogue does not replace an upload; remove it to install this one.`;
      default: return '';
    }
  }
  function listedDetail(job) {
    if (job?.phase !== 'downloading' || job.done == null) return '';
    return job.total ? `${MB(job.done)} of ${MB(job.total)} MB` : `${MB(job.done)} MB`;
  }
  const listedFailed = (p, job, said) => job?.phase === 'failed' || !!said?.error || p?.state === 'blocked';
  const KIND_WORDS = { renderer: 'Source', service: 'Service' };
  const listedFacts = (p) => [KIND_WORDS[p.kind] ?? p.kind, p.author && `by ${p.author}`, p.licence].filter(Boolean);
  const MONTH_WORDS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function daySaid(when) {
    const d = typeof when === 'number' ? new Date(when * 1000) : new Date(String(when ?? ''));
    return Number.isNaN(d.getTime()) ? '' : `${d.getDate()} ${MONTH_WORDS[d.getMonth()]} ${d.getFullYear()}`;
  }
  const catalogueSubtitle = $derived(
    catalogue?.available ? `Published ${daySaid(catalogue.date)}` : catalogueReading ? 'Reading the catalogue…' : ''
  );

  //: **An explanation is said once** (George, 2026-10-03: "if a setting opens
  //: a modal then the explanation should go only in the modal, not the
  //: overview as well as it clutters the screen"). A row that opens a sheet
  //: or the skin picker keeps its note there; a switch, a read-only row and
  //: a document page have nowhere else to say it, so theirs stays.
  function opensItsOwn(row) {
    return !['toggle', 'readonly', 'document'].includes(row.type);
  }

  function rowOf(key) {
    for (const g of groups) for (const r of g.rows) if (r.key === key) return r;
    return null;
  }

  function valueOf(key) {
    for (const g of groups) for (const r of g.rows) if (r.key === key) return r.value;
    return undefined;
  }

  onMount(() => {
    loadSettings();
    // Leaving Settings inside the 300 ms still writes the last tap.
    return () => { if (pickedTimer) savePicked(); };
  });

  //: Opened on a row from outside (ADR-0109, amended 2026-10-03: *Choose*,
  //: when a different screen is attached): its page, and its sheet.
  $effect(() => {
    if (!openRow || !groups.length) return;
    const group = groups.find((g) => g.rows.some((r) => r.key === openRow));
    const row = rowOf(openRow);
    if (group && row) {
      cat = group.id;
      drilled = group.id;
      if (row.kind === 'equaliser') eqPage = true;
      else openSheet(row);
    }
    onrowopened?.();
  });

  // The core's own words go to the console; a person reads a sentence
  // (the copy review, 2026-10-05 - as Setup's errors were).
  function plainly(raw, sentence) {
    if (raw) console.warn('settings:', raw);
    // A request that never reached the player, or never came back, says
    // so in its own words (George, 2026-10-12, answer 10): "Try again"
    // alone reads as if the player had refused.
    if (raw === UNREACHED) return raw;
    return sentence;
  }

  function flash(text, ms = 1900) {
    clearTimeout(toastTimer);
    toast = text;
    toastTimer = setTimeout(() => (toast = null), ms);
  }

  //: **A switch moves when it is tapped** (George, 2026-10-19: "the
  //: toggles are a bit slow to activate or deactivate"). It waited for the
  //: save and then for the whole list read again - two round trips over the
  //: phone's Wi-Fi. Now the switch shows the new state at once, and goes back,
  //: with the reason, only if the save is refused.
  let flipped = $state({});
  const toggleOn = (r) => (r.key in flipped ? flipped[r.key] : !!r.value);
  $effect(() => {
    for (const key of Object.keys(flipped)) {
      const row = rowOf(key);
      if (row && !!row.value === flipped[key]) delete flipped[key];
    }
  });

  async function write(row, value) {
    if (row.type === 'toggle') {
      flipped[row.key] = !!value;
      setTimeout(() => delete flipped[row.key], 8000);
    }
    saving = true;
    clearTimeout(busyTimer);
    busyTimer = setTimeout(() => (busy = true), SHOW_SAVING_MS);
    try {
      const result = await writeSetting(row.key, value);
      // A 409 is a choice the hardware has taken away (its reason is on the
      // row already, in words) or a row this release does not apply.
      if (!result.ok && row.type === 'toggle') delete flipped[row.key];
      if (result.status === 409) flash(row.unavailable?.[value] ?? plainly(result.error, `${row.label} cannot be changed yet`));
      // A value not in the row's form says what the form is (`invalid`).
      else if (result.status === 400 && row.invalid) flash(row.invalid, 4500);
      else if (!result.ok) flash(plainly(result.error ?? `HTTP ${result.status}`, `${row.label} was not saved. Try again.`));
      return result.ok;
    } finally {
      clearTimeout(busyTimer);
      busy = false;
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
    // ADR-0123: the cable at a glance, the line the core keeps for it.
    if (row.kind === 'cable') return row.note ?? '';
    // A screen reads as its maker and model, not the picker's `Maker/Model`.
    if (row.optionTags && typeof v === 'string') return v.replace('/', ' ');
    // A skin by the name its pack gives it (George's "Brand · Model").
    if (row.optionLabels && v != null && row.optionLabels[v]) return row.optionLabels[v];
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
    // ADR-0135: standby times - the one, or how many.
    if (row.type === 'intervals') {
      const held = Array.isArray(v) ? v : [];
      if (!held.length) return 'None';
      if (held.length > 1) return `${held.length} times`;
      return `${held[0].from}–${held[0].until} · ${daysSaid(held[0].days)}`;
    }
    if (row.type === 'list') {
      // A server list reads out which one is in use; a device list counts
      // what it holds. The design takes the count in both cases, which loses
      // the connected network's name on the Wi-Fi row - recorded in
      // docs/findings/042 §7 as one more place its prose and its literal
      // disagree.
      // ADR-0115: the shares are drawn on the row itself, each with its
      // Forget (George, 2026-10-03: the stored list "look[ed] like just code").
      if (row.kind === 'share') return '';
      // ADR-0115 decision 23: the same, for the folders chosen on USB drives.
      if (row.kind === 'usb-folder') return (row.items ?? []).length ? '' : 'None added';
      if (v) return String(v);
      // The items are on the row because the daemon seeds a list that does
      // not have to go looking (ADR-0044 §1, amended). A row counting only
      // what the *sheet* fetches reads "None" until someone opens it -
      // which is what it did with a phone paired (George, on the panel,
      // 2026-09-21).
      const n = (row.items ?? []).length;
      if (!n) return 'None';
      // Counted in what the list holds: Bluetooth's are paired, the rest
      // are not (the copy review, 2026-10-05: Restore read "12 paired").
      if (row.kind === 'backup') return n === 1 ? '1 backup' : `${n} backups`;
      if (row.kind === 'network') return `${n} saved`;
      return `${n} paired`;
    }
    if (v === null || v === undefined) return row.type === 'action' || row.type === 'document' ? '' : '—';
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

  async function openDocument(row) {
    docKey = row.key;
    docPage = null;
    docError = null;
    try {
      const { response: res, body } = await askPlayer(`/notices/${encodeURIComponent(row.document)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      docPage = body;
    } catch (e) {
      docError = 'This page could not be loaded.';
    }
  }

  // ADR-0100 as amended: a plugin's download in words.
  const MB = (n) => (n / 1048576).toFixed(1);
  function downloadShare(c) {
    if (c.state === 'verifying' || c.state === 'installing') return 1;
    // A skin pack (ADR-0111) reports its share as the updater measures it.
    if (c.share != null) return Math.min(1, Math.max(0, c.share));
    return c.received != null && c.total ? Math.min(1, c.received / c.total) : null;
  }
  function downloadLine(c) {
    // A source with no name is left out rather than called "its maker".
    const from = c.from ? ` from ${c.from}` : '';
    const label = c.label ?? 'it';
    switch (c.state) {
      case 'preparing': return `Starting the download${from}…`;
      case 'downloading': {
        const share = downloadShare(c);
        return `Downloading ${label}${from}` + (share != null ? ` · ${Math.round(share * 100)}%` : '…');
      }
      case 'retrying': return `The download was interrupted: ${c.error ?? 'retrying'}`;
      case 'verifying': return `Checking ${label}…`;
      case 'installing': return `Installing ${label}…`;
      case 'installed': {
        const recent = c.updated && Date.now() / 1000 - c.updated < 120;
        return recent ? `Downloaded and installed just now · ${label}` : `Installed · ${label}`;
      }
      case 'failed': return c.error ?? `The download${from} failed`;
      default: return `Not installed · downloaded${from} when you switch it on`;
    }
  }
  function downloadDetail(c) {
    // Only while it is moving: once installed or failed, the size is noise.
    if (c.state !== 'downloading' && c.state !== 'retrying') return '';
    const parts = [];
    if (c.received != null) parts.push(c.total ? `${MB(c.received)} of ${MB(c.total)} MB` : `${MB(c.received)} MB`);
    if (c.attempt && c.attempts && (c.attempt > 1 || c.state === 'retrying')) parts.push(`attempt ${c.attempt} of ${c.attempts}`);
    return parts.join(' · ');
  }

  function tap(row) {
    if (row.kind === 'equaliser') {
      eqPage = true;
      return;
    }
    // A read-only row is a disabled button - except an uploaded plugin's,
    // which holds its Remove: a browser drops every tap inside a disabled
    // button, and that Remove did nothing (George, 2026-10-03). The row
    // itself still opens nothing.
    if (row.type === 'readonly') return;
    // ADR-0168: a blocked plugin's row holds its Remove, so it is not
    // disabled; its switch still does nothing.
    if (toggleBlocked(row)) return;
    if (row.type === 'document') openDocument(row);
    // ADR-0098: a switch with a warning asks before it turns ON - the
    // notice before a plugin's software is downloaded. Off
    // never asks.
    else if (row.type === 'toggle' && row.warn && !row.value) openSheet(row);
    else if (row.type === 'toggle') write(row, !toggleOn(row));
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

  //: **A choice row's warning waits for the choice** (George, 2026-10-02:
  //: "C" - on a Pixel 10 the Attached screen warning left room for one and
  //: a half models). A string warning on a choice is about changing it, so it
  //: shows once something other than the value is picked, with Confirm. A
  //: text row's (device_name) stays up the whole time: what it warns about
  //: happens whatever is typed (ADR-0044 §2).
  function warnsOnChoice(row) {
    return typeof row?.warn === 'string' && (row.type === 'choice' || row.grouped);
  }
  //: **A long list fills a phone** (the same day, "C"): more than this many
  //: choices and the sheet is the whole screen rather than a card over it.
  const FULL_SHEET_OPTIONS = 6;
  const sheetFull = $derived.by(() => {
    if (wide || !sheet) return false;
    const n = sheet.grouped ? (region === null ? regions.length : places.length)
      : (sheet.type === 'choice' || sheet.type === 'multi') ? (sheet.options ?? []).length : 0;
    return n > FULL_SHEET_OPTIONS;
  });

  //: What a written choice says. A change of volume type stops playback
  //: (ADR-0046 amended 2026-10-11), and so does a change of output (George,
  //: 2026-10-12), and each says so.
  function said(row, option) {
    const playing = $metadata?.transport === 'playing';
    // ADR-0046 amended 2026-10-11: a change of volume type stops playback
    // and reopens the sources at once (George) - no more waiting for a pause.
    if (row.key === 'output_mode' && playing) {
      flash(`Volume: ${option}. Playback stopped for the change; start it again when ready.`, 7000);
    } else if (row.key === 'output_device' && playing) {
      // George, 2026-10-12 (answer 12): the source playing is stopped before
      // the output changes, so nothing resumes on the new one by itself.
      flash(`${row.label}: ${option}. Playback stopped for the change; start it again when ready.`, 7000);
    } else {
      flash(`${row.label}: ${option}`);
    }
  }

  //: **The option tapped is drawn chosen at once** (George, 2026-10-11:
  //: "The option flashes but then it takes a bit to be selected"). Since a
  //: sheet with option notes stays open, the tick waited for the player to
  //: save and send the settings back; it now moves on the tap, and goes back
  //: to what is stored if the save fails.
  let choiceShown = $state(null);
  $effect(() => {
    // Let go once the stored value has caught up, or the sheet changes.
    if (!sheet || String(sheet.value) === untrack(() => choiceShown)) choiceShown = null;
  });

  async function choose(option) {
    const row = sheet;
    //: **A sheet whose options are described stays open** (George,
    //: 2026-10-11, on Volume: "shouldn't close automatically the modal.
    //: Should stay open until user closes it"): the descriptions are read
    //: beside the choice, and Close ends it.
    const stays = !!row.optionNotes;
    if (String(row.value) === option) {
      // Back to what is stored. With something held back that is a change of
      // mind, not a choice, so the sheet stays open and lets go of it.
      if (choicePending !== null) {
        choicePending = null;
        return;
      }
      if (!stays) sheetKey = null;
      return;
    }
    // ADR-0044 §2: a warned option is selected first and committed second.
    // The warning is the whole point of the mechanic and "turn your
    // amplifier down before confirming" cannot be said after the write.
    if (row.warn?.[option] || warnsOnChoice(row)) {
      choicePending = option;
      return;
    }
    if (!stays) sheetKey = null;
    else choiceShown = option;
    if (await write(row, option)) said(row, option);
    else if (choiceShown === option) choiceShown = null;
  }

  //: ADR-0044 §7. **Drawn at once, written just after** (George,
  //: 2026-10-16: wallpaper topics felt slow on sofapi). A tap used to wait
  //: for its write and then a full reload of the settings, 0.4-0.65 s on
  //: sofapi, and a second tap inside that worked from the old value and
  //: could undo the first. The sheet now draws a copy, as the standby times
  //: do, and writes it 300 ms after the last tap or as the sheet closes; a
  //: set the core refuses puts the copy back to what it holds.
  //: **The last one cannot be turned off**: the daemon refuses an empty set
  //: and the sheet says so rather than sending a write it knows will fail.
  let picked = $state([]);
  let pickedKey = null;
  let pickedTimer = null;
  function toggleOne(option) {
    const row = sheet;
    const on = picked.includes(option);
    if (on && picked.length === 1) {
      flash('At least one has to stay selected');
      return;
    }
    // Sent in the registry's order so the readout is stable; the daemon
    // sorts it the same way and the two agreeing is worth the sort here.
    picked = (row.options ?? []).filter((o) => (o === option ? !on : picked.includes(o)));
    pickedKey = row.key;
    clearTimeout(pickedTimer);
    pickedTimer = setTimeout(savePicked, 300);
  }
  async function savePicked() {
    clearTimeout(pickedTimer);
    pickedTimer = null;
    const row = pickedKey ? rowOf(pickedKey) : null;
    if (!row || row.type !== 'multi') return;
    const wanted = $state.snapshot(picked);
    if (JSON.stringify(wanted) === JSON.stringify(row.value ?? [])) return;
    if (!(await write(row, wanted)) && sheet?.key === row.key) picked = [...(row.value ?? [])];
  }

  //: **ADR-0135: standby times.** Edited in a copy the sheet draws at once -
  //: a day chip waiting for the player's answer felt slow (George,
  //: 2026-10-11) - and written 400 ms after the last change, or as the sheet
  //: closes. A time the core refuses puts the copy back to what it holds and
  //: says why. Times are picked from our own grid, hours then quarters: the
  //: browser's list was "really old school" and the panel has no keyboard.
  const DAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
  const HOURS = Array.from({ length: 24 }, (_, h) => String(h).padStart(2, '0'));
  const QUARTERS = ['00', '15', '30', '45'];
  let ivs = $state([]);
  let picking = $state(null); // { i, which } while a time's grid is open
  let ivTimer = null;
  //: The times row the sheet last opened - the standby times or the
  //: dashboard's (ADR-0156) - for a write still waiting when it closes.
  let ivKey = 'standby_times';
  function daysSaid(days = []) {
    const on = DAYS.filter((d) => days.includes(d));
    if (on.length === 7) return 'every day';
    if (on.join() === 'Mon,Tue,Wed,Thu,Fri') return 'Mon–Fri';
    if (on.join() === 'Sat,Sun') return 'weekends';
    return on.join(', ');
  }
  function ivChanged(list) {
    ivs = list;
    clearTimeout(ivTimer);
    ivTimer = setTimeout(saveIntervals, 400);
  }
  async function saveIntervals() {
    clearTimeout(ivTimer);
    ivTimer = null;
    const row = sheet ?? rowOf(ivKey);
    if (!row || row.type !== 'intervals') return;
    const wanted = $state.snapshot(ivs);
    if (JSON.stringify(wanted) === JSON.stringify(row.value ?? [])) return;
    if (!(await write(row, wanted))) ivs = structuredClone(row.value ?? []);
  }
  function setTime(i, which, part, value) {
    const [h, m] = ivs[i][which].split(':');
    const time = part === 'h' ? `${value}:${m}` : `${h}:${value}`;
    // The grid stays open to show what was chosen (George, 2026-10-11);
    // tapping the time again closes it.
    ivChanged(ivs.map((iv, k) => (k === i ? { ...iv, [which]: time } : iv)));
  }
  function toggleDay(i, day) {
    const days = ivs[i].days;
    if (days.includes(day) && days.length === 1) {
      flash('At least one day has to stay selected');
      return;
    }
    const next = days.includes(day) ? days.filter((d) => d !== day) : DAYS.filter((d) => d === day || days.includes(d));
    ivChanged(ivs.map((iv, k) => (k === i ? { ...iv, days: next } : iv)));
  }
  function addInterval() {
    picking = null;
    ivChanged([...ivs, { from: '22:00', until: '06:00', days: [...DAYS] }]);
  }
  function removeInterval(i) {
    picking = null;
    ivChanged(ivs.filter((_, k) => k !== i));
  }

  let draft = $state(null);

  //: **Hardware feedback opens whole** (George, 2026-10-11: it "still loads
  //: in two steps which is making the entire thing look like it's
  //: jumping"). The sheet opened on "Reading the hardware…" and grew when
  //: the answer came; the read takes about 0.2 s, so the sheet now waits for
  //: it and opens once, complete. A read that fails or takes over 4 s opens
  //: the sheet anyway, on its error and Try again.
  let hwPreloaded = null; // the answer, false when it failed, null when not asked
  let hwPreloading = false;
  async function preloadHardware(row) {
    if (hwPreloading) return;
    hwPreloading = true;
    const stop = new AbortController();
    const late = setTimeout(() => stop.abort(), 4000);
    try {
      const r = await fetch('/hardware-report', { signal: stop.signal });
      hwPreloaded = r.ok ? await r.json() : false;
    } catch {
      hwPreloaded = false;
    } finally {
      clearTimeout(late);
      hwPreloading = false;
    }
    openSheet(row);
  }

  function openSheet(row) {
    // A multi-choice tap still waiting goes before another sheet takes the copy.
    if (pickedTimer) savePicked();
    if (row.kind === 'hardware' && !onPanel() && hwPreloaded === null) {
      preloadHardware(row);
      return;
    }
    sheetKey = row.key;
    manual = false;
    shareBrowse = null;
    shareFolder = null;
    usbBrowse = null;
    picks = [];
    shareLogin = null;
    choicePending = null;
    joinItem = null;
    join = null;
    joinError = null;
    restoring = null;
    listError = null;
    addError = null;
    // A grouped choice opens on the region the current value is in, so the
    // zone in use is one tap away rather than two.
    region = row.grouped ? String(row.value ?? '').split('/')[0] || null : null;
    if (region !== null && !String(row.value ?? '').includes('/')) region = null;
    // ADR-0119: a row its plugin reports done opens empty - Claim again
    // wants a new token, and the spent one is no use to edit.
    draft = row.type === 'text' ? (row.status ? '' : (row.value ?? '')) : row.type === 'number' ? (row.value ?? row.min) : null;
    // A seeded list is drawn from the row itself, so the sheet opens with
    // its devices on it rather than with a spinner for the 25 ms the read
    // takes (ADR-0044 §1, amended 2026-09-21).
    items = row.items ?? [];
    if (row.type === 'list') openList(row.key);
    if (row.type === 'intervals') {
      ivs = structuredClone(row.value ?? []);
      ivKey = row.key;
      picking = null;
    }
    if (row.type === 'multi') picked = Array.isArray(row.value) ? [...row.value] : [];
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
    listError = answer.error ? plainly(answer.error, 'The list could not be read. Try again in a moment.') : null;
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
        // ADR-0123 as amended: on the cable, the network is saved for later.
        flash(answer.notice ?? `Joined ${name}`, answer.notice ? 6000 : undefined);
      }, 1300);
    });
  }

  async function doForget(item) {
    const key = sheetKey;
    await command({ name: item.address ?? item.name, action: 'forget' }, (answer) => {
      // A phone keeps its half of the pairing, and pairing again fails
      // silently until it forgets too (George, 2026-10-03: "Yes. Add text").
      if (answer.ok && key === 'bt_trusted') {
        flash(`${item.name} forgotten. To pair it again, forget ${deviceName} on it too.`, 6000);
      } else {
        flash(answer.ok ? `${item.name} forgotten` : plainly(answer.error, 'Could not forget it. Try again.'));
      }
      if (answer.ok) openList(key);
    });
  }

  //: ADR-0115: Forget on the row itself, without opening the sheet.
  async function forgetShare(row, item) {
    const answer = await listAction(row.key, { name: item.address ?? item.name, action: 'forget' });
    const done = row.kind === 'usb-folder' ? 'removed' : 'forgotten';
    flash(answer.ok ? `${item.name} ${done}` : plainly(answer.error, `Could not ${row.kind === 'usb-folder' ? 'remove' : 'forget'} it. Try again.`));
  }

  //: ADR-0115: the share being added.
  let share = $state({ address: '', user: '', password: '' });
  //: ADR-0115's scan: the server whose shares are shown (with the login
  //: that showed them), and the server waiting for a login first.
  let shareBrowse = $state(null);
  //: George, 2026-10-18: the share folder open in the sheet, at any depth.
  let shareFolder = $state(null);
  //: ADR-0115 decision 23: the USB drive and folder open in the sheet.
  let usbBrowse = $state(null);
  //: A switch whose *on* is unavailable, while it is off: greyed and not
  //: tappable, its reason under it (George, 2026-10-19: USB drives with no
  //: drive plugged in).
  const toggleBlocked = (r) => r.type === 'toggle' && !toggleOn(r) && !!r.unavailable?.true;

  //: **Tick several** (George, 2026-10-18): folders ticked on a drive or a
  //: share, at any level, kept while browsing, added with one button.
  let picks = $state([]);

  function tickable(item) {
    if (sheet?.kind === 'usb-folder') return !!item.drive;
    if (sheet?.kind === 'share') return !!item.share && !!item.address && !item.server;
    return false;
  }
  function pickOf(item) {
    return sheet?.kind === 'usb-folder'
      ? { key: `${item.drive}/${item.folder ?? ''}`, drive: item.drive, folder: item.folder ?? '', name: item.name }
      : { key: item.address, address: item.address, name: item.name };
  }
  //: A ticked folder covers the folders inside it.
  function inside(outer, inner) {
    return sheet?.kind === 'usb-folder'
      ? outer.drive === inner.drive && (outer.folder === '' || inner.folder.startsWith(outer.folder + '/'))
      : inner.key.toLowerCase().startsWith(outer.key.toLowerCase() + '/');
  }
  function coveredBy(item) {
    const p = pickOf(item);
    return picks.find((x) => x.key !== p.key && inside(x, p)) ?? null;
  }
  function isPicked(item) {
    const p = pickOf(item);
    return !!coveredBy(item) || picks.some((x) => x.key === p.key);
  }
  function togglePick(item) {
    if (coveredBy(item)) return;
    const p = pickOf(item);
    if (picks.some((x) => x.key === p.key)) {
      picks = picks.filter((x) => x.key !== p.key);
      return;
    }
    picks = [...picks.filter((x) => !inside(p, x)), p];
  }
  async function addPicked() {
    const key = sheetKey;
    const usb = sheet?.kind === 'usb-folder';
    const { user, password } = shareBrowse ?? {};
    let added = 0;
    for (const p of [...picks]) {
      const body = usb ? { name: p.drive, action: 'add', folder: p.folder }
        : { name: p.address, action: 'add', user: user ?? (p.address.startsWith('//') ? 'guest' : null), password: password ?? null };
      const answer = await listAction(key, body);
      if (!answer.ok) {
        flash(`${p.name}: ${plainly(answer.error, 'could not be added.')}`);
        break;
      }
      picks = picks.filter((x) => x.key !== p.key);
      added += 1;
    }
    if (added) flash(added === 1 ? 'One folder added' : `${added} folders added`);
    if (!picks.length && sheetKey === key) {
      usbBrowse = null;
      shareFolder = null;
      shareBrowse = null;
      openList(key);
    }
  }
  function goCrumb(c) {
    if (sheet?.kind === 'usb-folder') {
      if (c.top) {
        usbBrowse = null;
        openList(sheetKey);
      } else browseUsb(c.drive, c.folder);
    } else if (c.server) {
      shareFolder = null;
      browseShares(shareBrowse.server, shareBrowse.user, shareBrowse.password);
    } else browseShareFolder(c.address);
  }
  let shareLogin = $state(null);
  let shareCreds = $state({ user: '', password: '' });

  async function browseShares(item, user = null, password = null) {
    searching = true;
    listError = null;
    await command({ name: item.name, action: 'browse', server: item.server, user, password }, (answer) => {
      searching = false;
      if (answer.login) {
        shareLogin = item;
        shareCreds = { user: user ?? '', password: '' };
        if (user) flash(plainly(answer.error, 'The user or password was not accepted.'));
        return;
      }
      if (!answer.ok) {
        flash(plainly(answer.error, 'Could not read its shares. Try again.'));
        return;
      }
      shareBrowse = { server: item, user, password };
      items = answer.items ?? [];
      if (!items.length) listError = `${item.name} shows no shares to this user.`;
    });
  }

  async function browseUsb(drive, folder) {
    searching = true;
    listError = null;
    await command({ name: drive, action: 'browse', folder }, (answer) => {
      searching = false;
      if (!answer.ok) {
        flash(plainly(answer.error, 'Could not read the drive. Is it still plugged in?'));
        return;
      }
      usbBrowse = { drive, folder, title: answer.title ?? 'USB drive',
                    crumbs: [{ name: 'Drives', top: true }, ...(answer.crumbs ?? [])] };
      items = answer.items ?? [];
    });
  }

  async function browseShareFolder(address) {
    searching = true;
    listError = null;
    const { user, password } = shareBrowse ?? {};
    await command({ name: address, action: 'folders', user: user ?? null, password: password ?? null }, (answer) => {
      searching = false;
      if (!answer.ok) {
        flash(plainly(answer.error, 'Could not read its folders. Try again.'));
        return;
      }
      shareFolder = { address, title: answer.title ?? address, crumbs: answer.crumbs ?? [] };
      items = answer.items ?? [];
    });
  }

  function enterManual() {
    share = { address: '', user: '', password: '' };
    manual = true;
    draft = String(rowOf(sheetKey)?.value ?? '');
  }

  async function chooseItem(item) {
    const row = rowOf(sheetKey);
    if (!row) return;
    // Choosing a server is a write; joining a network is a command. The row
    // that stores a value and the row that performs one are the same type,
    // and `kind` is what tells them apart (ADR-0044 §1).
    // ADR-0115: a found server shows its shares; a share on it is added with
    // the login that showed it; a share already added says how it is.
    // ADR-0115 decision 23: a drive opens at its top, a folder opens, Back
    // up goes one level up, and the first item adds what is open.
    if (row.kind === 'usb-folder') {
      // Tick several (George, 2026-10-18): the row opens; its box ticks.
      if (item.drive) browseUsb(item.drive, item.folder ?? '');
      return;
    }
    if (row.kind === 'share') {
      // George, 2026-10-18: an SMB share opens into its folders; the first
      // item adds what is open, Back up goes one level up.
      if (item.share && shareBrowse && !item.add && (item.open || item.up || (item.address ?? '').startsWith('//'))) {
        browseShareFolder(item.address ?? item.name);
      } else if (item.share && shareBrowse) {
        // An NFS export is not opened: tapping it ticks it.
        togglePick(item);
      } else if (item.server) {
        browseShares(item);
      } else if (item.login) {
        // ADR-0115 decision 15: restored without its password, which backups
        // do not carry - typed in again here.
        share = { address: item.address, user: item.user ?? '', password: '' };
        manual = true;
      }
      return;
    }
    if (row.kind === 'server') {
      closeSheet();
      // Tapping the server already in use says "that one", so the sheet
      // closes and nothing is written.
      // A found server is shown by its name and stored by its address.
      const address = item.address ?? item.name;
      if (String(row.value ?? '') === address) return;
      // The daemon reads this at its start, so saving it restarts the core
      // (George, 2026-10-23, ADR-0048 amended): moving a running player to
      // another server means dropping its subscription, re-resolving the
      // player and re-arbitrating.
      if (await write(row, address)) flash(restartToast(row), 6000);
      return;
    }
    if (row.kind === 'backup') {
      // An empty or damaged file is listed to be forgotten, never restored
      // (2026-10-16): its line already says why.
      if (item.broken) {
        flash(`${item.name} cannot be restored. Forget it, or copy in a good one.`, 4500);
        return;
      }
      // ADR-0083: ask first. Everything this replaces is unrecoverable
      // afterwards, and the device restarts.
      restorePending = item;
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
    share: { title: 'Looking for shares', note: 'Servers that announce themselves answer within a few seconds.' },
  };

  const ORDINAL = /^(\d+)G5_(.*)$/;
  function parts(name, row = picker) {
    // The pack's own name for it, when the pack has one (George, 2026-10-02:
    // "Brand · Model · variant", no numbers, no underscores).
    const label = row?.optionLabels?.[name];
    if (label) return { ord: '', label };
    const m = ORDINAL.exec(String(name));
    return m ? { ord: m[1], label: m[2] } : { ord: '', label: String(name) };
  }

  //: The picker's order: a catalogue, by name, where the pack names its
  //: skins; otherwise the corpus order it always had.
  function byLabel(row) {
    const options = row.options ?? [];
    const labels = row.optionLabels;
    if (!labels) return options;
    return [...options].sort((a, b) => (labels[a] ?? a).localeCompare(labels[b] ?? b));
  }

  //: **Swipe between skins on a phone** (George, 2026-10-02): left for the
  //: next, right for the one before, in the list's order. Only a mostly
  //: sideways stroke counts, so scrolling the pane still scrolls.
  let swipeFrom = null;
  const SWIPE_PX = 50;
  function swipeStart(e) {
    if (wide || e.pointerType === 'mouse') return;
    swipeFrom = { x: e.clientX, y: e.clientY };
  }
  function swipeEnd(e, options) {
    const from = swipeFrom;
    swipeFrom = null;
    if (!from || !pickerView) return;
    const dx = e.clientX - from.x;
    const dy = e.clientY - from.y;
    if (Math.abs(dx) < SWIPE_PX || Math.abs(dx) < 2 * Math.abs(dy)) return;
    const at = options.indexOf(pickerView);
    const to = at + (dx < 0 ? 1 : -1);
    if (at >= 0 && to >= 0 && to < options.length) pickerView = options[to];
  }

  //: The one write the picker makes, from the button under the preview.
  //: **The picker stays open** on the skin just chosen, now In use (George,
  //: 2026-10-02: "once a skin is selected, stay on the selecting screen ...
  //: User can go back by himself").
  async function pick(name) {
    const row = picker;
    if (!name || String(row.value) === name) return;
    if (await write(row, name)) flash(`${row.label}: ${parts(name).label}`);
  }

  async function saveNumber() {
    const row = sheet;
    if (Number(draft) === row.value) return;
    if (await write(row, Number(draft))) flash(`${row.label}: ${shown({ ...row, value: Number(draft) })}`);
  }

  //: **A challenge that needs no keyboard** (ADR-0132; George, 2026-10-09:
  //: "add a challenge of sorts when triggering a reset ... something that
  //: could work without a keyboard"). A row with `hold` confirms only after
  //: its button is held for HOLD_MS - a finger, a mouse, or Space or Enter
  //: held down; letting go early starts over. A stray tap cannot reset.
  const HOLD_MS = 3000;
  let holdShare = $state(0);
  let holdFrame = null;
  function holdStart(event) {
    if (holdFrame !== null || busy) return;
    event?.preventDefault?.();
    const from = performance.now();
    const tick = (now) => {
      holdShare = Math.min(1, (now - from) / HOLD_MS);
      if (holdShare >= 1) {
        holdFrame = null;
        holdShare = 0;
        confirmSheet();
        return;
      }
      holdFrame = requestAnimationFrame(tick);
    };
    holdFrame = requestAnimationFrame(tick);
  }
  function holdStop() {
    if (holdFrame !== null) cancelAnimationFrame(holdFrame);
    holdFrame = null;
    holdShare = 0;
  }
  const holdKey = (down) => (event) => {
    if (event.key !== ' ' && event.key !== 'Enter') return;
    event.preventDefault();
    if (!down) holdStop();
    else if (!event.repeat) holdStart(event);
  };

  async function confirmSheet() {
    if (saving) return; // a tap during a save is not a second request
    const row = sheet;
    // A failed attempt returns to the field with the password still in it.
    if (join === 'error') {
      join = null;
      joinError = null;
      restoring = null;
      return;
    }
    if (restorePending) {
      // ADR-0083. The daemon answers before it reboots, so there is one to
      // hear - and then the device goes, which is what the row said.
      const item = restorePending;
      restorePending = null;
      restoring = item.name;
      join = 'connecting';
      await command({ name: item.name, action: 'join' }, (answer) => {
        if (!answer.ok) {
          console.warn('restore:', answer.error);
          join = 'error';
          return;
        }
        join = null;
        restoring = null;
        closeSheet();
        flash('Restoring — the device is restarting');
      });
      return;
    }
    if (joinItem) {
      doJoin(joinItem.name, draft);
      return;
    }
    if (row.type === 'share-login') {
      const item = shareLogin;
      shareLogin = null;
      browseShares(item, shareCreds.user.trim() || null, shareCreds.password || null);
      return;
    }
    if (row.type === 'share') {
      // ADR-0115: added, then mounted by the core; the list says how that went.
      const key = sheetKey;
      const { address, user, password } = share;
      await command({ name: address.trim(), action: 'add', user: user.trim() || null, password: password || null }, (answer) => {
        if (!answer.ok) {
          flash(plainly(answer.error, 'Could not add it. Check the address and try again.'));
          return;
        }
        manual = false;
        flash(`${address.trim()} added`);
        openList(key);
      });
      return;
    }
    if (row.type === 'toggle') {
      // The warned switch, confirmed (ADR-0098).
      closeSheet();
      await write(row, true);
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
      if (await write(row, option)) said(row, option);
      return;
    }
    if (!row.wired) {
      sheetKey = null;
      flash(`${row.label} cannot be changed yet`);
      return;
    }
    if (row.kind === 'hardware') {
      if (hwUrl) sheetKey = null;
      else if (!hw) loadHardware();
      else if (!hwLast) {
        if (hwStep === 'screen' && hwCheck?.showing) showScreenCheck(false).catch(() => {});
        hwError = null;
        hwStep = hwSteps[hwAt + 1];
      } else await prepareHardwareReport();
      return;
    }
    if (row.kind === 'report') {
      if (reportStep === 'what') await prepareReport();
      else if (reportStep === 'preparing') {
        if (reportReady) reportStep = 'send';
        else if (reportError) await prepareReport();
      }
      return;
    }
    if (row.type === 'action') {
      sheetKey = null;
      const result = await runSetting(row.key);
      if (!result.ok) flash(plainly(result.error ?? `HTTP ${result.status}`, `${row.label} did not run. Try again.`));
      // ADR-0132: the reset screen at once, not when /state says so.
      else if (row.key === 'factory_reset') resetting.set(true);
      return;
    }
    if (row.type === 'text') {
      if (await write(row, draft)) {
        sheetKey = null;
        // A row that takes effect at a restart restarts the device once
        // saved (ADR-0048, amended 2026-10-05) - and a new name is a new
        // address, so the toast says where the player comes back.
        if (row.restart === 'core') {
          flash(restartToast(row), 6000);
        } else if (row.restart) {
          const back = row.key === 'device_name' && draft ? ` It comes back as ${hostOf(draft)}.local.` : '';
          flash(`${row.label} saved. The device is restarting.${back}`, 12000);
        } else {
          flash(`${row.label} saved`);
        }
      }
    }
  }

  /** A row the core reads at its start (`restart: "core"`): saving it
   *  restarts the core, and the player is back within seconds. */
  function restartToast(row) {
    return `${row.label} saved. The player is restarting to use it.`;
  }

  function cancelSheet() {
    // ADR-0135: standby times still waiting to be written go now.
    if (sheet?.type === 'intervals' && ivTimer) saveIntervals();
    if (pickedTimer) savePicked();
    // A feedback step after the first goes back one step.
    if (sheet?.kind === 'hardware' && hw && hwAt > 0 && !hwUrl) {
      hwError = null;
      hwStep = hwSteps[hwAt - 1];
      return;
    }
    // The problem report's Preparing step goes back to what happened; the
    // report the player is making carries on, and is made again on Next.
    if (sheet?.kind === 'report' && reportStep === 'preparing') {
      clearTimeout(reportPoll);
      reportError = null;
      reportStep = 'what';
      return;
    }
    // A pending restore is a step inside the sheet, not the sheet: cancelling
    // it goes back to the list, the way cancelling a choice does.
    if (restorePending) {
      restorePending = null;
      return;
    }
    closeSheet();
  }

  function closeSheet() {
    // ADR-0135: standby times still waiting to be written go now.
    if (sheet?.type === 'intervals' && ivTimer) saveIntervals();
    if (pickedTimer) savePicked();
    restorePending = null;
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
    // ADR-0115's scan: from a server's shares or its login, back to the list.
    // Out of a share's folders, back to the server's shares.
    if (shareFolder && shareBrowse) {
      shareFolder = null;
      browseShares(shareBrowse.server, shareBrowse.user, shareBrowse.password);
      return;
    }
    if (shareBrowse || shareLogin) {
      const key = sheetKey;
      shareFolder = null;
      shareBrowse = null;
      shareLogin = null;
      openList(key);
      return;
    }
    // ADR-0115 decision 23: out of a drive's folders, back to the drives.
    if (usbBrowse) {
      const key = sheetKey;
      usbBrowse = null;
      openList(key);
      return;
    }
    sheetKey = null;
    choicePending = null;
    manual = false;
    joinItem = null;
    join = null;
    restoring = null;
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

{#snippet eye()}
  <button class="pw__eye" type="button" aria-label={pwShown ? 'Hide the password' : 'Show the password'} aria-pressed={pwShown} onclick={() => (pwShown = !pwShown)}>
    <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7S2 12 2 12z" /><circle cx="12" cy="12" r="3" />{#if pwShown}<path d="M4 4l16 16" />{/if}</svg>
  </button>
{/snippet}

<div class="settings" class:is-embedded={embedded} class:is-flat={flat} bind:clientWidth={width}>
  {#if !embedded && !flat}
    <div class="weave"></div>
  {/if}
  {#if !flat}<div class="veil"></div>{/if}

  <div class="frame">
    <div class="head" class:head--wide={wide}>
      {#if (wide && onback) || (!wide && drilled)}
        <button
          class="back"
          class:is-pressed={press.is('back')}
          type="button"
          aria-label="Back"
          data-dpad-back
          onpointerdown={() => press.down('back')}
          onpointerup={press.up}
          onpointercancel={press.up}
          onclick={() => press.act(back)}
        ><span></span></button>
      {/if}
      <div class="head__text">
        <div class="title-row">
          <div class="title" class:title--wide={wide}>{!wide && current ? current.label : 'Settings'}</div>
          <!-- ADR-0136: on a phone, the way to the other players - at the
               right end of the title's line (George, 2026-10-11). -->
          {#if !onPanel() && switcher}<PlayerSwitcher />{/if}
        </div>
        <!-- Shown at both widths: the panel is where someone types the
             name, so it is where the resolved host has to sit beside it. -->
        <!-- **Each fact whole** (George, 2026-10-16): on a narrow screen
             the address goes to the next line instead of being cut off. -->
        <div class="subtitle subtitle--facts">
          {#each facts as fact, i (i)}<span class="fact">{fact}</span>{/each}
        </div>
      </div>
    </div>

    {#if loadError}
      <div class="error">Settings could not be loaded. Check the connection to the player, then reload this page.</div>
    {:else}
      <div class="body" data-dpad-start>
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
            {#if current?.id === 'plugins' && catalogue?.keyed}
              <!-- ADR-0168: other authors' plugins, checked before they are
                   listed - first, above Upload a plugin, on every screen. -->
              <button class="row" class:row--apart={embedded} type="button" onclick={openCatalogue}>
                <span class="row__body">
                  <span class="row__text">
                    <span class="row__label"><span class="row__name">More plugins</span></span>
                    <span class="row__note">By other authors, checked before they are listed. Not part of Gexis Player.</span>
                  </span>
                  {#if catalogueUpdates}<span class="row__value">{catalogueUpdates === 1 ? '1 update' : `${catalogueUpdates} updates`}</span>{/if}
                  <span class="chev"></span>
                </span>
              </button>
            {/if}
            {#if current?.id === 'plugins' && !embedded}
              <!-- ADR-0106: a phone or computer only; the panel has no file
                   picker and does not offer it. **First and on its own**, in
                   no group (George, 2026-09-30), and a file icon rather than
                   a chevron: it opens the device's files, not a page. -->
              <button class="row row--upload" type="button" onclick={pickPlugin}>
                <span class="row__body">
                  <span class="row__text">
                    <span class="row__label"><span class="row__name">Upload a plugin</span></span>
                    <span class="row__note">Opens your files to choose a package (.tar.gz). Not part of Gexis Player.</span>
                  </span>
                  <svg class="upload__icon" viewBox="0 0 24 24" aria-hidden="true">
                    <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8z" />
                    <path d="M14 3v5h5" />
                    <path d="M12 17v-6m-3 3 3-3 3 3" />
                  </svg>
                </span>
              </button>
              <input class="upload__input" type="file" accept=".tar.gz,.tgz,application/gzip" bind:this={pluginFile} onchange={onPluginPicked} />
            {/if}
            {#if current?.id === 'system' && hwPrompt}
              <div class="hwprompt">
                <button class="hwprompt__go" type="button" onclick={() => { const row = rowOf('hardware_report'); if (row) openSheet(row); }}>
                  {hwPrompt}
                </button>
                <button class="hwprompt__x" type="button" aria-label="Do not ask again" onclick={dismissHardwarePrompt}>×</button>
              </div>
            {/if}
            {#each rows as r, i (r.key ?? `group-${i}`)}
              {#if r.type === 'group'}
                <div class="subhead">
                  <span class="subhead__dot" style:background={r.accent}></span>
                  <span class="subhead__label" style:color={r.accent}>{r.label}</span>
                  <span class="subhead__rule"></span>
                  {#if r.indicator}
                    <!-- ADR-0129 as amended: what the service is doing, the
                         core's reading, above the rows its keys go in. -->
                    <span class="ind ind--{r.indicator.tone}">
                      <span class="ind__mark" aria-hidden="true">{r.indicator.tone === 'ok' ? '✓' : r.indicator.tone === 'bad' ? '✕' : ''}</span>
                      {r.indicator.text}
                    </span>
                  {/if}
                </div>
              {:else if r.key === 'screen'}
                <!-- **The display in use, with Change** (George, 2026-10-14:
                     "Let's go back to two tiles. One displaying the current
                     display used by the pi together with the change button.
                     And another one for switching between ports"). Change
                     opens the list at its makers: opened inside the current
                     maker, a TV's "Other screen" held one size, and it read
                     as a button that did nothing. -->
                {@const port = rowOf('screen_port') ?? rowOf('screen_port_info')}
                {@const portLine = port?.key === 'screen_port' ? port.optionNotes?.[port.value] : port?.value}
                {@const named = String(r.value ?? '').startsWith('Other screen/')
                  ? (String(portLine ?? '').replace(/^(HDMI \d+|DSI( \d+)?) · /, '').split(' · ')[0] || String(r.value).replace('/', ' '))
                  : String(r.value ?? '').replace('/', ' ')}
                <div class="row row--tile">
                  <span class="row__body">
                    <span class="row__text">
                      <span class="row__label"><span class="row__name">{r.label}</span></span>
                      <span class="row__value row__value--tile">{named || '—'}</span>
                      {#if r.note}<span class="row__note">{r.note}</span>{/if}
                    </span>
                    <button type="button" class="tile__btn" onclick={() => { openSheet(r); region = null; }}>Change</button>
                  </span>
                </div>
              {:else if r.key === 'screen_port'}
                <!-- **What is on each port, in the tile** (George,
                     2026-10-14: "The screen port tile should display also
                     the info on what is connected directly in the tile
                     before opening the modal"): the lines the picker shows
                     under each port, the port in use first. -->
                {@const ports = [r.value, ...(r.options ?? []).filter((o) => o !== r.value)]}
                <div class="row row--tile">
                  <span class="row__body">
                    <span class="row__text">
                      <span class="row__label"><span class="row__name">{r.label}</span></span>
                      <span class="row__value row__value--tile">{r.value || '—'}</span>
                      {#each ports as option (option)}
                        {#if r.optionNotes?.[option]}
                          <span class="row__note">{option} · {r.optionNotes[option]}</span>
                        {/if}
                      {/each}
                      {#if r.note}<span class="row__note">{r.note}</span>{/if}
                    </span>
                    <button type="button" class="tile__btn" onclick={() => openSheet(r)}>Change</button>
                  </span>
                </div>
              {:else if r.key === 'software_update'}
                <!-- ADR-0110 §2 as amended (George, 2026-10-01): the
                     Software update tile - what the updater found and when,
                     the waiting release's notes, and one button. Release,
                     above it, only says what this device runs. -->
                <!-- *Update…* checks again before it offers anything (George,
                     2026-10-13): the waiting release is last night's check's,
                     and the channel may have moved since - guestpi offered
                     0.11.0 with its notes, then installed 0.12.0. -->
                {@const waiting = $update?.state === 'available'}
                <div class="row row--tile">
                  <span class="row__body">
                    <span class="row__text">
                      <span class="row__label"><span class="row__name">{r.label}</span></span>
                      <span class="row__value row__value--tile">{r.value}</span>
                      <!-- ADR-0116: only while it waits; once installed, its
                           notes are under Change logs. -->
                      {#if ($update?.whats_new || $update?.whats_new_all?.length) && $update?.state === 'available'}
                        <!-- ADR-0110 amended 2026-10-07: every release it skips. -->
                        <span class="row__note">{($update.whats_new_all?.filter((e) => e?.release).length ?? 0) > 1
                          ? `What's new since ${$update.installed}`
                          : `What's new in ${$update.release}`}</span>
                        <span class="tile__notes"><ReleaseHistory update={$update} /></span>
                      {:else if r.note}<span class="row__note">{r.note}</span>{/if}
                    </span>
                    <button
                      type="button"
                      class="tile__btn"
                      class:tile__btn--go={waiting}
                      class:tile__btn--busy={$update?.active}
                      onclick={() => (updateModal = $update?.active ? 'progress' : 'check')}
                    >{$update?.active ? 'Updating…' : waiting ? 'Update…' : 'Check for updates'}</button>
                  </span>
                </div>
              {:else if r.key === 'hardware_report' && hwKept}
                <!-- ADR-0126 amended 2026-10-11 (George chose the row): the
                     last feedback, with its two buttons. -->
                <div class="row row--tile">
                  <span class="row__body row__body--stack">
                    <button type="button" class="row__text hwkept__open" onclick={() => tap(r)}>
                      <span class="row__label"><span class="row__name">{r.label}</span></span>
                      <span class="row__value row__value--tile">{hardwareKeptLine(hwKept)}</span>
                      <span class="row__note">{[hwKept.board, hwKept.screen].filter(Boolean).join(' · ')}</span>
                    </button>
                    {#if onPanel()}
                      <!-- GitHub opens on a phone or computer, not here. -->
                      <span class="row__note">Send it again from Settings on a phone or computer.</span>
                    {:else}
                      <span class="hwkept__actions">
                        <a class="tile__btn tile__btn--go hwkept__btn" href={hwKept.url} target="_blank" rel="noopener">Send again ↗</a>
                        <button type="button" class="tile__btn" onclick={() => startHardwareOver(r)}>Start over</button>
                      </span>
                    {/if}
                  </span>
                </div>
              {:else if r.key === 'sweep_all'}
                <!-- George, 2026-10-06: the Lyrion Client's portraits and
                     covers in one tile - what the last run found inside it,
                     kept as its history, and one button that starts again
                     from scratch. -->
                {@const running = String(r.value ?? '').startsWith('Running')}
                <div class="row row--tile">
                  <span class="row__body">
                    <span class="row__text">
                      <span class="row__label"><span class="row__name">{r.label}</span></span>
                      <span class="row__value row__value--tile">{r.value ?? 'Never run'}</span>
                      {#if r.note}<span class="row__note">{r.note}</span>{/if}
                    </span>
                    <button
                      type="button"
                      class="tile__btn"
                      class:tile__btn--busy={running}
                      disabled={running}
                      onclick={async () => {
                        const result = await runSetting(r.key);
                        if (!result.ok) flash(plainly(result.error ?? `HTTP ${result.status}`, `${r.label} did not start. Try again.`));
                      }}
                    >{running ? 'Running…' : r.label}</button>
                  </span>
                </div>
              {:else}
                <!-- A readonly row takes no tap and draws no chevron: there
                     is nothing to change, and a chevron promises a sheet that
                     only repeats the value already on the row. `disabled`
                     rather than a different element, so the row keeps its
                     layout and its 44px height. -->
                {#if r.kind === 'share'}
                  <!-- George, 2026-10-18: the shares added in a tile of
                       their own, each with its Forget; adding is the tile
                       under it, which says so. -->
                  <div class="row row--readonly row--static">
                    <span class="row__body">
                      <span class="row__text">
                        <span class="row__label"><span class="row__name">{r.label}</span></span>
                        {#if r.items?.length}
                          <span class="shares">
                            {#each r.items as s (s.address ?? s.name)}
                              <span class="shares__one">
                                <span class="shares__text">
                                  <span class="shares__name">{s.name}</span>
                                  {#if s.meta}<span class="item__meta">{s.meta}</span>{/if}
                                </span>
                                <span
                                  class="forget"
                                  role="button"
                                  tabindex="0"
                                  onclick={(e) => { e.stopPropagation(); forgetShare(r, s); }}
                                  onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); forgetShare(r, s); } }}
                                >Forget</span>
                              </span>
                            {/each}
                          </span>
                        {:else}
                          <span class="row__note">None added yet.</span>
                        {/if}
                      </span>
                    </span>
                  </div>
                {/if}
                <button
                  class="row"
                  class:row--add={r.kind === 'share'}
                  class:row--danger={r.danger}
                  class:row--readonly={(r.type === 'readonly' && r.kind !== 'equaliser') || toggleBlocked(r)}
                  class:row--dl={!!r.component}
                  type="button"
                  disabled={(r.type === 'readonly' && !r.uploaded && r.kind !== 'equaliser') || (toggleBlocked(r) && !r.uploaded)}
                  data-unwired={r.wired ? undefined : 'settings'}
                  onclick={() => tap(r)}
                >
                  <span class="row__body">
                    <span class="row__text">
                      <span class="row__label">
                        <span class="row__name">{r.kind === 'share' ? 'Add share' : r.label}</span>
                        <!-- ADR-0167: a few words a plugin puts beside its name
                             (AirPlay's Limited testing), in the Tested tag's look. -->
                        {#if r.tag}<span class="row__tag">{r.tag}</span>{/if}
                        {#if pending(r)}<span class="dot dot--sm"></span>{/if}
                      </span>
                      <!-- A plugin's version, and the program it runs (George, 2026-10-12). -->
                      {#if r.version}<span class="row__note row__version">{r.version}</span>{/if}
                      {#if toggleBlocked(r)}<span class="row__note">{r.unavailable.true}.</span>
                      {:else if r.kind === 'share'}<span class="row__note">Find a share on your network, or add one by its address.</span>
                      {:else if r.note && !opensItsOwn(r)}<span class="row__note"><NoteText text={r.note} links={false} /></span>{/if}
                      <!-- A row that opens its own sheet keeps its note for the
                           sheet; `summary` is the one line it shows on the tile
                           (George, 2026-10-18: Personalise). -->
                      {#if r.summary && opensItsOwn(r)}<span class="row__note">{r.summary}</span>{/if}
                      {#if r.status?.error}<span class="row__note row__note--failed">{r.status.error}</span>{/if}
                      {#if r.status?.text && r.again}
                        <!-- ADR-0119: a row its plugin reports done offers to do it
                             again - the row is the button; this says so. -->
                        <span class="row__again">{r.again}</span>
                      {/if}
                      {#if r.uploaded && (r.key.endsWith('.missing') || !r.value) && (!embedded || r.catalogue) && !arriving(r)}
                        <!-- ADR-0106: an uploaded plugin is removed from here,
                             switched off first. One from the catalogue on every
                             screen: it is installed again from there. -->
                        <span
                          class="dl__retry"
                          role="button"
                          tabindex="0"
                          onclick={(e) => { e.stopPropagation(); uninstallPlugin(r); }}
                          onkeydown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); uninstallPlugin(r); } }}
                        >Remove</span>
                      {/if}
                      {#if r.uploaded}
                        <!-- ADR-0168: its download from the catalogue while one
                             runs - an update, or a restore's - and Update when a
                             newer version is listed (decision 4). -->
                        {@const id = pluginIdOf(r)}
                        {@const job = jobOf(id)}
                        {@const listed = r.catalogue ? listedOf(id) : null}
                        {@const said = saidOnRow(r, id)}
                        {#if job || said}
                          <span class="row__note dl__line" class:dl--failed={listedFailed(null, job, said)}>
                            {listedLine(null, job, said)}{#if listedDetail(job)}<span class="dl__sub"> · {listedDetail(job)}</span>{/if}
                          </span>
                        {/if}
                        {#if listed?.state === 'update' && (!job || job.phase === 'failed')}
                          <span
                            class="dl__retry dl__go"
                            role="button"
                            tabindex="0"
                            onclick={(e) => { e.stopPropagation(); installListed(listed, { asked: !!job }); }}
                            onkeydown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); installListed(listed, { asked: !!job }); } }}
                          >{job ? 'Retry' : `Update to ${listed.version}`}</span>
                        {/if}
                      {/if}
                      {#if r.component}
                        <!-- ADR-0100 as amended: the plugin's download, inside
                             its own row (George: "part of the pill itself
                             otherwise it floats"). -->
                        {@const c = $components[r.component] ?? { state: 'absent' }}
                        <span class="row__note dl__line" class:dl--failed={c.state === 'failed'}>
                          {downloadLine(c)}{#if downloadDetail(c)}<span class="dl__sub"> · {downloadDetail(c)}</span>{/if}
                        </span>
                        {#if c.state === 'installed' && !r.value && rowOf(r.key.replace(/\.enabled$/, '.remove'))}
                          <!-- ADR-0100, amended 2026-09-28: off stops it; Remove
                               deletes the download, after asking. -->
                          <span
                            class="dl__retry"
                            role="button"
                            tabindex="0"
                            onclick={(e) => { e.stopPropagation(); openSheet(rowOf(r.key.replace(/\.enabled$/, '.remove'))); }}
                            onkeydown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); openSheet(rowOf(r.key.replace(/\.enabled$/, '.remove'))); } }}
                          >Remove</span>
                        {/if}
                        {#if c.state === 'failed'}
                          <span
                            class="dl__retry"
                            role="button"
                            tabindex="0"
                            onclick={(e) => { e.stopPropagation(); runSetting(r.key.replace(/\.enabled$/, '.download')); }}
                            onkeydown={(e) => { if (e.key === 'Enter') { e.stopPropagation(); runSetting(r.key.replace(/\.enabled$/, '.download')); } }}
                          >Retry</span>
                        {/if}
                      {/if}
                    </span>
                    {#if r.status?.text}
                      <!-- ADR-0119: what the row's plugin says it is (Plexamp:
                           "Claimed"), in place of the value - a spent claim
                           token's dots say nothing. -->
                      <span class="row__value row__value--done"><span class="row__tick" aria-hidden="true">✓</span> {r.status.text}</span>
                    {:else if r.type !== 'toggle' && !(r.type === 'readonly' && r.links?.length && r.value == null) && shown(r)}
                      <span class="row__value" class:is-pending={pending(r)}>{shown(r)}</span>
                    {/if}
                    {#if r.kind === 'usb-folder' && r.items?.length}
                      <!-- ADR-0115: each share by its name, with its Forget
                           (George, 2026-10-03). Spans, not buttons: the row
                           is the button that opens the sheet. -->
                      <span class="shares">
                        {#each r.items as s (s.address ?? s.drive ?? s.name)}
                          <span class="shares__one">
                            <span class="shares__text">
                              <span class="shares__name">{s.name}</span>
                              {#if s.meta}<span class="item__meta">{s.meta}</span>{/if}
                            </span>
                            {#if s.address}
                            <!-- A USB drive not added yet has nothing to
                                 remove: tapping the row chooses its folders. -->
                            <span
                              class="forget"
                              role="button"
                              tabindex="0"
                              onclick={(e) => { e.stopPropagation(); forgetShare(r, s); }}
                              onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); forgetShare(r, s); } }}
                            >{r.kind === 'usb-folder' ? 'Remove' : 'Forget'}</span>
                            {/if}
                          </span>
                        {/each}
                      </span>
                    {/if}
                    {#if r.component && ['preparing', 'downloading', 'retrying', 'verifying', 'installing'].includes(($components[r.component] ?? {}).state)}
                      {@const c = $components[r.component]}
                      <span class="dl__bar" class:dl__bar--busy={!downloadShare(c)}>
                        <span style:width={`${Math.round((downloadShare(c) ?? 0) * 100)}%`}></span>
                      </span>
                    {/if}
                    {#if r.uploaded && arriving(r)}
                      {@const job = jobOf(pluginIdOf(r))}
                      <span class="dl__bar" class:dl__bar--busy={job.phase !== 'downloading' || !job.total}>
                        <span style:width={`${Math.round((job.total ? job.done / job.total : 0) * 100)}%`}></span>
                      </span>
                    {/if}
                    {#if r.links?.length && !onPanel()}
                      <!-- ADR-0150: where the rest is - on the phone only; on
                           the panel a store or another page leads nowhere. -->
                      <span class="links">
                        {#each r.links as l (l.url)}
                          <a class="links__one" href={l.url} target="_blank" rel="noopener" onclick={(e) => e.stopPropagation()}>{l.label} ↗</a>
                        {/each}
                      </span>
                    {/if}
                    {#if r.progress != null || r.busy}
                      <!-- ADR-0115 decision 28: how far Lyrion has read, or
                           that it is working with no count to give. -->
                      <span class="dl__bar" class:dl__bar--busy={r.progress == null}>
                        <span style:width={`${Math.round((r.progress ?? 0) * 100)}%`}></span>
                      </span>
                    {/if}
                    {#if r.type === 'toggle'}
                      <span class="toggle" class:is-on={toggleOn(r)}><span></span></span>
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
  {#if docKey}
    {@const docRow = rowOf(docKey)}
    <div class="picker">
      {#if !flat}
        <div class="weave"></div>
        <div class="veil"></div>
      {/if}
      <div class="picker__head" class:head--wide={wide}>
        <button
          class="back"
          class:is-pressed={press.is('doc-back')}
          type="button"
          aria-label="Back"
          data-dpad-back
          onpointerdown={() => press.down('doc-back')}
          onpointerup={press.up}
          onpointercancel={press.up}
          onclick={() => press.act(() => (docKey = null))}
        ><span></span></button>
        <div class="head__text">
          <div class="title" class:title--wide={wide}>{docPage?.title ?? docRow?.label}</div>
          {#if docPage?.updated}<div class="subtitle">Updated {docPage.updated}</div>{/if}
        </div>
      </div>
      <div class="picker__body">
        <div class="doc" class:doc--wide={wide} data-noscrollbar>
          {#if docError}
            <p class="doc__p">{docError}</p>
          {:else if !docPage}
            <p class="doc__p">Loading…</p>
          {:else}
            {#each docPage.sections as section, i (i)}
              {#if section.heading}<h2 class="doc__h">{section.heading}</h2>{/if}
              {#each section.paragraphs as paragraph, j (j)}
                <p class="doc__p">{paragraph}</p>
              {/each}
              <!-- ADR-0116: a release's notes, drawn as the update draws them. -->
              {#if section.notes}<div class="doc__notes"><ReleaseNotes text={section.notes} /></div>{/if}
              {#if section.url}<p class="doc__p doc__muted doc__url">{section.url}</p>{/if}
              {#if section.entries}
                <ul class="doc__list">
                  {#each section.entries as entry, k (k)}
                    <li class="doc__entry">
                      <div class="doc__name">{entry.name}{#if entry.licence}<span class="doc__licence">{entry.licence}</span>{/if}</div>
                      {#if entry.role}<div class="doc__line">{entry.role}</div>{/if}
                      {#if entry.author}<div class="doc__line doc__muted">{entry.author}</div>{/if}
                      {#if entry.url}<div class="doc__line doc__muted doc__url">{entry.url}</div>{/if}
                    </li>
                  {/each}
                </ul>
              {/if}
            {/each}
          {/if}
        </div>
      </div>
    </div>
  {/if}

  {#if catalogueOpen}
    <!-- ADR-0168 decision 7: More plugins, from the Plugins page's own parts
         - a tile per listed plugin, its download inside it, with Retry. -->
    <div class="picker" data-dpad-layer>
      {#if !flat}
        <div class="weave"></div>
        <div class="veil"></div>
      {/if}
      <div class="picker__head" class:head--wide={wide}>
        <button
          class="back"
          class:is-pressed={press.is('catalogue-back')}
          type="button"
          aria-label="Back"
          data-dpad-back
          onpointerdown={() => press.down('catalogue-back')}
          onpointerup={press.up}
          onpointercancel={press.up}
          onclick={() => press.act(() => (catalogueOpen = false))}
        ><span></span></button>
        <div class="head__text">
          <div class="title" class:title--wide={wide}>More plugins</div>
          {#if catalogueSubtitle}<div class="subtitle">{catalogueSubtitle}</div>{/if}
        </div>
      </div>
      <div class="picker__body">
        <div class="list" class:list--wide={wide} data-noscrollbar data-dpad-start>
          {#if catalogue?.available && catalogue.error && !catalogueReading}
            <p class="listed__note">The catalogue could not be read again just now. This is the one read on {daySaid(catalogue.checked)}.</p>
          {/if}
          {#if !catalogue?.available && !catalogueReading}
            <div class="row row--tile">
              <span class="row__body">
                <span class="row__text">
                  <span class="row__label"><span class="row__name">The catalogue could not be read</span></span>
                  <span class="row__note">Check that the player is connected to the internet, then try again.</span>
                </span>
                <button type="button" class="tile__btn" onclick={openCatalogue}>Try again</button>
              </span>
            </div>
          {:else if catalogue?.available && !catalogue.plugins.length}
            <p class="listed__note">Nothing is listed for this player yet.</p>
          {/if}
          {#each catalogue?.available ? catalogue.plugins : [] as p (p.id)}
            {@const job = jobOf(p.id)}
            {@const said = catalogueSaid[p.id]}
            {@const moving = job && job.phase !== 'failed'}
            {@const offered = !moving && !said?.done && (p.state === 'available' || p.state === 'update')}
            <div class="row row--tile listed">
              <span class="row__body">
                <span class="row__text">
                  <span class="row__label"><span class="row__name">{p.name}</span></span>
                  {#if p.summary}<span class="row__note">{p.summary}</span>{/if}
                  <!-- Each fact whole, as the title's (a licence broke at its hyphen). -->
                  <span class="row__note row__version listed__facts">
                    {#each listedFacts(p) as fact, i (i)}<span class="listed__fact">{i ? `· ${fact}` : fact}</span>{/each}
                  </span>
                  {#if p.source && onPanel()}
                    <!-- Shown, not followed: the panel has nowhere to go. -->
                    <span class="row__note row__version listed__source">{p.source.replace(/^https:\/\//, '')}</span>
                  {/if}
                  <span class="row__note dl__line" class:dl--failed={listedFailed(p, job, said)}>
                    {listedLine(p, job, said)}{#if listedDetail(job)}<span class="dl__sub"> · {listedDetail(job)}</span>{/if}
                  </span>
                </span>
                {#if offered || job?.phase === 'failed' || (p.source && !onPanel())}
                  <span class="listed__actions">
                    {#if job?.phase === 'failed'}
                      <button type="button" class="tile__btn tile__btn--go" onclick={() => installListed(p, { asked: true })}>Retry</button>
                    {:else if offered}
                      <button type="button" class="tile__btn tile__btn--go" onclick={() => installListed(p)}>
                        {p.state === 'update' ? `Update to ${p.version}` : 'Install'}
                      </button>
                    {/if}
                    {#if p.source && !onPanel()}
                      <a class="tile__btn listed__link" href={p.source} target="_blank" rel="noopener">Source code ↗</a>
                    {/if}
                  </span>
                {/if}
              </span>
              {#if moving}
                <span class="dl__bar" class:dl__bar--busy={job.phase !== 'downloading' || !job.total}>
                  <span style:width={`${Math.round((job.total ? job.done / job.total : 0) * 100)}%`}></span>
                </span>
              {/if}
            </div>
          {/each}
        </div>
      </div>
    </div>
  {/if}

  {#if eqPage}
    <Equaliser surface={!onPanel() ? 'phone' : screen.family === 'bar' ? 'bar' : 'panel'} {flat} onback={() => (eqPage = false)} />
  {/if}

  {#if picker}
    {@const options = byLabel(picker)}
    {@const inUse = picker.value == null ? null : String(picker.value)}
    {@const viewing = pickerView ?? (wide ? inUse : null)}
    <div class="picker">
      <!-- Its own ground, embedded or not: it covers the rows, so the
           panel's weave behind the app cannot reach it. -->
      {#if !flat}
        <div class="weave"></div>
        <div class="veil"></div>
      {/if}
      <div class="picker__head" class:head--wide={wide}>
        <button
          class="back"
          class:is-pressed={press.is('picker-back')}
          type="button"
          aria-label="Back"
          data-dpad-back
          onpointerdown={() => press.down('picker-back')}
          onpointerup={press.up}
          onpointercancel={press.up}
          onclick={() => press.act(() => (pickerKey = null))}
        ><span></span></button>
        <div class="head__text">
          <div class="title" class:title--wide={wide}>{picker.label}</div>
          <div class="subtitle">{options.length} skins</div>
          {#if picker.note}<div class="head__note">{picker.note}</div>{/if}
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
              {#if p.ord}<span class="skin__ord">{p.ord}</span>{/if}
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
          <div
            class="pane"
            class:pane--over={!wide}
            onpointerdown={(e) => swipeStart(e)}
            onpointerup={(e) => swipeEnd(e, options)}
            onpointercancel={() => (swipeFrom = null)}
          >
            {#if !wide}
              <div class="pane__back">
                <button
                  class="back back--small"
                  class:is-pressed={press.is('view-back')}
                  type="button"
                  aria-label="Back to list"
                  data-dpad-back
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
              <!-- ADR-0050, amended 2026-10-03: 960 px wide, made once on the
                   player - the whole picture was up to 3.7 MB. -->
              <img src={`/skins/${encodeURIComponent(viewing)}/preview?w=960`} alt="" />
            </div>
            <div class="pane__text">
              <div class="pane__name">{p.label}</div>
              <div class="pane__meta">{isCurrent ? 'In use' : 'Not in use'}</div>
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
    <div class="sheet" class:sheet--full={sheetFull} class:sheet--fit={sheet.type === 'action' && !sheet.kind && !restorePending}
      class:sheet--steps={sheet.kind === 'hardware' || sheet.kind === 'report'} role="dialog" aria-label={sheet.label}
      ondpadback={(event) => { event.preventDefault(); closeSheet(); }}>
      <div class="sheet__head">
        <div class="sheet__title">{sheet.grouped && region !== null ? region : sheet.label}</div>
        {#if sheet.note && !joinItem && sheet.kind !== 'cable'}<div class="sheet__note"><NoteText text={sheet.note} /></div>{/if}
        {#if joinItem && sheet.note}<div class="sheet__note"><NoteText text={sheet.note} /></div>{/if}
      </div>

      {#if sheet.kind === 'hardware'}
        <div class="report report--scroll">
          {#if onPanel()}
            <p class="report__text">
              This feedback opens GitHub, which the screen cannot. Open Settings on a phone or computer on the same
              network, at <span class="report__addr">{device.hostname ? `${device.hostname}.local` : device.address}</span>,
              then System → Hardware feedback.
            </p>
          {:else if hwUrl}
            <!-- ADR-0138 §3: the Send step the problem report ends on too. -->
            <p class="report__step">Send</p>
            <SendStep githubUrl={hwUrl} fileHref="/hardware-report/file" fileName={`gexis-hardware-${new Date().toISOString().slice(0, 10)}.txt`}
              fileKind="the feedback" email={REPORT_EMAIL}
              githubSays="Filled in with everything: your answers, your notes and what the player read." />
            <p class="report__text report__text--quiet">The player keeps it: System → Hardware feedback can send it again.</p>
          {:else if hw === null && !hwError}
            <p class="report__text report__text--quiet">Reading the hardware…</p>
          {:else if hw}
            <p class="report__step">Step {hwAt + 1} of {hwSteps.length} · {HW_STEP_NAMES[hwStep]}</p>
            {#if hwStep === 'screen'}
              <p class="report__text"><span class="report__addr">{hw.screen ?? 'Screen'}</span></p>
              <div class="hwq">
                <span class="report__label">Screen check</span>
                <p class="report__text report__text--quiet">
                  A test pattern on the player's screen: a coloured line along each edge{#if hw.touch}, then four
                  circles to tap in turn{/if}.
                </p>
                {#if hwCheckLines}
                  <ul class="hwq__tones">{#each hwCheckLines as t (t)}<li>{t}</li>{/each}</ul>
                {/if}
                <div class="hwq__options">
                  <button type="button" class="hwq__option" onclick={toggleScreenCheck}>
                    {hwCheck?.showing ? 'Take it down' : hwCheck ? 'Show it again' : 'Show the test pattern'}
                  </button>
                </div>
              </div>
            {:else if hwStep === 'sound'}
              <p class="report__text">
                <span class="report__addr">{hw.board ?? 'No sound card'}</span>{#if hw.state} · {hw.state}{/if}
              </p>
              <div class="hwq">
                <span class="report__label">Sound check</span>
                <p class="report__text report__text--quiet">
                  A short tone at 44.1, 96 and 192 kHz, at the current volume. Turn the amplifier down first.
                </p>
                {#if hwTones}
                  <ul class="hwq__tones">{#each hwTones as t (t)}<li>{t}</li>{/each}</ul>
                {/if}
                <div class="hwq__options">
                  <button type="button" class="hwq__option" disabled={hwTonesBusy} onclick={playHardwareTones}>
                    {hwTonesBusy ? 'Playing…' : hwTones ? 'Play them again' : 'Play test tones'}
                  </button>
                </div>
              </div>
            {/if}
            {#each hwStep === 'notes' ? [] : HW_QUESTIONS.filter((x) => hwStep === 'screen' ? (x.screen || (x.touch && hw.touch)) : !(x.screen || x.touch)) as item (item.id)}
              <div class="hwq">
                <span class="report__label">{item.q}</span>
                <div class="hwq__options">
                  {#each item.options as option (option)}
                    <button type="button" class="hwq__option" class:is-on={hwAnswers[item.id] === option}
                      onclick={() => (hwAnswers = { ...hwAnswers, [item.id]: option })}>{option}</button>
                  {/each}
                </div>
              </div>
            {/each}
            {#if hwStep === 'notes'}
            <label class="report__label" for="hw-notes">Your notes (optional)</label>
            <p class="report__text report__text--quiet">What worked, what did not, how it sounds or looks. Leave it empty if the answers say it all.</p>
            <textarea id="hw-notes" class="report__note report__note--tall" rows="7" maxlength="2000" bind:value={hwNotes}></textarea>
            <details class="hwq__facts"><summary>What the player adds for you</summary>
              <p class="report__text report__text--quiet">Read from the hardware and put in the feedback, so you need not type it. Nothing about you, and no serial numbers.</p>
              <pre>{hw.text}</pre></details>
            {/if}
          {/if}
          {#if hwError}<p class="report__text report__text--warn">{hwError}</p>{/if}
        </div>
      {/if}

      {#if sheet.kind === 'cable'}
        <!-- ADR-0123: the cable's own sheet, with its own Save. -->
        <CableSheet />
      {/if}
      {#if sheet.kind === 'report'}
        <div class="report report--scroll">
          {#if onPanel()}
            <p class="report__text">
              The screen has nowhere to save a file. Open Settings on a phone or computer on the same
              network, at <span class="report__addr">{device.hostname ? `${device.hostname}.local` : device.address}</span>,
              then System → Problem report.
            </p>
          {:else}
            <p class="report__step">Step {['what', 'preparing', 'send'].indexOf(reportStep) + 1} of 3 · {REPORT_STEP_NAMES[reportStep]}</p>
            {#if reportStep === 'what'}
              <textarea id="report-note" class="report__note report__note--tall" rows="6" maxlength="4000" bind:value={reportNote}
                aria-label="What happened?"
                placeholder="What you did, what you expected, what happened instead"></textarea>
              <div class="hwq">
                <span class="report__label">How often does it happen?</span>
                <div class="hwq__options">
                  {#each REPORT_OFTEN as option (option)}
                    <button type="button" class="hwq__option" class:is-on={reportOften === option}
                      onclick={() => (reportOften = reportOften === option ? null : option)}>{option}</button>
                  {/each}
                </div>
              </div>
            {:else if reportStep === 'preparing'}
              {@const steps = reportStatus?.steps ?? []}
              {@const at = steps.findIndex((x) => !x.done)}
              <ul class="check">
                {#each steps as item, i (item.id)}
                  <li class="check__item" class:is-done={item.done} class:is-now={i === at && !reportError}>
                    <span class="check__mark" aria-hidden="true">{item.done ? '✓' : i === at && !reportError ? '' : '○'}</span>
                    <span class="check__text">
                      <span class="check__label">{item.label}</span>
                      {#if item.detail}<span class="check__detail">{item.detail}</span>{/if}
                    </span>
                  </li>
                {/each}
              </ul>
              {#if !reportStatus && !reportError}<p class="report__text report__text--quiet">Starting…</p>{/if}
              {#if reportReady}
                <p class="report__text">
                  Ready: <span class="report__addr">{reportStatus.name}</span>, {sizeSaid(reportStatus.size)}. Nothing has left
                  the player.
                </p>
                <details class="hwq__facts"><summary>What is in it</summary>
                  <ul class="check__files">
                    {#each reportStatus.files as f (f.name)}<li><span>{f.name}</span><span>{sizeSaid(f.size)}</span></li>{/each}
                  </ul>
                </details>
              {/if}
            {:else}
              <SendStep githubUrl={reportIssue} fileHref="/report/file" fileName={reportStatus?.name ?? 'gexis-report.zip'}
                fileKind="the report" email={REPORT_EMAIL} attach
                githubSays="Filled in with what happened, how often, the version, what was taken out and the log's last errors and warnings." />
            {/if}
            {#if reportError}<p class="report__text report__text--warn">{reportError}</p>{/if}
          {/if}
        </div>
      {/if}

      <!-- ADR-0044 §2, both forms. A **string** warns about the row and is
           shown the whole time the sheet is open, because what it describes
           happens whatever is typed (`device_name`); an **object** warns
           about one option and waits until that option is picked. -->
      {#if typeof sheet.warn === 'string' && (!warnsOnChoice(sheet) || choicePending !== null)}
        <div class="warn">
          <span class="warn__mark">!</span>
          <span class="warn__text">{sheet.warn}</span>
        </div>
      {:else if choicePending !== null && sheet.warn?.[choicePending]}
        <div class="warn">
          <span class="warn__mark">!</span>
          <span class="warn__text">{sheet.warn[choicePending]}</span>
        </div>
      {:else if restorePending}
        <!-- ADR-0083: say which one, and what it costs. A confirm that does
             not name what it is confirming is a confirm nobody reads. -->
        <div class="warn">
          <span class="warn__mark">!</span>
          <span class="warn__text"
            >Restoring <b>{restorePending.name}</b> replaces every setting, the
            library's pictures and the paired devices with what this backup
            holds, then restarts the device. Nothing it replaces can be got
            back.</span
          >
        </div>
      {/if}

      <!-- A grouped choice, level one: the regions. ADR-0044 §4 - two short
           lists rather than one of several hundred. -->
      {#if sheet.grouped && region === null}
        <div class="options" data-noscrollbar>
          {#each loose as option (option)}
            {@const selected = choicePending !== null ? choicePending === option : (choiceShown ?? String(sheet.value)) === option}
            <button class="option" class:is-selected={selected} type="button" onclick={() => choose(option)}>
              <span class="radio"><span></span></span>
              <span class="option__label">{option}</span>
            </button>
          {/each}
          {#each regions as name (name)}
            {@const selected = String(sheet.value ?? '').split('/')[0] === name}
            <button class="option" class:is-selected={selected} type="button" onclick={() => chooseRegion(name)}>
              <span class="radio"><span></span></span>
              <span class="option__label">{name.replace(/_/g, ' ')}</span>
              {#if sheet.optionTags}
                <!-- Round 2's Attached screen: how many models a maker has. -->
                {@const n = grouped.filter((o) => o.split('/')[0] === name).length}
                <span class="option__meta">{n} {n === 1 ? 'model' : 'models'}</span>
              {/if}
              <span class="chev"></span>
            </button>
          {/each}
        </div>
      {:else if sheet.grouped}
        <div class="options" data-noscrollbar>
          {#each places as option (option)}
            {@const selected = choicePending !== null ? choicePending === option : (choiceShown ?? String(sheet.value)) === option}
            <button class="option" class:is-selected={selected} type="button" onclick={() => choose(option)}>
              <span class="radio"><span></span></span>
              <span class="option__label">{placeLabel(option)}</span>
              {#if sheet.optionTags?.[option]}
                <!-- George, 2026-10-18: Tested beside a model tested here or
                     reported working by owners; nothing beside the rest. -->
                <span class="option__tag" class:option__tag--tested={sheet.optionTags[option] === 'Tested'}>{sheet.optionTags[option]}</span>
              {/if}
              <!-- A problem owners reported: a line under it, not a word. -->
              {#if sheet.optionProblems?.[option]}<span class="option__why">{sheet.optionProblems[option]}</span>{/if}
            </button>
          {/each}
        </div>
      {:else if sheet.type === 'intervals'}
        <div class="iv" data-noscrollbar>
          {#each ivs as iv, i (i)}
            <div class="iv__item">
              <button class="iv__remove" type="button" aria-label="Remove this time"
                onclick={() => removeInterval(i)}>
                <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7l10 10M17 7L7 17" /></svg>
              </button>
              <div class="iv__times">
                {#each [['from', 'From'], ['until', 'Until']] as [which, label] (which)}
                  {@const open = picking?.i === i && picking?.which === which}
                  <span class="iv__pair">
                    <span class="iv__label">{label}</span>
                    <button class="iv__time" class:open type="button" aria-expanded={open}
                      aria-label="{label} {iv[which]}"
                      onclick={() => (picking = open ? null : { i, which })}>{iv[which]}</button>
                  </span>
                {/each}
              </div>
              {#if picking?.i === i}
                {@const [hh, mm] = iv[picking.which].split(':')}
                <div class="iv__picker">
                  <div class="iv__grid iv__grid--hours">
                    {#each HOURS as h (h)}
                      <button class="iv__cell" class:on={h === hh} type="button"
                        onclick={() => setTime(i, picking.which, 'h', h)}>{h}</button>
                    {/each}
                  </div>
                  <div class="iv__grid iv__grid--quarters">
                    {#each QUARTERS as m (m)}
                      <button class="iv__cell" class:on={m === mm} type="button"
                        onclick={() => setTime(i, picking.which, 'm', m)}>:{m}</button>
                    {/each}
                  </div>
                </div>
              {/if}
              <div class="iv__days">
                {#each DAYS as d (d)}
                  <button class="iv__day" class:on={iv.days.includes(d)} type="button"
                    aria-pressed={iv.days.includes(d)} onclick={() => toggleDay(i, d)}>{d}</button>
                {/each}
              </div>
            </div>
          {:else}
            <p class="iv__none">No times yet.</p>
          {/each}
          <button class="iv__add" type="button" disabled={ivs.length >= (sheet.max ?? 6)}
            onclick={addInterval}>Add a time</button>
        </div>
      {:else if sheet.type === 'multi'}
        <!-- The choice sheet with the radio replaced: tapping toggles, and
             nothing closes the sheet because there is no single answer that
             ends it (ADR-0044 §7). -->
        <div class="options" data-noscrollbar>
          {#each sheet.options ?? [] as option (option)}
            {@const selected = picked.includes(option)}
            <button
              class="option"
              class:is-selected={selected}
              type="button"
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
            {@const selected = choicePending !== null ? choicePending === option : (choiceShown ?? String(sheet.value)) === option}
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
              {#if sheet.optionNotes?.[option]}
                <!-- A line under the option (George, 2026-10-11: Volume's
                     three, each short; only Fixed keeps the amber warning). -->
                <span class="option__text"><span class="option__label">{p.label}</span><span class="option__note">{sheet.optionNotes[option]}</span></span>
              {:else}
                <span class="option__label">{p.label}</span>
              {/if}
              <!-- The outputs carry the same Tested tag and problem line as
                   the screens and boards (George, 2026-10-18). -->
              {#if sheet.optionTags?.[option]}
                <span class="option__tag" class:option__tag--tested={sheet.optionTags[option] === 'Tested'}>{sheet.optionTags[option]}</span>
              {/if}
              {#if sheet.optionProblems?.[option]}<span class="option__why">{sheet.optionProblems[option]}</span>{/if}
              <!-- Why it cannot be chosen: a line of its own across the whole
                   tile, in amber and not dimmed with the rest (George,
                   2026-10-12, Hardware on a USB DAC - beside the note it
                   squeezed the note into a column a word wide). -->
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
        {@const crumbs = usbBrowse?.crumbs ?? shareFolder?.crumbs ?? null}
        {#if crumbs?.length}
          <!-- The path, a step each: how a folder goes back up (George,
               2026-10-18, "Tick several"). -->
          <div class="crumbs">
            {#each crumbs as c, i (i)}
              <button type="button" class="crumb" class:is-here={i === crumbs.length - 1} onclick={() => goCrumb(c)}>{c.name}</button>
            {/each}
          </div>
        {/if}
        {#if items.length}
          <div class="items" data-noscrollbar>
            <!-- A USB folder by where it is: two folders can share a name. -->
            {#each items as item (item.address ?? (item.drive != null ? `${item.drive}:${item.folder ?? ''}:${item.add ? '+' : item.up ? '^' : ''}${item.name}` : item.name))}
              {@const joined = item.state === 'connected' || item.state === 'current'}
              <!-- Only the network in use takes no tap: there is nothing to
                   join. The server in use still does - tapping the one you
                   are on is how the sheet is dismissed, and refusing it
                   leaves the sheet looking stuck (George, on the panel,
                   2026-09-20). -->
              {@const inert = item.state === 'connected' && !item.details}
              <button
                class="item"
                class:item--backup={sheet.key === 'restore'}
                class:is-joined={joined}
                class:item--static={inert}
                type="button"
                disabled={inert}
                aria-expanded={item.state === 'connected' && item.details ? netOpen : undefined}
                onclick={() => (item.state === 'connected' ? (netOpen = !netOpen) : chooseItem(item))}
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
                  </span>
                  {#if tickable(item) && coveredBy(item)}<span class="item__meta">In {coveredBy(item).name}</span>
                  {:else if item.meta}<span class="item__meta" class:is-joined={joined}>{keepUnit(item.state === 'connected' && netOpen && netLive?.name === item.name && netLive.speed ? `Connected · ${netLive.speed}` : item.meta)}</span>{/if}
                </span>
                {#if tickable(item)}
                  <!-- Tick several (George, 2026-10-18): the box ticks, the
                       row opens. -->
                  <span
                    class="pick"
                    class:is-on={isPicked(item)}
                    class:is-covered={!!coveredBy(item)}
                    role="checkbox"
                    tabindex="0"
                    aria-checked={isPicked(item)}
                    aria-label={`Tick ${item.name}`}
                    onclick={(e) => { e.stopPropagation(); togglePick(item); }}
                    onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); togglePick(item); } }}
                  ><span></span></span>
                {/if}
                <!-- The lock alone, at the end of the line before its action,
                     leaves the name its room (George, 2026-10-07): closed
                     where a password is still needed, open where one was
                     given before. -->
                {#if item.state === 'locked'}
                  <span class="lock" role="img" aria-label="Password needed"><span></span><span></span></span>
                {:else if item.secured}
                  <span class="lock lock--open" role="img" aria-label="Password saved"><span></span><span></span></span>
                {/if}
                {#if sheet.key === 'restore' && !onPanel() && !item.broken}
                  <!-- ADR-0083 as amended 2026-10-08: a backup saved on the
                       phone or computer, for a newly flashed card's setup
                       (ADR-0131). Not on the panel, which saves nothing. -->
                  <span
                    class="forget"
                    role="button"
                    tabindex="0"
                    onclick={(e) => { e.stopPropagation(); downloadBackup(item); }}
                    onkeydown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); e.stopPropagation(); downloadBackup(item); } }}
                  >Download</span>
                {/if}
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
                {/if}
                {#if item.state === 'connected' && item.details}
                  <span class="netchev" class:netchev--open={netOpen} aria-hidden="true"></span>
                {/if}
              </button>
              {#if item.state === 'connected' && item.details && netOpen}
                <!-- ADR-0123: the connected network in detail, under its line
                     rather than in a row of its own. -->
                <dl class="netinfo">
                  {#each (netLive?.name === item.name ? netLive.details : item.details) as [k, v] (k)}
                    <div class="netinfo__row"><dt>{k}</dt><dd>{v}</dd></div>
                  {/each}
                </dl>
                <!-- ADR-0123 decision 2: this network's address, Automatic or
                     Manual, kept the way the cable's is. -->
                <div class="netaddr"><CableSheet port="wifi" facts={false} /></div>
              {/if}
            {/each}
            {#if sheet.hint}<div class="items__hint">{sheet.hint}</div>{/if}
          </div>
        {:else}
          <div class="empty">
            <span class="empty__ring"></span>
            <span class="empty__text">{listError ?? (crumbs?.length ? 'No folders inside.' : sheet.empty ?? 'Nothing here yet.')}</span>
          </div>
        {/if}
        {#if picks.length}
          <button type="button" class="btn btn--confirm pick-add" onclick={addPicked}>
            Add {picks.length} {picks.length === 1 ? 'folder' : 'folders'}
          </button>
        {/if}
      {/if}

      {#if sheet.type === 'list' && sheet.key === 'restore' && !onPanel() && !join && !restorePending}
        <!-- ADR-0083 as amended 2026-10-17: on a phone or computer, as
             Download is; the panel has no files to pick. -->
        <label class="iv__add addbackup" class:is-busy={adding !== null}>
          <input type="file" hidden disabled={adding !== null} onchange={(e) => addBackup(e.currentTarget)} />
          {adding !== null ? `Adding the backup… ${Math.round(adding * 100)}%` : 'Add a backup'}
        </label>
        {#if addError}<div class="addbackup__error">{addError}</div>{/if}
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
              {restoring
                ? join === 'connecting' ? `Restoring ${restoring}` : 'Could not restore'
                : join === 'connecting' ? `Joining ${joinItem?.name ?? ''}` : join === 'ok' ? 'Connected' : 'Could not join'}
            </div>
            <div class="joining__note">
              {restoring
                ? join === 'connecting' ? 'Reading the backup. The device restarts when it is done.' : 'The backup could not be restored.'
                : join === 'connecting'
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
      {:else if sheet.type === 'share-login'}
        <input class="field" type="text" placeholder="User" bind:value={shareCreds.user}
          autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="User" />
        <span class="pw">
          <input class="field" type={pwShown ? 'text' : 'password'} placeholder="Password" bind:value={shareCreds.password}
            autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="Password" />
          {@render eye()}
        </span>
      {:else if sheet.type === 'share'}
        <!-- ADR-0115: SMB as //nas/music with a user and a password; NFS as
             nas:/music, with neither. -->
        <input class="field" type="text" placeholder="//nas/music or nas:/music" bind:value={share.address}
          autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="Share address" />
        <input class="field" type="text" placeholder="User (SMB)" bind:value={share.user}
          autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="User" />
        <span class="pw">
          <input class="field" type={pwShown ? 'text' : 'password'} placeholder="Password (SMB)" bind:value={share.password}
            autocomplete="off" autocapitalize="off" spellcheck="false" aria-label="Password" />
          {@render eye()}
        </span>
      {:else if sheet.wired && sheet.type === 'text'}
        <!-- The panel and the phone take the same input; a panel without a
             keyboard attached reads every setting and changes every one that
             is not text (ADR-0044). -->
        <span class="pw">
          <input
            class="field"
            type={sheet.secret && !pwShown ? 'password' : 'text'}
            placeholder={sheet.placeholder ?? ''}
            bind:value={draft}
            autocomplete="off"
            autocapitalize="off"
            spellcheck="false"
            aria-label={sheet.label}
          />
          {#if sheet.secret}{@render eye()}{/if}
        </span>
      {:else if sheet.type === 'readonly' || sheet.type === 'text' || sheet.type === 'number'}
        <div class="sheet__value">{shown(sheet)}</div>
      {/if}

      {#if join !== 'connecting' && join !== 'ok'}
      <div class="sheet__actions">
        <button class="btn" type="button" disabled={busy} onclick={cancelSheet}>
          {#if join === 'error'}
            Give up
          {:else if joinItem || shareBrowse || shareLogin || (sheet.grouped && region !== null)
                     || (sheet.kind === 'hardware' && hw && hwAt > 0 && !hwUrl)
                     || (sheet.kind === 'report' && reportStep === 'preparing')}
            Back
          {:else if restorePending}
            Cancel
          {:else if (sheet.kind === 'hardware' && hwUrl) || (sheet.kind === 'report' && reportStep === 'send')}
            Close
          {:else if choicePending === null && (sheet.type === 'choice' || sheet.type === 'multi' || sheet.type === 'intervals' || sheet.grouped || (sheet.wired && sheet.type === 'number'))}
            Close
          {:else}
            Cancel
          {/if}
        </button>
        {#if join === 'error' || joinItem || restorePending || choicePending !== null || (sheet.type === 'action' && sheet.kind !== 'cable' && !((sheet.kind === 'report' || sheet.kind === 'hardware') && onPanel()) && !(sheet.kind === 'hardware' && hwUrl) && !(sheet.kind === 'report' && reportStep === 'send')) || sheet.type === 'toggle' || sheet.type === 'text' || sheet.type === 'share' || sheet.type === 'share-login' || (sheet.type === 'number' && !sheet.wired) || (sheet.type === 'list' && sheet.manual && !searching)}
          <button
            class="btn btn--confirm"
            class:btn--danger={sheet.danger || restorePending || choicePending !== null}
            type="button"
            class:btn--hold={sheet.hold}
            disabled={busy || hwBusy || (sheet.kind === 'hardware' && !hw && !hwUrl && !hwError)
              || (sheet.kind === 'report' && reportStep === 'preparing' && !reportReady && !reportError)}
            onclick={sheet.hold ? (event) => event.preventDefault() : confirmSheet}
            onpointerdown={sheet.hold ? holdStart : null}
            onpointerup={sheet.hold ? holdStop : null}
            onpointerleave={sheet.hold ? holdStop : null}
            onpointercancel={sheet.hold ? holdStop : null}
            oncontextmenu={sheet.hold ? (event) => event.preventDefault() : null}
            onkeydown={sheet.hold ? holdKey(true) : null}
            onkeyup={sheet.hold ? holdKey(false) : null}
          >
            {#if sheet.hold}<span class="btn__hold" style:width="{Math.round(holdShare * 100)}%"></span>{/if}
            {#if sheet.kind === 'hardware'}
              {#if hwBusy}<span class="btn__spin"></span>Preparing…{:else if hwUrl}Done{:else if !hw && hwError}Try again{:else if hw && !hwLast}{hwSteps[hwAt + 1] === 'sound' ? 'Next: the sound' : 'Next: anything else'}{:else}Prepare the feedback{/if}
            {:else if sheet.kind === 'report'}
              {#if reportStep === 'what'}Next: prepare the report{:else if reportError}Try again{:else if reportReady}Next: send it{:else}<span class="btn__spin"></span>Preparing…{/if}
            {:else if busy}
              <span class="btn__spin"></span>Saving
            {:else if join === 'error'}
              Try again
            {:else if restorePending}
              Restore and restart
            {:else if joinItem}
              Join
            {:else if choicePending !== null}
              {sheet.confirm ?? 'Confirm'}
            {:else if sheet.type === 'list'}
              {sheet.manual}
            {:else if sheet.type === 'toggle'}
              {sheet.confirm ?? 'I understand, switch it on'}
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

  {#if updateModal}
    <UpdateModal start={updateModal} onclose={closeUpdate} />
  {/if}

  {#if ask}
    <!-- ADR-0106: the confirm before an upload or a removal. Centred, not a
         bottom sheet: on a tall phone it sat at the foot of the screen
         (George, 2026-09-30). -->
    <div class="ask" role="dialog" aria-modal="true" aria-label={ask.title}>
      <div class="ask__card">
        <div class="ask__title">{ask.title}</div>
        <div class="warn">
          <span class="warn__mark">!</span>
          <span class="warn__text">{ask.text}</span>
        </div>
        <div class="ask__buttons">
          <button type="button" class="btn" data-dpad-back onclick={() => answerAsk(false)}>Cancel</button>
          <button type="button" class="btn btn--confirm" class:btn--danger={ask.danger} onclick={() => answerAsk(true)}>{ask.confirm}</button>
        </div>
      </div>
    </div>
  {:else if task}
    <div class="ask" role="dialog" aria-modal="true" aria-live="polite" aria-label={task.title}>
      <div class="ask__card">
        <div class="ask__title">{task.title}</div>
        {#if task.phase === 'failed'}
          <div class="warn">
            <span class="warn__mark">!</span>
            <span class="warn__text">{task.text}</span>
          </div>
        {:else if task.phase === 'done'}
          <div class="task__text">{task.text}</div>
        {:else}
          <div class="task__text">
            {#if task.phase === 'sending'}Uploading… {Math.round((task.share ?? 0) * 100)} %
            {:else if task.phase === 'checking'}Checking and installing…
            {:else}The player is restarting…{/if}
          </div>
          <span class="task__bar" class:task__bar--busy={task.phase !== 'sending'}>
            <span style:width={`${Math.round((task.share ?? 0) * 100)}%`}></span>
          </span>
        {/if}
        {#if task.phase === 'done' || task.phase === 'failed'}
          <div class="ask__buttons">
            <button type="button" class="btn btn--confirm" onclick={() => (task = null)}>OK</button>
          </div>
        {/if}
      </div>
    </div>
  {/if}
</div>

<style>
  .settings {
    position: relative;
    width: 100%;
    height: 100%;
    min-height: 100%;
    /* `clip`, not `hidden` (George, 2026-10-08, a phone pasting the Beszel
       key): the weave is drawn 90 px past every edge, and `hidden` is still a
       scroll container - 131 px of sideways scroll at 412 px wide, which a
       phone used to bring a field's caret into view, sliding the page left
       under the fixed mini player. `clip` crops the same and scrolls nothing. */
    overflow: clip;
    font-family: var(--font-ui);
    color: var(--ink);
    background: var(--bg-base);
    -webkit-tap-highlight-color: transparent;
  }
  .settings.is-embedded {
    background: none;
  }
  .settings.is-flat,
  .settings.is-flat .picker,
  .settings.is-flat .pane--over {
    background: var(--bg-panel);
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
  .title-row {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .title-row .title {
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
  .subtitle--facts {
    white-space: normal;
    overflow: visible;
    display: flex;
    flex-wrap: wrap;
    column-gap: 0.9em;
    row-gap: 2px;
  }
  .fact {
    white-space: nowrap;
  }
  /* The dot ends the line it is on, so a wrapped address starts its own. */
  .fact:not(:last-child)::after {
    content: '\00b7';
    margin-left: 0.9em;
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
  /* ADR-0110 §2: the Release tile. A row that holds a button, so a div. */
  .row--tile { cursor: default; }
  /* The button under the text, not beside it: beside it, a phone's width
     broke "Up to date · checked today 13:20" mid-word. */
  .row--tile .row__body { flex-direction: column; align-items: stretch; gap: 14px; }
  .row--tile .tile__btn { align-self: flex-start; }
  .row--tile:active { transform: none; }
  .row__value--tile {
    display: block;
    margin-top: 4px;
    font-family: var(--font-mono);
    font-size: 15px;
    color: var(--ink-body);
  }
  /* A name wraps between its words, a single long one still breaks; over
     `.row__value`'s break-all, which comes later. */
  .row__value.row__value--tile {
    word-break: normal;
    overflow-wrap: anywhere;
  }
  .tile__btn {
    flex-shrink: 0;
    height: 44px;
    padding: 0 18px;
    border-radius: 13px;
    background: rgba(233, 238, 242, 0.07);
    border: 1px solid rgba(233, 238, 242, 0.14);
    color: var(--ink);
    font-size: 15px;
    font-weight: 600;
    white-space: nowrap;
  }
  .tile__btn:active { background: rgba(233, 238, 242, 0.2); }
  .tile__btn--go {
    font-weight: 700;
    background: rgba(126, 214, 188, 0.16);
    border-color: rgba(126, 214, 188, 0.4);
    color: var(--accent-lms);
  }
  .tile__btn:disabled { opacity: 0.6; }
  .row__body--stack {
    flex-direction: column;
    align-items: stretch;
    gap: 12px;
  }
  .hwkept__open {
    display: block;
    width: 100%;
    padding: 0;
    border: 0;
    background: none;
    color: inherit;
    font: inherit;
    text-align: left;
  }
  .hwkept__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
  .hwkept__btn {
    display: inline-flex;
    align-items: center;
    text-decoration: none;
  }
  .report__send {
    display: flex;
    align-items: center;
    justify-content: center;
    min-height: 52px;
    text-decoration: none;
  }
  /* A running install: dimmed as before, but a tap brings back the modal
     that Hide put away (George, 2026-10-02: "how do I see it again?"). */
  .tile__btn--busy { opacity: 0.6; }
  .tile__notes { display: block; margin-top: 8px; color: var(--ink-body); }
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
    /* The height of a reading's mark, so a heading does not move when its
       reading comes or goes (the Library's Lyrion switch, 2026-10-19). */
    line-height: 20px;
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
    position: relative;
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
  /* Not a tile: a tile is not pressed, only its button is - `:active`
     holds on every ancestor of what the finger is on, so a tile lit up as a
     whole when its button was tapped (George, 2026-10-07, Find portraits
     and covers). */
  .row:not(.row--tile):active {
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
  .row__tag {
    flex-shrink: 0;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--ink-quiet);
    padding: 4px 8px;
    border-radius: 6px;
    border: 1px solid rgba(233, 238, 242, 0.14);
    white-space: nowrap;
  }
  .row--danger .row__name {
    color: var(--accent-warn);
  }
  .head__note {
    margin-top: 4px;
    font-size: 14px;
    line-height: 1.4;
    color: var(--ink-quiet);
    text-wrap: pretty;
  }
  .row__note.row__version {
    font-family: var(--font-mono);
    font-size: 13px;
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
  .row__value--done {
    color: var(--accent-lms);
  }
  .ind {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    flex-shrink: 0;
    font-size: 15px;
    font-weight: 600;
    white-space: nowrap;
    color: var(--ind);
  }
  .ind__mark {
    display: inline-grid;
    place-items: center;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    font-family: var(--font-sans, inherit);
    font-size: 12px;
    color: var(--ink-on-accent);
    background: var(--ind);
  }
  .ind--ok {
    --ind: var(--accent-ok);
  }
  .ind--wait {
    --ind: var(--accent-warn);
  }
  .ind--bad {
    --ind: var(--accent-bad);
  }
  .ind--wait .ind__mark {
    animation: indWait 1400ms ease-in-out infinite;
  }
  @keyframes indWait {
    50% { opacity: 0.35; }
  }
  .row__tick {
    font-family: var(--font-sans, inherit);
  }
  .row__note--failed {
    color: var(--accent-warn);
  }
  .row__again {
    display: block;
    margin-top: 6px;
    font-size: 14px;
    color: var(--accent-lms);
    text-decoration: underline;
    text-underline-offset: 2px;
  }
  /* Below 520px the value drops under the label instead of squeezing it. */
  @container srow (max-width: 520px) {
    .row__body {
      flex-wrap: wrap;
    }
    /* The arrow in the middle of the tile, not beside its first line
       (George, 2026-10-03: "center the arrow on the tiles on mobile"). */
    .row__body:has(> .chev) {
      padding-right: 26px;
    }
    .row__body > .chev {
      position: absolute;
      right: 24px;
      top: calc(50% - 6px);
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

  /* A sheet and its dimming sit above the phone's mini player (20) - as the
     confirmations (60) and the full-screen picker (30) already did - and
     below that picker. Under it, a tall sheet's Close and its last options
     were covered on a laptop's screen (George, 2026-10-07). On the panel
     both stay inside the screen layer, so nothing there changes. */
  .scrim {
    position: absolute;
    inset: 0;
    z-index: 24;
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
    z-index: 25;
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
  /* ADR-0109, Bar family: a sheet is the full height less 12 px above and
     below, min(760, W - 172) wide on the library's content area (W - 124),
     centred on it (design/source/13b/Bar States.dc.html, lib-sheet). On a
     400 px screen the panel's 82% cap leaves a sheet too short to hold a
     list. */
  /* A long list on a phone: the whole screen, not a card over it. */
  /* **A sheet in steps stays where it opened** (George, 2026-10-11, on
     Hardware feedback: "when opening the modal it jumps"). Centred, a sheet
     that grew - the step area arriving after "Reading the hardware…", or the
     next step - re-centred and pushed what was already read upwards. Held
     at the top, it grows downwards only. Before the bar's rules, which
     already hold every sheet at the top. */
  .sheet.sheet--steps {
    top: 9%;
    transform: translate(-50%, 0);
  }
  .sheet.sheet--full {
    top: 0;
    left: 0;
    transform: none;
    width: 100%;
    max-width: none;
    height: 100%;
    max-height: none;
    border: none;
    border-radius: 0;
    box-shadow: none;
    padding: 20px 18px;
  }
  :global(.panel--bar) .sheet {
    top: 12px;
    bottom: 12px;
    transform: translateX(-50%);
    width: min(760px, 100% - 48px);
    max-width: none;
    max-height: none;
    border-radius: 20px;
    padding: 18px 20px 14px;
    gap: 12px;
  }
  /* A confirmation holds a title, a line and two buttons: drawn the bar's
     full height it was mostly empty (George, 2026-10-08, *Reboot* on the
     11.9" bar). It takes its own height, centred, as on other screens. */
  :global(.panel--bar) .sheet.sheet--fit {
    top: 50%;
    bottom: auto;
    transform: translate(-50%, -50%);
    max-height: calc(100% - 24px);
  }
  .sheet__head {
    flex-shrink: 0;
    min-width: 0;
  }
  /* **On a bar the head gives way, not the controls** (George, 2026-10-24:
     a smoothing sheet's button cut off). The sheet's height is fixed there
     (376 px), and a long note above a warning and a slider pushed Close
     below its edge; the note now scrolls instead. */
  :global(.panel--bar) .sheet__head {
    flex-shrink: 1;
    min-height: 0;
    overflow-y: auto;
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
    flex-wrap: wrap;
    align-items: center;
    gap: 16px;
    min-height: 62px;
    padding: 12px 18px;
    border-radius: 14px;
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid rgba(233, 238, 242, 0.1);
  }
  /* No press colour (George, 2026-10-16): a phone holds :active for about
     150 ms after the finger lifts, so with a tap drawn at once, unticking
     put out the box while the row stayed lit - "the teal background is
     slower than the selection dot". The selection is the feedback. */
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
  .option.is-unavailable > :not(.option__why) {
    opacity: 0.42;
  }

  .iv {
    flex: 1;
    min-height: 0;
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .iv__item {
    position: relative;
    display: flex;
    flex-direction: column;
    gap: 12px;
    padding: 14px 16px;
    border-radius: var(--r-lg);
    background: rgba(255, 255, 255, 0.04);
    border: 1px solid var(--ink-line);
  }
  .iv__remove {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 44px;
    height: 44px;
    padding: 0;
    display: grid;
    place-items: center;
    border-radius: 50%;
    border: 1px solid var(--ink-line);
    background: var(--ink-fill);
    color: var(--ink-muted);
  }
  .iv__remove svg {
    width: 18px;
    height: 18px;
    fill: none;
    stroke: currentColor;
    stroke-width: 2.2;
    stroke-linecap: round;
  }
  .iv__times {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding-right: 56px;
  }
  .iv__pair {
    display: inline-flex;
    align-items: center;
    gap: 12px;
  }
  .iv__label {
    min-width: 56px;
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .iv__time {
    min-width: 104px;
    text-align: center;
    min-height: 48px;
    padding: 0 16px;
    border-radius: var(--r-md);
    border: 1px solid var(--ink-line);
    background: var(--ink-fill);
    color: var(--ink);
    font: inherit;
    font-size: 22px;
    font-weight: 600;
    font-variant-numeric: tabular-nums;
  }
  .iv__time.open {
    border-color: var(--accent-lms);
    color: var(--accent-lms);
  }
  .iv__picker {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  .iv__grid {
    display: grid;
    gap: 6px;
  }
  .iv__grid--hours {
    grid-template-columns: repeat(6, minmax(0, 1fr));
  }
  .iv__grid--quarters {
    grid-template-columns: repeat(4, minmax(0, 1fr));
  }
  .iv__cell {
    min-height: 44px;
    padding: 0;
    text-align: center;
    border-radius: var(--r-md);
    border: 1px solid var(--ink-line);
    background: var(--ink-fill);
    color: var(--ink-body);
    font: inherit;
    font-size: 16px;
    font-variant-numeric: tabular-nums;
  }
  .iv__cell.on {
    border-color: var(--accent-lms);
    background: rgba(126, 214, 188, 0.16);
    color: var(--accent-lms);
    font-weight: 700;
  }
  .iv__days {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .iv__day {
    min-width: 50px;
    text-align: center;
    min-height: 44px;
    padding: 0 10px;
    border-radius: 22px;
    border: 1px solid var(--ink-line);
    background: var(--ink-fill);
    color: var(--ink-muted);
    font: inherit;
    font-size: 15px;
    font-weight: 600;
  }
  .iv__day.on {
    border-color: var(--accent-lms);
    background: rgba(126, 214, 188, 0.16);
    color: var(--accent-lms);
  }
  .iv__add {
    min-height: 52px;
    text-align: center;
    border-radius: var(--r-lg);
    border: 1px dashed var(--ink-line);
    background: transparent;
    color: var(--ink);
    font: inherit;
    font-size: 16px;
    font-weight: 600;
  }
  .iv__add:disabled {
    opacity: 0.45;
  }
  .addbackup {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 16px;
    margin-top: 12px;
    flex-shrink: 0;
    cursor: pointer;
  }
  .addbackup.is-busy {
    opacity: 0.6;
    cursor: default;
  }
  .addbackup__error {
    margin-top: 8px;
    color: var(--accent-warn);
    font-size: 15px;
  }
  .iv__none {
    color: var(--ink-quiet);
    margin: 0;
  }
  .option__text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 4px;
  }
  .option__note {
    font-size: 14px;
    line-height: 1.35;
    color: var(--ink-quiet);
  }
  .option__why {
    flex-basis: 100%;
    font-size: 14px;
    line-height: 1.35;
    color: var(--accent-warn);
  }

  .option__meta {
    flex-shrink: 0;
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--ink-muted);
  }
  .option__tag {
    flex-shrink: 0;
    font-family: var(--font-mono);
    font-size: 11px;
    letter-spacing: var(--track-label);
    text-transform: uppercase;
    color: var(--ink-quiet);
    padding: 4px 8px;
    border-radius: 6px;
    border: 1px solid rgba(233, 238, 242, 0.14);
  }
  .option__tag--tested {
    color: var(--accent-lms);
    border-color: rgba(126, 214, 188, 0.4);
  }
  .option__label {
    flex: 1;
    /* Never narrower than its longest word: a greyed option's reason beside
       it wraps instead of running over it (Volume's Hardware on HDMI). */
    min-width: min-content;
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
  /* On a bar the value stands beside its slider, not above it: the line it
     took was what pushed Close off a 376 px sheet under a long note. A fixed
     width keeps the slider still while the number changes. */
  :global(.panel--bar) .editor {
    display: grid;
    grid-template-columns: 170px 1fr;
    column-gap: 20px;
    row-gap: 0;
    align-items: center;
  }
  :global(.panel--bar) .editor__read {
    grid-row: 1 / span 2;
  }
  :global(.panel--bar) .editor__ends {
    grid-column: 2;
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
  /* Only the row's own tap: a press on Download or Forget inside it is
     that button's, and the whole tile shrinking with it read as the row
     being chosen (George, 2026-10-08, downloading a backup). */
  .item:active:not(:has(.forget:active)) {
    transform: scale(0.95);
  }
  .forget:active {
    transform: scale(0.92);
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
  /* A backup's name and date take the line; Download and Forget go under
     them, at the right (2026-10-08: beside them, on a phone, the name
     shrank to "ge…" and the date broke word by word). */
  .netaddr {
    padding: 4px 18px 14px;
  }
  .item--backup {
    flex-wrap: wrap;
    row-gap: 12px;
  }
  .item--backup .item__text {
    flex: 1 1 100%;
  }
  .item--backup .forget:first-of-type {
    margin-left: auto;
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
  /* Open: the shackle lifted and free on one side. */
  /* The closed lock's own shackle, in its own place: only its left leg
     cut short, free of the body. Lifted or moved sideways, the open lock
     read larger than the closed one (George, 2026-10-07); this way both
     fill the same 13 x 15. */
  .lock.lock--open span:last-child {
    clip-path: polygon(0 0, 100% 0, 100% 100%, 50% 100%, 50% 50%, 0 50%);
  }
  .lock span:last-child {
    position: absolute;
    left: 3px;
    top: 0;
    width: 7px;
    /* Down to the body's top edge, not into it: the two translucent layers
       overlapping drew a brighter square at each leg. */
    height: 6px;
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
  /* Below the label and its chevron, the full width, on every screen. */
  .row__body:has(> .shares) {
    flex-wrap: wrap;
  }
  .shares {
    order: 10;
    flex-basis: 100%;
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-bottom: 4px;
  }
  .shares__one {
    display: flex;
    align-items: center;
    gap: 12px;
  }
  .shares__text {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .shares__name {
    font-size: 17px;
    overflow-wrap: anywhere;
  }
  /* George, 2026-10-18: the shares added, a tile that takes no tap; and the
     tile that adds one, dashed as Upload a plugin is. */
  .row--static {
    cursor: default;
  }
  /* George, 2026-10-19: room between the tile's name and its first share. */
  .row--static .shares {
    margin-top: 14px;
  }
  .row--add {
    border-style: dashed;
  }
  /* ADR-0150: a row's links, as small buttons under its note - on a line of
     their own at every width, as the shares are (George, 2026-10-19: on a
     laptop they sat beside the note, squeezing both). */
  .row__body:has(> .links) {
    flex-wrap: wrap;
  }
  .links {
    order: 10;
    flex-basis: 100%;
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
  }
  .links__one {
    padding: 8px 12px;
    border-radius: 10px;
    border: 1px solid rgba(233, 238, 242, 0.16);
    background: rgba(233, 238, 242, 0.05);
    color: inherit;
    font-size: 14px;
    text-decoration: none;
  }
  /* Tick several (George, 2026-10-18): the box on a folder, the path above
     the list, and the button under it. */
  .pick {
    flex-shrink: 0;
    width: 24px;
    height: 24px;
    margin: -12px 0;
    padding: 12px;
    box-sizing: content-box;
    display: grid;
    place-items: center;
    cursor: pointer;
    background-clip: content-box;
    border-radius: 7px;
    outline: none;
  }
  .pick::before {
    content: '';
    grid-area: 1 / 1;
    width: 24px;
    height: 24px;
    box-sizing: border-box;
    border-radius: 7px;
    border: 2px solid rgba(233, 238, 242, 0.42);
  }
  .pick > span {
    grid-area: 1 / 1;
    width: 11px;
    height: 6px;
    margin-top: -3px;
    border-left: 2.5px solid #0d151c;
    border-bottom: 2.5px solid #0d151c;
    transform: rotate(-45deg);
    display: none;
  }
  .pick.is-on::before {
    background: var(--accent, #7ed6bc);
    border-color: var(--accent, #7ed6bc);
  }
  .pick.is-on > span {
    display: block;
  }
  .pick.is-covered {
    opacity: 0.55;
    cursor: default;
  }
  .crumbs {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-bottom: 12px;
  }
  .crumb {
    padding: 8px 14px;
    border-radius: 999px;
    border: 1px solid rgba(233, 238, 242, 0.14);
    background: rgba(233, 238, 242, 0.05);
    color: inherit;
    font: inherit;
    font-size: 15px;
    cursor: pointer;
  }
  .crumb.is-here {
    background: rgba(233, 238, 242, 0.14);
    border-color: rgba(233, 238, 242, 0.3);
    font-weight: 700;
  }
  .pick-add {
    width: 100%;
    min-height: 52px;
    flex-shrink: 0;
    margin-top: 12px;
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
  /* On a bar the empty state is compact: at the panel's size it took the
     room the note above it needed (Restore). */
  :global(.panel--bar) .empty {
    padding: 8px 20px;
    gap: 10px;
  }
  :global(.panel--bar) .empty__ring {
    width: 40px;
    height: 40px;
  }
  :global(.panel--bar) .empty__text {
    max-width: 60ch;
  }

  /* ADR-0044 §5 - the full-screen picker. */
  .picker {
    position: absolute;
    inset: 0;
    z-index: 30;
    background: var(--bg-base);
    display: flex;
    flex-direction: column;
    overflow: clip;
  }
  /* ADR-0100 as amended: a plugin's download, inside its own row. */
  .row--dl { position: relative; }
  .dl__line { color: var(--ink); }
  .dl__sub { color: var(--ink-quiet); font-family: var(--font-mono); }
  .dl--failed { color: var(--accent-warn); }
  .dl__retry {
    display: inline-block;
    margin-top: 6px;
    padding: 4px 14px;
    border-radius: var(--r-pill, 999px);
    border: 1px solid var(--accent-warn);
    color: var(--accent-warn);
    font-size: 13px;
  }
  .dl__bar {
    position: absolute;
    left: 18px;
    right: 18px;
    bottom: 6px;
    height: 3px;
    border-radius: 2px;
    background: rgba(233, 238, 242, 0.12);
    overflow: hidden;
  }
  .dl__bar span {
    display: block;
    height: 100%;
    background: var(--accent-lms);
    transition: width 0.4s ease;
  }
  /* No total known yet: a sliver that moves, so it never looks stuck. */
  .dl__bar--busy span {
    width: 30% !important;
    animation: dl-busy 1.2s ease-in-out infinite;
  }
  @keyframes dl-busy {
    from { transform: translateX(-100%); }
    to { transform: translateX(340%); }
  }
  /* ADR-0099: Legal and Credits, read on the panel as on a phone. Links
     are shown, not followed: the kiosk has nowhere to go. */
  .doc {
    width: 100%;
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
    padding: 12px 24px 32px;
    box-sizing: border-box;
    color: var(--ink);
  }
  .doc--wide { padding: 18px 64px 40px; }
  .doc__h {
    font-size: 18px;
    font-weight: 600;
    color: var(--ink);
    margin: 22px 0 8px;
  }
  .doc__p { font-size: 15px; line-height: 1.5; margin: 0 0 10px; }
  .doc__notes { margin: 0 0 18px; }
  .doc__list { list-style: none; margin: 0; padding: 0; }
  .doc__entry {
    padding: 10px 0;
    border-bottom: 1px solid rgba(233, 238, 242, 0.07);
  }
  .doc__name { font-size: 15px; font-weight: 600; color: var(--ink); }
  .doc__licence {
    margin-left: 10px;
    font-size: 12px;
    font-weight: 500;
    opacity: 0.7;
  }
  .doc__line { font-size: 13px; line-height: 1.45; }
  .doc__muted { color: var(--ink-quiet); }
  .doc__url { word-break: break-all; }
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
  /* Sideways strokes are ours (the swipe between skins); up and down still
     scroll the pane. */
  .pane--over { touch-action: pan-y; }
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
  .pw {
    position: relative;
    display: block;
    flex-shrink: 0;
    width: 100%;
  }
  .pw .field {
    padding-right: 64px;
  }
  .pw__eye {
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    width: 46px;
    height: 46px;
    border: 0;
    border-radius: 12px;
    background: transparent;
    color: var(--ink-quiet);
    display: grid;
    place-items: center;
  }
  .pw__eye svg {
    width: 24px;
    height: 24px;
    fill: none;
    stroke: currentColor;
    stroke-width: 1.8;
    stroke-linecap: round;
    stroke-linejoin: round;
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
    /* A label that wraps ("Prepare the feedback" at phone width) stays
       centred and clear of the edges. */
    padding: 0 14px;
    text-align: center;
    line-height: 1.2;
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
  /* ADR-0132: held, not tapped - the fill shows how long is left. */
  .btn--hold {
    position: relative;
    overflow: hidden;
    touch-action: none;
    user-select: none;
    -webkit-user-select: none;
    -webkit-touch-callout: none;
  }
  .btn__hold {
    position: absolute;
    inset: 0 auto 0 0;
    background: rgba(224, 167, 88, 0.35);
    pointer-events: none;
  }
  .btn--danger {
    background: rgba(224, 167, 88, 0.2);
    border-color: rgba(224, 167, 88, 0.5);
    color: var(--accent-warn);
  }

  .upload__input {
    display: none;
  }
  /* ADR-0168: More plugins, apart from the groups where Upload a plugin
     does not follow it (the panel, the bars). */
  .row--apart {
    margin-bottom: 18px;
  }
  /* Update, in the row's Retry shape but the colour of going ahead. */
  .dl__go {
    border-color: var(--accent-lms);
    color: var(--accent-lms);
  }
  .listed__note {
    margin: 0 4px 6px;
    font-size: 14px;
    line-height: 1.4;
    color: rgba(233, 238, 242, 0.55);
    text-wrap: pretty;
  }
  .listed__actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
  }
  /* Wide - the panel, the bars - its button at the right, as a row's
     switch is: a bar is 400 px tall. */
  .list--wide .listed .row__body {
    flex-direction: row;
    align-items: center;
  }
  .list--wide .listed .listed__actions {
    flex-shrink: 0;
  }
  .listed__link {
    display: inline-flex;
    align-items: center;
    text-decoration: none;
  }
  .listed__source {
    word-break: break-all;
  }
  .listed__facts {
    display: flex;
    flex-wrap: wrap;
    column-gap: 0.6em;
  }
  .listed__fact {
    max-width: 100%;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  .row--upload {
    margin-bottom: 18px;
    border-style: dashed;
    border-color: rgba(233, 238, 242, 0.28);
  }
  .upload__icon {
    width: 28px;
    height: 28px;
    flex-shrink: 0;
    fill: none;
    stroke: rgba(233, 238, 242, 0.7);
    stroke-width: 1.8;
    stroke-linecap: round;
    stroke-linejoin: round;
  }
  .ask {
    position: fixed;
    inset: 0;
    z-index: 60;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 16px;
    background: var(--bg-scrim);
  }
  /* Inside the phone's remote (ADR-0164) Settings is one half of a track
     slid by half its width, and a fixed dialog was centred on the track:
     half off the screen, its title and Cancel out of reach (found
     2026-10-29). There it covers Settings' own area instead. */
  .settings.is-flat .ask {
    position: absolute;
  }
  .ask__card {
    width: min(560px, 100%);
    padding: 24px 22px 28px;
    border-radius: var(--r-xl);
    background: var(--bg-panel);
    display: flex;
    flex-direction: column;
    gap: 18px;
  }
  .ask__title {
    font-size: 20px;
    font-weight: 700;
  }
  .task__text {
    font-size: 17px;
    line-height: 1.4;
  }
  .task__bar {
    display: block;
    height: 6px;
    border-radius: 3px;
    background: rgba(233, 238, 242, 0.12);
    overflow: hidden;
  }
  .task__bar span {
    display: block;
    height: 100%;
    background: var(--accent-lms);
    transition: width 0.2s ease;
  }
  /* Nothing to measure: a sliver that moves, as .dl__bar--busy. */
  .task__bar--busy span {
    width: 30% !important;
    animation: dl-busy 1.2s ease-in-out infinite;
  }
  .ask__buttons {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
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
  /* The phone's closed mini player stands over the foot of the page: the
     scrolling lists end with room for it (App.svelte's --foot-clear, 0 on
     the panel). */
  .rail::after,
  .list::after {
    content: '';
    /* Less the list's own foot padding, which already stands below the
       last row. */
    flex: 0 0 max(0px, calc(var(--foot-clear, 0px) - 30px));
  }
  /* ADR-0123: the connected network's details. */
  /* ADR-0125: the problem report's sheet. */
  .report {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }
  /* The hardware report is taller than a phone: its questions scroll inside
     the sheet, and the sheet's buttons stay where a thumb can reach them. */
  .report--scroll {
    flex: 1 1 auto;
    min-height: 0;
    overflow-y: auto;
    overscroll-behavior: contain;
  }
  .report__text {
    margin: 0;
    font-size: 15px;
    line-height: 1.45;
    color: var(--ink-body);
  }
  .report__text--quiet { color: var(--ink-quiet); }
  /* ADR-0138: the checklist the player works down while preparing. */
  .check {
    list-style: none;
    margin: 0;
    padding: 0;
    display: flex;
    flex-direction: column;
    gap: 12px;
  }
  .check__item {
    display: flex;
    gap: 12px;
    align-items: flex-start;
    color: var(--ink-quiet);
  }
  .check__item.is-done,
  .check__item.is-now { color: var(--ink); }
  .check__mark {
    flex-shrink: 0;
    width: 22px;
    height: 22px;
    display: grid;
    place-items: center;
    border-radius: 50%;
    font-size: 13px;
    font-weight: 700;
  }
  .check__item.is-done .check__mark {
    background: rgba(126, 214, 188, 0.16);
    color: var(--accent-lms);
  }
  .check__item.is-now .check__mark {
    border: 2px solid var(--ink-line);
    border-top-color: var(--accent-lms);
    animation: check-turn 0.9s linear infinite;
  }
  @keyframes check-turn { to { transform: rotate(360deg); } }
  .check__text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }
  .check__label { font-size: 15px; line-height: 1.35; }
  .check__detail {
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--ink-quiet);
    overflow-wrap: anywhere;
  }
  .check__files {
    list-style: none;
    margin: 8px 0 0;
    padding: 0;
    font-family: var(--font-mono);
    font-size: 12px;
    color: var(--ink-quiet);
  }
  .check__files li {
    display: flex;
    justify-content: space-between;
    gap: 12px;
  }
  .report__text--warn { color: var(--accent-warn); }
  .report__addr {
    font-family: var(--font-mono);
    font-size: 14px;
    word-break: break-all;
  }
  .report__link { color: var(--accent-lms); }
  .report__step {
    margin: 0;
    font-family: var(--font-mono);
    font-size: 13px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--ink-dim, #9fb0bd);
  }
  .hwprompt {
    display: flex;
    align-items: stretch;
    gap: 8px;
    border-radius: 14px;
    border: 1px solid rgba(124, 208, 176, 0.35);
    background: rgba(124, 208, 176, 0.08);
  }
  .hwprompt__go {
    flex: 1;
    min-width: 0;
    text-align: left;
    padding: 14px 18px;
    font-size: 16px;
    font-weight: 600;
    color: var(--ink);
    background: none;
    border: 0;
  }
  .hwprompt__x {
    flex-shrink: 0;
    width: 52px;
    font-size: 22px;
    color: var(--ink-dim, #9fb0bd);
    background: none;
    border: 0;
  }
  .hwq {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }
  .hwq__options {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }
  .hwq__option {
    padding: 8px 14px;
    border-radius: 10px;
    border: 1px solid rgba(233, 238, 242, 0.18);
    background: rgba(255, 255, 255, 0.05);
    color: var(--ink);
    font: inherit;
    font-size: 15px;
  }
  .hwq__option.is-on {
    border-color: var(--accent-lms);
    background: rgba(126, 214, 188, 0.16);
  }
  .hwq__tones {
    margin: 0;
    padding-left: 18px;
    font-family: var(--font-mono);
    font-size: 13px;
    color: var(--ink-body);
  }
  .hwq__facts pre {
    margin: 6px 0 0;
    font-family: var(--font-mono);
    font-size: 12px;
    white-space: pre-wrap;
    color: var(--ink-quiet);
  }
  .report__go {
    font-size: 17px;
    font-weight: 600;
  }
  .report__copy {
    margin-left: 8px;
    padding: 2px 10px;
    border-radius: 8px;
    border: 1px solid rgba(233, 238, 242, 0.2);
    background: rgba(255, 255, 255, 0.06);
    color: var(--ink);
    font: inherit;
    font-size: 13px;
  }
  .report__label {
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .report__note--tall {
    min-height: 168px;
  }
  /* Never squeezed: in a sheet taller than the phone, the flex column shrank
     the box to one line (George, 2026-10-09, on guestpi). */
  .report__note {
    flex-shrink: 0;
    min-height: 96px;
    width: 100%;
    box-sizing: border-box;
    padding: 12px 14px;
    border-radius: 12px;
    border: 1px solid rgba(233, 238, 242, 0.16);
    background: rgba(255, 255, 255, 0.045);
    color: var(--ink);
    font: inherit;
    font-size: 16px;
    line-height: 1.4;
    resize: vertical;
  }
  .netinfo {
    margin: -2px 0 8px;
    padding: 10px 16px 12px 52px;
    display: grid;
    gap: 6px;
  }
  .netinfo__row {
    display: flex;
    justify-content: space-between;
    gap: 16px;
  }
  .netinfo dt {
    font-family: var(--font-mono);
    font-size: 12px;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--ink-quiet);
  }
  .netinfo dd {
    margin: 0;
    font-family: var(--font-mono);
    font-size: 14px;
    color: var(--ink-body);
    font-variant-numeric: tabular-nums;
    white-space: nowrap;
  }
  /* A narrow phone gives up the indent under the name before a value
     breaks ("5 GHz · channel / 116" at 360 px). */
  @media (max-width: 380px) {
    .netinfo {
      padding-left: 18px;
    }
  }
  /* Not `.chev`: that one is drawn with its own two borders, and adding
     a third drew two chevrons over each other. */
  .netchev {
    flex-shrink: 0;
    width: 9px;
    height: 9px;
    border-right: 2px solid var(--ink-quiet);
    border-bottom: 2px solid var(--ink-quiet);
    transform: rotate(45deg);
    margin: 0 2px 4px 0;
    transition: transform var(--dur-fast) var(--ease);
  }
  .netchev--open {
    transform: rotate(225deg);
    margin-bottom: -4px;
  }
</style>
