# Arquitectura y decisiones

## Visión general

Sistema de IA en producción (MVP académico) que responde preguntas sobre el mercado bursátil argentino, combinando RAG, re-ranking, un agente cíclico con LangGraph, herramientas externas vía MCP, y observabilidad básica. Basado en la arquitectura de referencia del curso, adaptado a un alcance manejable para un entregable individual.

## Flujo end-to-end

1. **Ingesta** (`retrieval/ingest.py`): se cargan PDFs/txt, se trocean en chunks (~800 caracteres, overlap 150) y se generan embeddings.
2. **Retrieval** (`orquestacion/pipeline.py`): ante una pregunta, se buscan los 10 chunks más similares por embeddings.
3. **Ranking** (`ranking/reranker.py`): esos 10 candidatos se reordenan
   con un cross-encoder (compara pregunta+chunk juntos, más preciso que
   solo similitud de vectores) y se toman los 4 mejores.
4. **Orquestación** (`orquestacion/pipeline.py`): se arma el prompt con el contexto final y se llama al LLM.
5. **Agente** (`agente/agente.py`, endpoint alternativo `/chat-agente`):
   variante con LangGraph que, si el contexto recuperado es insuficiente, reformula la pregunta y reintenta la búsqueda (hasta 2 intentos) antes de generar la respuesta final. Es un flujo cíclico con estado, no lineal.
6. **Adaptador MCP** (`adaptadores_mcp/`): expone una herramienta externa
   (`consultar_cotizacion`) siguiendo el protocolo MCP, con validación de inputs. Queda como pieza independiente/demostrativa; el siguiente paso natural es conectarla como un nodo más del agente.
7. **Observabilidad** (`observabilidad/`): cada consulta queda logueada
   con latencia, uso de CPU/memoria y una heurística de posible
   alucinación. Si se configura `LANGCHAIN_API_KEY`, además se envían
   trazas automáticas a LangSmith.
8. **Despliegue** (`despliegue/`): manifiestos de Kubernetes (Deployment +
   Service + template de Secret) y scripts de `deploy.sh` / `escalar.sh`.

## Decisiones clave y por qué

| Decisión | Alternativa considerada | Por qué se eligió así |
|---|---|---|
| Embeddings locales (sentence-transformers) | OpenAI embeddings | Gratis, sin dependencia de crédito externo, suficiente calidad para el MVP |
| LLM: Groq (Llama 3.1 8B) | OpenAI GPT-4o-mini | Free tier sin tarjeta de crédito, latencia muy baja |
| Chroma como vector store | Pinecone / Weaviate | Corre local, sin infraestructura ni cuenta externa, ideal para MVP |
| Cross-encoder para re-ranking | Re-ranking solo con score de embeddings | Mejora precisión sin agregar dependencia de API paga |
| LangGraph solo en endpoint separado (`/chat-agente`) | Reemplazar el pipeline lineal por completo | Permite comparar ambos enfoques y no arriesgar el flujo simple, que es más predecible para la demo |
| MCP como módulo independiente (no integrado al agente todavía) | Integrarlo directo al grafo | Alcance de tiempo del MVP; queda documentado como próximo paso |
| Heurística léxica de alucinación (en vez de un evaluador LLM) | Usar RAGAS o un juez LLM | Cero costo adicional y cero latencia extra; a cambio, es una señal aproximada, no una medición rigurosa |

## Métricas definidas

- **Latencia** (ms): tiempo total de la consulta, medido en
  `observabilidad/logger.py`.
- **Uso de recursos**: CPU% y memoria (MB) del proceso, vía `psutil`.
- **Tasa de posible alucinación**: heurística de solapamiento léxico entre
  la respuesta generada y el contexto recuperado. Un ratio alto de
  palabras "no soportadas" por el contexto dispara una alerta (`alerta:
  true`) en el log. **Limitación conocida:** es un proxy simple, no un
  detector semántico real — para producción se reemplazaría por un
  evaluador basado en LLM (ej. RAGAS, o los evaluators nativos de
  LangSmith).
- **Chunks recuperados** por consulta, como proxy de si el retrieval está
  encontrando contexto relevante.

## Despliegue y monitoreo (resumen)

- La imagen se construye con el `Dockerfile` de la raíz.
- `despliegue/deploy.sh` construye la imagen y aplica los manifiestos de
  K8s (`deployment.yaml`, `service.yaml`).
- Las credenciales (`GROQ_API_KEY`, etc.) se inyectan vía un `Secret` de
  Kubernetes (ver `despliegue/secret.example.yaml`), nunca hardcodeadas en
  la imagen.
- El `Deployment` define `readinessProbe`/`livenessProbe` contra `/health`
  para que Kubernetes pueda detectar instancias caídas y reiniciarlas.
- `despliegue/escalar.sh` permite ajustar manualmente el número de
  réplicas según carga.
- El monitoreo continuo, en este MVP, se apoya en el `queries.log`
  estructurado (JSON por línea) y, opcionalmente, en el dashboard de
  LangSmith si se configuró la API key.

## Alcance no cubierto (fuera del MVP)

- Integración de la tool MCP directamente en el grafo del agente.
- Autoscaling automático (HPA) en Kubernetes — el escalado es manual.
- Evaluación de alucinaciones basada en LLM-as-judge.
- Pipeline de CI/CD para build y deploy automático.
