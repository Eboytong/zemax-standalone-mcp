"""Generate status and queue views for the current development roadmap."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.development import roadmap


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--markdown', type=Path)
    parser.add_argument('--queue', type=Path)
    parser.add_argument('--ranked', type=Path)
    args = parser.parse_args()
    report = roadmap.summarize(ROOT)
    roadmap.write_outputs(report, args.output, args.markdown, args.queue, args.ranked)
    print(json.dumps({key: report[key] for key in ('plan_id', 'planned_count', 'completed_count', 'next_item')},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
