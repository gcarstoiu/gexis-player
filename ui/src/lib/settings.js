// SPDX-License-Identifier: GPL-3.0-or-later
// Settings from the daemon's registry (ADR-0035), refetched whenever
// `settings_revision` moves so a change on one surface reaches the other.
import { writable, derived } from 'svelte/store';
import { playback } from './state.js';

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
    const response = await fetch('/settings');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const body = await response.json();
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

export const settingValues = derived(settingsGroups, ($groups) => {
  const values = {};
  for (const g of $groups) for (const r of g.rows) if (r.key) values[r.key] = r.value;
  return values;
});

/** **Fixed output chosen but not yet in force, or left but still in force**
 *  (ADR-0046, amended 2026-10-10): the core changes it only when playback
 *  pauses or stops (ADR-0018), so the setting and the device disagree until
 *  then. George, on sofapi: "It was misleading as it was showing that fixed
 *  was turned on, when in fact it was not." `'on'` while Fixed waits to
 *  start, `'off'` while it waits to end, null when they agree - and null
 *  until both the settings and the state have arrived, so a page still
 *  loading does not claim a change is waiting. */
export const fixedPending = derived([settingValues, playback], ([$values, $state]) => {
  if (!$state || $values.output_mode === undefined) return null;
  const wanted = $values.output_mode === 'Fixed';
  const now = $state.fixed_output === true;
  return wanted === now ? null : wanted ? 'on' : 'off';
});

/** A `list` row's items, fetched when its sheet opens (ADR-0044 §1). A Wi-Fi
 *  scan takes seconds and LMS discovery listens for 2.5 s, so this is slow on
 *  purpose and the sheet shows that it is searching. */
export async function listItems(key) {
  const response = await fetch(`/settings/${key}/items`);
  const body = await response.json().catch(() => ({}));
  if (!response.ok) return { items: [], error: body.error ?? `HTTP ${response.status}` };
  return { items: body.items ?? [], error: body.error ?? null };
}

/** A per-item command: joining a network, forgetting one. A refusal comes
 *  back as `{ok: false, error}` with a 200, because "that password was not
 *  accepted" is an answer, not a broken request. */
export async function listAction(key, body) {
  const response = await fetch(`/settings/${key}/items`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  const answer = await response.json().catch(() => ({}));
  if (!response.ok) return { ok: false, error: answer.error ?? `HTTP ${response.status}` };
  if (answer.ok) await loadSettings();
  // `items` and `login` for a list that browses inside an item (ADR-0115's
  // network shares: a server's shares, or the login it wants first).
  return { ok: !!answer.ok, error: answer.error ?? null, items: answer.items ?? null, login: !!answer.login };
}

/** An `action` row. Nothing called this before `reboot` was wired: `power`
 *  has never been, so the panel's only answer was the 409 flash. */
export async function runSetting(key) {
  const response = await fetch(`/settings/${key}`, { method: 'POST' });
  const body = await response.json().catch(() => ({}));
  return { ok: response.ok, status: response.status, error: body.error };
}

export async function writeSetting(key, value) {
  const response = await fetch(`/settings/${key}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ value }),
  });
  const body = await response.json().catch(() => ({}));
  // The answer is the save; the list catches up behind it. Waiting for the
  // reload held the sheet's button disabled for seconds on the player
  // (George, 2026-10-05).
  if (response.ok) loadSettings();
  return { ok: response.ok, status: response.status, error: body.error };
}
