// SPDX-License-Identifier: GPL-3.0-or-later
//
// The group (ADR-0166; design/source/22, picks 1a, 2a, 3a): what every
// surface draws from - `/state`'s `group` - the requests that change it, and
// the words each surface says of a player and of the group.
import { derived } from 'svelte/store';
import { playback } from './state.js';

/** This player's group as the core publishes it, or null alone. */
export const group = derived(playback, ($s) => $s?.group ?? null);

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

export const joinPlayer = (id) => post('/group/join', { player: id });
export const removePlayer = (id) => post('/group/remove', { player: id });
export const leaveGroup = () => post('/group/leave');
export const undoGroup = () => post('/group/undo');
export const setGroupMute = (muted) => post('/group/mute', { muted });
export const setMemberVolume = (id, percent) =>
  post(`/group/members/${encodeURIComponent(id)}/volume`, { percent });
export const setMemberMute = (id, muted) =>
  post(`/group/members/${encodeURIComponent(id)}/mute`, { muted });

/** **The *All* slider and a member's row while a finger moves them**: one
 *  request in flight, only the latest after it, as the volume slider sends.
 *  The *All* slider's drag keeps the members' levels as it began (`from`),
 *  so a drag down to nothing and back keeps the balance (the design's
 *  `_gBase`). */
export class LevelSender {
  #inFlight = false;
  #queued = null;
  #send;
  #onerror;

  constructor(send, onerror = () => {}) {
    this.#send = send;
    this.#onerror = onerror;
  }

  send(...args) {
    this.#queued = args;
    if (!this.#inFlight) this.#next();
  }

  async #next() {
    const args = this.#queued;
    if (args == null) return;
    this.#queued = null;
    this.#inFlight = true;
    try {
      await this.#send(...args);
    } catch (error) {
      this.#onerror(error);
    } finally {
      this.#inFlight = false;
      if (this.#queued != null) this.#next();
    }
  }
}

export const groupLevel = (percent, from) => post('/group/volume', { percent, from });

/** The levels the *All* slider's drag starts from: each reachable Variable
 *  member's own. */
export function dragStart(g) {
  const from = {};
  for (const m of g?.members ?? []) {
    if (m.reachable && !m.fixed && m.volume != null) from[m.id] = m.volume;
  }
  return from;
}

/** The members a drag moves, from where they were: the design's `dragGroup`,
 *  drawn before the core's answer comes back. */
export function stepped(from, target) {
  const ids = Object.keys(from);
  if (!ids.length) return {};
  const mean = ids.reduce((a, k) => a + from[k], 0) / ids.length;
  const out = {};
  for (const k of ids) out[k] = Math.max(0, Math.min(100, Math.round(from[k] + target - mean)));
  return out;
}

// -- words (design/source/22/README.md, *Words*) --------------------------------

/** "Living Room, Kitchen and Study". */
export function joinNames(names) {
  if (names.length < 2) return names.join('');
  return `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
}

/** The mark: `with Kitchen, Study`, and past two names `+ 3` - as
 *  [text, more]. Empty when not grouped. */
export function withText(g) {
  if (!g) return ['', ''];
  const others = g.members.filter((m) => !m.me).map((m) => m.name);
  if (others.length <= 2) return [`with ${others.join(', ')}`, ''];
  return [`with ${others.slice(0, 2).join(', ')}`, ` + ${others.length - 2}`];
}

/** What plays, as a player row says it: *Playing · Lyrion*, *Paused ·
 *  Spotify*, *Idle*. */
export function plays(transport, source) {
  if (transport === 'playing') return source ? `Playing · ${source}` : 'Playing';
  if (transport === 'paused') return source ? `Paused · ${source}` : 'Paused';
  return 'Idle';
}

/** A member's row in the group block. */
export function memberStatus(g, m) {
  if (!m.reachable) return m.leads ? 'Off · was leading the group' : 'Not reachable';
  if (m.joining) return 'Joining · catching up';
  if (m.leads) return plays(g.transport, g.source?.name);
  return g.silent ? 'In this group · silent' : 'In this group';
}

/** Another player's row, from what it says of itself (`/players`): in a
 *  group of its own, or playing alone. One older than multiroom says so. */
export function otherStatus(p) {
  const named = p?.group?.members?.filter((m) => m.id !== p.id).map((m) => m.name) ?? [];
  if (p?.group && named.length) {
    return `In a group with ${joinNames(named)}${p.renderer ? ` · ${p.renderer}` : ''}`;
  }
  const status = plays(p?.transport, p?.renderer);
  return p?.multiroom ? status : `${status} · Update to join`;
}

/** Whether another player can be joined from here. */
export const joinable = (p) => !!(p?.multiroom && p?.id);

/** The group head: *Grouped · 3 players*, or *Grouped · silent*. */
export function groupHead(g) {
  return g.silent ? 'Grouped · silent' : `Grouped · ${g.members.length} players`;
}

/** Under the head: what plays (*Playing · Lyrion · Rempompi*), or the
 *  leader gone (*Living Room is off*). */
export function groupSub(g) {
  if (g.silent) {
    const leader = g.members.find((m) => m.leads);
    return leader ? `${leader.name} is off` : 'The leader is off';
  }
  const what = plays(g.transport, g.source?.name);
  return g.title && g.transport !== 'stopped' ? `${what} · ${g.title}` : what;
}

/** The note when the leader is gone: who can start music and lead. */
export function silentNote(g, panel = false) {
  const live = g.members.filter((m) => m.reachable && !m.leads).map((m) => m.name);
  const leader = g.members.find((m) => m.leads)?.name ?? 'The leader';
  const who = live.length < 2 ? live.join('') : `${live.slice(0, -1).join(', ')} or ${live[live.length - 1]}`;
  return panel
    ? `${leader} is off. The group stays: start music on ${who} and it leads.`
    : `The group stays. Start music on ${who} and it leads.`;
}

/** *Undo the group?* - the body. With the leader gone there is no music to
 *  stay on it (the design's `undoBody`). */
export function undoBody(g) {
  const names = g.members.map((m) => m.name);
  const leader = g.members.find((m) => m.leads)?.name ?? names[0];
  const again = `${joinNames(names)} each play on their own again.`;
  return g.silent ? again : `${again} The music stays on ${leader}.`;
}

/** The sheet's sub-line: *3 players · each keeps its own level*. */
export const levelsSub = (g) => `${g.members.length} players · each keeps its own level`;

/** The note under the group volume's rows, naming Fixed members. */
export function fixedNote(g) {
  const fixed = g.members.filter((m) => m.fixed).map((m) => m.name);
  const base = 'The group slider moves each player by the same step, so the balance between rooms stays.';
  if (!fixed.length) return base;
  return `${base} ${joinNames(fixed)} ${fixed.length > 1 ? 'are' : 'is'} on Fixed volume: the amplifier sets the level.`;
}
