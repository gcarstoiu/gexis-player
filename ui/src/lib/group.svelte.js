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
//: ADR-0166 decision 11: this player, in no group, joins another one whole.
export const enterGroup = (leader) => post('/group/enter', { leader });
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
 *  so a drag down to nothing and back gives their levels back (the design's
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

/** The members a drag moves, from where they were - drawn before the core's
 *  answer, by its rule (D6, `group.step_levels`): every member the same
 *  share of its own way, to 100 going up and to 0 going down, so the mean
 *  is where the finger is. */
export function stepped(from, target) {
  const ids = Object.keys(from);
  if (!ids.length) return {};
  const mean = ids.reduce((a, k) => a + from[k], 0) / ids.length;
  const t = Math.max(0, Math.min(100, target));
  const out = {};
  for (const k of ids) {
    const l = from[k];
    const v = t >= mean
      ? l + (mean >= 100 ? 0 : (t - mean) / (100 - mean)) * (100 - l)
      : l - (mean <= 0 ? 0 : (mean - t) / mean) * l;
    out[k] = Math.max(0, Math.min(100, Math.round(v)));
  }
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

/** Whether another player can be joined from here: one in no group of its
 *  own (ADR-0166 decision 11 - another group is joined whole, not raided). */
export const joinable = (p) => !!(p?.multiroom && p?.id) && !(p?.group?.members?.length > 1);

/** **The other players as they are now, seen from this one** (`self`, its
 *  id; `mine`, the ids in its group). `/players` is up to half a minute old:
 *  a group that names this player, though this player is not in it, was read
 *  before this player left it (sofapi, 2026-10-31: after *Undo group* the
 *  phone showed the other player's group still, this player in it *Not
 *  reachable*). This player is taken out of it; a group of one, or one this
 *  player led, is no group. */
export function withoutMe(others, self, mine = new Set()) {
  if (!self) return others ?? [];
  return (others ?? []).map((p) => {
    const members = p?.group?.members;
    if (mine.has(p?.id) || !members?.some((m) => m.id === self)) return p;
    const left = members.filter((m) => m.id !== self);
    return { ...p, group: left.length > 1 && p.group.leader !== self ? { ...p.group, members: left } : null };
  });
}

/** **The other players, another group's together** (ADR-0166 decision 11,
 *  George 2026-10-28: a group seen from outside it is a group, not loose
 *  players). `{loose, groups}`: a group is `{id, leader, title, status,
 *  members, canEnter}`, its leader first; a member the list has not found
 *  (switched off) is `listed: false`. `mine`: this player's own group's ids,
 *  left out. */
export function othersByGroup(others, mine = new Set()) {
  const loose = [];
  const found = new Map();
  for (const p of others ?? []) {
    if (mine.has(p.id)) continue;
    const gid = p?.group?.id;
    if (!gid || !(p.group.members?.length > 1)) {
      loose.push(p);
      continue;
    }
    if (!found.has(gid)) found.set(gid, { summary: p.group, listed: new Map() });
    found.get(gid).listed.set(p.id, p);
  }
  const groups = [...found.entries()].map(([id, { summary, listed }]) => {
    const leader = summary.leader;
    const lead = listed.get(leader);
    const members = (summary.members ?? [])
      .map((m) => ({ id: m.id, name: m.name, leads: m.id === leader, listed: listed.has(m.id),
                     url: listed.get(m.id)?.url ?? null }))
      .sort((a, b) => Number(b.leads) - Number(a.leads));
    const any = lead ?? [...listed.values()][0];
    return {
      id, leader, members,
      title: joinNames(members.map((m) => m.name)),
      status: lead ? plays(lead.transport, lead.renderer) : 'Its leader is off',
      // Joined through its leader, which has to be there and new enough.
      canEnter: !!(lead?.multiroom && any),
    };
  });
  return { loose, groups };
}

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
  const base = 'The group slider moves each player the same share of its way up or down, so a louder room stays louder.';
  if (!fixed.length) return base;
  return `${base} ${joinNames(fixed)} ${fixed.length > 1 ? 'are' : 'is'} on Fixed volume: the amplifier sets the level.`;
}
