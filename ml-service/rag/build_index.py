"""Build a BM25 index from the paraphrased guideline snippets."""
import pickle
import re
from pathlib import Path

from rank_bm25 import BM25Okapi

GUIDELINES_DIR = Path(__file__).parent / "guidelines"
INDEX_PATH = Path(__file__).parent / "bm25_index.pkl"  # generated, gitignored


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def load_snippets() -> list[dict]:
    """Parse lines of the form 'g2-1 | text' from grade_*.txt files."""
    snippets = []
    for path in sorted(GUIDELINES_DIR.glob("grade_*.txt")):
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if not line or "|" not in line:
                continue
            snippet_id, text = (part.strip() for part in line.split("|", 1))
            snippets.append({"id": snippet_id, "text": text})
    return snippets


def build_index() -> None:
    snippets = load_snippets()
    if not snippets:
        raise RuntimeError(f"No guideline snippets found in {GUIDELINES_DIR}")
    bm25 = BM25Okapi([tokenize(s["text"]) for s in snippets])
    with open(INDEX_PATH, "wb") as f:
        pickle.dump({"snippets": snippets, "bm25": bm25}, f)
    print(f"Indexed {len(snippets)} snippets -> {INDEX_PATH}")


if __name__ == "__main__":
    build_index()