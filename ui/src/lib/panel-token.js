// SPDX-License-Identifier: GPL-3.0-or-later
// ADR-0170: the panel proves itself. A plugin calls the player from loopback
// too, so the kiosk opens this page with the boot's token in its address
// (`#panel=…`), and the page sends it with every request to the player - and
// in the touchpad socket's address, since a socket sends no headers. A phone
// has no token and needs none.
const found = /(?:^#|&)panel=([^&]+)/.exec(location.hash);
export const panelToken = found ? decodeURIComponent(found[1]) : null;

if (panelToken) {
  const fetchOf = window.fetch.bind(window);
  window.fetch = (input, init = {}) => {
    const href = input instanceof Request ? input.url : String(input);
    if (new URL(href, location.href).origin !== location.origin) return fetchOf(input, init);
    const headers = new Headers(init.headers ?? (input instanceof Request ? input.headers : undefined));
    headers.set('X-Gexis-Panel', panelToken);
    return fetchOf(input, { ...init, headers });
  };
}
