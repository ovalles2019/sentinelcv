# SentinelCV — Recruiter Pitch & Mock Q&A

Use this for phone screens, recruiter intros, and hiring-manager warm-ups.

---

## 60-Second Pitch

> "I built **SentinelCV** — a realtime computer-vision operator console.
>
> It polls public traffic-camera JPEG feeds, runs object detection through a pluggable backend, and pushes results to a live dashboard over WebSockets. Each feed degrades independently — Up, Stale, or Down — and operators can run a self-test from their phone camera.
>
> Architecturally it's FastAPI with an asyncio poller, an in-memory detection store, and pluggable vision backends — mock for free demos, or AWS Rekognition / Azure AI Vision for real boxes. I deploy it on Render with mock by default so demos stay reliable, and GitHub Actions runs pytest on every push.
>
> It's a prototype, but the production path is clear: persist history, add auth, and move heavy inference to a dedicated worker."

---

## Mock Recruiter Q&A

### Opening

**Recruiter:** "Walk me through one project you're proud of."

**You:** "SentinelCV — a live CV operator console. Multi-camera feeds, object detection, realtime dashboard with feed health. FastAPI on Render, WebSockets for updates, and a GO LIVE button that runs your phone camera through the same pipeline. Happy to screen-share a two-minute demo."

### What & Why

**Recruiter:** "What problem does it solve?"

**You:** "It shows how you'd monitor unreliable external feeds under an API rate budget — polling instead of streaming, isolating failures per feed, and never letting operators confuse stale frames for live ones."

**Recruiter:** "Why mock detections in production?"

**You:** "Free Render has no GPU and Azure Vision is metered. Mock keeps the deploy always-on for interviews. Same interface — I can flip to Azure with env vars when I want real boxes. That pluggability is the architecture point."

### Technical

**Recruiter:** "What's the tech stack?"

**You:** "Python FastAPI, asyncio camera poller, httpx, Pillow for display downscale, native WebSockets, vanilla JS dashboard, Render Blueprint, GitHub Actions pytest."

**Recruiter:** "Is it live?"

**You:** "Yes — URL on Render. Free tier cold-starts after idle, so I warm `/health` before interviews. API docs are at `/docs`."

### Maturity

**Recruiter:** "Is this production-ready?"

**You:** "Deliberate prototype. Real: polling, health model, pluggable vision, dashboard, CI, cloud deploy. Next: persistence, auth, dedicated inference worker, alert rules."

**Recruiter:** "What was hardest?"

**You:** "Demo reliability. YouTube/HLS ingestion looks impressive locally but breaks on Linux PaaS without ffmpeg. I cut that on purpose — two stable NYC DOT JPEGs plus one intentional dead feed. Interview demos beat fragile complexity."

---

## 90-Second Demo Cheat Sheet

| Step | Action | Say |
|------|--------|-----|
| 1 | Open dashboard | "Operator console — realtime-first" |
| 2 | Feed tiles | "Green/stale/down — one feed is intentionally dead" |
| 3 | Bounding boxes | "Detections pushed over WebSocket as frames analyze" |
| 4 | `/docs` | "REST for state; WS for events — OpenAPI included" |
| 5 | **GO LIVE** | "Same pipeline for device camera — analyzed, not stored" |
| 6 | Stats + GitHub Actions | "Rolling counts; pytest greens on every push" |

---

## One-Liners

- Built a realtime CV operator console: multi-feed ingestion, health degradation, pluggable mock/Azure detection, WebSockets, Render deploy, CI.
- Demonstrated systems thinking for rate-limited Vision pipelines with a cloud-safe mock default and a clear path to dedicated inference.
