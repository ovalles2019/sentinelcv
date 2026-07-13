"""Background camera poller — staggered per-feed loops with isolated failures."""

from __future__ import annotations

import asyncio
import base64
import logging
from datetime import datetime, timezone
from io import BytesIO

import httpx
from PIL import Image

from app.models import CameraConfig, FrameResult
from app.store import DetectionStore
from app.vision.base import VisionClient
from app.ws import ConnectionManager

logger = logging.getLogger("sentinelcv.poller")


def to_display_jpeg(original: bytes, max_width: int = 960, quality: int = 74) -> bytes:
    """Downscale for dashboard payload size; detect on the full-resolution frame."""
    with Image.open(BytesIO(original)) as image:
        if image.width <= max_width:
            return original
        ratio = max_width / image.width
        new_size = (max_width, int(image.height * ratio))
        resized = image.convert("RGB").resize(new_size, Image.Resampling.LANCZOS)
        out = BytesIO()
        resized.save(out, format="JPEG", quality=quality)
        return out.getvalue()


class CameraPoller:
    def __init__(
        self,
        cameras: list[CameraConfig],
        vision: VisionClient,
        store: DetectionStore,
        hub: ConnectionManager,
        poll_interval: float = 15.0,
        http_timeout: float = 10.0,
    ) -> None:
        self._cameras = cameras
        self._vision = vision
        self._store = store
        self._hub = hub
        self._interval = poll_interval
        self._timeout = http_timeout
        self._tasks: list[asyncio.Task] = []

    def start(self) -> None:
        n = max(len(self._cameras), 1)
        for i, cam in enumerate(self._cameras):
            offset = self._interval * i / n
            self._tasks.append(asyncio.create_task(self._run_loop(cam, offset)))
        logger.info(
            "Polling %s cameras every %ss (staggered)",
            len(self._cameras),
            self._interval,
        )

    async def stop(self) -> None:
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def _run_loop(self, cam: CameraConfig, offset: float) -> None:
        try:
            if offset > 0:
                await asyncio.sleep(offset)
            while True:
                await self._poll_one(cam)
                await asyncio.sleep(self._interval)
        except asyncio.CancelledError:
            return

    async def _poll_one(self, cam: CameraConfig) -> None:
        try:
            try:
                bytes_ = await self._fetch(cam.image_url)
            except Exception as primary_err:
                if not cam.fallback_url:
                    raise
                logger.warning(
                    "Camera %s primary failed (%s); using fallback",
                    cam.id,
                    primary_err,
                )
                bytes_ = await self._fetch(cam.fallback_url)

            detections = await self._vision.detect_objects(bytes_)
            frame = FrameResult(
                camera_id=cam.id,
                captured_at=datetime.now(timezone.utc),
                image_base64=base64.b64encode(to_display_jpeg(bytes_)).decode("ascii"),
                detections=detections,
            )
            self._store.record_success(cam, frame)
            await self._hub.broadcast(
                "frame",
                {
                    "cameraId": cam.id,
                    "capturedAt": frame.captured_at.isoformat(),
                    "detections": [d.model_dump() for d in detections],
                },
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Camera %s poll failed: %s", cam.id, exc)
            self._store.record_failure(cam, str(exc))
            await self._hub.broadcast(
                "feedFault",
                {"cameraId": cam.id, "error": str(exc)},
            )

    async def _fetch(self, url: str) -> bytes:
        if url.startswith("txdot://"):
            return await self._fetch_txdot(url)
        async with httpx.AsyncClient(timeout=self._timeout, follow_redirects=True) as client:
            res = await client.get(url)
            res.raise_for_status()
            return res.content

    async def _fetch_txdot(self, url: str) -> bytes:
        """Fetch a TxDOT ITS still via GetCctvSnapshotByIcdId.

        URL shape: txdot://{districtCode}/{icd_Id}
        Example:   txdot://DAL/US75 @ IH635 North
        """
        district, icd_id = parse_txdot_url(url)
        params = {"icdId": icd_id, "districtCode": district}
        endpoint = "https://its.txdot.gov/its/DistrictIts/GetCctvSnapshotByIcdId"
        headers = {
            "Accept": "application/json",
            "Referer": f"https://its.txdot.gov/its/District/{district}/cameras",
            "User-Agent": "SentinelCV/0.1 (+https://github.com/ovalles2019/sentinelcv)",
        }
        timeout = max(self._timeout, 25.0)
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
            res = await client.get(endpoint, params=params, headers=headers)
            res.raise_for_status()
            data = res.json()
        if isinstance(data, list):
            data = data[0] if data else {}
        snippet = (data or {}).get("snippet") if isinstance(data, dict) else None
        if not snippet:
            raise RuntimeError(f"TxDOT returned no snapshot for {district}/{icd_id}")
        return decode_txdot_snippet(snippet)


def parse_txdot_url(url: str) -> tuple[str, str]:
    """txdot://DAL/US75 @ IH635 North -> ('DAL', 'US75 @ IH635 North')."""
    if not url.startswith("txdot://"):
        raise ValueError(f"not a txdot URL: {url}")
    rest = url[len("txdot://") :]
    district, sep, icd = rest.partition("/")
    if not sep or not district or not icd:
        raise ValueError(
            "txdot URL must be txdot://{districtCode}/{icd_Id} "
            "(e.g. txdot://DAL/US75 @ IH635 North)"
        )
    return district.strip(), icd.strip()


def decode_txdot_snippet(snippet: str) -> bytes:
    """Decode TxDOT base64 JPEG snippet (optionally data:-prefixed)."""
    payload = snippet.split(",", 1)[-1] if snippet.startswith("data:") else snippet
    payload = payload.replace("\\/", "/")
    try:
        return base64.b64decode(payload, validate=False)
    except Exception as exc:
        raise RuntimeError(f"invalid TxDOT snapshot encoding: {exc}") from exc
