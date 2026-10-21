# Finding 132 — Home Assistant framed by another page: what it takes in 2026.10

**Date:** 2026-10-21. **For:** ADR-0156 (Phase 18, `ph-ha-dashboard`), its
*Unverified* points.

## Scope

- **Tested:** a throwaway Home Assistant **2026.10.2** in Docker on R2D2
  (`ghcr.io/home-assistant/home-assistant:stable`, bound to 127.0.0.1),
  onboarded with a test user; a page on `http://127.0.0.1:9988` framing
  `http://localhost:8123/lovelace/0` - a different site, as a Home Assistant
  on `homeassistant.local` is to the player's `127.0.0.1:8090` - in
  Playwright's Chromium (build 1248), headless, driven over its debugging
  port in real time.
- **Not tested:** George's own Home Assistant (he declined changes to it,
  2026-10-21); the player's kiosk Chromium on a Pi; a sign-in by login form
  rather than trusted networks; whether a kept sign-in survives a reboot of
  the player; Home Assistant versions before 2026.10.

## Results

1. **As shipped, Home Assistant refuses to be framed**: every page answers
   with `X-Frame-Options: SAMEORIGIN`.
2. **From 2026.10 the `http:` lines in `configuration.yaml` no longer apply.**
   They are migrated into Home Assistant's own storage once
   (`yaml_migration_done`) and ignored after. A change is staged as
   *pending*, applied by a restart, and must be **promoted** within five
   minutes, or Home Assistant reverts to the previous settings and restarts:
   seen here - `use_x_frame_options: false` written in YAML after the first
   start was staged, never promoted, and rolled back (*"Pending HTTP config
   was not confirmed within 0:05:00; reverting to the stable config"*).
3. **The setting in Home Assistant's interface** is *Settings → System →
   Network → HTTP server → More options → **Send X-Frame-Options***, saved
   with *Save and restart*. Changed through the same API the page uses
   (`http/config/configure`, then `http/config/promote`), it stayed: the
   header was gone and the stored config had no pending change twenty
   seconds later. That the Network page promotes the change by itself when
   Home Assistant comes back is read from its code and wording (*"If Home
   Assistant is not confirmed reachable ... rolled back automatically after
   5 minutes"*), not watched.
4. **With the header off, the dashboard shows in the frame and works**, from
   another site, in Chromium's default settings.
5. **Trusted networks lets the frame in without a login**: `auth_providers`
   with `trusted_networks` (the Docker bridge's range) and
   `allow_bypass_login: true`, still read from `configuration.yaml` in
   2026.10. The dashboard opened as the only user, with no login page.
6. **Home Assistant's header and side bar show** inside the frame, as on any
   browser; hiding them is the dashboard's or the user's profile's.

## What changed because of it

- The manual names the setting in Home Assistant's interface and the
  five-minute confirmation, and gives the YAML line only for versions before
  2026.10.
- The panel's sentence for a refused frame (`dashboard.REASONS`) names
  *Send X-Frame-Options* first.
