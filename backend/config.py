"""
FaceTrack - Global configuration.
Loads settings from environment variables with sane local-dev defaults.
"""
import os
from functools import lru_cache

BASE_DIR = os.path.dirname(os.path.abspath(__file__))  # .../backend


class Settings:
    # --- Database ---
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "facetrack")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "Rkim2346?")
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "facetrack")
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: str = os.getenv("POSTGRES_PORT", "5432")

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # --- Redis ---
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
    ATTENDANCE_COOLDOWN_SECONDS: int = int(os.getenv("ATTENDANCE_COOLDOWN_SECONDS", "60"))

    # --- Camera discovery ---
    DISCOVERY_SUBNET: str = os.getenv("DISCOVERY_SUBNET", "192.168.1.0/24")
    ONVIF_DISCOVERY_TIMEOUT: float = float(os.getenv("ONVIF_DISCOVERY_TIMEOUT", "4.0"))
    DEFAULT_CAMERA_USER: str = os.getenv("DEFAULT_CAMERA_USER", "admin")
    DEFAULT_CAMERA_PASSWORD: str = os.getenv("DEFAULT_CAMERA_PASSWORD", "")
    RTSP_STREAM_PATH: str = os.getenv("RTSP_STREAM_PATH", "stream1")

    # --- Recognition pipeline ---
    FACE_MATCH_THRESHOLD: float = float(os.getenv("FACE_MATCH_THRESHOLD", "0.65"))
    EMBEDDING_DIM: int = int(os.getenv("EMBEDDING_DIM", "128"))
    FRAME_SAMPLE_INTERVAL_SEC: float = float(os.getenv("FRAME_SAMPLE_INTERVAL_SEC", "0.5"))
    YOLO_FACE_MODEL_PATH: str = os.getenv(
        "YOLO_FACE_MODEL_PATH", os.path.join(BASE_DIR, "models", "yolov8n-face.pt")
    )
    YOLO_CONFIDENCE: float = float(os.getenv("YOLO_CONFIDENCE", "0.5"))
    DETECTION_DEVICE: str = os.getenv("DETECTION_DEVICE", "cpu")  # "cpu" or "cuda"

    # --- Relay / access control ---
    RELAY_OPEN_DURATION_SEC: int = int(os.getenv("RELAY_OPEN_DURATION_SEC", "3"))
    RELAY_HTTP_TIMEOUT_SEC: float = float(os.getenv("RELAY_HTTP_TIMEOUT_SEC", "3.0"))
    RELAY_MAX_RETRIES: int = int(os.getenv("RELAY_MAX_RETRIES", "2"))

    # --- App ---
    APP_NAME: str = "FaceTrack"
    CORS_ORIGINS: list = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-change-me")
    STORAGE_DIR: str = os.getenv("STORAGE_DIR", os.path.join(BASE_DIR, "storage", "enrollment_photos"))


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
