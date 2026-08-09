"""
adaptadores_mcp/servidor_mcp.py

Adaptador MCP (Model Context Protocol) mínimo: expone una herramienta
externa ("consultar_cotizacion") de forma estandarizada, para que
cualquier cliente compatible con MCP (incluido un agente propio) pueda
invocarla con validación de inputs.

Este es un scaffold de ejemplo: la "cotización" es un dato simulado/mock.
En una versión real, acá adentro llamarías a una API de mercado real
(ej. BYMADATA) con las credenciales correspondientes.

Para correr el servidor standalone (modo desarrollo/test):
    python adaptadores_mcp/servidor_mcp.py

Requiere el paquete `mcp` (pip install mcp).
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("mercado-ar-tools")

_COTIZACIONES_MOCK = {
    "GGAL": 3250.50,
    "YPFD": 41200.00,
    "PAMP": 2870.25,
    "MERV": 1_950_300.10,  
}


@mcp.tool()
def consultar_cotizacion(ticker: str) -> dict:
    """Consulta la cotización simulada de un ticker del mercado argentino.

    Args:
        ticker: símbolo de la acción o índice (ej. "GGAL", "YPFD", "MERV").

    Returns:
        dict con el ticker, precio y una advertencia de que es un dato mock.
    """
    ticker_normalizado = ticker.strip().upper()

    if not ticker_normalizado.isalnum() or len(ticker_normalizado) > 6:
        return {"error": "Ticker inválido. Usá solo letras/números, hasta 6 caracteres."}

    precio = _COTIZACIONES_MOCK.get(ticker_normalizado)
    if precio is None:
        return {
            "error": f"No tengo datos para '{ticker_normalizado}'. "
            f"Tickers disponibles (mock): {list(_COTIZACIONES_MOCK.keys())}"
        }

    return {
        "ticker": ticker_normalizado,
        "precio": precio,
        "moneda": "ARS",
        "fuente": "MOCK — reemplazar por API real de mercado en producción",
    }


if __name__ == "__main__":
    mcp.run()
