"""
Entry point del PipelineOrchestrator 3Dosim para 3D Slicer.

Uso desde terminal:
  Slicer.exe --python-script main.py --data-dir "C:/ruta/datos"

Para reiniciar checkpoints:
  Slicer.exe --python-script main.py --data-dir "C:/ruta/datos" --reset

O desde la consola Python de Slicer:
  exec(open("main.py").read())
"""

import argparse
import sys
import os

from .pipeline import PipelineTestOrchestrator


def main():
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
    # Slicer puede pasar argumentos extra, los ignoramos
    args, _ = parser.parse_known_args()

    orchestrator = PipelineTestOrchestrator(args.data_dir, reset=args.reset)
    orchestrator.run()


if __name__ == "__main__":
    main()
