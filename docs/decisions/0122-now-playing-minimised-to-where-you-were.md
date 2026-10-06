# ADR-0122 — Now Playing minimised, back to where you were

**Status:** **Accepted** — George, 2026-10-06, on four questions: *"1. Keep
both 2. The home screen on now playing is on the bottom left, not the top
left corner. But yes, the Chevron should be in top left corner. Let's see
how it looks and we might love it after. 3. Keep that 4. Agree."*
**Builds on:** [ADR-0118](0118-lyrion-s-own-menus.md) (Lyrion's menus, which
made the library deep), [ADR-0033](0033-idle-and-home.md) (the library
as the screen with nothing connected), [ADR-0109](0109-other-screens.md)
(the Bar family).

## Context

George, 2026-10-06: *"Now that we have the full navigation it is clear we
need to be able to give the user to show where he came from on the now
playing screen. What I think we should do is to have a minimize button for
now playing, which puts it in the mini strip and shows the screen the user
came from. For example if user is in Spotify playlists and starts a
playlist then for him to go back to the playlists overview is to track down
his steps all the way back to the playlists which is a huge chore."*

Until now the library was **unmounted** whenever Now Playing showed
(`App.svelte`: one screen mounted at a time over the shared backdrop), and
Now Playing's Home opened it afresh at its root. Where the user had been -
the path, the level's items, the scroll - was gone. With Lyrion's menus a
path is often four or five levels deep.

## Decision

1. **Home and Minimise, both** (George, 1). Home stays where it is (Now
   Playing's bottom left) and still opens the library at its root.
   **Minimise** is new: a downward chevron in Now Playing's **top left**
   (George, 2: "let's see how it looks"), and the same corner of the bar's
   strip. It shows the library as it was left, with the mini strip.
2. **The library is kept, not rebuilt.** While Now Playing is up the
   library stays mounted and is hidden (`display: none`), so its path,
   loaded levels and scroll positions survive as they are. A hidden layer
   lays nothing out and paints nothing; the rule "one screen at a time over
   the backdrop" is about what is *drawn*, and still holds. Home remounts it
   (its `{#key}`), as today.
3. **Starting playback does not change**: playing from the library switches
   to Now Playing only when nothing was playing before (George, 3).
4. **Not from the library** - Now Playing reached from the idle screen,
   Settings, or the phone's Now playing button - Minimise shows the library
   where it was last left, or its root if it was never opened (George, 4).

## Consequences

- The library's own timers and effects keep running while hidden. None of
  them draws, and they ran while it was open before; measured after the
  build is how a hidden library behaves on a Pi 4 over an hour (owed).
- The phone's Home (ADR-0101 amended) still means the root: it remounts the
  library, as Now Playing's Home does.
- With LMS off there is no library ([ADR-0079](0079-with-lms-off-the-panel-is-two-screens.md)): no Minimise either.
