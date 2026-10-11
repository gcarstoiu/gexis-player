// SPDX-License-Identifier: GPL-3.0-or-later
/**
 * **Copy text, on a page served over plain http** (George, 2026-10-11: the
 * Send step's Copy showed no tick). The player's page is `http://name.local`,
 * and browsers give the clipboard API only to secure pages: it threw, quietly,
 * every time. The older copy command still works there - a hidden text field,
 * selected, copied. Resolves true when the text was copied.
 */
export async function copyText(text) {
  if (window.isSecureContext && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Refused: the older way below.
    }
  }
  const field = document.createElement('textarea');
  field.value = text;
  field.setAttribute('readonly', '');
  // Off screen, and not zoomed into on a phone (16 px).
  Object.assign(field.style, { position: 'fixed', top: '-1000px', left: '0', fontSize: '16px', opacity: '0' });
  document.body.append(field);
  field.select();
  field.setSelectionRange(0, text.length);
  let copied = false;
  try {
    copied = document.execCommand('copy');
  } catch {
    copied = false;
  }
  field.remove();
  return copied;
}
