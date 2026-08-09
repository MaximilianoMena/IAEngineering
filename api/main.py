"""
api/main.py

API principal del asistente. Expone:
  - GET  /health : estado del servicio
  - POST /chat   : consulta al asistente RAG

Para correr: uvicorn api.main:app --reload
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from orquestacion.pipeline import get_pipeline
from observabilidad.logger import medir_consulta
from agente.agente import responder_con_agente

app = FastAPI(
    title="Mercado AR RAG",
    description="Asistente de IA sobre el mercado bursátil argentino",
    version="1.0",
)


class PreguntaRequest(BaseModel):
    pregunta: str


class ChatResponse(BaseModel):
    respuesta: str
    chunks_recuperados: int
    fuentes: list[str]


class ChatAgenteResponse(BaseModel):
    respuesta: str
    chunks_recuperados: int
    intentos_reformulacion: int
    pregunta_final_usada: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: PreguntaRequest):
    if not request.pregunta or not request.pregunta.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía.")

    try:
        pipeline = get_pipeline()
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    with medir_consulta(request.pregunta) as resultado_holder:
        resultado = pipeline.responder(request.pregunta)
        resultado_holder["chunks_recuperados"] = resultado["chunks_recuperados"]
        resultado_holder["respuesta"] = resultado["respuesta"]
        resultado_holder["contexto"] = resultado["contexto"]

    return ChatResponse(
        respuesta=resultado["respuesta"],
        chunks_recuperados=resultado["chunks_recuperados"],
        fuentes=resultado["fuentes"],
    )


@app.post("/chat-agente", response_model=ChatAgenteResponse)
def chat_agente(request: PreguntaRequest):
    """Variante que usa el agente con LangGraph: si el contexto recuperado
    no alcanza, reformula la pregunta y vuelve a buscar antes de responder.
    """
    if not request.pregunta or not request.pregunta.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía.")

    with medir_consulta(request.pregunta) as resultado_holder:
        resultado = responder_con_agente(request.pregunta)
        resultado_holder["chunks_recuperados"] = resultado["chunks_recuperados"]

    return ChatAgenteResponse(
        respuesta=resultado["respuesta"],
        chunks_recuperados=resultado["chunks_recuperados"],
        intentos_reformulacion=resultado["intentos_reformulacion"],
        pregunta_final_usada=resultado["pregunta_final_usada"],
    )
