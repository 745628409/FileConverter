from __future__ import annotations

from pathlib import Path
from typing import List
import numpy as np

from sentence_transformers import SentenceTransformer

from models import IndexData, Shot
from video_analysis import detect_shots, extract_frame_at, write_thumbnail, estimate_visual_tags


def try_transcribe(video_path: Path):
    try:
        from faster_whisper import WhisperModel
    except Exception:
        return []

    model = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _ = model.transcribe(str(video_path), beam_size=5)
    rows = []
    for seg in segments:
        rows.append({"start": float(seg.start), "end": float(seg.end), "text": seg.text.strip()})
    return rows


def transcript_for_shot(segments, start_sec: float, end_sec: float) -> str:
    parts = []
    for item in segments:
        overlap = min(end_sec, item["end"]) - max(start_sec, item["start"])
        if overlap > 0:
            parts.append(item["text"])
    return " ".join(parts).strip()


def build_feature_text(tags: List[str], transcript: str) -> str:
    base = "，".join(tags)
    if transcript:
        return f"镜头特征：{base}。台词：{transcript}"
    return f"镜头特征：{base}。"


def build_index(video_path: Path, project_dir: Path) -> IndexData:
    shots_raw = detect_shots(video_path)
    segments = try_transcribe(video_path)

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    shots: List[Shot] = []
    feature_texts: List[str] = []

    thumb_dir = project_dir / "thumbnails"
    for i, raw in enumerate(shots_raw):
        mid = (raw.start_sec + raw.end_sec) / 2
        frame = extract_frame_at(video_path, mid)
        tags = estimate_visual_tags(frame)
        transcript = transcript_for_shot(segments, raw.start_sec, raw.end_sec)
        feature_text = build_feature_text(tags, transcript)

        thumb = thumb_dir / f"shot_{i:05d}.jpg"
        write_thumbnail(frame, thumb)

        shot = Shot(
            shot_id=i,
            start_sec=raw.start_sec,
            end_sec=raw.end_sec,
            mid_sec=mid,
            thumbnail_path=str(thumb),
            transcript=transcript,
            tags=tags,
            feature_text=feature_text,
        )
        shots.append(shot)
        feature_texts.append(feature_text)

    embeddings = model.encode(feature_texts, normalize_embeddings=True).tolist() if feature_texts else []

    index_data = IndexData(video_path=str(video_path), shots=shots, embeddings=embeddings)
    index_data.save(project_dir)
    return index_data


def search(index_data: IndexData, query: str, top_k: int = 12):
    if not index_data.shots:
        return []

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    q = model.encode([query], normalize_embeddings=True)[0]
    embs = np.array(index_data.embeddings)
    sims = embs @ q

    order = np.argsort(-sims)[:top_k]
    results = []
    for idx in order:
        shot = index_data.shots[int(idx)]
        results.append({"score": float(sims[idx]), "shot": shot})
    return results
