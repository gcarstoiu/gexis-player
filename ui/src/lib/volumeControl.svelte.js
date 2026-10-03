// SPDX-License-Identifier: GPL-3.0-or-later
//
// The volume as the panel's drawer and the bar's tray both handle it (one copy
// since 2026-10-01): the level a finger is dragging, one request at a time,
// mute, and which level changes came from somewhere else.
import { setVolume, setMute } from './state.js';

//: A level change the panel did not cause - a phone, most often - opens the
//: drawer. Ours are recognised by a short window after each command; a
//: takeover restoring a renderer's remembered level is not a user action.
const OWN_WINDOW_MS = 1500;
const TAKEOVER_MS = 3000;

export class VolumeControl {
  dragging = $state(false);
  settling = $state(false);
  local = $state(0);
  toast = $state(null);

  #get;
  #toastTimer;
  #ownUntil = 0;
  #activeChangedAt = 0;
  #last = null;
  #lastActive;
  // One request at a time; while one is in flight only the latest value waits.
  #inFlight = false;
  #queued = null;

  /** `get` reads the component's props as they are now: `volume`,
   *  `active`, `onexternal`, `onsettled`. Construct during component set-up:
   *  it watches them. */
  constructor(get) {
    this.#get = get;
    $effect(() => {
      const active = this.#get.active();
      if (active !== this.#lastActive) {
        if (this.#lastActive !== undefined) this.#activeChangedAt = performance.now();
        this.#lastActive = active;
      }
    });
    $effect(() => {
      const volume = this.#get.volume();
      const current = volume ? `${volume.percent}/${volume.muted}` : null;
      const previous = this.#last;
      this.#last = current;
      if (previous === null || current === previous) return;
      const now = performance.now();
      if (now < this.#ownUntil || this.dragging || now - this.#activeChangedAt < TAKEOVER_MS) return;
      this.#get.onexternal()?.();
    });
  }

  get muted() {
    return !!this.#get.volume()?.muted;
  }
  get shown() {
    return this.dragging || this.settling ? this.local : (this.#get.volume()?.percent ?? 0);
  }
  get pct() {
    return this.muted ? 0 : this.shown;
  }

  #markOwn() {
    this.#ownUntil = performance.now() + OWN_WINDOW_MS;
  }

  flash(text) {
    this.toast = text;
    clearTimeout(this.#toastTimer);
    this.#toastTimer = setTimeout(() => (this.toast = null), 2200);
  }

  async send(percent) {
    if (this.#inFlight) {
      this.#queued = percent;
      return;
    }
    this.#inFlight = true;
    this.#markOwn();
    try {
      await setVolume(percent);
      this.#markOwn();
    } catch (err) {
      this.flash(`Volume not changed: ${err.message}`);
    } finally {
      this.#inFlight = false;
    }
    if (this.#queued !== null) {
      const next = this.#queued;
      this.#queued = null;
      await this.send(next);
    } else if (!this.dragging) {
      this.settling = false;
    }
  }

  /** The level under the finger, measured against `track` - the drawer's
   *  own slider, or the tray's rail rather than its taller touch area. */
  fromPointer(event, track) {
    const r = track.getBoundingClientRect();
    this.local = Math.round(Math.min(1, Math.max(0, (event.clientX - r.left) / r.width)) * 100);
    this.send(this.local);
  }

  down(event, track) {
    this.dragging = true;
    this.settling = true;
    event.currentTarget.setPointerCapture?.(event.pointerId);
    this.fromPointer(event, track);
  }

  move(event, track) {
    if (this.dragging) this.fromPointer(event, track);
  }

  up() {
    this.dragging = false;
    if (!this.#inFlight && this.#queued === null) this.settling = false;
    // **The drawer stops being held open when the finger leaves it**
    // (George, 2026-09-23: "the volume modal is not going away after the
    // 3s"). `onactivity` pins it on pointerdown so a drag is never cut off
    // mid-gesture; without a matching release the pin was permanent.
    this.#get.onsettled()?.();
  }

  async toggleMute() {
    const next = !this.muted;
    this.#markOwn();
    try {
      await setMute(next);
      this.#markOwn();
      this.flash(next ? 'Muted' : 'Unmuted');
    } catch (err) {
      this.flash(`Mute not changed: ${err.message}`);
    }
  }
}
