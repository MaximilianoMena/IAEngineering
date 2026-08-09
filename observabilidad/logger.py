"""
observabilidad/logger.py

Logging simple y estructurado de cada consulta al asistente:
timestamp, pregunta, cantidad de chunks recuperados, latencia, uso de
recursos y una heurística de posible alucinación.

Además, si están seteadas las variables de entorno LANGCHAIN_TRACING_V2 y
LANGCHAIN_API_KEY (gratis en https://smith.langchain.com), LangChain manda
automáticamente trazas detalladas de cada llamada a LangSmith — no hace
falta código extra para eso, solo configurarlo en el .env.
"""

import json
import logging
import time
from contextlib import contextmanager
from pathlib import Path

from observabilidad.metricas import estimar_posible_alucinacion, medir_uso_recursos

LOG_FILE = Path(__file__).resolve().parent / "queries.log"

logger = logging.getLogger("mercado_ar_rag")
logger.setLevel(logging.INFO)

if not logger.handlers:
    handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)


@contextmanager
def medir_consulta(pregunta: str):
    """Context manager que mide latencia, uso de recursos y una heurística
    de alucinación, y loguea todo al salir.

    Se le puede pasar al holder (dict) las claves opcionales:
      - chunks_recuperados (int)
      - respuesta (str) y contexto (str), para calcular la heurística de
        alucinación.
    """
    inicio = time.time()
    resultado_holder = {}

    yield resultado_holder

    duracion_ms = round((time.time() - inicio) * 1000, 2)

    registro = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "pregunta": pregunta,
        "chunks_recuperados": resultado_holder.get("chunks_recuperados"),
        "latencia_ms": duracion_ms,
        **medir_uso_recursos(),
    }

    if "respuesta" in resultado_holder and "contexto" in resultado_holder:
        registro["alucinacion"] = estimar_posible_alucinacion(
            resultado_holder["respuesta"], resultado_holder["contexto"]
        )

    logger.info(json.dumps(registro, ensure_ascii=False))
