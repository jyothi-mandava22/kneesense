"""Pre-generate one report pair per KL grade (0-4) into cache/cached_reports.json.
Run once from ml-service:  python -m rag.make_cache
"""
import json
import time
from pathlib import Path

from rag.report_generator import ReportGenerationError, generate_reports
from rag.retriever import retrieve

CACHE_PATH = Path(__file__).parent.parent / "cache" / "cached_reports.json"


def main() -> None:
    cache = {}
    for grade in range(5):
        chunks = retrieve(grade, top_k=4)
        for attempt in (1, 2, 3):
            try:
                cache[str(grade)] = generate_reports(grade, None, chunks)
                print(f"Grade {grade}: ok")
                break
            except ReportGenerationError as exc:
                print(f"Grade {grade}: attempt {attempt} failed: {exc}")
                time.sleep(5)
        else:
            raise SystemExit(f"Could not generate grade {grade}; nothing written.")
        time.sleep(2)  # stay well under free-tier rate limits
    CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"Saved {len(cache)} grades -> {CACHE_PATH}")


if __name__ == "__main__":
    main()