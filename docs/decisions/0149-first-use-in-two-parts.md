# ADR-0149 — First use in two parts: set up, then make it yours

**Status:** **Accepted** — 2026-10-18: Claude Design's hand-off (*first use, parts 1 and 2*) given by George to build, with the decisions while building delegated to Claude (*"after the initial questions to me, I will let you make the decisions until completion of phase. Document them"*); they are below, under *Decisions taken while building*. Built on the branch `ph-first-use`, not merged. Proposed 2026-10-15. The direction is George's (2026-10-15,
*"Let's do it"*); the questions, answers and defaults below are for his review.
On acceptance it amends ADR-0031 (the setup network), ADR-0104 (what setup
needs), ADR-0128 (plugins and settling in setup) and ADR-0131 (restore in
setup). Phase 14, `ph-first-use`.

## Context

Setup today is one walk on the phone, over the setup network or the cable:
Network, Start (new or restore), Name, Time, Output, Music, Screen,
Visualiser, Plugins, Review. Then the player joins the home network and the
panel shows the downloads until it has settled (ADR-0128).

George (2026-10-15): *"have 2 parts. One like now on first boot, but only
with the device specific things to make it work like WiFi, display, audio,
device name and clock, and then another part shown once the player boots
that covers customisations that will make the player personalised to the
user and be driven by questions ... At the end of this small wizard we would
have the download part."* And before MPD, *"because mpd will add another
option of playing and indexing music ... for a person who is just starting
it might get too much."*

Three facts make the split worth more than tidiness:

- **The setup network is the fragile part** (Finding 126: a screen can jam
  its channel; a phone far away or among busy channels may not get in). The
  less is asked over it, the shorter that window.
- **Several questions work better on the home network**: finding a Lyrion
  server searches the LAN, which the setup network cannot see (today it
  searches once, after the join); a service's sign-in and every download need
  the internet.
- **What is downloaded follows from the choices** (skins, plugins), so the
  downloads belong at the end of the choosing, not of the device setup.

## Decision

### Part 1 — make it work (as today, shorter)

On the phone, over the setup network or the cable, unchanged in how it is
reached (ADR-0031, ADR-0104). Only what the player needs to run:

1. **Network** — Wi-Fi, or the cable.
2. **New player or a backup** (ADR-0131). A backup answers part 2 as well:
   after a restore part 2 is not offered.
3. **Name.**
4. **Time** — time zone and clock. The time zone also sets the Wi-Fi country,
   which is why it stays here.
5. **Output** — where the sound goes.
6. **Screen** — which screen, or none (Headless).
7. **Review**, then the player joins the home network and restarts if it must.

Gone from part 1: Music, Visualiser and Plugins.

### Part 2 — make it yours (new), on the phone

**On the phone** (George, 2026-10-15: *"It's where the user sets up the panel
in the first place and we have more control over the space. A bar might be
tough to accommodate for certain things."*). Part 1's last page already tells
the phone to go back to the home Wi-Fi and open the player's address; that
page now continues with part 2. **The panel**, meanwhile, shows a QR code to
the same page (*Make it yours on your phone*), and at the end the downloads.
Every question has a default and a **Later** that keeps the defaults and
leaves; the whole of part 2 can be run again from **Settings → System →
Personalise**.

| # | Question | Answers | Default | What it does |
|---|---|---|---|---|
| 1 | **What should the player's screen show?** (not asked without a screen) | *My music library, to browse, and what is playing* · *Only what is playing: I choose music on my phone and in apps* | none: an answer is needed (Later = the first) | The second turns **library navigation off on the screen** (below); the Lyrion client keeps running |
| 2 | **Lyrion Music Server**: plays your music files, and its apps can play to this player | a server found on the network (each listed) · *Enter an address* · *Install the Lyrion Server on this player* · *I don't use Lyrion* (not offered with the first answer to 1) | the one server found, if exactly one | `lms_server`; *Install* turns on the Lyrion Server plugin; *I don't use Lyrion* turns the Lyrion client off (`lms_enabled`), as today |
| 3 | **Which services?** | Spotify Connect · Plexamp · Bluetooth, each a switch | Spotify Connect and Bluetooth on, Plexamp off (as today) | `spotify_enabled`, `bt_enabled`, Plexamp's plugin switch. With nothing on and no Lyrion, the page says the player would have nothing to play |
| 4 | **On the screen** (not asked without a screen) | the visualiser yes/no · a clock and weather when nothing plays yes/no, and its place for the weather | visualiser: needs an answer as today; idle screen off (ADR-0133) | `visualiser_skins` (its pack downloads), `idle_enabled`, the weather's location |
| 5 | **Anything else to install?** | Beszel monitoring, and future plugins | off | the plugin switches |
| 6 | **Downloads** (ADR-0128's settling) | — | — | on the panel as today, and on the phone at the end of part 2 |

**Library navigation off, the Lyrion client on** (George, 2026-10-15: *"the
lyrion client is up and running but there is no library navigation on the
screen. This would be a modification of the current no lyrion client
enabled."*): the player is still a Lyrion player - Lyrion's apps, other
controllers and its radio play to it, and Now Playing shows what they play -
but the screen has no library, browse or Lyrion menus. Its home is the
waiting screen, as with the client off (ADR-0079, ADR-0133), with Lyrion
among the sources. Today's *client off* stays, for *I don't use Lyrion*.

**When Phase 15 (MPD) lands**, question 2 becomes *Where is your music?* and
gains *Music on this player or a share* (MPD); until then it is Lyrion's.

### Who sees it

- **A new player** - part 2 follows part 1 on the phone; the panel shows its
  QR code until it is done or put off. **Only until the first boot after
  setup** (George, 2026-10-18: *"automatic trigger of personalise flow should
  only be triggered on the first boot after setup has ran"*): unanswered by
  any later boot, it is put off as *Do it later* would (`personalise.at_start`,
  from the kernel's boot id). Opened from Settings, it lasts the boot it was
  opened in.
- **Without a screen** - questions 1 and 4 are not asked.
- **A restored player** - not offered; Settings has Personalise. (George,
  2026-10-18: *"the user already brought back all the settings he wanted"*.)
- **A player already set up** (an update) - not offered; Settings has
  Personalise.
- **After a factory reset** - both parts, as a new player.

## Settings (ADR-0022)

Proposed, not appended until George confirms:

- **[N] Library on the screen** - on / off; on by default, off from question
  1's second answer. Display (or Sources), beside the Lyrion client row,
  which it needs.
- *Personalise* is an action row in System, like *Reset to factory settings*
  (**moved to Display 2026-10-18**, George: *"most of the settings from
  Personalisation are display related"*);
  whether part 2 was finished or put off is state, not a setting. **Appended
  to ADR-0022 2026-10-18 on George's confirmation.**

## Open (George)

1. The questions and wording above.
2. **Library on the screen** as a setting ([N] above), and where it sits.
3. Settled 2026-10-15: *Only stream* keeps the Lyrion client and hides the
   library on the screen; part 2 runs on the phone, the panel showing a QR
   code to it and then the downloads.
4. Claude Design draws part 2 on the phone, the panel's QR and download
   screens (10.1", bars), and the shorter part 1, once 1-2 are settled.

## Not decided here

The look (Claude Design), and how part 2 is told apart from Settings for
someone who opens Personalise again.


## Decisions taken while building (Claude, delegated by George, 2026-10-18)

George answered three questions first: **Library on the screen** is a setting
in Sources → Lyrion Client (appended to ADR-0022); SofaPi tests **part 2
only**, through Settings → System → Personalise, without a reset; the work
lives on **its own branch**, `ph-first-use`, nothing merged. The rest was left
to Claude, and each choice is recorded here with its reason.

**How part 2 works**
1. **Answers are written at Finish, in one request** (`POST
   /personalise/finish`), never step by step. Back and the review then
   change nothing on the player, and one place on the core checks them: only
   part 2's own keys (`personalise.KEYS`), a request with any other key
   refused whole. *Why:* the design's review walks back into any step; a
   step that had already written would make Back a lie.
2. **Three steps act at once**, because they must: Plexamp's download
   (minutes, and the claim code needs it installed), a Bluetooth phone
   accepted, a network share added (it is browsed live with a login). Each
   uses the route Settings already uses.
3. **Plugins are only switched on, never off.** Found walking the page
   against sofapi with writes held: asked again from Settings, *My music +
   streaming* sent `plexamp.enabled: false` and would have removed Plexamp
   and its sign-in. Removing a plugin stays a choice in Settings → Plugins.
4. **Owed, done, put off** is the only state kept
   (`/var/lib/gexis/personalise.json`); `/state` carries `personalise:
   pending`. A new player's part 1 marks it owed once the join has worked
   (not a restore, not an update).
5. **Personalise in Settings marks it owed again.** The phone opens on it and
   the panel shows its code, exactly as for a new player. *Why:* one
   mechanism, and the panel says where to go whichever surface started it.
   On that run the page starts from what the player has now; on a new
   player's first run, from the design's defaults (the visualiser and the
   idle screen on, the weather off).
6. **The panel's code is a step of the existing setup screen**
   (`SetupScreen`, *Make it yours on your phone*), so the 10.1" panel and
   both bars get setup's tested layout. **Not now** on the panel puts part 2
   off, as *Do it later* does on the phone. *Why:* a player nobody scans for
   must not show a code for ever. No mobile-data warning there: the phone is
   on the home network.
7. ***Do it later* keeps the defaults**, and looks for a Lyrion server once,
   using it when exactly one answers. *Why:* part 1 did that before part 2
   existed; a player put off should still find its library.

**Part 1**
8. **Part 1 is the design's**: Network, Start, Name, Time, Output, Screen,
   *Check it over*. A restore asks Network, Start, the upload, **Output** and
   Screen, then *Check it over*. The design's restore path has no Output
   step: it is kept (the design's own Output screen) because George decided
   on 2026-10-08 that the output and the screen are asked on a restore - a
   0.9.5 restore put guestpi's DAC on a player with another one.
9. **A restore's review changes Network, Name, Output and Screen**; the time
   zone and the sources are listed as the backup's, as designed. The design
   lists the name as the backup's too. *Change* is kept on it, with the
   design's tick row *A second player* once it is changed, because ADR-0131
   as amended (George, 2026-10-08) and the FAQ and manual offer a backup made
   into a second player. Changing a restore's time zone or sources in setup,
   which the old review allowed, is gone: Settings does it after.
10. **The last page carries on by itself**, as the design says: once the
    setup network has gone (over a cable, after 15 s), the page asks
    `http://<name>.local:8090` every 4 s and opens it when it answers, where
    part 2 is owed. The address stays on the page for a phone whose browser
    does not find `.local` names. *Restoring*'s *Done* opens the same address.
11. **What the design does not draw is said in its own blocks**: a join that
    failed, a hidden network (*Other network*), setup over the cable, the
    upload's progress and refusals, choosing a zone by hand, a DAC board not
    listed, a list of screens that did not arrive, and Headless's
    setup-network note. Each is a `note`, `status`, `field` or list row, as
    the design draws them elsewhere.
**The questions**
11. **Lyrion found**: the server in use if it answers, else the first found;
    shown by its name (Phase 13's host names). Several are not listed here:
    Settings chooses among them.
12. **Lyrion on this player** sets `lms_server` to the player's own address
    and port 9000, as Settings' list offers it, and switches the Lyrion
    Server on. **Skip** on that step installs nothing.
13. **Folders**: the Music folder and USB drive are drawn ticked and do not
    untick. They are always offered to Lyrion (ADR-0115), and a switch for
    them would change nothing. Network shares use Settings' scan, sign-in and
    add.
14. **Browse**: Extended = Extended navigation on; Simple = off; Off =
    Library on the screen off.
15. **Wallpaper styles are one answer for both screens** (the design has
    one), written to the idle screen's and the waiting screen's.
16. **Starts after** offers 2, 10 or 30 min; a player whose timeout is
    something else starts on the nearest.
17. **Plex**: after the claim code is given the page says *"has its claim
    code"*, not *"on your Plex account"*: the player cannot confirm the
    account here.
18. **Headless** players still get part 2 on the phone (how you listen, the
    services); the screen's questions are skipped and the panel shows
    nothing.
19. The *Library service* row stays as drawn, marked *Next phase* (MPD,
    `ph-mpd`).

**The look** (revised 2026-10-18, after George: *"Check properly and let's do
it as it should be"*)
20. **The page is generated from the design files, not drawn after them.**
    `tools/design/gen_personalise.py` converts `Setup Prototype.dc.html`'s
    phone frame - markup, inline styles, keyframes - mechanically
    (`dc2svelte.py`), and keeps the prototype's script verbatim: its screens,
    paths, copy, Back and Next, animations and thumbnails. Where the
    prototype simulates the player, an asserted replacement calls the core
    instead (40 of them, each commented in the generator). `Panel Mini` and
    `Phone Device List` are generated the same way. *Why:* the first build
    redrew the screens by hand and drifted - animations, the Simple and
    Extended thumbnails, a review screen part 2 does not have. A generated
    page cannot drift without the generator saying so. The design files are
    kept in `design/source/14-first-use`.
21. **Part 2 has no review screen**: the design's path ends at *Getting
    ready*. Finish writes the answers there.
22. **The wide layout is the design's**: the preview in a left column and
    the animated *How will you listen?*, from 900 px wide.
23. **The design's font name is the player's**: *Nunito Sans* is the
    player's `Nunito Sans Variable`, listed first, so the same face draws.
24. **What is not the design's frame**: the mock-up phone's border, shadow
    and fixed 390 × 844 size; the page is the phone.
25. Checked side by side against the prototype at 390 × 844 and 1100 × 700,
    every part 1 and part 2 screen, with the player's real data.

**Added at George's request (2026-10-18)**
26. **A Touchpad step in part 2, before the visualiser** (*"just a note ...
    saying where more settings around the touchpad are and what these
    settings are"*): one switch, *Phone touchpad*, and one info note naming
    *Display → Touchpad* with Pointer speed and Pointer style; no new
    setting. Skipped without a screen. Its header is the panel preview (the
    library) with the player's teal pointer gliding and tapping, drawn with
    the design's tap ring; switched off, no pointer. Its colour is the one
    in the design's palette no step used (`#a8d68f`).
27. **The Output step asks the volume type** (Hardware, Software, Fixed),
    as Settings' Volume row offers it for the output chosen: Hardware is
    drawn as unavailable, with Settings' reason, on an output with no
    control of its own, and choosing such an output moves Hardware to
    Software. On a restore too, since the volume type follows this player's
    output. The Volume row's limits now change the moment an output is
    chosen, not when the switch runs, so a volume type written right after
    the output is judged against it.

28. **Getting ready shows the opening animation** (George: *"take the
    animation we have at the begining of the flow on wide and replace the
    current one, adding the status icon next to the panel"*): `PanelMini`'s
    `flow`, cycling through only the sources chosen, 3 s each; the badge on
    the panel's corner is the design's check when done and the design's own
    spinner ring while anything installs (an amber ! if something failed).
    The title follows the badge - *Getting Living Room ready*, then *Living
    Room is ready* - rather than one title for both, so it is never ahead of
    what the page shows.
29. **The Lyrion servers are known before part 2 asks** (George: *"the panel
    should already know if there is a lyrion server on the network"*): the
    core searches in the background (`discovery.Known`, every 2 min, every
    30 s while none answers) and answers from the last search.

30. **Every stage of a download is said** (George, testing part 2 on
    sofapi: *"Even if a download is at 100% but there is an install coming
    after then this should be transparent to the user. Same with starting a
    download"*): Getting ready reads each download's live status, the one
    Settings reads, and names its stage - starting, preparing, downloading
    with its MB, retrying, checking, installing, installed, did not finish.
    This replaces decision 28's wait for the settling record, which held a
    pack already installed at 0 % for 30 s (*"download of Vis skins was slow
    to start"* on sofapi, where the 1280 x 800 pack was already in). The
    panel's settling screen names the same stages, and the core reports the
    skins as preparing from the moment their install is asked for.
31. **Personalise sits at the top of Display** (George: *"since most of the
    settings from Personalisation are display related, let's move the
    setting to Display category"*); ADR-0022 says so.

32. **Plexamp is one screen** (George: *"basically everything happens in
    one screen not two"*): the design's *Plexamp* and *Sign in to Plex*
    become one step - the download's stage at the top, the claim code under
    it.
33. **Signed in to Plex is asked, not assumed** (George: *"verify if
    Plexamp is claimed unimportant if that happened during the setup flow or
    it was done in the past"*): the page reads the plugin's status on the
    Claim token row, which reads Plexamp's own token. Already claimed, the
    step says *<name> is on your Plex account* and asks nothing; a code
    pasted shows *Signing in to Plex* until Plexamp has signed in, or says
    why it did not. Before, a code accepted by the setting counted as
    signed in.
34. **The page is drawn once the player's values are in** (at most 3 s):
    until then the design's sample values (its name, its network) could
    show.

**After George's full run on sofapi (2026-10-18)**
35. **Part 2's panel screen comes first after setup's restart**: it shows as
    soon as part 2 is owed, its code filling in when the player's address
    arrives - the player's own screens no longer show first.
36. **Do it later, on a new player, is Spotify and Bluetooth** (George: the
    panel should show *"the waiting screen with the default sources (Spotify
    and Bluetooth) with the calm backgrounds"*): the Lyrion client goes off,
    no server is looked for. This replaces decision 7. Asked again from
    Settings, *Do it later* changes nothing.
37. **A Lyrion server part 2 sets is used at once** (George: after *My own
    mix*, a home screen *"without any functional tiles"*): a server is read at
    the core's start, so the core restarts once part 2's downloads are in.
38. **Picking the minutes closes the time picker**, so the time chosen shows
    before going on.
39. **Recommended is the best real output** (George: *"HDMI 1 ... makes no
    sense since those would be the embedded speakers of the display"*): a
    tested DAC, else any other DAC, never the Pi's HDMI or headphone jack; on
    a new player it is also chosen by default. The design marks the DAC; the
    first port marked the output already set.
40. **Headless is a list of its own**, under *No screen* (George: *"a
    completely different option"*).

41. **Every password field can be shown** (George: *"Had to rewrite the
    password multiple times because i was afraid I misspelled"*): the design's
    field gets an eye on its right - the Wi-Fi step and the share sign-ins -
    as Settings' password fields do.

**After George's test of 1.1.0 on sofapi (2026-10-19)**
42. **The visualiser's skins download at the visualiser step** (George:
    *"Download the visualiser skins during the setup flow similar to
    plexamp"*, so it is clear that setup goes on while they download; asked
    when, *"At the visualiser step"*). **The switch starts off, and turning
    it on is the answer that starts the download** (amended the same day,
    George: *"Skins should not download until a choice is made by the user.
    If toggle is set by default to enable then the user is seeing something
    happening without him actually taking any action"*; the first build
    started them as the step showed with the design's default, on). Turned
    on, the step switches `visualiser_skins` on once - the one write besides
    decision 2's three - and shows the download's stage under the switch
    with *The download carries on while you continue*. Turned off again, the
    download is not stopped; Finish removes the pack. Finish waits only for what is
    not in yet, so on most players only Lyrion is left for Getting ready. A
    No at Finish removes the pack, as switching it off in Settings does; put
    off with *Do it later* after the step, the pack stays with the
    visualiser on. The visualiser's restart for a new pack is held while part
    2 is owed, as it is under the settling screen, so it does not open over
    *Make it yours*.
43. **The panel follows Lyrion through its steps, on the waiting screen's
    plate** (George: the plate *"was showing something getting ready and
    then the next minute the library was there in full"*; asked how far,
    *"Through the read"*; then, the first build having put them in the
    settling dialog, *"The steps for lyrion in the panel should be in the
    plate not the modal. Make sure this works in the bars too"*). The
    waiting screen's *Lyrion is getting ready* / *is reading your music*
    (ADR-0115 decision 29) follows the phone's five steps - the download,
    its start, its add-ons, reading the music, ready. **As George approved
    it on renders** (*"Can we make the plate smaller so that it can be
    centered on the screen? ... just say something like step 1 of 7. Also
    in the title that is the most visible we should add the description of
    the current step"*; then *"Design looks fine"*): a smaller plate,
    centred, with *Lyrion · Step 3 of 5* above, the current step as its
    title (*Downloading Lyrion*, *Starting Lyrion*, *Adding Lyrion's
    add-ons*, *Reading your music*), the step's bar and Lyrion's own detail
    under it; on a bar the plate and smaller source marks are centred
    together beside the clock. The first build listed all five steps on a
    plate beside the clock. On a panel it is then made wider and set a
    little lower (George: *"make the plate wider ... and the clock doesn't
    feel squeezed in on the left"*), so its lines do not wrap and it keeps
    clear of the date. **A first read stays one until it ends**: Lyrion
    counts songs as it finds them, and "no songs yet" had ended the plate
    with the first song found.
    The core gives the Lyrion component its `steps` (`settling.lyrion_steps`).
    The settling dialog is for the other downloads: the record still marks
    the Lyrion server `follow`, so decision 37's restart waits for the
    downloads only, never for the read, and the dialog (`modal`) shows only
    while something other than Lyrion is in it, or Lyrion's download failed.
44. **The panel draws nothing until the core's first state is in** (George:
    *"Before the make it yours screen on panel is shown there is a blink of a
    second where the player is shown"*). Decision 35 put *Make it yours*
    first, but the panel learns that it is a panel (`/surface`) before it
    learns that part 2 is owed (the state socket), and drew its own screens
    in between.
45. **What is ticked on *Where is your music?* is added at Finish** (George:
    *"I selected network shares but nothing is there in lyrion"*): ticked
    USB folders and shares wait for the *Add* button under their list, and
    leaving the step by *Next* dropped them. Finish adds whatever is still
    ticked before it writes the answers, and stops with the reason if one
    cannot be added.

**Settled by George afterwards (2026-10-18)**
- **Personalise** is in ADR-0022's inventory (*"Yes it goes in the list"*).
- Part 1 is tested by George on sofapi after *Reset to factory settings*
  (*"I will do it manually on sofapi after a restore to factory settings"*),
  before the branch is merged.
