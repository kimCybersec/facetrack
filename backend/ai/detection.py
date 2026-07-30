"""
FaceTrack - Face detection using YOLOv8-Face.

Wraps an Ultralytics YOLO model fine-tuned for face detection. The model
returns bounding boxes for every face found in a frame; each box is then
cropped and handed off to the embedding module.
"""
from dataclasses import dataclass
from typing import List

import numpy as np
from ultralytics import YOLO

from config import settings


@dataclass
class FaceDetection:
    box: tuple  # (x1, y1, x2, y2) in pixel coordinates
    confidence: float
    crop: np.ndarray  # BGR face crop, ready for embedding


class FaceDetector:
    """Thin, lazily-initialized wrapper around a YOLOv8-Face model.

    One instance is shared across all camera worker threads; Ultralytics
    models are safe to call concurrently for inference as long as you don't
    mutate model state, but we still guard with a lock to be defensive on
    older CPU builds.
    """

    _instance: "FaceDetector | None" = None

    def __init__(self, model_path: str | None = None, device: str | None = None):
        self.model_path = model_path or settings.YOLO_FACE_MODEL_PATH
        self.device = device or settings.DETECTION_DEVICE
        self.confidence = settings.YOLO_CONFIDENCE
        self._model = YOLO(self.model_path)
        if self.device:
            self._model.to(self.device)

    @classmethod
    def shared(cls) -> "FaceDetector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def detect(self, frame_bgr: np.ndarray, min_face_px: int = 40) -> List[FaceDetection]:
        """Run detection on a single BGR frame and return cropped faces."""
        results = self._model.predict(
            source=frame_bgr,
            conf=self.confidence,
            device=self.device,
            verbose=False,
        )

        detections: List[FaceDetection] = []
        if not results:
            return detections

        result = results[0]
        if result.boxes is None:
            return detections

        h, w = frame_bgr.shape[:2]
        for box in result.boxes:
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            if (x2 - x1) < min_face_px or (y2 - y1) < min_face_px:
                continue
            conf = float(box.conf[0]) if box.conf is not None else 0.0
            crop = frame_bgr[y1:y2, x1:x2].copy()
            if crop.size == 0:
                continue
            detections.append(FaceDetection(box=(x1, y1, x2, y2), confidence=conf, crop=crop))

        return detections
