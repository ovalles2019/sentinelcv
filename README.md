# SentinelCV

**Live CV operator console** — public traffic-camera feeds → pluggable object detection → realtime dashboard with feed health and device-camera self-test.

Built as a Python/FastAPI + Render interview demo (inspired by [sarreola07/overwatch](https://github.com/sarreola07/overwatch)).

## Stack

| Layer | Tech |
|-------|------|
| API | FastAPI, Pydantic, httpx, Pillow |
| Realtime | Native WebSockets |
| Detection | Mock (default) or Azure AI Vision |
| Dashboard | Vanilla JS operator console |
| Deploy | Render free web service (`render.yaml`) |
| CI | GitHub Actions + pytest |

## Run locally

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open http://localhost:8000 — dashboard, `/docs`, and `/health`.

With no Azure key configured, `VISION_PROVIDER=auto` selects **mock** mode (real polling + feed health, fake detections).

### Real Azure detections (optional)

```bash
export VISION_PROVIDER=azure
export AZURE_VISION_ENDPOINT=https://<resource>.cognitiveservices.azure.com
export AZURE_VISION_KEY=<key>
```

## API

| Surface | Purpose |
|---------|---------|
| `GET /api/cameras` | Feed health + last success |
| `GET /api/frames/{id}` | Latest frame + detections |
| `GET /api/stats?minutes=10` | Rolling counts |
| `POST /api/analyze` | Analyze a posted JPEG |
| `GET /healthz` | 503 only if every feed is Down |
| `WS /ws/detections` | `frame` / `feedFault` / `liveDetections` |

## Design notes

- **Three demo feeds** — two NYC DOT JPEG endpoints + one intentional dead URL for degraded-mode demos.
- **No YouTube/HLS/ffmpeg** — kept out of scope so Render Linux free tier stays reliable.
- **Per-camera isolation** — one dead feed does not stop the others (Up → Stale → Down).
- **Pluggable vision** — swap mock ↔ Azure via env; same `VisionClient` protocol.
- **In-memory store** — deliberate prototype cut; roadmap is Postgres/Redis.

## Tests

```bash
cd backend && pytest -q
```

## Deploy (Render)

1. Push this repo to GitHub.
2. Create a Blueprint from `render.yaml`, or a Python web service with:
   - **Root directory:** `backend`
   - **Build:** `pip install -r requirements.txt`
   - **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health check:** `/health`
3. Hit `/health` once before interviews (free tier cold starts).

## License

MIT. Dashboard visual language adapted from the Overwatch open-source project.
