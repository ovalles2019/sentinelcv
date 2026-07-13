"""SentinelCV Platform API — CV operator console over live camera feeds.

Surfaces:
- GET  /health                 -> Render liveness (always 200 when process is up)
- GET  /healthz                -> feed-aware readiness (503 only if every feed is Down)
- GET  /api/cameras            -> health + last-success per feed
- GET  /api/frames/{id}        -> latest analyzed frame (base64 JPEG) + detections
- GET  /api/stats?minutes=10   -> rolling detection counts
- POST /api/analyze            -> run a posted JPEG through the pipeline
- GET  /api/mode               -> active vision provider
- WS   /ws/detections          -> realtime frame / feedFault / liveDetections
"""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings, get_settings
from app.models import CameraConfig, FeedHealth
from app.poller import CameraPoller
from app.store import DetectionStore
from app.vision import AzureVisionClient, MockVisionClient
from app.ws import ConnectionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentinelcv")

STATIC_DIR = Path(__file__).parent / "static"


def load_cameras(settings: Settings) -> list[CameraConfig]:
    path = Path(settings.cameras_path)
    with path.open() as f:
        raw = json.load(f)
    return [CameraConfig(**c) for c in raw]


def resolve_provider(settings: Settings) -> tuple[str, object]:
    provider = (settings.vision_provider or "auto").lower()
    has_key = bool(settings.azure_vision_key.strip())
    if provider == "auto":
        provider = "azure" if has_key else "mock"
    if provider == "azure":
        if not has_key or not settings.azure_vision_endpoint.strip():
            logger.warning("Azure Vision requested but endpoint/key missing — falling back to mock")
            return "mock", MockVisionClient()
        client = AzureVisionClient(
            endpoint=settings.azure_vision_endpoint,
            key=settings.azure_vision_key,
            min_gap_seconds=settings.azure_min_gap_seconds,
            http_timeout=settings.http_timeout_seconds,
        )
        return "azure", client
    return "mock", MockVisionClient()


store = DetectionStore()
hub = ConnectionManager()
_provider_name = "mock"
_vision: object = MockVisionClient()
_poller: CameraPoller | None = None
_cameras: list[CameraConfig] = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _provider_name, _vision, _poller, _cameras
    settings = get_settings()
    _cameras = load_cameras(settings)
    store.seed_cameras(_cameras)
    _provider_name, _vision = resolve_provider(settings)
    logger.info("Vision provider: %s (%s cameras)", _provider_name, len(_cameras))
    _poller = CameraPoller(
        cameras=_cameras,
        vision=_vision,  # type: ignore[arg-type]
        store=store,
        hub=hub,
        poll_interval=float(settings.poll_interval_seconds),
        http_timeout=settings.http_timeout_seconds,
    )
    _poller.start()
    yield
    if _poller:
        await _poller.stop()


app = FastAPI(
    title="SentinelCV API",
    version="0.1.0",
    description=(
        "Computer-vision pipeline over live camera feeds. REST for state and analysis; "
        "WebSocket at /ws/detections pushes frame/feedFault/liveDetections events."
    ),
    lifespan=lifespan,
)


@app.get("/health")
def health():
    """Render / load-balancer liveness — process is up."""
    return {"status": "ok"}


@app.get("/healthz")
def healthz():
    """App readiness — 503 only if every configured feed is Down."""
    statuses = store.get_statuses()
    any_up = len(statuses) == 0 or any(s.health != FeedHealth.DOWN for s in statuses)
    body = {"status": "ok" if any_up else "degraded", "feeds": len(statuses)}
    if any_up:
        return body
    return JSONResponse(body, status_code=503)


@app.get("/api/cameras")
def list_cameras():
    return [
        s.model_dump(by_alias=True, mode="json")
        for s in store.get_statuses()
    ]


@app.get("/api/frames/{camera_id}")
def get_frame(camera_id: str):
    frame = store.get_latest(camera_id)
    if frame is None:
        return JSONResponse({"detail": "Not found"}, status_code=404)
    return frame.model_dump(by_alias=True, mode="json")


@app.get("/api/stats")
def get_stats(minutes: int | None = Query(default=10)):
    window_min = minutes if minutes is not None and 0 < minutes <= 30 else 10
    return store.get_stats(timedelta(minutes=window_min))


@app.get("/api/mode")
def get_mode():
    return {"provider": _provider_name, "mock": _provider_name == "mock"}


@app.post("/api/analyze")
async def analyze(request: Request, device: str | None = Query(default=None)):
    body = await request.body()
    if not body or len(body) > 4_000_000:
        return JSONResponse(
            {"error": "expected image body up to 4 MB"},
            status_code=400,
        )
    detections = await _vision.detect_objects(body)  # type: ignore[attr-defined]
    device_id = f"live-{device}" if device and device.strip() else "live-device"
    store.record_live_detections(device_id, detections)
    if detections:
        await hub.broadcast(
            "liveDetections",
            {
                "device": device_id,
                "detections": [d.model_dump() for d in detections],
            },
        )
    return [d.model_dump() for d in detections]


@app.websocket("/ws/detections")
async def detections_ws(websocket: WebSocket):
    await hub.connect(websocket)
    try:
        while True:
            # Keep the socket alive; clients send pings or we wait for disconnect.
            await websocket.receive_text()
    except WebSocketDisconnect:
        hub.disconnect(websocket)
    except Exception:
        hub.disconnect(websocket)


if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/")
    def index():
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/style.css")
    def style_css():
        return FileResponse(STATIC_DIR / "style.css")

    @app.get("/app.js")
    def app_js():
        return FileResponse(STATIC_DIR / "app.js")
