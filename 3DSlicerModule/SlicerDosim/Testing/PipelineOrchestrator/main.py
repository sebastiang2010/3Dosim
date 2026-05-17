"""
Entry point del PipelineOrchestrator 3Dosim para 3D Slicer.

Uso desde terminal:
  Slicer.exe --python-script main.py --data-dir "C:/ruta/datos"
  Slicer.exe --python-script main.py --data-dir "C:/ruta/datos" --reset
"""

import argparse
import os
import sys


def _add_parent_to_path():
    """Agrega Testing/ al sys.path para encontrar PipelineOrchestrator como paquete."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(script_dir)  # Testing/
    if parent not in sys.path:
        sys.path.insert(0, parent)
    return parent


def main():
    _add_parent_to_path()

    parser = argparse.ArgumentParser(
        description="Pipeline orchestrator para SlicerDosim"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=r"C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2",
        help="Directorio con subdirectorios CT/ y PET/",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reiniciar checkpoints (ignora estado guardado)",
    )
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=0,
        help="Puerto para el servidor MCP (default: 0 = deshabilitado)",
    )
    parser.add_argument(
        "--no-consola",
        action="store_true",
        help="Deshabilita la consola interactiva de comandos",
    )
    args, _ = parser.parse_known_args()

    from PipelineOrchestrator.pipeline import PipelineTestOrchestrator

    orchestrator = PipelineTestOrchestrator(
        args.data_dir,
        reset=args.reset,
        mcp_port=args.mcp_port,
        no_consola=args.no_consola,
    )
    orchestrator.run()


if __name__ == "__main__":
    main()
