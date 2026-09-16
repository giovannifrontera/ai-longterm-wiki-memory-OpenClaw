"""Cross-encoder reranking dei candidati recuperati dal bi-encoder.

Il bi-encoder (bge-m3) valuta query e chunk separatamente e li confronta via
cosine similarity: veloce ma perde interazioni fini tra i token. Il
cross-encoder valuta la coppia (query, chunk) in un solo forward pass ed è
usato solo come seconda fase, sui candidati già filtrati dall'ANN search.

Modello di default: BAAI/bge-reranker-v2-m3 — stessa famiglia di bge-m3,
multilingue (italiano incluso), nessuna dipendenza nuova (sentence-transformers
la include già).
"""

DEFAULT_RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"

_model = None
_model_name = None


def _load_reranker(model_name: str = DEFAULT_RERANKER_MODEL, device: str | None = None):
    global _model, _model_name
    if _model is None or _model_name != model_name:
        from sentence_transformers import CrossEncoder
        _model = CrossEncoder(model_name, device=device)
        _model_name = model_name
    return _model


def rerank(query: str, candidates: list[dict], cfg: dict, text_key: str = "chunk_text") -> list[dict]:
    """Riordina candidates per rilevanza cross-encoder rispetto a query.

    candidates: lista di dict con almeno text_key. Ogni dict riceve in output
    un campo "_rerank_score" (più alto = più rilevante) e la lista torna
    ordinata per score decrescente. Se il reranking è disabilitato in config
    o i candidati sono vuoti, ritorna candidates invariato.
    """
    if not candidates:
        return candidates

    reranker_cfg = cfg.get("reranker", {})
    if not reranker_cfg.get("enabled", True):
        # I chiamanti leggono sempre _rerank_score: senza reranking, usiamo la
        # similarità del bi-encoder (1 - _distance) come fallback, ordine invariato
        # (query_similar restituisce già in ordine di rilevanza decrescente).
        for c in candidates:
            c.setdefault("_rerank_score", 1.0 - c.get("_distance", 0.0))
        return candidates

    model_name = reranker_cfg.get("model", DEFAULT_RERANKER_MODEL)
    device = cfg.get("device")
    model = _load_reranker(model_name, device)

    pairs = [(query, c[text_key]) for c in candidates]
    scores = model.predict(pairs)

    for c, s in zip(candidates, scores):
        c["_rerank_score"] = float(s)

    return sorted(candidates, key=lambda c: c["_rerank_score"], reverse=True)
