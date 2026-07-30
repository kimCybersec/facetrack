"""
FaceTrack - Camera manager with enhanced discovery.
"""
import logging
from typing import List, Optional

from sqlalchemy.orm import Session

from database.models import Camera
from services.discovery import discover_cameras, scan_specific_ip
from ai.pipeline import registry as worker_registry

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
            # Update RTSP URL if it has changed
            if existing.rtsp_url != device.rtsp_url:
                existing.rtsp_url = device.rtsp_url
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


def discover_specific_camera(db: Session, ip_address: str) -> Optional[Camera]:
    """Discover and register a specific camera by IP address."""
    device = scan_specific_ip(ip_address)
    if not device:
        return None
    
    existing = db.query(Camera).filter(Camera.ip_address == device.ip_address).one_or_none()
    if existing:
        return existing
    
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
    db.commit()
    db.refresh(camera)
    return camera


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


def build_nvr_channel_rtsp_url(
    nvr_ip: str,
    channel: int,
    username: str,
    password: str,
    port: int = 554,
    main_stream: bool = True,
) -> str:
    """Constructs a channel-specific RTSP URL for cameras that sit behind an
    NVR's own PoE ports."""
    stream_suffix = "01" if main_stream else "02"
    return f"rtsp://{username}:{password}@{nvr_ip}:{port}/Streaming/Channels/{channel}{stream_suffix}"


def register_manual_camera(
    db: Session,
    name: str,
    ip_address: str,
    rtsp_url: str,
    location_label: str | None = None,
) -> Camera:
    """Registers a single camera/channel directly, bypassing ONVIF discovery."""
    existing = db.query(Camera).filter(Camera.rtsp_url == rtsp_url).one_or_none()
    if existing:
        return existing

    # Try to discover more info via ONVIF
    device = scan_specific_ip(ip_address)
    
    camera = Camera(
        name=name,
        manufacturer=device.manufacturer if device else "ZKTeco",
        model=device.model if device else None,
        ip_address=ip_address,
        onvif_port=device.onvif_port if device else 80,
        rtsp_url=rtsp_url,
        location_label=location_label,
        is_active=False,
    )
    db.add(camera)
    db.commit()
    db.refresh(camera)
    return camera


def resume_active_cameras(db: Session) -> None:
    """Called on application startup to reattach workers for any cameras
    that were left active before the last restart."""
    active_cameras = db.query(Camera).filter(Camera.is_active == True).all()
    for camera in active_cameras:
        worker_registry.start(camera.id, camera.name, camera.rtsp_url)
        logger.info("Resumed worker for previously-active camera %s", camera.name)