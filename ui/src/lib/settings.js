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
