"""Minimal LMS CLI client (port 9090) for the Phase 2c test harness.

Protocol: connect, send space-separated URL-encoded fields terminated by
\\n, read one line back. See LMS's own "Logitech Media Server CLI"
documentation - fields are individually URL-encoded (colons in a MAC-style
playerid become %3A), not the whole line.
"""

import socket
import urllib.parse

LMS_HOST = "192.168.178.188"
LMS_CLI_PORT = 9090
GEXIS_PLAYER_ID = "e4:5f:01:58:89:07"


def _enc(s):
    return urllib.parse.quote(s, safe="")


class LmsCli:
    def __init__(self, host=LMS_HOST, port=LMS_CLI_PORT, timeout=5):
        self.sock = socket.create_connection((host, port), timeout=timeout)
        self.buf = b""

    def close(self):
        self.sock.close()

    def _readline(self):
        while b"\n" not in self.buf:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("LMS CLI closed the connection")
            self.buf += chunk
        line, _, self.buf = self.buf.partition(b"\n")
        return line.decode("utf-8", errors="replace")

    def command(self, *fields):
        """Sends fields (already logical, not yet encoded) and returns the
        raw response line, decoded fields (still URL-encoded per LMS's own
        convention - caller decodes only what it needs)."""
        line = " ".join(_enc(f) for f in fields) + "\n"
        self.sock.sendall(line.encode("utf-8"))
        return self._readline()

    def play(self, player_id=GEXIS_PLAYER_ID):
        return self.command(player_id, "play")

    def pause(self, player_id=GEXIS_PLAYER_ID, value=1):
        return self.command(player_id, "pause", str(value))

    def mode(self, player_id=GEXIS_PLAYER_ID):
        resp = self.command(player_id, "mode", "?")
        parts = resp.split(" ")
        return urllib.parse.unquote(parts[-1]) if parts else None


if __name__ == "__main__":
    import sys

    cli = LmsCli()
    try:
        cmd = sys.argv[1] if len(sys.argv) > 1 else "mode"
        if cmd == "play":
            print(cli.play())
        elif cmd == "pause":
            print(cli.pause())
        elif cmd == "mode":
            print(cli.mode())
    finally:
        cli.close()
