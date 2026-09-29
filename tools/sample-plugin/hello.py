#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""A sample uploaded plugin (ADR-0106): a service that says hello, keeps a file
in its own data folder, and reports what the sandbox lets it do. Package it
with ./package.sh and upload the .tar.gz from Settings -> Plugins on a phone."""
import json
import os
import socket
import time

socket_path = os.environ.get("GEXIS_PLUGIN_SOCKET", "/run/gexis/plugins.sock")
data = os.environ.get("STATE_DIRECTORY") or os.environ.get("GEXIS_PLUGIN_DATA", ".")
print(f"hello: uid {os.getuid()}, groups {os.getgroups()}, data {data}", flush=True)

conn = socket.socket(socket.AF_UNIX)
conn.connect(socket_path)
stream = conn.makefile("rw")
stream.write(json.dumps({"t": "hello", "contract": 1, "id": "hello", "kind": "service",
                         "name": "Hello (sample)", "unit": "gexis-uploaded-service@hello.service"}) + "\n")
stream.flush()
print(f"hello: the core said {stream.readline().strip()}", flush=True)

with open(os.path.join(data, "alive"), "w") as f:
    f.write(f"{time.time()}\n")
print("hello: wrote its own data folder", flush=True)

# What the sandbox should refuse (ADR-0106): anywhere outside that folder.
for place in ("/etc/gexis/hello-was-here", "/home/pi/hello-was-here",
              "/var/lib/gexis/hello-was-here", "/usr/local/lib/gexis/hello-was-here"):
    try:
        with open(place, "w") as f:
            f.write("x")
        print(f"hello: WROTE {place} - the sandbox did not stop it", flush=True)
    except OSError as exc:
        print(f"hello: refused {place} ({exc.strerror})", flush=True)
try:
    os.listdir("/dev/snd")
    print("hello: CAN SEE /dev/snd - a service should not", flush=True)
except OSError as exc:
    print(f"hello: no sound devices ({exc.strerror})", flush=True)

while True:
    time.sleep(60)
