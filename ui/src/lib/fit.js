// SPDX-License-Identifier: GPL-3.0-or-later
// ADR-0109, Bar family: text that has a box and must never leave it.
//
// `use:fitText={{ sizes: [[64, 1], [52, 2], ...], key }}` tries each size in
// turn - font size in px, and the most lines the text may take at it - and
// keeps the first at which nothing sticks out sideways and the lines are
// within the count. A bar is 400 logical px tall and as narrow as 1200, so a
// name the design drew at one size ("LMS") can be one that size cannot hold
// ("Squeezelite-ESP32", a single 454 px word at 52). When even the last size
// does not fit, the text may break inside a word rather than overflow.
//
// The element needs a definite width (a `max-width`, or `min-width: 0` in a
// flex row) and an explicit `line-height`. It runs again when `key` changes
// (pass the text), when the window resizes, and once the fonts are in.

export function fitText(node, options) {
  let opts = options;

  function fits(lines) {
    if (node.scrollWidth > node.clientWidth + 1) return false;
    if (!lines) return true;
    const lh = parseFloat(getComputedStyle(node).lineHeight);
    // Rounded: the glyphs of the last line stand a little below its line
    // box (about 0.15 em in Nunito at a tight line height), and
    // `scrollHeight` counts that.
    return !lh || Math.round(node.scrollHeight / lh) <= lines;
  }

  function run() {
    if (!node.isConnected) return;
    node.style.overflowWrap = '';
    node.style.wordBreak = '';
    for (const [px, lines] of opts.sizes) {
      node.style.fontSize = `${px}px`;
      if (fits(lines)) return;
    }
    node.style.overflowWrap = 'anywhere';
    if (opts.nowrapBreak) node.style.whiteSpace = 'normal';
  }

  run();
  // `fonts.ready` alone can resolve before a face this text uses has even
  // been asked for; `loadingdone` fires when one arrives.
  document.fonts?.ready.then(run);
  document.fonts?.addEventListener('loadingdone', run);
  window.addEventListener('resize', run);
  return {
    update(next) {
      opts = next;
      node.style.whiteSpace = '';
      run();
    },
    destroy() {
      window.removeEventListener('resize', run);
      document.fonts?.removeEventListener('loadingdone', run);
    },
  };
}
