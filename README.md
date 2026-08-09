# Mercado AR RAG 🇦🇷📈

Sistema de IA en producción (MVP académico) que responde preguntas sobre
el mercado bursátil argentino (BYMA, CEDEARs, bonos, informes económicos),
con RAG, re-ranking, un agente cíclico con LangGraph, un adaptador MCP y
observabilidad básica.

Proyecto final — Curso de AI Engineering (Coderhouse).
Basado en la arquitectura de [ai-system-production](https://github.com/FedeGG09/ai-system-production).
Decisiones de diseño detalladas en [`docs/arquitectura.md`](docs/arquitectura.md).

## Arquitectura — flujo general

1. Se cargan documentos (PDFs/txt) en `data/raw/`.
2. **Retrieval** (`retrieval/`): se trocean y generan embeddings, guardados
   en una base vectorial local (Chroma).
3. Ante una pregunta, se recuperan los 10 chunks más similares.
4. **Ranking** (`ranking/`): un cross-encoder los reordena por relevancia
   real y se queda con los 4 mejores.
5. **Orquestación** (`orquestacion/`): LangChain arma el prompt con ese
   contexto y llama al LLM (Groq/Llama 3.1).
6. **Agente** (`agente/`): variante alternativa con LangGraph — si el
   contexto no alcanza, reformula la pregunta y reintenta (flujo cíclico
   con estado) antes de responder.
7. **Adaptador MCP** (`adaptadores_mcp/`): expone una herramienta externa
   (cotizaciones) siguiendo el protocolo MCP, con validación de inputs.
8. **Observabilidad** (`observabilidad/`): latencia, uso de recursos y una
   heurística de posible alucinación por consulta, más trazas opcionales
   a LangSmith.
9. **Despliegue** (`despliegue/`): manifiestos de Kubernetes y scripts de
   deploy/escalado.

## Estructura

```
mercado-ar-rag/
├── retrieval/          # ingestión, chunking y embeddings
│   └── ingest.py
├── ranking/             # re-ranker (cross-encoder)
│   └── reranker.py
├── orquestacion/        # pipeline RAG lineal con LangChain
│   └── pipeline.py
├── agente/               # agente cíclico con estado (LangGraph)
│   └── agente.py
├── adaptadores_mcp/      # servidor MCP con herramienta externa
│   ├── servidor_mcp.py
│   └── README.md
├── api/                  # API principal (FastAPI)
│   └── main.py
├── observabilidad/       # logging, métricas y heurística de alucinación
│   ├── logger.py
│   └── metricas.py
├── despliegue/            # Kubernetes + scripts de deploy/escalado
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── secret.example.yaml
│   ├── deploy.sh
│   └── escalar.sh
├── docs/                   # decisiones de arquitectura y métricas
│   └── arquitectura.md
├── data/raw/                # PDFs/txt fuente (vos los agregás)
├── tests/                    # pruebas básicas
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env.example
```

## Cómo correrlo localmente

### 1) Entorno

```bash
python -m venv venv
source venv/bin/activate      # en Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Variables de entorno

Este proyecto usa servicios **gratuitos**:
- **Embeddings**: modelo local (`sentence-transformers`), no necesita API key.
- **LLM**: [Groq](https://console.groq.com/keys) — gratis, sin tarjeta.
- **Observabilidad (opcional)**: [LangSmith](https://smith.langchain.com) — gratis.

```bash
cp .env.example .env
# completá GROQ_API_KEY (obligatoria) y, si querés, LANGCHAIN_API_KEY (opcional)
```

### 3) Agregar tus documentos

Poné tus PDFs o .txt sobre el mercado argentino (informes de CNV, BYMA,
IAMC, etc.) dentro de `data/raw/`.

### 4) Ingestión (generar la base vectorial)

```bash
python retrieval/ingest.py
```

### 5) Levantar la API

```bash
uvicorn api.main:app --reload
```

### 6) Probarlo

```bash
# Pipeline lineal (retrieval -> ranking -> LLM)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "¿Qué dice el último informe sobre el Merval?"}'

# Agente con LangGraph (reformula si el contexto no alcanza)
curl -X POST http://localhost:8000/chat-agente \
  -H "Content-Type: application/json" \
  -d '{"pregunta": "¿Qué dice el último informe sobre el Merval?"}'
```

O con Docker:

```bash
docker compose up --build
```

## Endpoints

| Método | Ruta            | Descripción                                          |
|--------|-----------------|-------------------------------------------------------|
| GET    | `/health`       | Estado del servicio                                   |
| POST   | `/chat`         | Pipeline RAG lineal (body: `{"pregunta": "..."}`)     |
| POST   | `/chat-agente`  | Variante con agente/LangGraph (mismo body)            |

## Adaptador MCP

Ver [`adaptadores_mcp/README.md`](adaptadores_mcp/README.md) para cómo
correr y conectar el servidor de herramientas.

## Despliegue

```bash
./despliegue/deploy.sh              # build + apply a Kubernetes
./despliegue/escalar.sh 4           # escalar a 4 réplicas
```

Requiere tener `kubectl` configurado contra tu cluster y haber creado el
Secret real (ver `despliegue/secret.example.yaml`).

## Observabilidad

Cada consulta se loguea en `observabilidad/queries.log` (JSON por línea)
con: timestamp, pregunta, chunks recuperados, latencia, uso de CPU/memoria
y una heurística de posible alucinación. Si completás `LANGCHAIN_API_KEY`
en `.env`, además se envían trazas automáticas a LangSmith sin tocar
código (más detalle en `docs/arquitectura.md`).

## Stack

- **LangChain** — orquestación del pipeline RAG
- **LangGraph** — agente cíclico con estado
- **MCP** — protocolo para herramientas externas
- **Chroma** — base de datos vectorial local
- **sentence-transformers** — embeddings locales + cross-encoder para ranking
- **Groq/Llama 3.1** — LLM (gratis)
- **FastAPI** — API
- **Docker / Kubernetes** — contenedorización y despliegue

## Sobre el uso de servicios gratuitos

Groq tiene límites de uso en su free tier (requests por minuto/día),
pensados para desarrollo — sobran de sobra para este proyecto. Si en algún
momento querés más calidad, cambiá `ChatGroq(model="llama-3.1-8b-instant")`
por otro modelo (ej. `llama-3.3-70b-versatile`) o por OpenAI/Anthropic, sin
tocar el resto del pipeline.

## Alcance no cubierto

Detallado en `docs/arquitectura.md` — brevemente: la tool MCP todavía no
está conectada como nodo del agente, no hay autoscaling automático en K8s,
y la heurística de alucinación es un proxy simple, no un evaluador LLM.
