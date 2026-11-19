"""Retrieve guideline snippets for a KL grade or short query."""
import pickle

from rag.build_index import INDEX_PATH, build_index, tokenize

DEFAULT_QUERY = "management treatment exercise referral specialist symptoms"
_data = None


def _load() -> dict:
    global _data
    if _data is None:
        if not INDEX_PATH.exists():
            build_index()
        with open(INDEX_PATH, "rb") as f:
            _data = pickle.load(f)
    return _data


def retrieve(query_or_grade: int | str, top_k: int = 3) -> list[dict]:
    """Return top_k snippets as [{"id": "g2-1", "text": "..."}].
    An int restricts results to that KL grade's snippets."""
    data = _load()
    snippets, bm25 = data["snippets"], data["bm25"]
    if isinstance(query_or_grade, int):
        prefix = f"g{query_or_grade}-"
        allowed = [i for i, s in enumerate(snippets) if s["id"].startswith(prefix)]
        query = DEFAULT_QUERY
    else:
        allowed = list(range(len(snippets)))
        query = str(query_or_grade)
    scores = bm25.get_scores(tokenize(query))
    ranked = sorted(allowed, key=lambda i: scores[i], reverse=True)[:top_k]
    return [snippets[i] for i in ranked]