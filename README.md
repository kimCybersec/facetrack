# FaceTrack

AI-powered facial recognition access control for college gate entry, built on
ZKTeco IP cameras.

## Architecture

- **backend/services/discovery.py** — ONVIF WS-Discovery probe that finds
  ZKTeco (and other ONVIF) cameras on the local subnet.
- **backend/services/camera_manager.py** — Persists discovered cameras and
  starts/stops a per-camera recognition worker when an admin toggles a
  camera on/off.
- **backend/ai/detection.py** — YOLOv8-Face wrapper for locating faces in a
  frame.
- **backend/ai/embedding.py** — FaceNet (InceptionResnetV1) wrapper that
  produces normalized embedding vectors from aligned face crops.
- **backend/ai/pipeline.py** — Per-camera worker thread: pulls RTSP frames,
  runs detection + embedding, matches against `pgvector` via cosine
  similarity, de-dupes repeat sightings with a Redis TTL key, triggers the
  gate relay, and logs + broadcasts every attempt.
- **backend/services/relay_service.py** — Fires the gate/turnstile open
  signal (HTTP first, TCP fallback) on a verified match.
- **backend/main.py** — FastAPI REST + WebSocket API.
- **frontend/** — Next.js 15 admin dashboard (Cameras, Gate Monitor,
  Students).

## Running locally with Docker

```bash
cp .env.example .env   # edit values for your network/camera credentials
docker compose up --build
```

The backend runs with `network_mode: host` so that ONVIF WS-Discovery's UDP
multicast probe can actually reach cameras on your physical LAN — this is a
Linux-only Docker feature. On macOS/Windows hosts, run the backend directly
with `uvicorn main:app` instead of inside Docker, or connect it to a
macvlan network with LAN access.

- Frontend: http://localhost:3000
- Backend docs: http://localhost:8000/docs

## Running the backend without Docker

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

You'll also need a local Postgres with the `vector` extension and a local
Redis instance (or point `POSTGRES_HOST`/`REDIS_HOST` at remote ones).

## Notes on hardware integration

- **RTSP URLs** are constructed as `rtsp://<user>:<password>@<ip>:554/stream1`
  using `DEFAULT_CAMERA_USER` / `DEFAULT_CAMERA_PASSWORD`. If your ZKTeco
  units use per-device credentials, update the row in the `cameras` table
  after discovery.
- **Relay triggering** supports either an HTTP endpoint on your access
  control panel or a raw TCP command port — configure whichever your gate
  hardware exposes in `RelayService`.
- The face-match threshold (`FACE_MATCH_THRESHOLD`, default 0.65) and the
  attendance de-duplication window (`ATTENDANCE_COOLDOWN_SECONDS`, default
  60s) are both tunable via environment variables.
# facetrack
