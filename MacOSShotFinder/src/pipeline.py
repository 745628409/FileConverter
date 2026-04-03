from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set
import re
import numpy as np

from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer

from models import IndexData, Shot
from recognition import detect_actors, load_actor_references
from video_analysis import (
    detect_shots,
    estimate_effect_tags,
    estimate_visual_tags,
    extract_frame_at,
    write_thumbnail,
)


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


def build_feature_text(tags: List[str], effects: List[str], actors: List[str], transcript: str) -> str:
    blocks = []
    if tags:
        blocks.append(f"镜头特征：{'，'.join(tags)}")
    if effects:
        blocks.append(f"特效：{'，'.join(effects)}")
    if actors:
        blocks.append(f"演员：{'，'.join(actors)}")
    if transcript:
        blocks.append(f"台词：{transcript}")
    return "。".join(blocks) + "。"


def build_index(video_path: Path, project_dir: Path) -> IndexData:
    shots_raw = detect_shots(video_path)
    segments = try_transcribe(video_path)
    actor_refs = load_actor_references(project_dir / "actors")

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    shots: List[Shot] = []
    feature_texts: List[str] = []

    thumb_dir = project_dir / "thumbnails"
    for i, raw in enumerate(shots_raw):
        mid = (raw.start_sec + raw.end_sec) / 2
        frame = extract_frame_at(video_path, mid)

        tags = estimate_visual_tags(frame)
        effects = estimate_effect_tags(frame)
        actors = detect_actors(frame, actor_refs)
        transcript = transcript_for_shot(segments, raw.start_sec, raw.end_sec)
        feature_text = build_feature_text(tags, effects, actors, transcript)

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
            actors=actors,
            effects=effects,
            feature_text=feature_text,
        )
        shots.append(shot)
        feature_texts.append(feature_text)

    embeddings = model.encode(feature_texts, normalize_embeddings=True).tolist() if feature_texts else []

    index_data = IndexData(
        video_path=str(video_path),
        shots=shots,
        embeddings=embeddings,
        feature_texts=feature_texts,
    )
    index_data.save(project_dir)
    return index_data


def _extract_actor_tokens(query: str, actor_pool: Set[str]) -> Set[str]:
    q = query.lower()
    return {name for name in actor_pool if name.lower() in q}


def _extract_effect_tokens(query: str) -> Set[str]:
    q = query.lower()
    mapping = {
        "爆炸": "火焰/爆炸特效",
        "火焰": "火焰/爆炸特效",
        "科幻": "冷色科幻特效",
        "蓝光": "冷色科幻特效",
        "烟雾": "烟雾/雾化特效",
        "雾": "烟雾/雾化特效",
        "模糊": "运动模糊/高速运动",
        "高速": "运动模糊/高速运动",
    }
    found = set()
    for k, v in mapping.items():
        if k in q:
            found.add(v)
    return found


def _normalize(arr: np.ndarray) -> np.ndarray:
    if len(arr) == 0:
        return arr
    mn, mx = float(arr.min()), float(arr.max())
    if mx - mn < 1e-9:
        return np.zeros_like(arr)
    return (arr - mn) / (mx - mn)


def search(index_data: IndexData, query: str, top_k: int = 12):
    if not index_data.shots:
        return []

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    q_emb = model.encode([query], normalize_embeddings=True)[0]
    sem_sims = np.array(index_data.embeddings) @ q_emb

    vectorizer = TfidfVectorizer(token_pattern=r"(?u)\b\w+\b")
    tfidf_mat = vectorizer.fit_transform(index_data.feature_texts)
    q_tfidf = vectorizer.transform([query])
    kw_sims = (tfidf_mat @ q_tfidf.T).toarray().reshape(-1)

    sem_sims = _normalize(sem_sims)
    kw_sims = _normalize(kw_sims)

    actor_pool = {a for s in index_data.shots for a in s.actors}
    actor_need = _extract_actor_tokens(query, actor_pool)
    effect_need = _extract_effect_tokens(query)

    boost = np.zeros(len(index_data.shots), dtype=float)
    for i, shot in enumerate(index_data.shots):
        if actor_need and actor_need.intersection(set(shot.actors)):
            boost[i] += 0.25
        if effect_need and effect_need.intersection(set(shot.effects)):
            boost[i] += 0.2

        # 对明显关键词增加额外排序偏好
        text = shot.feature_text.lower()
        for token in re.findall(r"\w+", query.lower()):
            if token and token in text:
                boost[i] += 0.01

    final_score = 0.58 * sem_sims + 0.30 * kw_sims + 0.12 * boost

    order = np.argsort(-final_score)[:top_k]
    results = []
    for idx in order:
        shot = index_data.shots[int(idx)]
        results.append(
            {
                "score": float(final_score[idx]),
                "semantic": float(sem_sims[idx]),
                "keyword": float(kw_sims[idx]),
                "boost": float(boost[idx]),
                "shot": shot,
            }
        )
    return results
