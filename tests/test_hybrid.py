from app.retrieval.hybrid import fuse

def test_fusion_promotes_common_result():
    a = [{"id": 1}, {"id": 2}]
    b = [{"id": 2}, {"id": 3}]
    assert fuse([a, b])[0]["id"] == 2
