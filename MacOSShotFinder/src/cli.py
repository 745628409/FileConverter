from __future__ import annotations

from pathlib import Path
import argparse

from models import IndexData
from pipeline import build_index, search
from video_analysis import sec_to_timecode


def main():
    parser = argparse.ArgumentParser(description="MacOS Shot Finder CLI")
    sub = parser.add_subparsers(dest="cmd", required=True)

    idx = sub.add_parser("index")
    idx.add_argument("--video", required=True)
    idx.add_argument("--project", required=True)
    idx.add_argument("--fast", action="store_true", help="启用快速索引（降低精度）")

    s = sub.add_parser("search")
    s.add_argument("--project", required=True)
    s.add_argument("--query", required=True)
    s.add_argument("--top-k", type=int, default=10)

    args = parser.parse_args()

    if args.cmd == "index":
        data = build_index(Path(args.video), Path(args.project), high_accuracy=not args.fast)
        print(f"Indexed {len(data.shots)} shots into {args.project}")
    elif args.cmd == "search":
        data = IndexData.load(Path(args.project))
        rows = search(data, args.query, top_k=args.top_k)
        for i, row in enumerate(rows, start=1):
            shot = row["shot"]
            print(
                f"#{i} score={row['score']:.3f} sem={row['semantic']:.3f} kw={row['keyword']:.3f} boost={row['boost']:.3f}\n"
                f"{sec_to_timecode(shot.start_sec)} - {sec_to_timecode(shot.end_sec)}  "
                f"thumb={shot.thumbnail_path}\n"
                f"tags={','.join(shot.tags)}\n"
                f"actors={','.join(shot.actors)}\n"
                f"effects={','.join(shot.effects)}\n"
                f"transcript={shot.transcript}\n"
            )


if __name__ == "__main__":
    main()
