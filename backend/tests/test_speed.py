"""Tests for TxDOT TVT speed mapping."""

from app.models import SpeedLinkConfig, congestion_level
from app.store import DetectionStore
from app.txdot_speed import readings_for_links


def test_congestion_levels():
    assert congestion_level(70) == "free"
    assert congestion_level(45) == "moderate"
    assert congestion_level(20) == "slow"
    assert congestion_level(None) == "unknown"


def test_readings_for_links_maps_avg_speed():
    index = {
        "US-75.NB.MainStToIH-635": {
            "avgSpeed": 35.0,
            "travelTimeMinutes": 18,
            "tvtLink": {"description": "Northbound US75 near Main St to IH635"},
        }
    }
    links = [SpeedLinkConfig(id="US-75.NB.MainStToIH-635", label="US-75 NB")]
    readings = readings_for_links(index, links)
    assert len(readings) == 1
    assert readings[0].avg_mph == 35.0
    assert readings[0].level == "moderate"
    assert readings[0].travel_time_minutes == 18


def test_store_attaches_speeds_to_status():
    store = DetectionStore()
    from app.models import CameraConfig, SpeedReading
    from datetime import datetime, timezone

    cam = CameraConfig(id="cam-4", name="Dallas", image_url="txdot://DAL/x")
    store.seed_cameras([cam])
    reading = SpeedReading(
        link_id="US-75.NB.MainStToIH-635",
        label="US-75 NB",
        avg_mph=52,
        level="moderate",
        updated_at=datetime.now(timezone.utc),
    )
    store.record_speeds("cam-4", [reading])
    status = store.get_statuses()[0]
    assert status.speeds[0].avg_mph == 52
    assert status.speeds[0].label == "US-75 NB"
