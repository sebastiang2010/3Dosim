"""Orquestador de agente IA para 3Dosim + 3D Slicer via MCP.

Componentes:
    AgenteState   - Gestiona agente.json (estados, ordenes, historial)
    MCPClient     - Cliente HTTP para slicer-mcp-server.py (Model Context Protocol)
    PanelIA       - GUI tkinter que conecta agente.json + MCP + Slicer
"""

from .agente import AgenteState
from .mcp_client import MCPClient
from .panel_ia import PanelIA

__all__ = ["AgenteState", "MCPClient", "PanelIA"]
