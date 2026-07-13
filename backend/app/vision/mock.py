"""Mock detections so the full pipeline demos with zero cloud keys."""

from __future__ import annotations

import random

from app.models import Detection

LABELS = ["car", "truck", "person", "bus", "bicycle"]


class MockVisionClient:
    def __init__(self) -> None:
        self._rng = random.Random()

    async def detect_objects(self, image_bytes: bytes) -> list[Detection]:
        _ = image_bytes  # unused — shape of a real frame is irrelevant for mock
        count = self._rng.randint(0, 5)
        out: list[Detection] = []
        for _ in range(count):
            w = self._rng.random() * 0.15 + 0.05
            h = self._rng.random() * 0.15 + 0.05
            out.append(
                Detection(
                    label=LABELS[self._rng.randint(0, len(LABELS) - 1)],
                    confidence=round(self._rng.random() * 0.45 + 0.5, 2),
                    x=self._rng.random() * (1 - w),
                    y=self._rng.random() * (1 - h),
                    w=w,
                    h=h,
                )
            )
        return out
