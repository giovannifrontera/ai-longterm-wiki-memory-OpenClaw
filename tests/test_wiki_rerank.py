"""Test per wiki_rerank.py — il CrossEncoder viene sempre mockato: nessun
download di modello né dipendenza da GPU/CPU reale."""

import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import wiki_rerank


def _fake_model(scores):
    model = MagicMock()
    model.predict.return_value = scores
    return model


def test_rerank_reorders_by_score(monkeypatch):
    monkeypatch.setattr(wiki_rerank, "_load_reranker", lambda *a, **k: _fake_model([0.1, 0.9, 0.5]))
    candidates = [
        {"chunk_text": "a", "path": "a.md"},
        {"chunk_text": "b", "path": "b.md"},
        {"chunk_text": "c", "path": "c.md"},
    ]
    cfg = {"reranker": {"enabled": True}}
    result = wiki_rerank.rerank("query", candidates, cfg)
    assert [c["path"] for c in result] == ["b.md", "c.md", "a.md"]
    assert result[0]["_rerank_score"] == 0.9


def test_rerank_disabled_is_noop_but_sets_fallback_score(monkeypatch):
    called = MagicMock()
    monkeypatch.setattr(wiki_rerank, "_load_reranker", called)
    candidates = [{"chunk_text": "a", "path": "a.md", "_distance": 0.2}]
    cfg = {"reranker": {"enabled": False}}
    result = wiki_rerank.rerank("query", candidates, cfg)
    called.assert_not_called()
    assert result[0]["_rerank_score"] == 0.8  # 1 - _distance


def test_rerank_empty_candidates_does_not_explode(monkeypatch):
    called = MagicMock()
    monkeypatch.setattr(wiki_rerank, "_load_reranker", called)
    result = wiki_rerank.rerank("query", [], {"reranker": {"enabled": True}})
    assert result == []
    called.assert_not_called()


def test_rerank_default_enabled_when_no_reranker_key(monkeypatch):
    monkeypatch.setattr(wiki_rerank, "_load_reranker", lambda *a, **k: _fake_model([0.3]))
    candidates = [{"chunk_text": "a", "path": "a.md"}]
    result = wiki_rerank.rerank("query", candidates, {})
    assert result[0]["_rerank_score"] == 0.3


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
