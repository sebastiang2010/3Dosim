"""
PipelineOrchestrator - Orchestrador del pipeline 3Dosim para 3D Slicer.

Estructura modular que luego se promocionara a SlicerDosimLib/orchestrator/:

  checkpoint.py          - CheckpointManager: estado persistente entre ejecuciones
  anonymize.py           - Anonimizacion DICOM (pydicom)
  couch_remover.py       - Eliminacion de camilla y aire del CT
  segmentation.py        - TotalSegmentator (TotalSegmentatorLogic.process())
  validation.py          - Dialogo de validacion medica obligatoria
  tumor_segmentation.py  - Preparacion ROI hepatica + MONAI Label (tumor)
  tumor_validation.py    - Dialogo de validacion medica del tumor
  git_commit.py          - Prompt de commit git al finalizar
  pipeline.py            - PipelineTestOrchestrator: orquesta todos los pasos
  comandos.py            - Consola interactiva de comandos (lenguaje natural)
  main.py                - Entry point con argparse
  ai_supervisor.py       - Revision IA paso a paso (DeepSeek/OpenRouter)
   deepseek_client.py     - Cliente OpenRouter multi-modelo
   monailabel_server.py   - Wrapper para iniciar servidor MONAI Label

Todos los imports internos son ABSOLUTOS (from PipelineOrchestrator.xxx)
para compatibilidad con 3D Slicer --python-script.
"""
