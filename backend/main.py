"""
FaceTrack - FastAPI backend entrypoint.
"""
import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager

import cv2
import numpy as np
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database.connection import init_db, get_db, session_scope
from backend.database.models import Camera, Student, AccessLog
from backend.services.camera_manager import (
    run_discovery_and_upsert,
    set_camera_active,
    resume_active_cameras,
)
from backend.ai.embedding import FaceEmbedder
from backend.ai.detection import FaceDetector
from backend.ai.pipeline import broadcaster

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("facetrack.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.STORAGE_DIR, exist_ok=True)
    init_db()
    broadcaster.bind_loop(asyncio.get_event_loop())
    with session_scope() as db:
        resume_active_cameras(db)
    yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Ensures unexpected errors still return a JSON response with CORS
    headers attached, instead of a bare 500 that the browser reports as
    a CORS failure."""
    logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ---------------------------------------------------------------------------
# Cameras
# ---------------------------------------------------------------------------

@app.get("/api/cameras")
def list_cameras(db: Session = Depends(get_db)):
    cameras = db.query(Camera).order_by(Camera.created_at.desc()).all()
    return [c.to_dict() for c in cameras]


@app.get("/api/cameras/discover")
def discover(db: Session = Depends(get_db)):
    """Runs ONVIF discovery and returns newly found / refreshed ZKTeco cameras."""
    cameras = run_discovery_and_upsert(db)
    return [c.to_dict() for c in cameras]


@app.patch("/api/cameras/{camera_id}/toggle")
def toggle_camera(camera_id: str, active: bool, db: Session = Depends(get_db)):
    """Enables or disables active recognition processing on a camera."""
    try:
        camera = set_camera_active(db, camera_id, active)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return camera.to_dict()


# ---------------------------------------------------------------------------
# Students
# ---------------------------------------------------------------------------

@app.post("/api/students/enroll")
async def enroll_student(
    student_number: str = Form(...),
    full_name: str = Form(...),
    program: str | None = Form(None),
    photo: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Accepts student profile info and a photo, extracts the FaceNet
    embedding, and saves the student record + embedding to the database."""
    existing = db.query(Student).filter(Student.student_number == student_number).one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="A student with this number already exists")

    raw_bytes = await photo.read()
    np_arr = np.frombuffer(raw_bytes, dtype=np.uint8)
    frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="Uploaded file is not a readable image")

    detector = FaceDetector.shared()
    faces = detector.detect(frame)
    if not faces:
        raise HTTPException(status_code=422, detail="No face detected in the uploaded photo")

    # Use the largest detected face (most likely the primary subject).
    best_face = max(faces, key=lambda f: (f.box[2] - f.box[0]) * (f.box[3] - f.box[1]))
    embedder = FaceEmbedder.shared()
    embedding = embedder.embed(best_face.crop)

    filename = f"{uuid.uuid4()}.jpg"
    photo_path = os.path.join(settings.STORAGE_DIR, filename)
    cv2.imwrite(photo_path, frame)

    student = Student(
        student_number=student_number,
        full_name=full_name,
        program=program,
        photo_path=photo_path,
        embedding=embedding.tolist(),
        is_active=True,
    )
    db.add(student)
    db.commit()
    db.refresh(student)
    return student.to_dict()


@app.get("/api/students")
def list_students(db: Session = Depends(get_db)):
    students = db.query(Student).order_by(Student.created_at.desc()).all()
    return [s.to_dict() for s in students]


@app.delete("/api/students/{student_id}")
def deactivate_student(student_id: str, db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id).one_or_none()
    if student is None:
        raise HTTPException(status_code=404, detail="Student not found")
    student.is_active = False
    db.commit()
    return {"status": "deactivated"}


# ---------------------------------------------------------------------------
# Logs
# ---------------------------------------------------------------------------

@app.get("/api/logs")
def list_logs(limit: int = 100, db: Session = Depends(get_db)):
    logs = db.query(AccessLog).order_by(AccessLog.timestamp.desc()).limit(limit).all()
    return [l.to_dict() for l in logs]


@app.websocket("/api/logs/live")
async def live_logs(websocket: WebSocket):
    """Streams live gate entry logs to the frontend UI as they occur."""
    await websocket.accept()
    try:
        while True:
            payload = await broadcaster.get()
            await websocket.send_json(payload)
    except WebSocketDisconnect:
        logger.info("Live log client disconnected")


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.APP_NAME}
