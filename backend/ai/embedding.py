"""
FaceTrack - Face embedding generation using FaceNet (InceptionResnetV1).

Produces L2-normalized embedding vectors from aligned face crops. The
`facenet-pytorch` InceptionResnetV1 model natively outputs 512-d vectors;
we project/truncate to the configured EMBEDDING_DIM (128 by default, per
spec) via a fixed random projection matrix seeded once at import time so
that the same crop always maps to the same reduced vector.
"""
import numpy as np
import cv2
import torch
from facenet_pytorch import InceptionResnetV1

from config import settings

_DEVICE = "cuda" if (settings.DETECTION_DEVICE == "cuda" and torch.cuda.is_available()) else "cpu"


class FaceEmbedder:
    _instance: "FaceEmbedder | None" = None

    def __init__(self, embedding_dim: int | None = None):
        self.embedding_dim = embedding_dim or settings.EMBEDDING_DIM
        self.model = InceptionResnetV1(pretrained="vggface2").eval().to(_DEVICE)

        # Fixed, deterministic random projection from the model's native
        # 512-d output down to the configured storage dimension. Seeded so
        # it is stable across process restarts.
        rng = np.random.RandomState(42)
        projection = rng.normal(size=(512, self.embedding_dim)).astype(np.float32)
        # Orthonormalize columns so the projection approximately preserves
        # cosine-similarity relationships between vectors.
        q, _ = np.linalg.qr(projection)
        self._projection = torch.from_numpy(q[:, : self.embedding_dim].copy()).to(_DEVICE)

    @classmethod
    def shared(cls) -> "FaceEmbedder":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def _preprocess(face_bgr: np.ndarray) -> torch.Tensor:
        face_rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
        face_rgb = cv2.resize(face_rgb, (160, 160), interpolation=cv2.INTER_LINEAR)
        tensor = torch.from_numpy(face_rgb).float()
        tensor = (tensor - 127.5) / 128.0  # standard FaceNet normalization
        tensor = tensor.permute(2, 0, 1).unsqueeze(0)  # NCHW
        return tensor

    @torch.no_grad()
    def embed(self, face_bgr: np.ndarray) -> np.ndarray:
        """Return an L2-normalized embedding vector for a single face crop."""
        tensor = self._preprocess(face_bgr).to(_DEVICE)
        raw_embedding = self.model(tensor)  # shape (1, 512)
        reduced = raw_embedding @ self._projection  # shape (1, embedding_dim)
        vec = reduced.squeeze(0).cpu().numpy()
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.astype(np.float32)

    @torch.no_grad()
    def embed_batch(self, face_crops: list[np.ndarray]) -> np.ndarray:
        """Vectorized embedding for a batch of face crops."""
        if not face_crops:
            return np.empty((0, self.embedding_dim), dtype=np.float32)
        tensors = torch.cat([self._preprocess(c) for c in face_crops], dim=0).to(_DEVICE)
        raw = self.model(tensors)
        reduced = raw @ self._projection
        vecs = reduced.cpu().numpy()
        norms = np.linalg.norm(vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        return (vecs / norms).astype(np.float32)


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """Both vectors are expected to already be L2-normalized, but we
    normalize defensively so this is safe to call standalone."""
    a_norm = a / (np.linalg.norm(a) or 1.0)
    b_norm = b / (np.linalg.norm(b) or 1.0)
    return float(np.dot(a_norm, b_norm))
