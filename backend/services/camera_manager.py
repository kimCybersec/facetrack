"""
FaceTrack - Camera manager.

Bridges the ONVIF discovery layer and the database, and dynamically
attaches/detaches recognition workers (backend.ai.pipeline.CameraWorker)
when an admin toggles a camera's `is_active` state from the dashboard.
"""
import logging
from typing import List

from sqlalchemy.orm import Session

from backend.database.models import Camera
from backend.services.discovery import discover_cameras
from backend.ai.pipeline import registry as worker_registry

logger = logging.getLogger("facetrack.camera_manager")


def run_discovery_and_upsert(db: Session) -> List[Camera]:
    """Run ONVIF discovery and upsert any newly-found devices into the
    cameras table (existing rows, matched by IP, are left untouched aside
    from refreshing last_seen_at)."""
    from datetime import datetime

    found = discover_cameras()
    new_or_updated: List[Camera] = []

    for device in found:
        existing = db.query(Camera).filter(Camera.ip_address == device.ip_address).one_or_none()
        if existing:
            existing.last_seen_at = datetime.utcnow()
            new_or_updated.append(existing)
            continue

        camera = Camera(
            name=device.name,
            manufacturer=device.manufacturer,
            model=device.model,
            ip_address=device.ip_address,
            onvif_port=device.onvif_port,
            rtsp_url=device.rtsp_url,
            is_active=False,
        )
        db.add(camera)
        new_or_updated.append(camera)

    db.commit()
    for cam in new_or_updated:
        db.refresh(cam)
    return new_or_updated


def set_camera_active(db: Session, camera_id: str, active: bool) -> Camera:
    """Toggle a camera's active state and start/stop its recognition
    worker thread accordingly."""
    camera = db.query(Camera).filter(Camera.id == camera_id).one_or_none()
    if camera is None:
        raise ValueError(f"Camera {camera_id} not found")

    camera.is_active = active
    db.commit()
    db.refresh(camera)

    if active:
        worker_registry.start(camera.id, camera.name, camera.rtsp_url)
        logger.info("Camera %s (%s) activated — worker attached", camera.name, camera.id)
    else:
        worker_registry.stop(camera.id)
        logger.info("Camera %s (%s) deactivated — worker detached", camera.name, camera.id)

    return camera


def resume_active_cameras(db: Session) -> None:
    """Called on application startup to reattach workers for any cameras
    that were left active before the last restart."""
    active_cameras = db.query(Camera).filter(Camera.is_active == True).all()  # noqa: E712
    for camera in active_cameras:
        worker_registry.start(camera.id, camera.name, camera.rtsp_url)
        logger.info("Resumed worker for previously-active camera %s", camera.name)
