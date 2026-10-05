# SPDX-License-Identifier: GPL-3.0-or-later
"""Where a background picture sits on the screen, by what it shows (ADR-0120).

A screen shows a band of a picture: a 1280 x 400 bar about a third of a 16:9
picture's height. Until 2026-10-05 the band sat 35 % from the top whatever the
picture held, which cut heads off and showed animals' feet (George). Now, in
this order:

1. **Faces** (YuNet): the band set by the eyes, a third of the way down it -
   how a portrait is framed, and still right for a face taller than the band,
   where centring the face lands on the nose (measured: 48 of 49 of George's
   artist pictures were placed this way).
2. **A person or an animal** (YOLOX-S): the band from the subject's top, where
   the head nearly always is.
3. **What stands out** (spectral-residual saliency): where the subject is,
   though not where its head is.

**A subject too big for the band** is shrunk until it fits, as long as the
picture still fills three quarters of the screen's width - the rest is its
own blur, drawn by the panel - and otherwise the picture is skipped (George:
*"rather than having more than half the screen blurred"*).

**Measured on gexis** (Pi 4, lowest priority): faces 86 ms, a person or animal
2.2 s, once per picture. OpenCV and the two models are optional at import: a
player without them places every picture as before, and says so once.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

#: Where the image puts the two models (ADR-0120): YuNet (232 KB) and YOLOX-S
#: (36 MB), both from OpenCV's model zoo, MIT and Apache-2.0.
MODELS = Path("/opt/gexis-core/models")
FACE_MODEL = "face_detection_yunet_2023mar.onnx"
SUBJECT_MODEL = "object_detection_yolox_2022nov.onnx"

#: Today's band, for a picture nothing could be found in and for a player
#: without the models: 35 % from the top (George, "C", 2026-10-04).
DEFAULT_Y = 0.35
#: The least of the screen's width a shrunk picture may fill (George: blur on
#: "less than let's say 25% of the screen").
MIN_WIDTH = 0.75
#: Where the eyes sit in the band, from its top: a third, as a portrait is
#: framed. Measured against the face's middle, which put noses in the band.
EYES_AT = 0.36
#: How much of a face has to fit the band: its detected box, forehead to
#: chin. Placed by the eyes, a face up to that size shows them whole (the
#: 2026-10-05 sheets); asking for half again as much skipped good portraits.
FACE_ROOM = 1.0
#: COCO's person and its ten animals, which is what YOLOX knows.
LIVING = {0} | set(range(14, 24))
#: A subject this much of the picture's area is a close-up: its top half is
#: what has to fit, or it is too big for the band.
CLOSE_UP = 0.5


@dataclass(frozen=True)
class Placement:
    """`y`: the CSS `object-position` height, 0 (top) to 1 (bottom).
    `width`: the share of the screen's width the picture fills - 1 to fill it,
    down to `MIN_WIDTH` for a shrunk one over its blur. `skip`: too big to
    show. `how`: what placed it, for the log."""

    y: float = DEFAULT_Y
    width: float = 1.0
    skip: bool = False
    how: str = "default"

    def to_json(self) -> dict:
        # Python floats: the detectors' numbers are numpy's, which the JSON
        # encoder refuses - every picture placed by faces failed its request
        # until 2026-10-05 (7 of 230 on gexis that afternoon).
        return {"y": round(float(self.y), 4), "width": round(float(self.width), 4), "how": self.how}


class Placer:
    """The models, loaded once; `place` is CPU work for a worker thread."""

    def __init__(self, models: Path = MODELS) -> None:
        self._models = models
        self._loaded = False
        self._cv2 = None
        self._faces = None
        self._subjects = None

    def _load(self) -> bool:
        if self._loaded:
            return self._cv2 is not None
        self._loaded = True
        try:
            import cv2  # noqa: PLC0415 - optional, and heavy
            import numpy  # noqa: F401, PLC0415

            cv2.setNumThreads(2)
            self._faces = cv2.FaceDetectorYN.create(str(self._models / FACE_MODEL), "", (320, 320), 0.7, 0.3, 50)
            self._subjects = _Yolox(cv2, self._models / SUBJECT_MODEL)
            self._cv2 = cv2
        except Exception as exc:  # noqa: BLE001 - placing as before beats not starting
            logger.warning("placement: cannot find faces or subjects (%s); pictures sit 35 %% from the top", exc)
            self._cv2 = None
        return self._cv2 is not None

    def place(self, data: bytes, screen: tuple[int, int]) -> Placement:
        """Where a picture (its encoded bytes) sits on a screen of this size."""
        if not self._load():
            return Placement()
        import numpy as np  # noqa: PLC0415

        cv2 = self._cv2
        image = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            return Placement(how="unreadable")
        return decide(image.shape[1], image.shape[0], screen,
                      faces=self._find_faces(image), subject=self._find_subject(image),
                      salient=lambda band: _salient_top(cv2, image, band))

    def _find_faces(self, image) -> list[tuple[float, float, float]]:
        """Each face as (top, height, eyes), in picture pixels."""
        cv2 = self._cv2
        scale = 640 / max(image.shape[:2])
        small = cv2.resize(image, (round(image.shape[1] * scale), round(image.shape[0] * scale)))
        self._faces.setInputSize((small.shape[1], small.shape[0]))
        _, found = self._faces.detect(small)
        if found is None:
            return []
        return [(f[1] / scale, f[3] / scale, (f[5] + f[7]) / 2 / scale) for f in found]

    def _find_subject(self, image) -> tuple[float, float, float] | None:
        """People and animals together: (top, bottom, share of the picture's
        area the largest covers), in picture pixels."""
        boxes = self._subjects.living(image)
        if not boxes:
            return None
        h, w = image.shape[:2]
        largest = boxes[0][0]
        keep = [b for b in boxes if b[0] >= 0.3 * largest]
        return min(b[1] for b in keep), max(b[2] for b in keep), largest / (w * h)


def decide(w: int, h: int, screen: tuple[int, int], *, faces, subject, salient) -> Placement:
    """The placement, from what was found. Pure arithmetic, tested alone.

    `faces`: (top, height, eyes) each. `subject`: (top, bottom, area share) or
    None. `salient(band)`: the top of the band where most of what stands out
    is, given the band's height - asked only when nothing else was found.
    """
    W, H = screen
    cover = max(W / w, H / h)
    band = H / cover  # the band's height in picture pixels, filling the screen

    if faces:
        eyes = sum(f[2] for f in faces) / len(faces)
        need = max(f[1] for f in faces) * FACE_ROOM
        how = "faces"
        if need <= band:
            return Placement(y=_y(eyes - EYES_AT * band, band, h), how=how)
        return _shrunk(w, h, W, H, need, top=eyes - EYES_AT * need, how=how)

    if subject:
        top, bottom, share = subject
        tall = bottom - top
        if share >= CLOSE_UP and tall > band:
            # A close-up: its top half has to fit.
            return _shrunk(w, h, W, H, tall / 2, top=top, how="subject")
        if tall <= band:
            return Placement(y=_y((top + bottom) / 2 + 0.05 * band - band / 2, band, h), how="subject")
        return Placement(y=_y(top - 0.06 * band, band, h), how="subject")

    return Placement(y=_y(salient(band), band, h), how="stands out")


def _y(top: float, band: float, h: float) -> float:
    """CSS object-position for a band starting at `top`, clamped to the picture."""
    spare = h - band
    if spare <= 0:
        return 0.5
    return min(1.0, max(0.0, top / spare))


def _shrunk(w: int, h: int, W: int, H: int, need: float, *, top: float, how: str) -> Placement:
    """Shrink until `need` picture pixels fit the screen's height, if the
    picture then still fills `MIN_WIDTH` of its width; skip it otherwise."""
    scale = H / need
    width = min(1.0, w * scale / W)
    if width >= 1.0:
        # It fits without shrinking after all (a close-up whose top half is
        # no taller than the band): the band from `top`, filling the screen.
        band = H / max(W / w, H / h)
        return Placement(y=_y(top, band, h), how=how)
    if width < MIN_WIDTH:
        return Placement(skip=True, how=f"{how}, too big")
    # Drawn at `width` of the screen and full height: the picture's own band.
    band = H / max(width * W / w, H / h)
    return Placement(y=_y(top, band, h), width=width, how=f"{how}, shrunk")


def _salient_top(cv2, image, band: float) -> float:
    """Spectral-residual saliency (Hou & Zhang, 2007): the top of the band
    holding most of what stands out from the picture's own background."""
    import numpy as np  # noqa: PLC0415

    h = image.shape[0]
    grey = cv2.resize(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY), (128, 128)).astype(np.float32)
    spectrum = np.fft.fft2(grey)
    log_amp = np.log(np.abs(spectrum) + 1e-6)
    residual = log_amp - cv2.blur(log_amp, (3, 3))
    sal = np.abs(np.fft.ifft2(np.exp(residual + 1j * np.angle(spectrum)))) ** 2
    rows = cv2.GaussianBlur(sal, (0, 0), 3).sum(axis=1)
    n = max(1, min(128, round(band / h * 128)))
    start = int(np.argmax(np.convolve(rows, np.ones(n), mode="valid")))
    return start / 128 * h


class _Yolox:
    """YOLOX-S as OpenCV's model zoo runs it: a 640 x 640 letterbox, three
    strides, scores as objectness x class."""

    SIZE = 640
    STRIDES = (8, 16, 32)

    def __init__(self, cv2, path: Path, threshold: float = 0.35) -> None:
        import numpy as np  # noqa: PLC0415

        self._cv2 = cv2
        self._np = np
        self._net = cv2.dnn.readNet(str(path))
        self._threshold = threshold
        grids, strides = [], []
        for stride in self.STRIDES:
            n = self.SIZE // stride
            xv, yv = np.meshgrid(np.arange(n), np.arange(n))
            grids.append(np.stack((xv, yv), 2).reshape(1, -1, 2))
            strides.append(np.full((1, n * n, 1), stride))
        self._grids = np.concatenate(grids, 1)
        self._strides = np.concatenate(strides, 1)

    def living(self, image) -> list[tuple[float, float, float]]:
        """People and animals as (area, top, bottom) in picture pixels,
        largest first."""
        cv2, np = self._cv2, self._np
        h, w = image.shape[:2]
        r = min(self.SIZE / h, self.SIZE / w)
        box = np.full((self.SIZE, self.SIZE, 3), 114, np.uint8)
        box[: round(h * r), : round(w * r)] = cv2.resize(image, (round(w * r), round(h * r)))
        self._net.setInput(np.transpose(box.astype(np.float32), (2, 0, 1))[np.newaxis])
        dets = self._net.forward(self._net.getUnconnectedOutLayersNames())[0][0]
        dets[:, :2] = (dets[:, :2] + self._grids) * self._strides
        dets[:, 2:4] = np.exp(dets[:, 2:4]) * self._strides
        xywh = np.column_stack((dets[:, 0] - dets[:, 2] / 2, dets[:, 1] - dets[:, 3] / 2, dets[:, 2], dets[:, 3]))
        scores = dets[:, 4:5] * dets[:, 5:]
        best, cls = scores.max(axis=1), scores.argmax(axis=1)
        keep = cv2.dnn.NMSBoxesBatched(xywh.tolist(), best.tolist(), cls.tolist(), self._threshold, 0.5)
        out = []
        for i in np.array(keep).reshape(-1):
            if int(cls[i]) in LIVING:
                _x, y, bw, bh = xywh[i] / r
                out.append((float(bw * bh), float(y), float(y + bh)))
        return sorted(out, reverse=True)
