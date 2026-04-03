from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List
import cv2
import numpy as np


@dataclass
class RawShot:
    start_sec: float
    end_sec: float


def detect_shots(video_path: Path, sample_fps: float = 2.0, threshold: float = 0.45) -> List[RawShot]:
    cap = cv2.VideoCapture(str(video_path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if total_frames > 0 else 0.0

    frame_step = max(1, int(fps / sample_fps))

    last_hist = None
    cut_times: List[float] = [0.0]
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % frame_step != 0:
            frame_idx += 1
            continue

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
        cv2.normalize(hist, hist)

        if last_hist is not None:
            sim = cv2.compareHist(last_hist, hist, cv2.HISTCMP_CORREL)
            if sim < threshold:
                cut_times.append(frame_idx / fps)

        last_hist = hist
        frame_idx += 1

    cap.release()

    if duration > 0:
        cut_times.append(duration)

    cut_times = sorted(set(round(x, 3) for x in cut_times))

    shots: List[RawShot] = []
    for i in range(len(cut_times) - 1):
        s, e = cut_times[i], cut_times[i + 1]
        if e - s >= 0.5:
            shots.append(RawShot(start_sec=s, end_sec=e))

    if not shots and duration > 0:
        shots = [RawShot(0.0, duration)]
    return shots


def estimate_visual_tags(frame: np.ndarray) -> List[str]:
    tags: List[str] = []

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean())
    if brightness < 70:
        tags.append("暗光")
    elif brightness > 170:
        tags.append("高亮")
    else:
        tags.append("正常光")

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)

    h, w = gray.shape
    if len(faces) == 0:
        tags.append("空镜头或远景")
    else:
        max_area = max((fw * fh for (_, _, fw, fh) in faces), default=0)
        ratio = max_area / float(h * w)
        if ratio > 0.15:
            tags.append("近景")
        elif ratio > 0.05:
            tags.append("中景")
        else:
            tags.append("远景")

        face_y = np.mean([y + fh / 2 for (_, y, _, fh) in faces])
        if face_y < h * 0.42:
            tags.append("低角度机位")
        elif face_y > h * 0.58:
            tags.append("高角度机位")
        else:
            tags.append("平视机位")

    edges = cv2.Canny(gray, 80, 160)
    edge_ratio = float(np.count_nonzero(edges)) / edges.size
    if edge_ratio > 0.14:
        tags.append("画面复杂/可能动作段落")
    else:
        tags.append("画面平稳/可能叙事段落")

    return tags


def estimate_effect_tags(frame: np.ndarray) -> List[str]:
    tags: List[str] = []
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    sat = float(hsv[:, :, 1].mean())
    val = float(hsv[:, :, 2].mean())

    warm_mask = cv2.inRange(hsv, (0, 110, 120), (35, 255, 255))
    warm_ratio = float(np.count_nonzero(warm_mask)) / warm_mask.size
    if warm_ratio > 0.22 and val > 120:
        tags.append("火焰/爆炸特效")

    blue_mask = cv2.inRange(hsv, (90, 90, 80), (130, 255, 255))
    blue_ratio = float(np.count_nonzero(blue_mask)) / blue_mask.size
    if blue_ratio > 0.28:
        tags.append("冷色科幻特效")

    low_sat = sat < 45 and 90 < val < 185
    blur_score = cv2.Laplacian(gray, cv2.CV_64F).var()
    if low_sat and blur_score < 120:
        tags.append("烟雾/雾化特效")

    if blur_score < 80:
        tags.append("运动模糊/高速运动")

    return tags


def extract_frame_at(video_path: Path, sec: float) -> np.ndarray:
    cap = cv2.VideoCapture(str(video_path))
    cap.set(cv2.CAP_PROP_POS_MSEC, sec * 1000)
    ret, frame = cap.read()
    cap.release()
    if not ret:
        raise RuntimeError(f"无法在 {sec:.2f}s 读取帧")
    return frame


def write_thumbnail(frame: np.ndarray, output_file: Path) -> None:
    output_file.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_file), frame)


def sec_to_timecode(sec: float) -> str:
    ms = int((sec % 1) * 1000)
    total = int(sec)
    s = total % 60
    m = (total // 60) % 60
    h = total // 3600
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
