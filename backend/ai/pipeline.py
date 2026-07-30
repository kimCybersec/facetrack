"""
FaceTrack - Recognition pipeline.

Each active camera gets one CameraWorker running in its own thread. The
worker pulls frames from the RTSP stream at a fixed sampling interval,
runs face detection + embedding, matches against the student vector store
in Postgres/pgvector, de-duplicates repeat sightings via Redis, triggers
the gate relay on a verified match, and logs every attempt (granted or
denied) to the database + broadcasts it over the live WebSocket feed.
"""
import asyncio
import logging
import threading
import time
from typing import Optional

import cv2
import redis
from sqlalchemy import text

from config import settings
from ai.detection import FaceDetector
from ai.embedding import FaceEmbedder
from database.connection import session_scope
from database.models import AccessLog, AccessStatus, Student
from services.relay_service import RelayService

logger = logging.getLogger("facetrack.pipeline")


class MatchResult:
    __slots__ = ("student_id", "student_name", "score")

    def __init__(self, student_id: Optional[str], student_name: Optional[str], score: float):
        self.student_id = student_id
        self.student_name = student_name
        self.score = score


def find_best_match(embedding, db) -> MatchResult:
    """Cosine-similarity nearest neighbor search against pgvector.

    pgvector's `<=>` operator returns cosine *distance*; similarity is
    1 - distance for normalized vectors.
    """
    vec_literal = "[" + ",".join(f"{v:.8f}" for v in embedding.tolist()) + "]"
    row = db.execute(
        text(
            """
            SELECT id, full_name, 1 - (embedding <=> :vec) AS similarity
            FROM students
            WHERE is_active = true
            ORDER BY embedding <=> :vec
            LIMIT 1
            """
        ),
        {"vec": vec_literal},
    ).fetchone()

    if row is None:
        return MatchResult(None, None, 0.0)
    return MatchResult(str(row.id), row.full_name, float(row.similarity))


class LiveLogBroadcaster:
    """In-process pub/sub so the WebSocket endpoint in main.py can stream
    log events out to connected admin dashboard clients."""

    def __init__(self):
        self._queue: "asyncio.Queue" = asyncio.Queue()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def bind_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def publish(self, payload: dict):
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._queue.put(payload), self._loop)

    async def get(self):
        return await self._queue.get()


broadcaster = LiveLogBroadcaster()


class CameraWorker:
    """Runs the full detect -> embed -> match -> act loop for one camera,
    in a dedicated background thread so it can be started/stopped
    independently as an admin toggles the camera on/off."""

    def __init__(self, camera_id: str, camera_name: str, rtsp_url: str):
        self.camera_id = camera_id
        self.camera_name = camera_name
        self.rtsp_url = rtsp_url
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._redis = redis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DB,
            decode_responses=True,
        )
        self._relay = RelayService()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name=f"cam-{self.camera_id}")
        self._thread.start()
        logger.info("Started worker for camera %s (%s)", self.camera_name, self.camera_id)

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Stopped worker for camera %s", self.camera_name)

    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def _cooldown_key(self, student_id: str) -> str:
        return f"attendance:{student_id}:{self.camera_id}"

    def _in_cooldown(self, student_id: str) -> bool:
        return self._redis.exists(self._cooldown_key(student_id)) == 1

    def _set_cooldown(self, student_id: str):
        self._redis.set(
            self._cooldown_key(student_id), "1", ex=settings.ATTENDANCE_COOLDOWN_SECONDS
        )

    def _log_and_broadcast(self, student_id, confidence, status, note=None):
        with session_scope() as db:
            log = AccessLog(
                student_id=student_id,
                camera_id=self.camera_id,
                confidence_score=confidence,
                status=status,
                note=note,
            )
            db.add(log)
            db.flush()
            payload = log.to_dict()
        broadcaster.publish(payload)

    def _run(self):
        detector = FaceDetector.shared()
        embedder = FaceEmbedder.shared()

        cap = cv2.VideoCapture(self.rtsp_url)
        if not cap.isOpened():
            logger.error("Could not open RTSP stream for camera %s: %s", self.camera_id, self.rtsp_url)
            self._log_and_broadcast(None, None, AccessStatus.DENIED, note="Stream unavailable")
            return

        last_sample_time = 0.0
        try:
            while not self._stop_event.is_set():
                ok, frame = cap.read()
                if not ok or frame is None:
                    time.sleep(0.5)
                    continue

                now = time.monotonic()
                if now - last_sample_time < settings.FRAME_SAMPLE_INTERVAL_SEC:
                    continue
                last_sample_time = now

                try:
                    faces = detector.detect(frame)
                except Exception:
                    logger.exception("Detection failed on camera %s", self.camera_id)
                    continue

                for face in faces:
                    try:
                        embedding = embedder.embed(face.crop)
                    except Exception:
                        logger.exception("Embedding failed on camera %s", self.camera_id)
                        continue

                    with session_scope() as db:
                        match = find_best_match(embedding, db)

                    if match.student_id and match.score >= settings.FACE_MATCH_THRESHOLD:
                        if self._in_cooldown(match.student_id):
                            continue  # already logged recently, skip duplicate
                        self._set_cooldown(match.student_id)
                        self._relay.trigger_open(
                            camera_id=self.camera_id, duration_sec=settings.RELAY_OPEN_DURATION_SEC
                        )
                        self._log_and_broadcast(
                            match.student_id, match.score, AccessStatus.GRANTED
                        )
                        logger.info(
                            "GRANTED cam=%s student=%s score=%.3f",
                            self.camera_id, match.student_name, match.score,
                        )
                    else:
                        self._log_and_broadcast(
                            None, match.score, AccessStatus.DENIED, note="No sufficiently confident match"
                        )
        finally:
            cap.release()


class CameraWorkerRegistry:
    """Tracks live CameraWorker instances so the API layer can start/stop
    recognition processing per camera on demand."""

    def __init__(self):
        self._workers: dict[str, CameraWorker] = {}
        self._lock = threading.Lock()

    def start(self, camera_id: str, camera_name: str, rtsp_url: str):
        with self._lock:
            worker = self._workers.get(camera_id)
            if worker is None:
                worker = CameraWorker(camera_id, camera_name, rtsp_url)
                self._workers[camera_id] = worker
            worker.start()

    def stop(self, camera_id: str):
        with self._lock:
            worker = self._workers.get(camera_id)
            if worker:
                worker.stop()

    def is_running(self, camera_id: str) -> bool:
        with self._lock:
            worker = self._workers.get(camera_id)
            return worker.is_running() if worker else False


registry = CameraWorkerRegistry()
