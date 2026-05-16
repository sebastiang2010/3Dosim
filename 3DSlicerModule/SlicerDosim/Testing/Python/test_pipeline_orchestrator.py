"""
Orchestrator de test del pipeline 3Dosim para 3D Slicer.

⚠ Archivo legacy - ahora delegado a Testing/PipelineOrchestrator/

La implementacion real esta en:
  Testing/PipelineOrchestrator/
    main.py           - Entry point con argparse
    pipeline.py       - PipelineTestOrchestrator (orquestador)
    checkpoint.py     - CheckpointManager
    anonymize.py      - Anonimizacion DICOM
    couch_remover.py  - Eliminacion de camilla y aire
    segmentation.py   - TotalSegmentator + progreso
    validation.py     - Validacion medica
    mcnp_builder.py   - Generacion MCNP
    git_commit.py     - Commit git prompt

Uso:
  Slicer.exe --python-script test_pipeline_orchestrator.py --data-dir "C:/ruta/datos"
  Slicer.exe --python-script test_pipeline_orchestrator.py --data-dir "C:/ruta/datos" --reset
"""

import argparse
import os
import sys


def _add_package_path():
    """Agrega Testing/PipelineOrchestrator al sys.path."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    pkg_dir = os.path.join(script_dir, "..", "PipelineOrchestrator")
    pkg_dir = os.path.normpath(pkg_dir)
    if os.path.isdir(pkg_dir) and pkg_dir not in sys.path:
        sys.path.insert(0, pkg_dir)
        return True
    return False


if __name__ == "__main__":
    _add_package_path()

    # Importar y ejecutar el entry point modular
    from PipelineOrchestrator.main import main
    main()
