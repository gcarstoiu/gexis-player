// SPDX-License-Identifier: GPL-3.0-or-later
// Settings from the daemon's registry (ADR-0035), refetched whenever
// `settings_revision` moves so a change on one surface reaches the other.
import { writable, derived } from 'svelte/store';
import { playback, connection } from './state.js';

export const settingsGroups = writable([]);
export const settingsError = writable(null);
/** The header's three facts (ADR-0048 §5): the stored name, the system's own
 *  hostname, and the address. After a rename the first two disagree until
 *  the restart, and that disagreement is the point - the panel must not
 *  guess the hostname from the name. */
export const settingsDevice = writable({ name: null, hostname: null, address: null });

//: One reload at a time. A save is followed by the settings revision every
//: open screen hears, and each used to start its own full reload on top of
//: the one the save asked for - three in a row on the player, each half a
//: second (2026-10-05). Asked for while one runs, it runs once more after.
let loading = null;
let again = false;

export function loadSettings() {
  if (loading) {
    again = true;
    return loading;
  }
  loading = fetchSettings().finally(() => {
    loading = null;
    if (again) {
      again = false;
      loadSettings();
    }
  });
  return loading;
}

async function fetchSettings() {
  try {
    const { response, body } = await ask('/settings');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    if (!Array.isArray(body.groups)) throw new Error('the answer had no settings in it');
    settingsGroups.set(body.groups);
    if (body.device) settingsDevice.set(body.device);
    settingsError.set(null);
  } catch (err) {
    console.warn('settings could not be loaded:', err.message);
    settingsError.set(err.message);
  }
}

let seenRevision;
playback.subscribe(($s) => {
  const revision = $s?.settings_revision;
  if (revision === undefined || revision === seenRevision) return;
  const first = seenRevision === undefined;
  seenRevision = revision;
  if (!first) loadSettings();
});

//: **A reconnect reads the settings again** (code review, 2026-10-12). The
//: revision is the core's own counter and starts at 0 with it, so a page
//: that outlives a core restart - the panel always does - can land on the
//: number it last saw and never hear that a plugin was put on or taken off
//: across the restart.
let lastConnection;
connection.subscribe((c) => {
  if (c === 'open' && lastConnection === 'reconnecting') loadSettings();
  lastConnection = c;
});

export const settingValues = derived(settingsGroups, ($groups) => {
  const values = {};
  for (const g of $groups) for (const r of g.rows) if (r.key) values[r.key] = r.value;
  return values;
});

//: **A request that never reached the player is an answer too** (code
//: review, 2026-10-12). These used to reject, and no caller caught it: a
//: Wi-Fi blip on the phone left a sheet on *Joining…* or a list spinning,
//: with no button to leave by. Each now comes back as the refusal it is, in
//: the shape its callers already handle.
export const UNREACHED = 'The player did not answer. Check the connection and try again.';

//: **A request that hangs ends too** (George, 2026-10-12, answer 10). One
//: the player took but never answered - a phone gone to sleep on the way, a
//: connection dropped without a reset - spun for ever, as a rejected one
//: used to; it is given up after this long and ends as one that never
//: arrived. ADR-0022 inventory: both are hardcoded.
export const REQUEST_TIMEOUT_MS = 20_000;
//: What is slow on purpose: joining a Wi-Fi network (the core allows nmcli
//: 45 s), a scan (20 s, then the list), changing an address, making or
//: restoring a backup, a plugin's upload or removal, finding and browsing
//: network shares (15 s per look, two kinds), preparing a problem report.
export const LONG_REQUEST_TIMEOUT_MS = 120_000;
//: A restore answers only once it has put every file back, and a backup
//: holds the lyrics-and-info cache, which may now grow to a tenth of the card
//: (George, 2026-10-12): it gets far longer than any other request.
export const RESTORE_TIMEOUT_MS = 15 * 60_000;

/** A request and its JSON answer within `ms`: `{response, body}`, `body`
 *  `{}` when the answer is not JSON. Throws an Error saying UNREACHED when
 *  the request did not reach the player or the answer did not come in
 *  time - the body is read inside the time too, since that can stall as
 *  well as the headers. */
export async function ask(url, options = {}, ms = REQUEST_TIMEOUT_MS) {
  const stop = new AbortController();
  const late = setTimeout(() => stop.abort(), ms);
  try {
    const response = await fetch(url, { ...options, signal: stop.signal });
    const body = await response.json().catch((err) => {
      if (stop.signal.aborted) throw err;
      return {};
    });
    return { response, body };
  } catch (err) {
    console.warn(`settings: ${url} ${stop.signal.aborted ? `did not answer in ${ms / 1000} s` : `did not reach the player: ${err.message}`}`);
    throw new Error(UNREACHED);
  } finally {
    clearTimeout(late);
  }
}
const reach = (url, options, ms) => ask(url, options, ms).catch(() => null);

//: The lists that go looking for longer than an ordinary request: a Wi-Fi
//: scan, and the network shares' search for servers.
const LONG_LISTS = new Set(['wifi', 'lyrion-server.shares']);
//: The per-item commands that take long: a join (Wi-Fi), a restore (also
//: `join`, on the backups list), and anything on the shares - a browse, or
//: a forget that unmounts (30 s allowed).
const longAction = (key, body) => body?.action === 'join' || key === 'lyrion-server.shares';
//: Action rows that are slow: making a backup.
const LONG_ACTIONS = new Set(['backup']);

/** A `list` row's items, fetched when its sheet opens (ADR-0044 §1). A Wi-Fi
 *  scan takes seconds and LMS discovery listens for 2.5 s, so this is slow on
 *  purpose and the sheet shows that it is searching. */
export async function listItems(key) {
  const got = await reach(`/settings/${key}/items`, {}, LONG_LISTS.has(key) ? LONG_REQUEST_TIMEOUT_MS : REQUEST_TIMEOUT_MS);
  if (!got) return { items: [], error: UNREACHED };
  const { response, body } = got;
  if (!response.ok) return { items: [], error: body.error ?? `HTTP ${response.status}` };
  return { items: body.items ?? [], error: body.error ?? null };
}

/** A per-item command: joining a network, forgetting one. A refusal comes
 *  back as `{ok: false, error}` with a 200, because "that password was not
 *  accepted" is an answer, not a broken request. */
export async function listAction(key, body) {
  const got = await reach(`/settings/${key}/items`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  }, key === 'restore' ? RESTORE_TIMEOUT_MS : longAction(key, body) ? LONG_REQUEST_TIMEOUT_MS : REQUEST_TIMEOUT_MS);
  if (!got) return { ok: false, error: UNREACHED, items: null, login: false };
  const { response, body: answer } = got;
  if (!response.ok) return { ok: false, error: answer.error ?? `HTTP ${response.status}` };
  if (answer.ok) await loadSettings();
  // `items` and `login` for a list that browses inside an item (ADR-0115's
  // network shares: a server's shares, or the login it wants first).
  // `notice` for a join while the cable is in (ADR-0123 as amended).
  return { ok: !!answer.ok, error: answer.error ?? null, items: answer.items ?? null, login: !!answer.login,
           notice: answer.notice ?? null };
}

/** An `action` row. Nothing called this before `reboot` was wired: `power`
 *  has never been, so the panel's only answer was the 409 flash. */
export async function runSetting(key) {
  const got = await reach(`/settings/${key}`, { method: 'POST' },
                          LONG_ACTIONS.has(key) ? LONG_REQUEST_TIMEOUT_MS : REQUEST_TIMEOUT_MS);
  if (!got) return { ok: false, status: 0, error: UNREACHED };
  const { response, body } = got;
  return { ok: response.ok, status: response.status, error: body.error };
}

export async function writeSetting(key, value) {
  const got = await reach(`/settings/${key}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value }),
  });
  if (!got) return { ok: false, status: 0, error: UNREACHED };
  const { response, body } = got;
  // The answer is the save; the list catches up behind it. Waiting for the
  // reload held the sheet's button disabled for seconds on the player
  // (George, 2026-10-05). **Once**: the answer names the revision the save
  // made, and the revision's broadcast for it is then not a second reload
  // (George, 2026-10-16: two full reloads followed each tap on sofapi). A
  // core before this sends none, and the reload runs as it did.
  if (response.ok) {
    if (typeof body.revision !== 'number') loadSettings();
    else if (body.revision !== seenRevision) {
      seenRevision = body.revision;
      loadSettings();
    }
  }
  return { ok: response.ok, status: response.status, error: body.error };
}
