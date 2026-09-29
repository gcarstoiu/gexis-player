# Writing a plugin for Gexis Player

A plugin adds something to the player that the player does not ship: a
**renderer** (a source of music, like a streaming receiver) or a **service**
(anything else that runs on the device, like a monitoring agent). This guide
takes you from an empty folder to a plugin installed from a phone.

- **The protocol** a plugin speaks is [PLUGIN-CONTRACT.md](PLUGIN-CONTRACT.md).
  This guide shows how to use it; the contract is the reference.
- **Why it works the way it does:** [ADR-0106](decisions/0106-plugins-you-install-and-update.md)
  (uploads and the sandbox), [ADR-0086](decisions/0086-a-plugin-declares-itself-in-a-manifest.md)
  (the manifest), [ADR-0088](decisions/0088-a-plugins-settings-reach-its-unit-as-environment.md)
  (settings as environment).
- **Two working examples** are in the repository: `tools/sample-plugin/` (a
  service) and `tools/sample-renderer/` (a renderer that plays a tone).

**A plugin you upload is not part of Gexis Player.** The person who installs it
is told so, and that it runs at their own risk and responsibility. What the
player guarantees is the sandbox it runs in, described below.

---

## 1. What a plugin is

A `.tar.gz` package with, at its **top level**:

```
plugin.json      what the plugin is (required)
mark.png         its mark, shown on the panel (optional, square, 256 px or more)
<your files>     the program and whatever it needs
```

The player unpacks it into `/var/lib/gexis/plugins/<id>/<version>/`, and
starts the command `plugin.json` names **from inside that folder**, under a
systemd unit the player writes for it. You never write a unit: a package that
brings one is refused.

## 2. The manifest: `plugin.json`

```json
{
  "id": "hello",
  "name": "Hello (sample)",
  "kind": "service",
  "version": "0.1.0",
  "run": "hello.py"
}
```

| Field | Required | Meaning |
|---|---|---|
| `id` | yes | Lowercase letters, digits and `-`, starting with a letter, 2-31 characters. It is the folder, the prefix of your settings, and a URL part. It may not be one of the player's own (`lms`, `spotify`, `bluetooth`, `plexamp`, `beszel`, …) |
| `name` | yes | What people see |
| `kind` | yes | `renderer` or `service` |
| `version` | yes | Letters, digits and `. + ~ -`, up to 40 characters. Uploading a different version updates the plugin; the same version again is refused |
| `run` | yes | The command to start, **relative to the package**. An **aarch64** program (the Pi 4 on a 64-bit system) or a script with a `#!` line |
| `label` | no | A renderer's status line for the moOde-compatible metadata file (`"Radio Foo Active"` style) |
| `accent` | no | A CSS colour for the panel's accent when your renderer plays |
| `status` | no | The waiting screen's second line under your mark (`"Ready"`, `"Pairable"`) |
| `settings` | no | Rows for **Settings**, below |

**Not allowed:** `unit` (the player writes it), paths that point outside the
package (`..`, absolute paths, links out), devices or pipes in the archive.

## 3. Where it runs: the sandbox

Every uploaded plugin runs under `gexis-uploaded-<kind>@<id>.service`:

| | |
|---|---|
| **User** | A temporary user made for each run - never root, never `pi` |
| **Can write** | Only its own data folder, `$STATE_DIRECTORY` (also `$GEXIS_PLUGIN_DATA`), kept across restarts and versions and deleted with the plugin. Plus its own `/tmp` |
| **Can read** | The system, read-only. **Not** `/home` |
| **Devices** | A **renderer** gets the sound cards (and the basics every program has, like `/dev/null`); a **service** gets no devices beyond those basics |
| **Network** | Open |
| **The player** | The plugin socket, `$GEXIS_PLUGIN_SOCKET` (`/run/gexis/plugins.sock`) |
| **Limits** | 512 MB of memory, 1.5 CPU cores, 128 tasks |
| **Restart** | Restarted 3 s after it exits with an error |

Your process starts **in its package folder** (`current/`), so relative paths
to your own files work.

Things that follow from this:

- **Keep state in `$STATE_DIRECTORY`**, never beside your program: the package
  folder is replaced on an update.
- **A program that expects `$HOME`** should be given one there:
  `export HOME=$STATE_DIRECTORY`.
- **A program that wants a config file** writes it into `$STATE_DIRECTORY`
  at start. `tools/sample-renderer/run.sh` shows the shape.

## 4. Talking to the player

Connect to the socket, send one JSON object per line, read one per line. The
plugin speaks first:

```python
import json, os, socket

conn = socket.socket(socket.AF_UNIX)
conn.connect(os.environ["GEXIS_PLUGIN_SOCKET"])
stream = conn.makefile("rw")

def send(message):
    stream.write(json.dumps(message) + "\n")
    stream.flush()

send({"t": "hello", "contract": 1, "id": "hello", "kind": "service",
      "name": "Hello (sample)", "unit": "gexis-uploaded-service@hello.service"})
welcome = json.loads(stream.readline())   # {"t": "welcome", "contract": 1, "settings": {...}}
```

- **`unit`** is optional in `hello`; if you give it, it must be
  `gexis-uploaded-<kind>@<id>.service`, the one the player gave you.
- **`welcome.settings`** holds the current value of each of your settings, by
  your own key (without the `<id>.` prefix). A `refused` instead of `welcome`
  closes the connection and says why.

**A service needs nothing else.** It can stay connected, or not connect at all
- the switch in Settings starts and stops its unit either way.

## 5. A renderer

A renderer plays music through the player's DAC and takes part in
**arbitration**: only one source plays at a time, and the newest deliberate
choice wins. Its `hello` says what it can do:

```json
{"t": "hello", "contract": 1, "id": "tone", "kind": "renderer", "name": "Tone (sample)",
 "release_action": "disconnect",
 "capabilities": {
   "audio_connection": "output",
   "acquisition_events": ["activate"],
   "supports_artwork": false,
   "supports_sample_rate": false,
   "volume_managed": false,
   "volume_mechanism": "software_api",
   "dummy_mixer_card": null,
   "volume_over_bluealsa": false,
   "controls": ["activate", "pause"]
 }}
```

**Play to the ALSA device `output`**, always - never to a card by number. The
player defines `output` and routes it to whichever DAC the user chose, with the
level meter tapped from it.

**The four messages that matter:**

| When | You send / receive | Do |
|---|---|---|
| Your user starts playing | send `{"t": "acquire"}` | Before you open `output`. The core stops whoever had the device first |
| You stop with nobody taking over | send `{"t": "release"}` | Safe to send any time |
| Another source takes over | receive `{"t": "release", "id": n}` | Stop playing, **close `output`**, answer `{"t": "ok", "id": n, "result": true}` |
| The panel's source button | receive `{"t": "activate", "id": n}` | Start playing if you can (then `acquire`), answer `ok` |

Every message from the player carries an `id` and wants **exactly one** answer,
`ok` or `error`. Answer `true` to the ones you have nothing to do for
(`device_freed`, `restart_after_release`, `signal_stop`).

**If you do not let go**, the player escalates: SIGTERM, then SIGKILL, on your
unit, and your unit restarts. Let go promptly and it never needs to.

**What the panel shows** comes from `{"t": "metadata", "metadata": {...}}`:
`title`, `artist`, `album`, `artwork` (a URL), `position` and `duration`
(seconds), `transport` (`playing`, `paused`, `stopped`), and more in the
contract. Send what you know; absent fields draw nothing.

**Volume.** With `volume_mechanism: "software_api"`, report your level with
`{"t": "volume", "value": 62, "steps": 100}` and apply `set_volume` when told.
The player keeps the DAC's own level separately; read ADR-0053 and ADR-0054
before you decide how yours behaves.

`tools/sample-renderer/` is a complete renderer in about a hundred lines of
Python: it plays a generated tone through `output` when the panel's button is
pressed, and stops when another source takes over.

## 6. Settings

A plugin can add rows to **Settings**. They appear under Sources (a renderer)
or System (a service), under your name:

```json
"settings": [
  {"key": "server", "type": "text", "label": "Server", "note": "Where to connect.",
   "placeholder": "http://example:8000", "default": null, "env": "SERVER"},
  {"key": "token", "type": "text", "label": "Token", "secret": true,
   "default": null, "env": "TOKEN"}
]
```

- **You read them two ways.** At `welcome`, by your own key, and on
  `{"t": "setting", "key": ..., "value": ...}` when one changes while you run.
  **Or** as environment variables: a row with `env` is exported to your unit's
  environment, and your unit is restarted when it changes. The second is the
  way to configure a program that does not speak the protocol.
- **Types** are the player's own row types (`text`, `toggle`, `choice` with
  `options`, and others); see ADR-0044 and `core/src/gexis_core/settings_registry.json`
  for their vocabulary.
- **`secret: true`** masks a value on the screen. It is **not** encryption: the
  settings are readable on the local network.
- **Every plugin gets an on/off switch** it did not declare. An uploaded plugin
  arrives **off**.

## 7. Package, install, update, remove

**Package** from inside your folder, so `plugin.json` is at the top:

```sh
tar -czf hello-0.1.0.tar.gz plugin.json hello.py mark.png
```

**Install** from a phone or computer: **Settings → Plugins → Upload a plugin**,
choose the file, confirm the notice. The player checks the package before
writing anything, and says why if it refuses. It restarts itself once to show
the new plugin, which arrives **switched off**.

The checks, so you can pass them first time:

- `plugin.json` at the top, readable JSON, with `id`, `name`, `kind`,
  `version`, `run`, and no `unit`;
- `run` is in the package and is an aarch64 program or a `#!` script;
- no path or link escapes the package;
- under 200 MB, and under 600 MB unpacked.

**Update** by uploading a package with a different `version`. The version
before it is kept on the device for one step back; your data folder is kept.

**Remove** from the plugin's row (switch it off first). Its package, its data
folder and its settings are deleted.

**Backups** keep your plugin's settings and data, not its package. After a
restore, the plugin is listed as needing to be uploaded again.

## 8. When something does not work

On the device (`ssh pi@<name>.local`):

```sh
journalctl -u gexis-uploaded-service@hello -f     # your plugin's own output
journalctl -u gexis-core | grep -i hello          # what the player made of it
systemctl status gexis-uploaded-service@hello
sudo ls -la /var/lib/gexis/plugins/hello/         # versions and `current`
```

- **`status=127`** or a shell error on start: your `run` script failed before
  your program - read its first lines of output.
- **`Permission denied` on the socket**: the unit is not one of the player's
  (you started it by hand as another user). Use the switch in Settings.
- **`Read-only file system`**: you wrote outside `$STATE_DIRECTORY`.
- **No sound from a renderer**: you opened a card by number or `default`
  instead of `output`, or you did not send `acquire` first.

`tools/sample-plugin/hello.py` prints what the sandbox allows and refuses when
it starts, which is a quick way to see the environment for yourself.
