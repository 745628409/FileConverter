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
    feature_text: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Shot":
        return cls(**data)


@dataclass
class IndexData:
    video_path: str
    shots: List[Shot]
    embeddings: List[List[float]]

    def save(self, output_dir: Path) -> None:
        output_dir.mkdir(parents=True, exist_ok=True)
        payload = {
            "video_path": self.video_path,
            "shots": [s.to_dict() for s in self.shots],
            "embeddings": self.embeddings,
        }
        (output_dir / "index.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, project_dir: Path) -> "IndexData":
        payload = json.loads((project_dir / "index.json").read_text(encoding="utf-8"))
        shots = [Shot.from_dict(item) for item in payload["shots"]]
        return cls(video_path=payload["video_path"], shots=shots, embeddings=payload["embeddings"])
