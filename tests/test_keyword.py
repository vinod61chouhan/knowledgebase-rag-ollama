from app.retrieval.keyword import bm25_rank

def test_keyword():
    rows = [{"id": 1, "content": "apple banana"}, {"id": 2, "content": "rocket moon space"},
            {"id": 3, "content": "orange pear fruit"}]
    assert bm25_rank("rocket", rows, 3)[0]["id"] == 2
