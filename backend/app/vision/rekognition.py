"""Amazon Rekognition DetectLabels vision provider."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any

import boto3
from botocore.exceptions import BotoCoreError, ClientError

from app.models import Detection


class AwsRekognitionClient:
    """Rate-limited Rekognition caller shared across pollers and live analyze.

    Uses DetectLabels with GENERAL_LABELS. Instance bounding boxes are already
    normalized 0..1 (Left/Top/Width/Height), matching SentinelCV's Detection model.
    """

    def __init__(
        self,
        region: str = "us-east-1",
        min_gap_seconds: float = 1.0,
        min_confidence: float = 55.0,
        max_labels: int = 20,
    ) -> None:
        self._region = region
        self._min_gap = min_gap_seconds
        self._min_confidence = min_confidence
        self._max_labels = max_labels
        self._gate = asyncio.Semaphore(1)
        self._last_call = datetime.min.replace(tzinfo=timezone.utc)
        self._client = boto3.client("rekognition", region_name=region)

    async def detect_objects(self, image_bytes: bytes) -> list[Detection]:
        async with self._gate:
            now = datetime.now(timezone.utc)
            wait = self._min_gap - (now - self._last_call).total_seconds()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = datetime.now(timezone.utc)
            return await asyncio.to_thread(self._call_sync, image_bytes)

    def _call_sync(self, image_bytes: bytes) -> list[Detection]:
        try:
            response = self._client.detect_labels(
                Image={"Bytes": image_bytes},
                MaxLabels=self._max_labels,
                MinConfidence=self._min_confidence,
                Features=["GENERAL_LABELS"],
            )
        except (BotoCoreError, ClientError) as exc:
            raise RuntimeError(f"Rekognition DetectLabels failed: {exc}") from exc
        return self._parse_labels(response.get("Labels", []))

    @staticmethod
    def _parse_labels(labels: list[dict[str, Any]]) -> list[Detection]:
        detections: list[Detection] = []
        for label in labels:
            name = label.get("Name") or "object"
            confidence = float(label.get("Confidence") or 0.0) / 100.0
            instances = label.get("Instances") or []
            if not instances:
                # Scene-level labels (e.g. "Outdoor") have no box — skip for overlay.
                continue
            for inst in instances:
                box = inst.get("BoundingBox") or {}
                inst_conf = float(inst.get("Confidence") or label.get("Confidence") or 0.0) / 100.0
                detections.append(
                    Detection(
                        label=name.lower(),
                        confidence=round(inst_conf, 3),
                        x=float(box.get("Left") or 0.0),
                        y=float(box.get("Top") or 0.0),
                        w=float(box.get("Width") or 0.0),
                        h=float(box.get("Height") or 0.0),
                    )
                )
        return detections
