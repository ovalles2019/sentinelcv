"""Unit tests for DetectionStore health transitions and stats."""

from datetime import datetime, timedelta, timezone

from app.models import CameraConfig, Detection, FrameResult
from app.store import DetectionStore


def _cam(cid: str = "cam-1") -> CameraConfig:
    return CameraConfig(id=cid, name=f"Camera {cid}", image_url="https://example.com/x.jpg")


def _frame(cid: str = "cam-1", labels: list[str] | None = None) -> FrameResult:
    labels = labels or ["car"]
    return FrameResult(
        camera_id=cid,
        captured_at=datetime.now(timezone.utc),
        image_base64="AAAA",
        detections=[
            Detection(label=l, confidence=0.9, x=0.1, y=0.1, w=0.2, h=0.2) for l in labels
        ],
    )


def test_record_success_sets_up():
    store = DetectionStore()
    cam = _cam()
    store.seed_cameras([cam])
    store.record_success(cam, _frame())
    status = store.get_statuses()[0]
    assert status.health.value == "Up"
    assert status.last_error is None
    assert store.get_latest("cam-1") is not None


def test_failure_after_recent_success_is_stale():
    store = DetectionStore()
    cam = _cam()
    store.record_success(cam, _frame())
    store.record_failure(cam, "timeout")
    status = store.get_statuses()[0]
    assert status.health.value == "Stale"
    assert status.last_error == "timeout"
    assert store.get_latest("cam-1") is not None


def test_failure_without_recent_success_is_down():
    store = DetectionStore()
    cam = _cam()
    store.seed_cameras([cam])
    # Force an old last_success so the next failure is Down
    frame = _frame()
    frame.captured_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    store.record_success(cam, frame)
    store.record_failure(cam, "dns failed")
    status = store.get_statuses()[0]
    assert status.health.value == "Down"


def test_stats_window_and_labels():
    store = DetectionStore()
    cam = _cam("cam-1")
    store.record_success(cam, _frame("cam-1", ["car", "person"]))
    store.record_live_detections("live-device", [
        Detection(label="bus", confidence=0.8, x=0.1, y=0.1, w=0.1, h=0.1),
    ])
    stats = store.get_stats(timedelta(minutes=10))
    assert stats["total"] == 3
    assert stats["byLabel"]["car"] == 1
    assert stats["byLabel"]["person"] == 1
    assert stats["byLabel"]["bus"] == 1
    assert stats["byCamera"]["cam-1"] == 2
    assert stats["byCamera"]["live-device"] == 1


def test_seed_cameras_shows_awaiting():
    store = DetectionStore()
    store.seed_cameras([_cam("a"), _cam("b")])
    statuses = store.get_statuses()
    assert len(statuses) == 2
    assert all(s.health.value == "Down" for s in statuses)
