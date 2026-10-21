# ADR-0157 — The phone's touchpad and keyboard as real input on the panel

**Status:** **Accepted** — 2026-10-21 (George: *"Not all users might have a
keyboard at hand so if we can do it directly, then let's. This way we are
also consistent with behaviour of the panel and input from phone."*). Part of
Phase 18 (`ph-ha-dashboard`). Nothing built yet.

## Context

The phone's touchpad (ADR-0121) moves a pointer the panel's page draws, and
its taps and typing are made-up events and inserted text inside that page
(`PanelPointer.svelte`). A page from another site in a frame - the Home
Assistant dashboard (ADR-0156) - is closed to the player's page: its fields
cannot be focused, tapped or typed into from it. So the phone could not sign
in to Home Assistant (George, 2026-10-21: *"Keyboard is not popping up in the
login"*; LESSONS 79), while a finger on the glass and a USB keyboard could.

## Decision

1. **Over a framed page, the phone's input becomes real input.** When the
   phone's pointer is over the dashboard's frame, a tap there is a real touch
   at that point of the screen, and the phone's typing real key presses -
   travelling kernel/compositor → Chromium like a finger and a keyboard, so
   they reach Home Assistant's own page. Everywhere else the touchpad keeps
   working as it does today (the pointer, its outline, scrolling and zoom are
   the page's own and are not changed).
2. **How:**
   - **taps** - a virtual touchscreen through `/dev/uinput` at the screen's
     coordinates, as `tools/panel-touch.py` already does for measurements
     (Finding 032), so a tap lands exactly under the drawn pointer;
   - **typing** - the compositor's virtual keyboard (`wlrctl keyboard type`,
     already on the image for the visualiser), which types any character the
     phone sends, layout or not; Backspace and Enter as keys.
   The core does both, on the panel's request (`POST /panel/input`), as the
   panel user; the phone's keyboard comes up when its pointer taps a field in
   the frame, as it does for the player's own fields.
3. **Only the panel's session.** The input goes to the kiosk's compositor and
   nowhere else; whoever can use the phone page could already drive the panel.
4. **No setting.** It is how the touchpad works over a frame.

## Unverified

- That `wlrctl keyboard type` reaches a focused field inside a cross-site
  frame in the kiosk's Chromium on labwc, and types every character
  (accents, symbols) a phone keyboard sends.
- That the panel can tell when the phone's tap lands on a text field inside
  the frame - it cannot see inside it - so when to bring up the phone's
  keyboard: likely a tap over the frame always offers it.
- That a uinput touchscreen added at run time is mapped to the panel's output
  as the real one is (labwc's `<touch mapToOutput>`).
