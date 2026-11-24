import asyncio
from functools import lru_cache
from sentence_transformers import CrossEncoder
from app.core.config import settings

@lru_cache
def get_reranker():
    return CrossEncoder(settings.rerank_model)

def _rank(question: str, rows: list[dict], top_k: int):
    scores = get_reranker().predict([(question, row["content"]) for row in rows])
    return sorted([dict(row, rerank_score=float(score)) for row, score in zip(rows, scores)],
                  key=lambda row: row["rerank_score"], reverse=True)[:top_k]

async def rerank(question: str, rows: list[dict], top_k: int):
    if not rows:
        return []
    return await asyncio.to_thread(_rank, question, rows, top_k)
