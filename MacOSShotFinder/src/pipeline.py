from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Set
import re
import numpy as np

from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer

from models import IndexData, Shot
from recognition import detect_actor_scores, load_actor_references, pick_actors
from video_analysis import (
    detect_shots,
    estimate_effect_scores,
    estimate_visual_tags,
    extract_frame_at,
    pick_effects,
    sample_times,
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


def _merge_effect_scores(score_rows: List[Dict[str, float]]) -> Dict[str, float]:
    merged: Dict[str, List[float]] = {}
    for row in score_rows:
        for k, v in row.items():
            merged.setdefault(k, []).append(v)
    return {k: float(np.mean(vals)) for k, vals in merged.items()}


def _temporal_refine(shots: List[Shot]) -> None:
    # 邻域平滑：当相邻镜头同类信息强一致时，补齐中间弱漏检
    for i in range(1, len(shots) - 1):
        prev_shot = shots[i - 1]
        cur = shots[i]
        next_shot = shots[i + 1]

        prev_actors = set(prev_shot.actors)
        next_actors = set(next_shot.actors)
        shared_actor = prev_actors.intersection(next_actors)
        for actor in shared_actor:
            if actor not in cur.actors and cur.actor_scores.get(actor, 0.0) >= 0.14:
                cur.actors.append(actor)

        prev_fx = set(prev_shot.effects)
        next_fx = set(next_shot.effects)
        shared_fx = prev_fx.intersection(next_fx)
        for fx in shared_fx:
            if fx not in cur.effects and cur.effect_scores.get(fx, 0.0) >= 0.30:
                cur.effects.append(fx)

        cur.actors = sorted(set(cur.actors))
        cur.effects = sorted(set(cur.effects))


def build_index(video_path: Path, project_dir: Path, high_accuracy: bool = True) -> IndexData:
    shots_raw = detect_shots(video_path)
    segments = try_transcribe(video_path)
    actor_refs = load_actor_references(project_dir / "actors")

    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    shots: List[Shot] = []
    feature_texts: List[str] = []

    thumb_dir = project_dir / "thumbnails"
    for i, raw in enumerate(shots_raw):
        mid = (raw.start_sec + raw.end_sec) / 2

        times = sample_times(raw.start_sec, raw.end_sec, 3 if high_accuracy else 1)
        frames = [extract_frame_at(video_path, t) for t in times]
        frame = frames[len(frames) // 2]

        tag_votes: Dict[str, int] = {}
        for frm in frames:
            for tg in estimate_visual_tags(frm):
                tag_votes[tg] = tag_votes.get(tg, 0) + 1
        tags = sorted([k for k, c in tag_votes.items() if c >= 1 + int(high_accuracy)])

        effect_score_rows = [estimate_effect_scores(frm) for frm in frames]
        effect_scores = _merge_effect_scores(effect_score_rows)
        effects = pick_effects(effect_scores, threshold=0.45 if high_accuracy else 0.55)

        actor_scores = detect_actor_scores(frames, actor_refs)
        actors = pick_actors(actor_scores, threshold=0.20 if high_accuracy else 0.25)

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
            actor_scores=actor_scores,
            effects=effects,
            effect_scores=effect_scores,
            feature_text=feature_text,
        )
        shots.append(shot)
        feature_texts.append(feature_text)

    _temporal_refine(shots)

    # temporal refine 后重建 feature_text
    feature_texts = []
    for shot in shots:
        shot.feature_text = build_feature_text(shot.tags, shot.effects, shot.actors, shot.transcript)
        feature_texts.append(shot.feature_text)

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
        matched_actor = actor_need.intersection(set(shot.actors))
        matched_effect = effect_need.intersection(set(shot.effects))

        if matched_actor:
            boost[i] += 0.18 + max(shot.actor_scores.get(a, 0.0) for a in matched_actor) * 0.22
        if matched_effect:
            boost[i] += 0.14 + max(shot.effect_scores.get(e, 0.0) for e in matched_effect) * 0.18

        text = shot.feature_text.lower()
        for token in re.findall(r"\w+", query.lower()):
            if token and token in text:
                boost[i] += 0.008

    final_score = 0.55 * sem_sims + 0.30 * kw_sims + 0.15 * _normalize(boost)

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
