"""
Entry point: lanza PanelIA como aplicacion independiente.
Uso:
    python -m SlicerDosimLib.orchestrator --agente /ruta/agente.json --mcp-url http://localhost:2026
"""

import sys
import os

# Asegurar que SlicerDosimLib esta en el path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from orchestrator.panel_ia import main

if __name__ == "__main__":
    main()
