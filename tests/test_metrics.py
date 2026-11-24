from app.evaluation.metrics import recall_at_k, reciprocal_rank

def test_recall():
    assert recall_at_k(["a", "b"], {"b", "c"}, 2) == 0.5

def test_mrr():
    assert reciprocal_rank(["a", "b"], {"b"}) == 0.5
