"""
ranking/reranker.py

Re-ranker de resultados: toma los chunks recuperados por similitud
semántica (embeddings) y los reordena con un cross-encoder, que es más
preciso porque compara pregunta y chunk juntos en vez de comparar
vectores por separado.

Modelo local, gratis, sin API key (se descarga la primera vez, ~90MB).
"""

from sentence_transformers import CrossEncoder

_modelo = None


def _get_modelo() -> CrossEncoder:
    global _modelo
    if _modelo is None:
        _modelo = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    return _modelo


def rerank(pregunta: str, documentos: list, top_n: int = 4) -> list:
    """Reordena documentos por relevancia real a la pregunta.

    Args:
        pregunta: la consulta del usuario.
        documentos: lista de Document (de LangChain) ya recuperados.
        top_n: cuántos devolver después de reordenar.

    Returns:
        Lista de documentos, los top_n más relevantes, ordenados de
        mayor a menor score.
    """
    if not documentos:
        return []

    modelo = _get_modelo()
    pares = [[pregunta, doc.page_content] for doc in documentos]
    scores = modelo.predict(pares)

    documentos_con_score = list(zip(documentos, scores))
    documentos_con_score.sort(key=lambda x: x[1], reverse=True)

    return [doc for doc, _score in documentos_con_score[:top_n]]
