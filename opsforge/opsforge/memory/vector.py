"""Vector-style recall with zero external dependencies.

Default embedder is a hashed bag-of-words (TF-IDF-ish) vector: deterministic,
offline, and good enough for incident-similarity search. The `Embedder`
protocol lets you swap in a real embedding model (sentence-transformers,
a hosted API, etc.) without touching callers.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from pathlib import Path
from typing import Callable, Protocol

Vector = dict[int, float]  # sparse: index -> weight

_STOP = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "was", "are",
    "it", "this", "that", "with", "as", "at", "by", "be", "from", "after", "before",
}


class Embedder(Protocol):
    def __call__(self, text: str) -> Vector: ...


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_]+", text.lower()) if t not in _STOP and len(t) > 1]


def hashing_embedder(dim: int = 4096) -> Callable[[str], Vector]:
    def embed(text: str) -> Vector:
        counts: dict[int, float] = {}
        for tok in _tokens(text):
            idx = int(hashlib.md5(tok.encode()).hexdigest(), 16) % dim
            counts[idx] = counts.get(idx, 0.0) + 1.0
        # sublinear tf + L2 norm
        vec = {i: 1.0 + math.log(c) for i, c in counts.items()}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        return {i: v / norm for i, v in vec.items()}

    return embed


def cosine(a: Vector, b: Vector) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b.get(i, 0.0) for i, w in a.items())


class VectorMemory:
    def __init__(self, path: Path, embedder: Embedder | None = None):
        self.path = Path(path)
        self.embed = embedder or hashing_embedder()
        self._docs: dict[str, dict] = {}
        if self.path.exists():
            raw = json.loads(self.path.read_text())
            for doc_id, d in raw.items():
                self._docs[doc_id] = {
                    "text": d["text"],
                    "vec": {int(k): v for k, v in d["vec"].items()},
                }

    def upsert(self, doc_id: str, text: str) -> None:
        self._docs[doc_id] = {"text": text, "vec": self.embed(text)}

    def delete(self, doc_id: str) -> None:
        self._docs.pop(doc_id, None)

    def search(self, query: str, k: int = 3, min_score: float = 0.05) -> list[tuple[str, float, str]]:
        q = self.embed(query)
        scored = [(doc_id, cosine(q, d["vec"]), d["text"]) for doc_id, d in self._docs.items()]
        scored = [s for s in scored if s[1] >= min_score]
        scored.sort(key=lambda s: s[1], reverse=True)
        return scored[:k]

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({k: {"text": v["text"], "vec": {str(i): w for i, w in v["vec"].items()}} for k, v in self._docs.items()})
        )

    def reindex(self, documents: list[tuple[str, str]]) -> None:
        """Rebuild from the file store (the source of truth)."""
        self._docs.clear()
        for doc_id, text in documents:
            self.upsert(doc_id, text)
        self.save()

    def __len__(self) -> int:
        return len(self._docs)
