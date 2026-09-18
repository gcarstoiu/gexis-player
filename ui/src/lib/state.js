// SPDX-License-Identifier: GPL-3.0-or-later
//
// The playback model, as a store fed by the WebSocket - ADR-0023: "views
// subscribe; nothing reads the socket directly." This module is the only
// thing in the UI that knows a socket exists.
//
// Reconnection matters more here than in an ordinary web app: the panel's
// Chromium is expected to stay up for months without restarting (Phase 4
// criterion 1), so it will outlive any number of gexis-core restarts. A
// page that needed reloading after a daemon restart would quietly become a
// screen showing stale state with no way for anyone to notice.
import { writable, derived } from 'svelte/store';

/** Raw payload from `/state`, or null before the first frame arrives.
 *
 * Named `playback`, not `state`: Svelte 5 has a `$state` rune, and a store
 * called `state` makes every `$state` in every component ambiguous - the
 * compiler warns about exactly this. Renamed once here rather than in
 * every component that will import it. */
export const playback = writable(null);

/** 'connecting' | 'open' | 'reconnecting' - for showing the connection honestly. */
export const connection = writable('connecting');

const RECONNECT_MIN_MS = 500;
const RECONNECT_MAX_MS = 5000;

let socket = null;
let retryDelay = RECONNECT_MIN_MS;

function socketUrl() {
  const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${protocol}//${location.host}/state`;
}

export function connect() {
  socket = new WebSocket(socketUrl());

  socket.addEventListener('open', () => {
    connection.set('open');
    retryDelay = RECONNECT_MIN_MS;
  });

  socket.addEventListener('message', (event) => {
    try {
      playback.set(JSON.parse(event.data));
    } catch {
      // A frame we cannot parse is a bug on the publishing side; dropping
      // it keeps the last good state on screen rather than blanking it.
    }
  });

  socket.addEventListener('close', () => {
    connection.set('reconnecting');
    setTimeout(connect, retryDelay);
    // Backing off matters because the common cause of a close is the
    // daemon restarting, which takes seconds - a tight retry loop would
    // hammer it through its own startup.
    retryDelay = Math.min(retryDelay * 2, RECONNECT_MAX_MS);
  });

  socket.addEventListener('error', () => socket.close());
}

/** Convenience views, so components never reach into the payload shape. */
export const active = derived(playback, ($s) => $s?.active ?? null);
export const metadata = derived(playback, ($s) => $s?.metadata ?? null);
export const availability = derived(playback, ($s) => $s?.available ?? {});
export const volume = derived(playback, ($s) => $s?.volume ?? null);
export const handoff = derived(playback, ($s) => $s?.handoff ?? null);
export const handoffExemptPairs = derived(playback, ($s) => $s?.handoff_exempt_pairs ?? []);
/** What each renderer has (ADR-0037 §2's static layer), by renderer id. */
export const capabilities = derived(playback, ($s) => $s?.capabilities ?? {});
/** What the active renderer can do right now (ADR-0037 §2's "can now"). */
export const available = derived(playback, ($s) => $s?.controls?.available ?? []);
/** The active renderer's own shuffle (bool) and repeat ('off'|'all'|'one'). */
export const shuffle = derived(playback, ($s) => $s?.controls?.shuffle ?? null);
export const repeat = derived(playback, ($s) => $s?.controls?.repeat ?? null);
/** What LMS has queued, for the rail on now playing; null for the renderers
 *  that have no queue (ADR-0038 §1). */
export const queue = derived(playback, ($s) => $s?.queue ?? null);

/**
 * Commands go over REST, never the socket (ADR-0028). Returns the parsed
 * body on success and throws with the server's own message on failure -
 * "LMS unreachable" has to reach the user, which is the whole reason that
 * record chose REST.
 */
async function post(path, body) {
  const response = await fetch(path, {
    method: 'POST',
    headers: body ? { 'Content-Type': 'application/json' } : {},
    body: body ? JSON.stringify(body) : undefined,
  });
  const parsed = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(parsed.error ?? `HTTP ${response.status}`);
  return parsed;
}

export const activate = (rendererId) => post(`/renderer/${rendererId}/activate`);
export const setVolume = (percent) => post('/volume', { percent });
export const setMute = (muted) => post('/volume/mute', { muted });

/** ADR-0037: to whichever renderer is active. The result arrives on /state;
 *  the button shows what the renderer reports, never what was pressed. */
export const sendTransport = (command, body) => post(`/transport/${command}`, body);

/** Phase 5 criterion 8: the Visualization button raises the Peppy screen. */
export const showPeppy = () => post('/peppy/show');

/** The daemon cannot see touches - they land in whichever window owns the
 *  screen - so the panel tells it, to restart the unattended-playback timer
 *  (ADR-0036). Fire and forget: a failed report must never block a tap. */
export function reportTouch() {
  fetch('/touch', { method: 'POST' }).catch(() => {});
}
