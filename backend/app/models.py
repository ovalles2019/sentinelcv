"""Domain models for feeds, detections, health, and TxDOT speed links."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class FeedHealth(str, Enum):
    UP = "Up"
    STALE = "Stale"
    DOWN = "Down"


class SpeedLinkConfig(BaseModel):
    """Maps a camera to a TxDOT travel-time (TVT) corridor segment."""

    id: str  # e.g. US-75.NB.MainStToIH-635
    label: str


class CameraConfig(BaseModel):
    id: str
    name: str
    image_url: str
    fallback_url: str | None = None
    speed_district: str | None = None  # e.g. DAL
    speed_links: list[SpeedLinkConfig] = Field(default_factory=list)


class Detection(BaseModel):
    label: str
    confidence: float
    # Bounding box normalized to 0..1 so the frontend can scale to any render size
    x: float
    y: float
    w: float
    h: float


class SpeedReading(BaseModel):
    link_id: str = Field(serialization_alias="linkId")
    label: str
    avg_mph: float = Field(serialization_alias="avgMph")
    travel_time_minutes: float | None = Field(default=None, serialization_alias="travelTimeMinutes")
    description: str | None = None
    updated_at: datetime | None = Field(default=None, serialization_alias="updatedAt")
    level: str = "unknown"  # free | moderate | slow | unknown

    model_config = {"populate_by_name": True}


class FrameResult(BaseModel):
    camera_id: str = Field(serialization_alias="cameraId")
    captured_at: datetime = Field(serialization_alias="capturedAt")
    image_base64: str = Field(serialization_alias="imageBase64")
    detections: list[Detection]

    model_config = {"populate_by_name": True}


class CameraStatus(BaseModel):
    id: str
    name: str
    health: FeedHealth
    last_success: datetime | None = Field(default=None, serialization_alias="lastSuccess")
    last_error: str | None = Field(default=None, serialization_alias="lastError")
    speeds: list[SpeedReading] = Field(default_factory=list)

    model_config = {"populate_by_name": True}


def congestion_level(avg_mph: float | None) -> str:
    if avg_mph is None:
        return "unknown"
    if avg_mph >= 55:
        return "free"
    if avg_mph >= 35:
        return "moderate"
    return "slow"
