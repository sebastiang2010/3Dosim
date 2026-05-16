"""
Orchestrator de test del pipeline 3Dosim para 3D Slicer.

⚠ Archivo legacy - la implementacion real esta en Testing/PipelineOrchestrator/

Uso:
  Slicer.exe --python-script test_pipeline_orchestrator.py --data-dir "C:/ruta/datos"
  Slicer.exe --python-script test_pipeline_orchestrator.py --data-dir "C:/ruta/datos" --reset
"""

import argparse
import os
import sys


def _add_package_path():
    """
    Agrega Testing/ (el padre de PipelineOrchestrator) al sys.path.
    Esto permite usar: from PipelineOrchestrator.pipeline import ...
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))  # Testing/Python/
    testing_dir = os.path.normpath(os.path.join(script_dir, ".."))  # Testing/
    if testing_dir not in sys.path:
        sys.path.insert(0, testing_dir)
    return testing_dir


if __name__ == "__main__":
    _add_package_path()

    # Importar y ejecutar el entry point modular
    from PipelineOrchestrator.main import main
    main()
