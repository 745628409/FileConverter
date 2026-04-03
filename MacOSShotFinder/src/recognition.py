from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple
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

    orb = cv2.ORB_create(nfeatures=300)
    descs: List[np.ndarray] = []
    for (x, y, w, h) in faces:
        face = gray[y : y + h, x : x + w]
        _kps, desc = orb.detectAndCompute(face, None)
        if desc is not None and len(desc) > 12:
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


def detect_actors(frame: np.ndarray, refs: List[ActorReference], threshold: float = 0.18) -> List[str]:
    if not refs:
        return []
    shot_descs = _extract_face_descriptors(frame)
    if not shot_descs:
        return []

    found: List[str] = []
    for actor in refs:
        best = 0.0
        for sd in shot_descs:
            for rd in actor.descriptors[:8]:
                best = max(best, _match_score(sd, rd))
                if best >= threshold:
                    found.append(actor.name)
                    break
            if actor.name in found:
                break
    return sorted(set(found))
