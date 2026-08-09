"""
agente/agente.py

Agente cíclico con LangGraph: en vez de un pipeline lineal (pregunta ->
retrieval -> respuesta), este flujo puede decidir reformular la pregunta
y volver a buscar si el contexto recuperado no alcanza, antes de generar
la respuesta final. Es un ejemplo mínimo de flujo con estado y decisiones
iterativas.

Flujo:
    buscar_contexto -> ¿alcanza? -> sí -> generar_respuesta -> FIN
                                  -> no (y quedan intentos) -> reformular -> buscar_contexto (loop)
                                  -> no (sin intentos) -> generar_respuesta (con lo que haya) -> FIN
"""

import sys
from pathlib import Path
from typing import TypedDict

sys.path.append(str(Path(__file__).resolve().parent.parent))

from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from orquestacion.pipeline import get_pipeline, _formatear_contexto
from ranking.reranker import rerank

MAX_INTENTOS = 2
MIN_CHUNKS_SUFICIENTES = 2


class AgenteState(TypedDict):
    pregunta_original: str
    pregunta_actual: str
    contexto_docs: list
    intentos: int
    respuesta: str


def _nodo_buscar_contexto(state: AgenteState) -> AgenteState:
    pipeline = get_pipeline()
    candidatos = pipeline.retriever.invoke(state["pregunta_actual"])
    docs = rerank(state["pregunta_actual"], candidatos, top_n=4)
    state["contexto_docs"] = docs
    return state


def _nodo_reformular(state: AgenteState) -> AgenteState:
    """Si no hubo contexto suficiente, le pide al LLM que reformule la
    pregunta de otra forma para intentar de nuevo."""
    pipeline = get_pipeline()
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Reformulá la siguiente pregunta sobre el mercado bursátil "
                "argentino usando otros términos o sinónimos, para mejorar "
                "una búsqueda semántica que no encontró buenos resultados. "
                "Respondé solo con la pregunta reformulada, nada más.",
            ),
            ("human", "{pregunta}"),
        ]
    )
    chain = prompt | pipeline.llm | StrOutputParser()
    nueva_pregunta = chain.invoke({"pregunta": state["pregunta_actual"]})

    state["pregunta_actual"] = nueva_pregunta.strip()
    state["intentos"] += 1
    return state


def _nodo_generar_respuesta(state: AgenteState) -> AgenteState:
    pipeline = get_pipeline()
    contexto = _formatear_contexto(state["contexto_docs"])

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", pipeline.prompt.messages[0].prompt.template),
            ("human", "{pregunta}"),
        ]
    )
    chain = (
        prompt.partial(contexto=contexto) | pipeline.llm | StrOutputParser()
    )
    state["respuesta"] = chain.invoke({"pregunta": state["pregunta_original"]})
    return state


def _decidir_siguiente_paso(state: AgenteState) -> str:
    """Función de decisión (edge condicional): ¿alcanza el contexto o
    reformulamos y buscamos de nuevo?"""
    contexto_suficiente = len(state["contexto_docs"]) >= MIN_CHUNKS_SUFICIENTES
    quedan_intentos = state["intentos"] < MAX_INTENTOS

    if contexto_suficiente or not quedan_intentos:
        return "generar_respuesta"
    return "reformular"


def construir_grafo():
    grafo = StateGraph(AgenteState)

    grafo.add_node("buscar_contexto", _nodo_buscar_contexto)
    grafo.add_node("reformular", _nodo_reformular)
    grafo.add_node("generar_respuesta", _nodo_generar_respuesta)

    grafo.set_entry_point("buscar_contexto")
    grafo.add_conditional_edges(
        "buscar_contexto",
        _decidir_siguiente_paso,
        {"generar_respuesta": "generar_respuesta", "reformular": "reformular"},
    )
    grafo.add_edge("reformular", "buscar_contexto")  # acá está el ciclo
    grafo.add_edge("generar_respuesta", END)

    return grafo.compile()


def responder_con_agente(pregunta: str) -> dict:
    """Punto de entrada: corre el grafo completo para una pregunta."""
    app = construir_grafo()
    estado_inicial: AgenteState = {
        "pregunta_original": pregunta,
        "pregunta_actual": pregunta,
        "contexto_docs": [],
        "intentos": 0,
        "respuesta": "",
    }
    estado_final = app.invoke(estado_inicial)

    return {
        "respuesta": estado_final["respuesta"],
        "intentos_reformulacion": estado_final["intentos"],
        "pregunta_final_usada": estado_final["pregunta_actual"],
        "chunks_recuperados": len(estado_final["contexto_docs"]),
    }


if __name__ == "__main__":
    # Prueba manual rápida desde la terminal
    resultado = responder_con_agente("¿Qué dice el último informe sobre financiamiento?")
    print(resultado)
