// SPDX-License-Identifier: GPL-3.0-or-later
/**
 * Pictures that would not load, tried again later rather than never.
 *
 * Remembered for the life of the page, one failure (Lyrion's image proxy
 * during a rescan) left initials in place of a face until a reload - every
 * album artist on the bar (George, 2026-10-24). Each failure is now tried
 * again after each of `RETRY_MS`.
 */
const RETRY_MS = [15_000, 60_000, 300_000];

export function failures() {
  let failed = $state(new Set());
  const tries = new Map();

  return {
    has(url) {
      return failed.has(url);
    },
    mark(url) {
      if (!url || failed.has(url)) return;
      failed = new Set(failed).add(url);
      const n = tries.get(url) ?? 0;
      tries.set(url, n + 1);
      if (n >= RETRY_MS.length) return;
      setTimeout(() => {
        const next = new Set(failed);
        next.delete(url);
        failed = next;
      }, RETRY_MS[n]);
    },
  };
}
