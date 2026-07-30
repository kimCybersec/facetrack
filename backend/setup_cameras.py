#!/usr/bin/env python
"""
Quick setup script for discovering and registering cameras.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.connection import session_scope, init_db
from services.camera_manager import run_discovery_and_upsert, set_camera_active
import logging

logging.basicConfig(level=logging.INFO)

def setup():
    print("🔧 Initializing database...")
    init_db()
    
    print("🔍 Discovering cameras...")
    with session_scope() as db:
        cameras = run_discovery_and_upsert(db)
        print(f"✅ Found {len(cameras)} cameras")
        
        for cam in cameras:
            print(f"  - {cam.name} ({cam.ip_address})")
        
        if cameras:
            print("\n🚀 Activating first camera...")
            try:
                active_cam = set_camera_active(db, cameras[0].id, True)
                print(f"✅ Activated: {active_cam.name}")
            except Exception as e:
                print(f"❌ Could not activate camera: {e}")
        
        print("\n📋 All cameras in database:")
        from database.models import Camera
        all_cams = db.query(Camera).all()
        for cam in all_cams:
            status = "🟢 Active" if cam.is_active else "⚪ Inactive"
            print(f"  - {cam.name} ({cam.ip_address}) - {status}")

if __name__ == "__main__":
    setup()