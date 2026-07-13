"""Domain models for feeds, detections, and health."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class FeedHealth(str, Enum):
    UP = "Up"
    STALE = "Stale"
    DOWN = "Down"


class CameraConfig(BaseModel):
    id: str
    name: str
    image_url: str
    fallback_url: str | None = None


class Detection(BaseModel):
    label: str
    confidence: float
    # Bounding box normalized to 0..1 so the frontend can scale to any render size
    x: float
    y: float
    w: float
    h: float


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

    model_config = {"populate_by_name": True}
