#!/usr/bin/env python
"""
Manual registration script for cameras on 172.16.0.0/20 network.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import session_scope
from services.camera_manager import discover_specific_camera, register_manual_camera
from services.discovery import scan_specific_ip
from config import settings

# Your 6 cameras - update with actual IPs
CAMERA_IPS = [
    "172.16.6.163",
    "172.16.6.164",  # Replace with your actual IPs
    "172.16.6.165",
    "172.16.6.166",
    "172.16.6.167",
    "172.16.6.168",
]

def register_all_cameras():
    with session_scope() as db:
        registered = []
        for ip in CAMERA_IPS:
            print(f"Checking camera at {ip}...")
            
            # Try automatic discovery first
            device = scan_specific_ip(ip)
            if device:
                camera = discover_specific_camera(db, ip)
                if camera:
                    registered.append(camera)
                    print(f"  ✅ Registered: {camera.name} at {ip}")
                else:
                    print(f"  ⚠️  Found but could not register: {ip}")
            else:
                # Manual registration with common RTSP URL
                rtsp_url = f"rtsp://{settings.DEFAULT_CAMERA_USER}:{settings.DEFAULT_CAMERA_PASSWORD}@{ip}:554/stream1"
                camera = register_manual_camera(
                    db,
                    name=f"Camera-{ip.replace('.', '-')}",
                    ip_address=ip,
                    rtsp_url=rtsp_url,
                    location_label=f"Location {ip}"
                )
                if camera:
                    registered.append(camera)
                    print(f"  ✅ Registered manually: {camera.name} at {ip}")
                else:
                    print(f"  ❌ Failed to register: {ip}")
        
        print(f"\n✅ Registered {len(registered)} cameras")
        
        # Show all cameras
        from database.models import Camera
        all_cameras = db.query(Camera).all()
        print("\nAll cameras in database:")
        for cam in all_cameras:
            print(f"  - {cam.name} ({cam.ip_address}) - Active: {cam.is_active}")

if __name__ == "__main__":
    register_all_cameras()