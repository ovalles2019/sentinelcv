# SentinelCV
**Realtime Computer-Vision Operator Console · FastAPI + Render**

> Public camera feeds → pluggable object detection → live operator dashboard with feed health, rolling stats, and device-camera self-test.

---

## The Problem

Monitor teams and ops demos often need a **multi-feed CV console**, but production systems hide behind proprietary hardware, GPU farms, and expensive Vision APIs. Interview/portfolio demos usually either:

- Fake the UI with static screenshots, or
- Depend on flaky YouTube streams / GPU runtimes that die on free PaaS

---

## The Solution

**SentinelCV** is a deliberately deployable miniature ISR-style pipeline:

| Layer | Role |
|-------|------|
| **Camera poller** | Staggered asyncio loops per feed; isolated failures |
| **Vision providers** | Mock (cloud-safe) or Azure AI Vision (optional) |
| **Detection store** | In-memory latest frames + rolling stats |
| **Dashboard** | Realtime WebSocket console with polling fallback |
| **Cloud + CI** | Render Blueprint, pytest on every push |

```
[Public JPEG feeds] ──poll──▶ CameraPoller ──frame──▶ VisionClient
[Phone/laptop cam]  ──POST /api/analyze ──────────▶      │
                                                         ▼
                                                  DetectionStore
                                                         │
                          REST + WebSocket ──▶ Operator dashboard
```

---

## What I Built

**Feed health model** — Up / Stale / Down with data-age always visible; one intentional dead feed for demos.

**Pluggable detection** — `VisionClient` protocol; `VISION_PROVIDER=mock|azure|auto`.

**Realtime-first UI** — WebSocket pushes with 30s safety poll / 5s fallback on disconnect.

**GO LIVE self-test** — Browser camera → `/api/analyze` → same pipeline; frames discarded.

**Engineering discipline** — GitHub Actions pytest, Render Blueprint, OpenAPI at `/docs`.

---

## Tech Stack

| Category | Technologies |
|----------|--------------|
| **Backend** | Python 3.12, FastAPI, Uvicorn, httpx, Pillow |
| **Realtime** | WebSockets |
| **Cloud** | Render (free web service) |
| **CI/CD** | GitHub Actions |
| **Auth** | Public demo API → API key / OIDC (roadmap) |

---

## Enterprise Roadmap

- Persist detection history (Postgres / Redis)
- Operator alert rules ("notify when > N objects on cam X")
- Dedicated inference worker for local/YOLO models
- Rate limits + auth on `/api/analyze`
- Motion gating to cut Vision API spend

---

## Links

| Resource | URL |
|----------|-----|
| **Repository** | [github.com/ovalles2019/sentinelcv](https://github.com/ovalles2019/sentinelcv) |
| **Live app** | _Connect Render Blueprint — URL after first deploy_ |
| **API docs** | `https://<service>.onrender.com/docs` |

---

## For Your Resume

**Option A — single bullet**
> Built **SentinelCV**, a realtime computer-vision operator console (FastAPI + WebSockets on Render) with multi-feed ingestion, feed-health degradation, pluggable mock/Azure detection, and CI-tested APIs.

**Option B — two bullets**
> Designed and shipped **SentinelCV**, a deployable CV pipeline: staggered camera polling, Up/Stale/Down health, and a realtime dashboard with device-camera self-test.
>
> Implemented pluggable vision backends (mock for free-tier demos, Azure AI Vision for real inference), pytest suite, and Render Blueprint deploy.

---

## One-Line Elevator Pitch

*"SentinelCV is a live CV operator console — multi-feed detection, health-aware degradation, and WebSocket updates — built to stay demoable on free Render."*
