"""
FaceTrack - SQLAlchemy ORM models.
"""
import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column,
    String,
    Boolean,
    Float,
    DateTime,
    ForeignKey,
    Enum as SQLEnum,
    Integer,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
from pgvector.sqlalchemy import Vector

from backend.config import settings

Base = declarative_base()


def gen_uuid() -> str:
    return str(uuid.uuid4())


class AccessStatus(str, enum.Enum):
    GRANTED = "GRANTED"
    DENIED = "DENIED"


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    manufacturer = Column(String(100), default="ZKTeco")
    model = Column(String(100), nullable=True)
    ip_address = Column(String(64), nullable=False, unique=True)
    onvif_port = Column(Integer, default=80)
    rtsp_url = Column(String(512), nullable=False)
    location_label = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=False, nullable=False)
    last_seen_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    logs = relationship("AccessLog", back_populates="camera", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "manufacturer": self.manufacturer,
            "model": self.model,
            "ip_address": self.ip_address,
            "onvif_port": self.onvif_port,
            "rtsp_url": self.rtsp_url,
            "location_label": self.location_label,
            "is_active": self.is_active,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }


class Student(Base):
    __tablename__ = "students"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    student_number = Column(String(64), nullable=False, unique=True)
    full_name = Column(String(255), nullable=False)
    program = Column(String(255), nullable=True)
    photo_path = Column(String(512), nullable=True)
    embedding = Column(Vector(settings.EMBEDDING_DIM), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    logs = relationship("AccessLog", back_populates="student", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_number": self.student_number,
            "full_name": self.full_name,
            "program": self.program,
            "photo_path": self.photo_path,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class AccessLog(Base):
    __tablename__ = "access_logs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    student_id = Column(UUID(as_uuid=False), ForeignKey("students.id"), nullable=True)
    camera_id = Column(UUID(as_uuid=False), ForeignKey("cameras.id"), nullable=False)
    confidence_score = Column(Float, nullable=True)
    status = Column(SQLEnum(AccessStatus), nullable=False)
    note = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    student = relationship("Student", back_populates="logs")
    camera = relationship("Camera", back_populates="logs")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "student_id": self.student_id,
            "student_name": self.student.full_name if self.student else None,
            "camera_id": self.camera_id,
            "camera_name": self.camera.name if self.camera else None,
            "confidence_score": self.confidence_score,
            "status": self.status.value if isinstance(self.status, AccessStatus) else self.status,
            "note": self.note,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }
