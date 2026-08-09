"""
orquestacion/pipeline.py

Pipeline principal del RAG: recibe una pregunta, busca contexto relevante
en la base vectorial, arma el prompt y llama al LLM para generar la respuesta.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

sys.path.append(str(Path(__file__).resolve().parent.parent))
from ranking.reranker import rerank

load_dotenv()

PERSIST_DIR = Path(__file__).resolve().parent.parent / "chroma_db"
CANDIDATOS_INICIALES = 10  # cuántos trae el retriever antes de re-rankear
TOP_K_FINAL = 4  # cuántos quedan después del re-ranker

SYSTEM_PROMPT = """Sos un asistente especializado en el mercado bursátil argentino \
(BYMA, CEDEARs, bonos, acciones locales, informes económicos).

Respondé SIEMPRE en base al contexto provisto a continuación. Si el contexto \
no tiene información suficiente para responder, decilo explícitamente en vez \
de inventar datos. Sé claro, conciso y citá de qué documento sale la información \
cuando sea posible.

Contexto:
{contexto}
"""


def _formatear_contexto(docs) -> str:
    partes = []
    for i, doc in enumerate(docs, start=1):
        fuente = doc.metadata.get("source", "desconocida")
        partes.append(f"[Fuente {i}: {fuente}]\n{doc.page_content}")
    return "\n\n".join(partes)


class RAGPipeline:
    """Encapsula el pipeline de retrieval + generación."""

    def __init__(self):
        if not PERSIST_DIR.exists():
            raise RuntimeError(
                "No se encontró la base vectorial. Corré primero: "
                "python retrieval/ingest.py"
            )

        embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
        self.vectorstore = Chroma(
            persist_directory=str(PERSIST_DIR),
            embedding_function=embeddings,
        )
        self.retriever = self.vectorstore.as_retriever(
            search_kwargs={"k": CANDIDATOS_INICIALES}
        )

        if not os.getenv("GROQ_API_KEY"):
            raise RuntimeError(
                "Falta GROQ_API_KEY. Conseguí una gratis en https://console.groq.com/keys "
                "y ponela en tu archivo .env"
            )
        self.llm = ChatGroq(model="llama-3.1-8b-instant", temperature=0.2)

        self.prompt = ChatPromptTemplate.from_messages(
            [
                ("system", SYSTEM_PROMPT),
                ("human", "{pregunta}"),
            ]
        )

    def responder(self, pregunta: str) -> dict:
        """Ejecuta el pipeline completo y devuelve la respuesta + metadata."""
        candidatos = self.retriever.invoke(pregunta)
        # Re-ranking: los candidatos vienen ordenados por similitud de
        # embeddings, acá los reordenamos comparando pregunta+chunk juntos
        # (más preciso) y nos quedamos con los mejores TOP_K_FINAL.
        docs_recuperados = rerank(pregunta, candidatos, top_n=TOP_K_FINAL)
        contexto = _formatear_contexto(docs_recuperados)

        chain = (
            {"contexto": lambda _: contexto, "pregunta": RunnablePassthrough()}
            | self.prompt
            | self.llm
            | StrOutputParser()
        )

        respuesta = chain.invoke(pregunta)

        return {
            "respuesta": respuesta,
            "contexto": contexto,
            "chunks_recuperados": len(docs_recuperados),
            "fuentes": list(
                {d.metadata.get("source", "desconocida") for d in docs_recuperados}
            ),
        }


# Instancia única reutilizada por la API (se carga una vez al arrancar)
_pipeline_instance = None


def get_pipeline() -> RAGPipeline:
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = RAGPipeline()
    return _pipeline_instance
