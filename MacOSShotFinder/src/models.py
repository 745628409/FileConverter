from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List
import json


@dataclass
class Shot:
    shot_id: int
    start_sec: float
    end_sec: float
    mid_sec: float
    thumbnail_path: str
    transcript: str
    tags: List[str]
    actors: List[str]
    actor_scores: Dict[str, float]
    effects: List[str]
    effect_scores: Dict[str, float]
    feature_text: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Shot":
        data.setdefault("actors", [])
        data.setdefault("actor_scores", {})
        data.setdefault("effects", [])
        data.setdefault("effect_scores", {})
        return cls(**data)


@dataclass
class IndexData:
    video_path: str
    shots: List[Shot]
    embeddings: List[List[float]]
    feature_texts: List[str]

    def save(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "video_path": self.video_path,
            "shots": [s.to_dict() for s in self.shots],
            "embeddings": self.embeddings,
            "feature_texts": self.feature_texts,
        }
        (output_dir / "index.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, project_dir: Path) -> "IndexData":
        payload = json.loads((project_dir / "index.json").read_text(encoding="utf-8"))
        shots = [Shot.from_dict(item) for item in payload["shots"]]
        feature_texts = payload.get("feature_texts")
        if not feature_texts:
            feature_texts = [s.feature_text for s in shots]
        return cls(
            video_path=payload["video_path"],
            shots=shots,
            embeddings=payload["embeddings"],
            feature_texts=feature_texts,
        )
