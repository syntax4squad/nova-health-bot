"""
MODULE 4 -- RAG (RETRIEVAL-AUGMENTED GENERATION)

Pipeline:
  verified KB documents -> chunking -> TF-IDF embeddings -> vector search
  -> relevant evidence -> (fed into the LLM prompt) -> grounded response

We use a lightweight TF-IDF + cosine-similarity retriever (scikit-learn)
instead of a hosted embeddings API. This keeps the prototype free to run
and fully offline for retrieval, while still implementing the
"retrieve-before-generate" architecture the blueprint requires
(Question -> Retrieval -> Context -> LLM -> Grounded answer), instead of
naive Question -> LLM -> Answer.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from knowledge_base import DISEASES, iter_chunks

_chunks = []          # list of text chunks
_chunk_meta = []       # list of (disease_key, field_name)
_vectorizer = None
_matrix = None


def _build_index():
    global _vectorizer, _matrix
    for key, field, text in iter_chunks():
        _chunks.append(text)
        _chunk_meta.append((key, field))
    _vectorizer = TfidfVectorizer(stop_words="english")
    _matrix = _vectorizer.fit_transform(_chunks)


_build_index()


def retrieve(query: str, top_k: int = 4):
    """Return top_k relevant chunks as a list of dicts with text + metadata."""
    if not query or not query.strip():
        return []
    q_vec = _vectorizer.transform([query])
    sims = cosine_similarity(q_vec, _matrix)[0]
    ranked = sorted(range(len(sims)), key=lambda i: sims[i], reverse=True)
    results = []
    for i in ranked[:top_k]:
        if sims[i] <= 0.02:
            continue
        key, field = _chunk_meta[i]
        results.append({
            "disease": DISEASES[key]["name"],
            "field": field,
            "text": _chunks[i],
            "score": float(sims[i]),
            "source": DISEASES[key]["source"],
            "last_updated": DISEASES[key]["last_updated"],
        })
    return results


def detect_disease_topic(query: str):
    """Best-effort match of a query to a single disease key, for analytics tagging."""
    results = retrieve(query, top_k=1)
    if not results:
        return None
    return results[0]["disease"]


def get_disease(key: str):
    return DISEASES.get(key)


def list_diseases():
    return [{"key": k, "name": v["name"]} for k, v in DISEASES.items()]
