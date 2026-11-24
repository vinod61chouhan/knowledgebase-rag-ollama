import json
from pathlib import Path
from app.retrieval.hybrid import search_hybrid

def recall_at_k(ids: list[str], relevant: set[str], k: int) -> float:
    return len(set(ids[:k]) & relevant) / len(relevant) if relevant else 0.0

def reciprocal_rank(ids: list[str], relevant: set[str]) -> float:
    return next((1 / i for i, x in enumerate(ids, 1) if x in relevant), 0.0)

async def evaluate_dataset(tenant: str, owner: str, top_k: int):
    examples = json.loads(Path("app/evaluation/dataset.json").read_text(encoding="utf-8"))
    results = []
    for item in examples:
        relevant = set(item.get("relevant_document_ids", []))
        if not relevant or any("REPLACE" in x for x in relevant):
            continue
        rows = await search_hybrid(item["question"], tenant, owner, max(20, top_k))
        ids = [str(r["document_id"]) for r in rows]
        results.append({"question": item["question"], "recall_at_k": recall_at_k(ids, relevant, top_k),
                        "reciprocal_rank": reciprocal_rank(ids, relevant)})
    return {"evaluated": len(results), "recall_at_k": sum(x["recall_at_k"] for x in results) / len(results)
            if results else None, "mrr": sum(x["reciprocal_rank"] for x in results) / len(results)
            if results else None, "details": results,
            "note": "Document-level retrieval evaluation; answer quality needs a human-labeled dataset."}
