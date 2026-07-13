"""Azure AI Vision v4.0 Image Analysis (objects feature)."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import httpx

from app.models import Detection


class AzureVisionClient:
    """Rate-limited Azure Vision caller shared across all pollers and live analyze."""

    def __init__(
        self,
        endpoint: str,
        key: str,
        min_gap_seconds: float = 3.2,
        http_timeout: float = 15.0,
    ) -> None:
        self._endpoint = endpoint.rstrip("/")
        self._key = key
        self._min_gap = min_gap_seconds
        self._timeout = http_timeout
        self._gate = asyncio.Semaphore(1)
        self._last_call = datetime.min.replace(tzinfo=timezone.utc)

    async def detect_objects(self, image_bytes: bytes) -> list[Detection]:
        async with self._gate:
            now = datetime.now(timezone.utc)
            wait = self._min_gap - (now - self._last_call).total_seconds()
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_call = datetime.now(timezone.utc)
            return await self._call(image_bytes)

    async def _call(self, image_bytes: bytes) -> list[Detection]:
        url = (
            f"{self._endpoint}/computervision/imageanalysis:analyze"
            "?api-version=2024-02-01&features=objects"
        )
        headers = {
            "Ocp-Apim-Subscription-Key": self._key,
            "Content-Type": "application/octet-stream",
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            res = await client.post(url, content=image_bytes, headers=headers)
            res.raise_for_status()
            data = res.json()

        meta = data.get("metadata", {})
        img_w = float(meta.get("width") or 1)
        img_h = float(meta.get("height") or 1)
        detections: list[Detection] = []
        objects = data.get("objectsResult", {}).get("values", [])
        for obj in objects:
            box = obj["boundingBox"]
            tag = obj["tags"][0]
            detections.append(
                Detection(
                    label=tag["name"],
                    confidence=float(tag["confidence"]),
                    x=box["x"] / img_w,
                    y=box["y"] / img_h,
                    w=box["w"] / img_w,
                    h=box["h"] / img_h,
                )
            )
        return detections
