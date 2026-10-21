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
   - **typing** - key presses from a virtual keyboard (`/dev/uinput`), as a
     USB keyboard makes them: each character is found as a key, with the
     Shift or AltGr it needs, on the compositor's own layout (libxkbcommon,
     with labwc's `XKB_DEFAULT_*`; none set on the image, so US). Backspace,
     Enter and Tab are keys of the same keyboard. A character the layout
     lacks (`£`, `ä` on US) is left out and the phone says so.
     **Amended 2026-10-21, after George's test on sofapi:** the first build
     typed with `wlrctl keyboard type`, which this record said types any
     character. It types ASCII only (*"Only ascii strings are currently
     supported"*), and, one call per character as the phone sends them, lost
     characters - `test.user@example.com` arrived as `test.usereaple.co`;
     the same text in one call typed nothing. Key presses, five runs of a
     48-character mixed string one character at a time, plus a whole string
     at once, Backspace and Enter: all exact.
   The core does both, on the panel's request (`POST /panel/input`), as the
   panel user; the phone's keyboard comes up when its pointer taps a field in
   the frame, as it does for the player's own fields.
3. **Only the panel's session.** The input goes to the kiosk's compositor and
   nowhere else; whoever can use the phone page could already drive the panel.
4. **No setting.** It is how the touchpad works over a frame.

## Checked on sofapi (2026-10-21)

With a stand-in login page framed as the dashboard is:
- a tap through the virtual touchscreen focuses the field under the
  pointer (labwc maps the added device to the panel's output);
- typing as above, exact;
- the phone's keyboard comes up over the frame (`data-real-input`).

## Still open

- Characters outside the panel's layout cannot be typed; the phone says so.
- Whether a sign-in kept in the frame survives a reboot (not needed with
  trusted networks).
