from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List
import cv2
import numpy as np


@dataclass
class ActorReference:
    name: str
    descriptors: List[np.ndarray]


def _extract_face_descriptors(image: np.ndarray) -> List[np.ndarray]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    detector = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = detector.detectMultiScale(gray, 1.1, 4)

    orb = cv2.ORB_create(nfeatures=350)
    descs: List[np.ndarray] = []
    for (x, y, w, h) in faces:
        face = gray[y : y + h, x : x + w]
        _kps, desc = orb.detectAndCompute(face, None)
        if desc is not None and len(desc) > 16:
            descs.append(desc)
    return descs


def load_actor_references(actor_dir: Path) -> List[ActorReference]:
    if not actor_dir.exists():
        return []

    refs: List[ActorReference] = []
    for sub in sorted(actor_dir.iterdir()):
        if not sub.is_dir():
            continue
        all_descs: List[np.ndarray] = []
        for img_path in sub.glob("*"):
            if img_path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}:
                continue
            img = cv2.imread(str(img_path))
            if img is None:
                continue
            all_descs.extend(_extract_face_descriptors(img))
        if all_descs:
            refs.append(ActorReference(name=sub.name, descriptors=all_descs))
    return refs


def _match_score(desc_a: np.ndarray, desc_b: np.ndarray) -> float:
    matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    pairs = matcher.knnMatch(desc_a, desc_b, k=2)
    good = 0
    total = 0
    for m_n in pairs:
        if len(m_n) < 2:
            continue
        m, n = m_n
        total += 1
        if m.distance < 0.75 * n.distance:
            good += 1
    if total == 0:
        return 0.0
    return good / total


def detect_actor_scores(frames: List[np.ndarray], refs: List[ActorReference]) -> Dict[str, float]:
    if not refs or not frames:
        return {}

    frame_descs = []
    for frame in frames:
        frame_descs.extend(_extract_face_descriptors(frame))

    if not frame_descs:
        return {}

    scores: Dict[str, float] = {}
    for actor in refs:
        local_scores: List[float] = []
        for sd in frame_descs:
            for rd in actor.descriptors[:10]:
                local_scores.append(_match_score(sd, rd))
        if not local_scores:
            continue
        # 用 top-k 均值减少偶然误匹配
        top = sorted(local_scores, reverse=True)[:8]
        scores[actor.name] = float(np.mean(top))

    return scores


def pick_actors(scores: Dict[str, float], threshold: float = 0.20) -> List[str]:
    return sorted([name for name, score in scores.items() if score >= threshold])
