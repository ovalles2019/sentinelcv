"""In-memory store: latest frame per camera plus rolling detection history."""

from __future__ import annotations

from collections import deque
from datetime import datetime, timedelta, timezone
from threading import Lock

from app.models import CameraConfig, CameraStatus, Detection, FeedHealth, FrameResult

HISTORY_WINDOW = timedelta(minutes=30)
STALE_THRESHOLD = timedelta(minutes=2)


class DetectionStore:
    def __init__(self) -> None:
        self._latest: dict[str, FrameResult] = {}
        self._status: dict[str, CameraStatus] = {}
        self._history: deque[tuple[datetime, str, str]] = deque()
        self._lock = Lock()

    def seed_cameras(self, cameras: list[CameraConfig]) -> None:
        """Register feeds before the first poll so /api/cameras is never empty."""
        with self._lock:
            for cam in cameras:
                if cam.id not in self._status:
                    self._status[cam.id] = CameraStatus(
                        id=cam.id,
                        name=cam.name,
                        health=FeedHealth.DOWN,
                        last_success=None,
                        last_error="awaiting first poll",
                    )

    def record_success(self, cam: CameraConfig, frame: FrameResult) -> None:
        with self._lock:
            self._latest[cam.id] = frame
            self._status[cam.id] = CameraStatus(
                id=cam.id,
                name=cam.name,
                health=FeedHealth.UP,
                last_success=frame.captured_at,
                last_error=None,
            )
            for d in frame.detections:
                self._history.append((frame.captured_at, cam.id, d.label))
            self._trim_unlocked()

    def record_failure(self, cam: CameraConfig, error: str) -> None:
        with self._lock:
            prev = self._status.get(cam.id)
            now = datetime.now(timezone.utc)
            if prev and prev.last_success and now - prev.last_success < STALE_THRESHOLD:
                health = FeedHealth.STALE
                last_success = prev.last_success
            else:
                health = FeedHealth.DOWN
                last_success = prev.last_success if prev else None
            self._status[cam.id] = CameraStatus(
                id=cam.id,
                name=cam.name,
                health=health,
                last_success=last_success,
                last_error=error,
            )

    def record_live_detections(self, device_id: str, detections: list[Detection]) -> None:
        with self._lock:
            now = datetime.now(timezone.utc)
            for d in detections:
                self._history.append((now, device_id, d.label))
            self._trim_unlocked()

    def get_latest(self, camera_id: str) -> FrameResult | None:
        with self._lock:
            return self._latest.get(camera_id)

    def get_statuses(self) -> list[CameraStatus]:
        with self._lock:
            return sorted(self._status.values(), key=lambda s: s.id)

    def get_stats(self, window: timedelta) -> dict:
        with self._lock:
            cutoff = datetime.now(timezone.utc) - window
            recent = [(at, cam, label) for at, cam, label in self._history if at >= cutoff]
        by_label: dict[str, int] = {}
        by_camera: dict[str, int] = {}
        for _, cam, label in recent:
            by_label[label] = by_label.get(label, 0) + 1
            by_camera[cam] = by_camera.get(cam, 0) + 1
        return {
            "windowMinutes": window.total_seconds() / 60,
            "total": len(recent),
            "byLabel": by_label,
            "byCamera": by_camera,
        }

    def _trim_unlocked(self) -> None:
        cutoff = datetime.now(timezone.utc) - HISTORY_WINDOW
        while self._history and self._history[0][0] < cutoff:
            self._history.popleft()
