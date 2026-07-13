# SentinelCV

**Live CV operator console** — public traffic-camera feeds → pluggable object detection → realtime dashboard with feed health and device-camera self-test.

Built as a Python/FastAPI + Render interview demo (inspired by [sarreola07/overwatch](https://github.com/sarreola07/overwatch)).

## Stack

| Layer | Tech |
|-------|------|
| API | FastAPI, Pydantic, httpx, Pillow |
| Realtime | Native WebSockets |
| Detection | Mock (default), Azure AI Vision, or **AWS Rekognition** |
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

With no cloud keys configured, `VISION_PROVIDER=auto` selects **mock** mode (real polling + feed health, fake detections).

### Real detections with AWS Rekognition

1. In AWS IAM, create a user (or role) with `rekognition:DetectLabels`.
2. Create an access key and set:

```bash
export VISION_PROVIDER=rekognition
export AWS_REGION=us-east-1
export AWS_ACCESS_KEY_ID=AKIAxxxxxxxx
export AWS_SECRET_ACCESS_KEY=xxxxxxxx
# optional tuning:
# export AWS_REKOGNITION_MIN_CONFIDENCE=55
# export AWS_REKOGNITION_MIN_GAP_SECONDS=1.0
```

3. Confirm `GET /api/mode` → `{"provider":"rekognition","mock":false}` and the dashboard badge shows **AWS REKOGNITION**.

On Render, add the same env vars as **secrets** (never commit keys). Leave `VISION_PROVIDER=mock` on free demos if you do not want AWS spend.

### Real Azure detections (optional)

```bash
export VISION_PROVIDER=azure
export AZURE_VISION_ENDPOINT=https://<resource>.cognitiveservices.azure.com
export AZURE_VISION_KEY=<key>
```

`VISION_PROVIDER=auto` picks Azure if an Azure key is set, else Rekognition if AWS keys are set, else mock.
### Add more cameras

Edit `backend/app/data/cameras.json`, then push to GitHub (Render auto-deploys).

**Direct JPEG feeds** (NYC DOT style):

```json
{
  "id": "cam-5",
  "name": "My camera",
  "image_url": "https://example.com/camera.jpg"
}
```

**TxDOT Dallas / statewide ITS** (LBJ 635, US 75, etc.) use a special URL because TxDOT does not expose plain image links:

```json
{
  "id": "cam-4",
  "name": "Dallas TxDOT — US 75 @ IH-635 North",
  "image_url": "txdot://DAL/US75 @ IH635 North"
}
```

Format: `txdot://{districtCode}/{icd_Id}` — browse names on [TxDOT ITS Dallas cameras](https://its.txdot.gov/its/District/DAL/cameras). Other useful DAL ids: `US75 @ Midpark`, `IH635 @ Coit`, `IH635 @ Park Central`, `High Five N.E. 1`.

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
