// SPDX-License-Identifier: GPL-3.0-or-later
// ADR-0121: the phone as the panel's touchpad and keyboard. One socket,
// `/touchpad`, used by both sides: a phone sends moves, taps and typing; the
// panel sends whether its pointer is over a text field and whether one has
// focus. The core relays and never interprets.
//
// Opened only while something uses it (the panel while Phone touchpad is on,
// a phone while its volume sheet is open), and reopened with a backoff, as
// the `/state` socket is.

const RECONNECT_MIN_MS = 500;
const RECONNECT_MAX_MS = 5000;

export function openTouchpad(onMessage) {
  let socket = null;
  let closed = false;
  let delay = RECONNECT_MIN_MS;
  let retry;

  function url() {
    const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${location.host}/touchpad`;
  }

  function connect() {
    if (closed) return;
    const mine = new WebSocket(url());
    socket = mine;
    mine.addEventListener('open', () => (delay = RECONNECT_MIN_MS));
    mine.addEventListener('message', (event) => {
      try {
        onMessage(JSON.parse(event.data));
      } catch {
        // A message we cannot read is dropped; the next one stands alone.
      }
    });
    mine.addEventListener('close', () => {
      // A socket already replaced (below) does not schedule another.
      if (closed || socket !== mine) return;
      retry = setTimeout(connect, delay);
      delay = Math.min(delay * 2, RECONNECT_MAX_MS);
    });
  }

  //: **Back on screen, a new socket at once** (George, 2026-10-06: away to
  //: another app and back, the touchpad answered only after a reload). A
  //: phone browser sent to the background freezes the page; its socket can
  //: die without a close the page ever hears, or wait out the backoff. Open
  //: on a hidden page it is left alone.
  function fresh() {
    if (closed || document.visibilityState !== 'visible') return;
    clearTimeout(retry);
    delay = RECONNECT_MIN_MS;
    const old = socket;
    socket = null;
    old?.close();
    connect();
  }
  document.addEventListener('visibilitychange', fresh);
  window.addEventListener('pageshow', fresh);
  window.addEventListener('online', fresh);

  connect();
  return {
    send(message) {
      if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
    },
    close() {
      closed = true;
      document.removeEventListener('visibilitychange', fresh);
      window.removeEventListener('pageshow', fresh);
      window.removeEventListener('online', fresh);
      clearTimeout(retry);
      socket?.close();
    },
  };
}

/** Whether an element takes typed text (an input that is not a button, a
 *  checkbox or a slider; a textarea; anything content-editable). */
export function takesText(element) {
  if (!element) return false;
  if (element.isContentEditable) return true;
  if (element.tagName === 'TEXTAREA') return !element.disabled && !element.readOnly;
  if (element.tagName !== 'INPUT') return false;
  const type = (element.getAttribute('type') || 'text').toLowerCase();
  const typed = ['text', 'search', 'password', 'email', 'url', 'tel', 'number'];
  return typed.includes(type) && !element.disabled && !element.readOnly;
}

/** The text field an element stands for: itself, or the field its label
 *  holds - a tap anywhere on a labelled field (the search field's glyph,
 *  its padding, its "typing on phone") focuses the field, so the phone's
 *  keyboard must come up for it too (George, 2026-10-06: "only when I tap
 *  right at the beginning of the field"). */
export function fieldOf(element) {
  if (!element) return null;
  if (takesText(element)) return element;
  // A control that opens a search field, focused as it opens (the apps'
  // field-button, My Music's Search): the keyboard comes up with that tap.
  const opener = element.closest?.('[data-text-entry]');
  if (opener) return opener;
  const control = element.closest?.('label')?.control;
  return takesText(control) ? control : null;
}
