# Adaptadores MCP

Este módulo expone herramientas externas siguiendo el protocolo MCP
(Model Context Protocol), que estandariza cómo un modelo/agente puede
invocar herramientas de forma segura (con validación de inputs y schema
tipado), en vez de que el LLM ejecute código arbitrario.

## Herramienta incluida

- `consultar_cotizacion(ticker)`: devuelve el precio simulado de un ticker del mercado argentino. Es un **mock** — en producción reemplazarías la función interna por una llamada real a una API de mercado (ej. BYMADATA), manejando ahí las credenciales y rate limits.

## Cómo probarlo

```bash
pip install mcp
python adaptadores_mcp/servidor_mcp.py
```

Esto levanta el servidor MCP por stdio, listo para que un cliente
compatible (Claude Desktop, otro agente, etc.) se conecte.

### Conectarlo a Claude Desktop (opcional, para probarlo interactivamente)

Agregá esto a tu configuración de Claude Desktop
(`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "mercado-ar-tools": {
      "command": "python",
      "args": ["/ruta/completa/a/adaptadores_mcp/servidor_mcp.py"]
    }
  }
}
```

## Por qué es "seguro"

- Valida el formato del ticker antes de usarlo (evita inyección o inputs maliciosos).
- Define explícitamente qué puede hacer la herramienta (un solo propósito, sin acceso a filesystem, red arbitraria, etc.).
- Devuelve errores controlados en vez de excepciones crudas.

## Próximo paso (fuera del MVP)

Integrar esta tool dentro del agente de `agente/agente.py` como un nodo
más del grafo, para que el LLM pueda decidir cuándo consultar una
cotización en tiempo real en vez de solo buscar en documentos.
