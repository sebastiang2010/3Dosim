"""
PipelineOrchestrator - Orchestrador del pipeline 3Dosim para 3D Slicer.

Estructura modular que luego se promocionara a SlicerDosimLib/orchestrator/:

  checkpoint.py     - CheckpointManager: estado persistente entre ejecuciones
  anonymize.py      - Anonimizacion DICOM (pydicom)
  couch_remover.py  - Eliminacion de camilla y aire del CT
  segmentation.py   - TotalSegmentator + barra de progreso + phantom sintetico
  validation.py     - Dialogo de validacion medica obligatoria
  mcnp_builder.py   - Generacion y verificacion de entrada MCNP
  git_commit.py     - Prompt de commit git al finalizar
  pipeline.py       - PipelineTestOrchestrator: orquesta todos los pasos
  main.py           - Entry point con argparse
"""

from .checkpoint import CheckpointManager
from .pipeline import PipelineTestOrchestrator
