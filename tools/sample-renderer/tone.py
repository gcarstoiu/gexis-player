#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""A sample renderer (docs/WRITING-A-PLUGIN.md): plays a quiet tone through the
player's `output` when its source button is pressed on the panel, and stops
when another source takes over. Standard library and `aplay` only."""
import json
import math
import os
import socket
import struct
import subprocess
import threading
import time
import wave

ID = "tone"
DATA = os.environ.get("STATE_DIRECTORY") or os.environ.get("GEXIS_PLUGIN_DATA", ".")
TONE = os.path.join(DATA, "tone.wav")
SECONDS = 20


def make_tone() -> None:
    """A 440 Hz tone at -20 dBFS: audible, never loud."""
    if os.path.exists(TONE):
        return
    rate, amplitude = 48000, 0.1 * 32767
    with wave.open(TONE, "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for n in range(rate * SECONDS):
            s = int(amplitude * math.sin(2 * math.pi * 440 * n / rate))
            frames += struct.pack("<hh", s, s)
        w.writeframes(bytes(frames))


class Plugin:
    def __init__(self) -> None:
        self.conn = socket.socket(socket.AF_UNIX)
        self.conn.connect(os.environ.get("GEXIS_PLUGIN_SOCKET", "/run/gexis/plugins.sock"))
        self.stream = self.conn.makefile("rw")
        self.lock = threading.Lock()
        self.player: subprocess.Popen | None = None

    def send(self, message: dict) -> None:
        with self.lock:
            self.stream.write(json.dumps(message) + "\n")
            self.stream.flush()

    def hello(self) -> None:
        self.send({
            "t": "hello", "contract": 1, "id": ID, "kind": "renderer", "name": "Tone (sample)",
            "release_action": "disconnect",
            "capabilities": {
                "audio_connection": "output",
                "acquisition_events": ["activate"],
                "supports_artwork": False,
                "supports_sample_rate": False,
                "volume_managed": False,
                "volume_mechanism": "software_api",
                "dummy_mixer_card": None,
                "volume_over_bluealsa": False,
                "controls": ["activate", "pause"],
            },
        })
        print("tone: the player said", self.stream.readline().strip(), flush=True)
        self.send({"t": "available", "available": True})

    def metadata(self, transport: str) -> None:
        self.send({"t": "metadata", "metadata": {
            "title": "A tone, 440 Hz", "artist": "Sample renderer", "album": "Gexis Player",
            "duration": float(SECONDS), "position": 0.0, "transport": transport,
        }})

    def play(self) -> None:
        """Take the device first, then open `output`. The previous source may
        still be letting go, so a busy device is tried again for a while."""
        if self.player and self.player.poll() is None:
            return
        self.send({"t": "acquire"})
        for _ in range(20):
            self.player = subprocess.Popen(["aplay", "-q", "-D", "output", TONE],
                                           stderr=subprocess.PIPE)
            time.sleep(0.4)
            if self.player.poll() is None:
                self.metadata("playing")
                threading.Thread(target=self.finished, daemon=True).start()
                return
            time.sleep(0.3)
        print("tone: output stayed busy; giving up", flush=True)
        self.send({"t": "release"})

    def finished(self) -> None:
        player = self.player
        if player is None:
            return
        player.wait()
        if player is self.player:
            self.player = None
            self.metadata("stopped")
            self.send({"t": "release"})

    def stop(self) -> None:
        player, self.player = self.player, None
        if player and player.poll() is None:
            player.terminate()
            player.wait()
        self.metadata("stopped")

    def serve(self) -> None:
        for line in self.stream:
            message = json.loads(line)
            kind, mid = message.get("t"), message.get("id")
            if kind == "activate":
                threading.Thread(target=self.play, daemon=True).start()
            elif kind == "release" or (kind == "transport" and message.get("command") == "pause"):
                self.stop()
            if mid is not None:
                self.send({"t": "ok", "id": mid, "result": True})


if __name__ == "__main__":
    make_tone()
    plugin = Plugin()
    plugin.hello()
    plugin.serve()
