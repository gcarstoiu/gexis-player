// SPDX-License-Identifier: GPL-3.0-or-later
// Settings from the daemon's registry (ADR-0035), refetched whenever
// `settings_revision` moves so a change on one surface reaches the other.
import { writable, derived } from 'svelte/store';
import { playback } from './state.js';

export const settingsGroups = writable([]);
export const settingsError = writable(null);

export async function loadSettings() {
  try {
    const response = await fetch('/settings');
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    settingsGroups.set((await response.json()).groups);
    settingsError.set(null);
  } catch (err) {
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
  return { ok: !!answer.ok, error: answer.error ?? null };
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
  if (response.ok) await loadSettings();
  return { ok: response.ok, status: response.status, error: body.error };
}
