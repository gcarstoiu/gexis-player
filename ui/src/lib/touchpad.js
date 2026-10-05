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
    socket = new WebSocket(url());
    socket.addEventListener('open', () => (delay = RECONNECT_MIN_MS));
    socket.addEventListener('message', (event) => {
      try {
        onMessage(JSON.parse(event.data));
      } catch {
        // A message we cannot read is dropped; the next one stands alone.
      }
    });
    socket.addEventListener('close', () => {
      if (closed) return;
      retry = setTimeout(connect, delay);
      delay = Math.min(delay * 2, RECONNECT_MAX_MS);
    });
  }

  connect();
  return {
    send(message) {
      if (socket?.readyState === WebSocket.OPEN) socket.send(JSON.stringify(message));
    },
    close() {
      closed = true;
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
