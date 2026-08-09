"""
observabilidad/metricas.py

Métricas adicionales de observabilidad:
  - Heurística simple de posible alucinación (compara la respuesta contra
    el contexto recuperado; no es un detector perfecto, es un proxy rápido
    para un MVP).
  - Uso de recursos del proceso (CPU% y memoria), vía psutil.
"""

import os
import re

import psutil

_proceso = psutil.Process(os.getpid())

# Palabras muy comunes en español que no aportan señal para la heurística.
_STOPWORDS = {
    "el", "la", "los", "las", "de", "del", "en", "y", "a", "un", "una",
    "que", "es", "por", "con", "para", "se", "su", "sus", "al", "lo",
    "como", "más", "o", "no", "sí", "este", "esta", "esos", "esas",
}


def _tokenizar(texto: str) -> set:
    palabras = re.findall(r"[a-záéíóúñ0-9%]+", texto.lower())
    return {p for p in palabras if p not in _STOPWORDS and len(p) > 2}


def estimar_posible_alucinacion(respuesta: str, contexto: str) -> dict:
    """Heurística de solapamiento léxico entre respuesta y contexto.

    Si una porción grande de las palabras "de contenido" de la respuesta
    NO aparece en el contexto recuperado, es una señal (no una prueba) de
    que el modelo puede estar agregando información que no vino de los
    documentos. Útil como alerta rápida en un MVP; para producción real
    conviene un evaluador basado en LLM (ej. RAGAS, LangSmith evaluators).
    """
    palabras_respuesta = _tokenizar(respuesta)
    palabras_contexto = _tokenizar(contexto)

    if not palabras_respuesta:
        return {"ratio_no_soportado": 0.0, "alerta": False}

    no_soportadas = palabras_respuesta - palabras_contexto
    ratio = len(no_soportadas) / len(palabras_respuesta)

    return {
        "ratio_no_soportado": round(ratio, 3),
        "alerta": ratio > 0.6,  # umbral arbitrario para el MVP
    }


def medir_uso_recursos() -> dict:
    """Snapshot de uso de CPU y memoria del proceso actual."""
    mem_info = _proceso.memory_info()
    return {
        "cpu_percent": _proceso.cpu_percent(interval=0.1),
        "memoria_mb": round(mem_info.rss / (1024 * 1024), 2),
    }
