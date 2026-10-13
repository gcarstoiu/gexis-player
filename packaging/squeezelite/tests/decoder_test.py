#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""ADR-0145: Squeezelite's decoders, driven end to end without Lyrion.

A stand-in server speaks just enough of slimproto: it takes the player's
HELO, sets unity gain (audg) and sends one `strm s` naming a local file -
Squeezelite's own LocalPlayer extension (server 127.0.0.1:3483), which
streams the file from disk. The player writes what it would play to stdout
(`-o - -a 32`, 32-bit little-endian stereo), and that is measured: which
tone of which channel arrived on which side, at what level.

Run by run-decoder-tests.sh inside an amd64 Debian trixie container, with an
upstream build (`--upstream`) and the patched one (`--patched`):
  - stereo and mono files: the patched build's output is byte for byte the
    upstream build's (the fold-down leaves them alone);
  - multichannel files: every channel's tone is where ITU-R BS.775 puts it,
    the LFE nowhere, and the log says "downmix: N channels folded to stereo";
  - what upstream does with the same files, for the record;
  - AAC: FAAD2's own fold-down, checked the same way, and its level;
  - formats the patch leaves alone (Opus, Vorbis, ALAC), for the record.
"""
from __future__ import annotations

import argparse
import hashlib
import math
import os
import socket
import struct
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import numpy as np

R2 = math.sqrt(0.5)
AMP = 0.25            # every generated tone, as a fraction of full scale
RATES = "44100,48000,88200,96000,176400,192000,352800,384000"

# Un-normalised (left, right) shares by position, ffmpeg's default rematrix.
SHARE = {"FL": (1, 0), "FR": (0, 1), "FC": (R2, R2), "LFE": (0, 0), "BL": (R2, 0), "BR": (0, R2),
         "SL": (R2, 0), "SR": (0, R2), "BC": (0.5, 0.5)}
ORDER = {3: "FL FR FC", 4: "FL FR BL BR", 5: "FL FR FC BL BR", 6: "FL FR FC LFE BL BR",
         7: "FL FR FC LFE BC SL SR", 8: "FL FR FC LFE BL BR SL SR"}
TONES = [200, 300, 400, 60, 500, 600, 700, 800]   # channel c's tone; 60 Hz where the LFE is


def expected_shares(layout: str) -> list[tuple[float, float]]:
    pos = layout.split()
    sl = sum(SHARE[p][0] for p in pos)
    sr = sum(SHARE[p][1] for p in pos)
    n = max(sl, sr, 1.0)
    return [(SHARE[p][0] / n, SHARE[p][1] / n) for p in pos]


# --- test files ---------------------------------------------------------------

def tones(channels: int, rate: int, secs: float, freqs: list[float] | None = None) -> np.ndarray:
    t = np.arange(int(rate * secs)) / rate
    freqs = freqs or (TONES[:channels] if channels > 2 else [1000, 1500][:channels])
    return np.stack([AMP * np.sin(2 * np.pi * f * t) for f in freqs], axis=1)


def quantise(x: np.ndarray, bits: int) -> np.ndarray:
    return np.round(x * (2 ** (bits - 1) - 1)).astype(np.int64)


def pack(q: np.ndarray, bits: int, big: bool = False) -> bytes:
    b = bits // 8
    flat = q.reshape(-1).astype(np.int64) & ((1 << bits) - 1)
    out = np.zeros((flat.size, b), dtype=np.uint8)
    for i in range(b):
        out[:, (b - 1 - i) if big else i] = (flat >> (8 * i)) & 0xFF
    return out.tobytes()


def write_wav(path: Path, q: np.ndarray, bits: int, rate: int, mask: int | None = None) -> None:
    ch = q.shape[1]
    data = pack(q, bits)
    align = ch * bits // 8
    if mask is None:
        fmt = struct.pack("<HHIIHH", 1, ch, rate, rate * align, align, bits)
    else:   # WAVE_FORMAT_EXTENSIBLE, KSDATAFORMAT_SUBTYPE_PCM
        guid = bytes.fromhex("0100000000001000800000aa00389b71")
        fmt = struct.pack("<HHIIHHHHI", 0xFFFE, ch, rate, rate * align, align, bits, 22, bits, mask) + guid
    body = b"WAVE" + b"fmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(data)) + data
    path.write_bytes(b"RIFF" + struct.pack("<I", len(body)) + body)


def run(*cmd: str) -> None:
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def dsf_to_dff(dsf: Path, dff: Path, ids: list[bytes]) -> None:
    """A DSDIFF file of the same audio: bytes interleaved per channel, MSB first."""
    raw = dsf.read_bytes()
    ch = struct.unpack_from("<I", raw, 28 + 24)[0]
    fs = struct.unpack_from("<I", raw, 28 + 28)[0]
    n = struct.unpack_from("<Q", raw, 28 + 36)[0]
    data = np.frombuffer(raw[28 + 52 + 12:], dtype=np.uint8)
    blocks = data.reshape(-1, ch, 4096)                        # block b, channel c
    per_ch = blocks.transpose(1, 0, 2).reshape(ch, -1)[:, : (n + 7) // 8]
    rev = np.array([int(f"{i:08b}"[::-1], 2) for i in range(256)], dtype=np.uint8)
    inter = rev[per_ch].T.reshape(-1).tobytes()                # LSB first -> MSB first
    chnl = struct.pack(">H", ch) + b"".join(ids)
    prop = (b"SND " + b"FS  " + struct.pack(">QI", 4, fs)
            + b"CHNL" + struct.pack(">Q", len(chnl)) + chnl
            + b"CMPR" + struct.pack(">Q", 20) + b"DSD " + bytes([14]) + b"not compressed" + b"\0")
    body = (b"DSD " + b"FVER" + struct.pack(">QI", 4, 0x01050000)
            + b"PROP" + struct.pack(">Q", len(prop)) + prop
            + b"DSD " + struct.pack(">Q", len(inter)) + inter)
    dff.write_bytes(b"FRM8" + struct.pack(">Q", len(body)) + body)


# --- the stand-in server ------------------------------------------------------

def strm(fmt: str, path: str, size="?", rate="?", chans="?", endian="?") -> bytes:
    # autostart '3': the LocalPlayer extension takes 2 off it (no `cont` to wait for)
    pkt = b"strm" + struct.pack(">c c c c c c c B c B c B B B I H 4s",
                                b"s", b"3", fmt.encode(), size.encode(), rate.encode(), chans.encode(),
                                endian.encode(), 255, b"0", 0, b"0", 0, 0, 0, 0, 3483,
                                socket.inet_aton("127.0.0.1")) + path.encode()
    return struct.pack(">H", len(pkt)) + pkt


def audg_unity() -> bytes:
    pkt = b"audg" + struct.pack(">IIBBII", 0, 0, 1, 255, 0x10000, 0x10000)
    return struct.pack(">H", len(pkt)) + pkt


def play(binary: str, fmt: str, path: Path, extra: list[str], params=("?", "?", "?", "?"),
         timeout: float = 60) -> tuple[bytes, str]:
    """Plays one file; returns (stdout, log)."""
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 3483))
    srv.listen(1)
    log = tempfile.TemporaryFile()
    proc = subprocess.Popen([binary, "-s", "127.0.0.1", "-o", "-", "-a", "32", "-n", "test",
                             "-r", RATES, "-d", "decode=info", "-d", "output=info", *extra],
                            stdout=subprocess.PIPE, stderr=log)
    # Output to stdout is not paced: whenever the decoder is behind, the
    # player writes silence, in blocks of MAX_SILENCE_FRAMES (2048) - gigabytes
    # of it over a few seconds of audio. So each run of silent frames (0 on
    # both sides; 0x69696969, DSD's silence, for native DSD) loses whole blocks
    # of 2048 as it comes, and keeps the rest: the music's own silent frames
    # (a set of tones crosses zero together now and then) stay where they are.
    kept: list[bytes] = []

    def reader() -> None:
        rest = b""
        held = np.zeros((0, 2), dtype="<i4")   # silent frames at the end of the last chunk
        while True:
            chunk = proc.stdout.read(1 << 20)
            chunk = rest + chunk if chunk else rest
            n = len(chunk) // 8 * 8
            rest = chunk[n:]
            x = np.frombuffer(chunk[:n], dtype="<i4").reshape(-1, 2)
            x = np.concatenate([held, x])
            quiet = np.all(x == 0, axis=1) | np.all(x == 0x69696969, axis=1)
            edges = np.diff(np.concatenate([[0], quiet.astype(np.int8), [0]]))
            keep = np.ones(len(x), dtype=bool)
            held = held[:0]
            for a, b in zip(np.nonzero(edges == 1)[0], np.nonzero(edges == -1)[0]):
                if b == len(x) and n:             # may go on in the next chunk
                    keep[a:b] = False
                    held = x[a:b].copy()
                else:
                    keep[a: a + (b - a) // 2048 * 2048] = False
            kept.append(x[keep].tobytes())
            if not n:
                break

    rt = threading.Thread(target=reader)
    rt.start()
    done = threading.Event()
    try:
        srv.settimeout(10)
        conn, _ = srv.accept()
        conn.settimeout(1)
        conn.sendall(audg_unity() + strm(fmt, str(path), *params))
        buf = b""
        deadline = time.time() + timeout
        while time.time() < deadline and proc.poll() is None:
            try:
                chunk = conn.recv(4096)
            except socket.timeout:
                continue
            if not chunk:
                break
            buf += chunk
            while len(buf) >= 8:
                op, n = buf[:4], struct.unpack(">I", buf[4:8])[0]
                if len(buf) < 8 + n:
                    break
                if op == b"STAT" and buf[8:12] == b"STMu":   # played to the end
                    done.set()
                buf = buf[8 + n:]
            if done.is_set():
                break
        conn.close()
    finally:
        srv.close()
        proc.terminate()          # this process, by its own PID
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        rt.join()
    log.seek(0)
    text = log.read().decode(errors="replace")
    if not done.is_set():
        text += f"\n[test] no STMu (end of output) within {timeout}s; exit {proc.returncode}"
    return b"".join(kept), text


# --- measuring ----------------------------------------------------------------

def out_rate(log: str) -> int:
    """The rate the player chose for the track, from its own log."""
    for line in log.splitlines():
        if "track start sample rate:" in line:
            return int(line.split("track start sample rate:")[1].split()[0])
    return 0


def frames(raw: bytes) -> np.ndarray:
    return np.frombuffer(raw[: len(raw) // 8 * 8], dtype="<i4").reshape(-1, 2)


def amplitude(x: np.ndarray, hz: float, rate: int) -> float:
    """Of a whole second taken from the middle, as a fraction of full scale."""
    mid = len(x) // 2
    seg = x[mid - rate // 2: mid - rate // 2 + rate].astype(np.float64) / 2 ** 31
    t = np.arange(len(seg)) / rate
    return float(2 * abs(np.dot(seg, np.exp(-2j * np.pi * hz * t))) / len(seg))


class Report:
    def __init__(self) -> None:
        self.failed = 0
        self.passed = 0

    def check(self, ok: bool, what: str) -> None:
        print(("  ok   " if ok else "  FAIL ") + what)
        if ok:
            self.passed += 1
        else:
            self.failed += 1


def check_fold(rep: Report, x: np.ndarray, rate: int, layout: str, freqs: list[float], scale: float,
               tol: float, relative_to_fl: bool = False) -> None:
    shares = expected_shares(layout)
    if len(x) < rate * 2:
        rep.check(False, f"{len(x)} frames of output, too short to measure")
        return
    measured = {(f, s): amplitude(x[:, s], f, rate) for f in freqs for s in (0, 1)}
    g = measured[(freqs[0], 0)] / (AMP * shares[0][0]) if relative_to_fl else scale
    if relative_to_fl:
        rep.check(g > 0.5, f"front left's tone is there at {g:.3f} of its level in the file")
    for (pos, f, (wl, wr)) in zip(layout.split(), freqs, shares):
        for side, want in ((0, wl), (1, wr)):
            got = measured[(f, side)]
            exp = AMP * want * g
            ok = abs(got - exp) <= tol * max(AMP * g, 1e-9)
            rep.check(ok, f"{pos:>3} {f:>4.0f} Hz on {'L' if side == 0 else 'R'}: {got:.5f} (expected {exp:.5f})")


# --- the cases ----------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--upstream", required=True)
    ap.add_argument("--patched", required=True)
    ap.add_argument("--dsfgen", required=True)
    ap.add_argument("--only", default="", help="run only the cases whose title contains this")
    a = ap.parse_args()
    rep = Report()
    w = Path(tempfile.mkdtemp())

    print("== generating test files")
    files = {}
    # stereo and mono, for byte-for-byte comparison
    write_wav(w / "st16.wav", quantise(tones(2, 44100, 3), 16), 16, 44100)
    write_wav(w / "st24.wav", quantise(tones(2, 96000, 3), 24), 24, 96000)
    write_wav(w / "mono16.wav", quantise(tones(1, 44100, 3), 16), 16, 44100)
    for n in ("st16", "st24", "mono16"):
        run("flac", "-s", "-f", "--channel-map=none", "-o", str(w / f"{n}.flac"), str(w / f"{n}.wav"))
    (w / "st24.pcm").write_bytes(pack(quantise(tones(2, 96000, 3), 24), 24))
    run(a.dsfgen, str(w / "st.dsf"), "64", "3")
    # multichannel
    for ch, rate, bits in ((3, 44100, 16), (4, 44100, 16), (5, 48000, 24), (6, 48000, 24), (7, 48000, 16), (8, 96000, 24)):
        q = quantise(tones(ch, rate, 3), bits)
        write_wav(w / f"mc{ch}.wav", q, bits, rate)
        run("flac", "-s", "-f", "--channel-map=none", "-o", str(w / f"mc{ch}.flac"), str(w / f"mc{ch}.wav"))
        (w / f"mc{ch}.pcm").write_bytes(pack(q, bits))
        files[ch] = (rate, bits)
    # a WAV whose mask is not the default order: 4 channels FL FR FC BC
    write_wav(w / "mask4.wav", quantise(tones(4, 48000, 3), 24), 24, 48000, mask=0x107)
    # AIFF 5.1, big-endian
    q6 = quantise(tones(6, 48000, 3), 24)
    (w / "mc6be.pcm").write_bytes(pack(q6, 24, big=True))
    run("sox", str(w / "mc6.wav"), str(w / "mc6.aiff"))
    run(a.dsfgen, str(w / "mc6.dsf"), "64", "3", "6")
    dsf_to_dff(w / "mc6.dsf", w / "mc6.dff", [b"MLFT", b"MRGT", b"C   ", b"LFE ", b"LS  ", b"RS  "])
    dsf_to_dff(w / "st.dsf", w / "st.dff", [b"SLFT", b"SRGT"])
    # the formats left alone, for the record
    run("ffmpeg", "-y", "-i", str(w / "mc6.wav"), "-c:a", "aac", "-b:a", "384k", "-f", "adts", str(w / "mc6.aac"))
    run("ffmpeg", "-y", "-i", str(w / "mc6.wav"), "-c:a", "libopus", "-b:a", "256k", str(w / "mc6.opus"))
    run("ffmpeg", "-y", "-i", str(w / "mc6.wav"), "-c:a", "libvorbis", str(w / "mc6.ogg"))
    run("ffmpeg", "-y", "-i", str(w / "mc6.wav"), "-c:a", "alac", "-movflags", "+faststart", str(w / "mc6.m4a"))

    print("\n== stereo and mono: the patched build plays exactly what upstream plays")
    same = [("f", "st16.flac", (), []), ("f", "st24.flac", (), []), ("f", "mono16.flac", (), []),
            ("p", "st16.wav", (), ["-W"]), ("p", "st24.pcm", ("2", "9", "2", "1"), []),
            ("d", "st.dsf", (), []), ("d", "st.dsf", (), ["-D", ":u32be"]), ("d", "st.dff", (), [])]
    for fmt, name, params, extra in ([] if a.only else same):
        params = params or ("?", "?", "?", "?")
        up, _ = play(a.upstream, fmt, w / name, extra, params)
        pa, plog = play(a.patched, fmt, w / name, extra, params)
        up, pa = frames(up), frames(pa)
        h = lambda x: hashlib.sha256(x.tobytes()).hexdigest()[:16]
        rep.check(len(pa) > 44100 and h(up) == h(pa) and "downmix" not in plog,
                  f"{name} {' '.join(extra)}: {len(pa)} frames, sha256 {h(pa)} (upstream {len(up)} frames, {h(up)})")

    print("\n== multichannel through the patched build")
    cases = []
    for ch, (rate, bits) in files.items():
        cases.append((f"mc{ch}.flac (FLAC {ch}ch {bits}/{rate})", "f", f"mc{ch}.flac", (), [], rate, ORDER[ch], ch))
        sizes = {16: "1", 24: "2"}
        rates = {44100: "3", 48000: "4", 96000: "9"}
        cases.append((f"mc{ch}.pcm (WAV {ch}ch {bits}/{rate} as Lyrion streams it: header stripped, format in strm)",
                      "p", f"mc{ch}.pcm", (sizes[bits], rates[rate], str(ch), "1"), [], rate, ORDER[ch], ch))
    # -W: the header read by the player, not the server's parameters (a short
    # file is otherwise all buffered, and so not read as a file, before decoding)
    cases.append(("mc6.wav (WAV read from its own header)", "p", "mc6.wav", (), ["-W"], 48000, ORDER[6], 6))
    cases.append(("mask4.wav (WAVE_FORMAT_EXTENSIBLE, mask FL FR FC BC)", "p", "mask4.wav", (), ["-W"], 48000, "FL FR FC BC", 4))
    cases.append(("mc6.aiff (AIFF 5.1 from its header)", "p", "mc6.aiff", (), ["-W"], 48000, ORDER[6], 6))
    cases.append(("mc6be.pcm (AIFF 5.1 as Lyrion streams it: big-endian)", "p", "mc6be.pcm", ("2", "4", "6", "0"), [], 48000, ORDER[6], 6))
    for fmt, name, params, extra, rate, layout, ch in [
            ("d", "mc6.dsf", (), [], 352800, "FL FR FC LFE BL BR", 6),
            ("d", "mc6.dsf", (), ["-D", ":u32be"], 352800, "FL FR FC LFE BL BR", 6),
            ("d", "mc6.dff", (), [], 352800, "FL FR FC LFE BL BR", 6),
            ("d", "mc6.dff", (), ["-D", ":dop"], 352800, "FL FR FC LFE BL BR", 6)]:
        cases.append((f"{name} {' '.join(extra)} (DSD64 5.1)".replace("  ", " "), fmt, name, params, extra, rate, layout, ch))

    for title, fmt, name, params, extra, rate, layout, ch in cases:
        if a.only not in title:
            continue
        print(f"-- {title}")
        params = params or ("?", "?", "?", "?")
        raw, log = play(a.patched, fmt, w / name, extra, params)
        x = frames(raw)
        line = next((l for l in log.splitlines() if "downmix:" in l), "")
        rep.check(f"downmix: {ch} channels folded to stereo ({layout}" in line, f"log: {line.split('] ', 1)[-1].strip() or '(none)'}")
        got_rate = out_rate(log)
        rep.check(got_rate == rate, f"played at {got_rate} Hz (expected {rate})")
        if a.only:
            print("\n".join("      | " + l for l in log.splitlines()[-25:]))
        if name.endswith((".dsf", ".dff")):
            freqs = [200 + 100 * c if c != 3 else 60 for c in range(ch)]
            # DSD: through a sigma-delta modulator and dsd2pcm's filter, so
            # levels are taken relative to the front left's, to 2 %
            check_fold(rep, x, rate, layout, freqs, 1.0, 0.02, relative_to_fl=True)
            if extra:
                rep.check("converted to PCM" in line, "native DSD asked for, PCM given (one-bit audio cannot be mixed)")
        else:
            bits = files.get(ch, (0, 24))[1] if name.startswith("mc") else 24
            q = (2 ** (bits - 1) - 1) / 2 ** (bits - 1)
            freqs = TONES[:ch]
            check_fold(rep, x, rate, layout, freqs, q, 1e-4)

    if not a.only or a.only in "mc6.aac":
        print("\n== AAC 5.1: FAAD2's own fold-down (downMatrix), which the patch only logs")
        raw, log = play(a.patched, "a", w / "mc6.aac", [], ("2", "?", "?", "?"))
        x = frames(raw)
        line = next((l for l in log.splitlines() if "downmix:" in l), "")
        rep.check("downmix: 6 channels folded to stereo (by FAAD2)" in line, f"log: {line.split('] ', 1)[-1].strip() or '(none)'}")
        # lossy: the shares to 3 % of the front left's level
        check_fold(rep, x, 48000, ORDER[6], TONES[:6], 1.0, 0.03, relative_to_fl=True)
        fl = amplitude(x[:, 0], 200, 48000)
        ours = AMP / (1 + 2 * R2)
        print(f"  level: front left {fl:.4f} of full scale; the FLAC fold gives {ours:.4f} "
              f"({20 * math.log10(fl / ours):+.1f} dB)")

    print("\n== the same multichannel files through upstream, for the record")
    for fmt, name, params in [] if a.only else (("f", "mc6.flac", ()), ("p", "mc6.pcm", ("2", "4", "6", "1")), ("d", "mc6.dsf", ())):
        raw, log = play(a.upstream, fmt, w / name, [], params or ("?", "?", "?", "?"))
        x = frames(raw)
        rate = 352800 if name.endswith(".dsf") else 48000
        if len(x) >= rate:
            freqs = [200, 300, 400, 60, 600, 700] if name.endswith(".dsf") else TONES[:6]
            heard = [f"{f}Hz L{amplitude(x[:, 0], f, rate):.3f}/R{amplitude(x[:, 1], f, rate):.3f}" for f in freqs]
            print(f"  {name}: {len(x)} frames; " + ", ".join(heard))
        else:
            err = [l.split("] ", 1)[-1] for l in log.splitlines() if "unsupported" in l or "error" in l.lower()][:1]
            print(f"  {name}: {len(x)} frames of sound; {err}")

    print("\n== formats the patch leaves alone (5.1), through the patched build, for the record")
    for fmt, name, params in [] if a.only else (("u", "mc6.opus", ()), ("o", "mc6.ogg", ()), ("l", "mc6.m4a", ())):
        raw, log = play(a.patched, fmt, w / name, [], params or ("?", "?", "?", "?"), timeout=30)
        x = frames(raw)
        notes = [l.split("] ", 1)[-1].strip() for l in log.splitlines()
                 if any(k in l for k in ("channels", "unsupported", "too many", "error", "[test]"))][:3]
        if len(x) >= 2 * 48000:
            heard = [f"{f}Hz L{amplitude(x[:, 0], f, 48000):.3f}/R{amplitude(x[:, 1], f, 48000):.3f}" for f in TONES[:6]]
            print(f"  {name}: {len(x)} frames; " + ", ".join(heard))
        else:
            print(f"  {name}: {len(x)} frames of sound")
        for n in notes:
            print(f"      log: {n}")

    print(f"\n{rep.passed} passed, {rep.failed} failed")
    return 1 if rep.failed else 0


if __name__ == "__main__":
    sys.exit(main())
