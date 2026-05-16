"""
Utilidades compartidas del PipelineOrchestrator.
Logger, paths, helpers sin dependencias de Slicer.
"""

import logging
import os
import sys


def setup_logger(name: str = "3DosimTest") -> logging.Logger:
    """Configura y retorna el logger global."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s", datefmt="%H:%M:%S"
    ))
    logger.addHandler(handler)
    return logger


logger = setup_logger()


def add_module_path(script_path: str = None) -> bool:
    """
    Agrega el directorio Scripted/ a sys.path para importar SlicerDosimLib.

    Busca desde el directorio del script hacia arriba hasta encontrar
    la estructura Modules/Scripted/SlicerDosim/SlicerDosimLib/

    Returns: True si se pudo agregar el path
    """
    if script_path is None:
        script_path = os.path.abspath(__file__)

    # Buscar la raiz de SlicerDosim (donde esta Modules/)
    current = os.path.dirname(script_path)  # Testing/PipelineOrchestrator/
    for _ in range(6):  # Subir hasta 6 niveles
        candidate = os.path.join(current, "Modules", "Scripted")
        if os.path.isdir(candidate) and candidate not in sys.path:
            sys.path.insert(0, candidate)
            logger.info(f"  Path agregado: {candidate}")
            return True
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    # Fallback: buscar script_path desde el test original
    # .../Testing/Python/test_pipeline_orchestrator.py
    # ../.. = SlicerDosim/ ; +Modules/Scripted = target
    alt = os.path.normpath(os.path.join(
        os.path.dirname(script_path), "..", "..", "Modules", "Scripted"
    ))
    if os.path.isdir(alt) and alt not in sys.path:
        sys.path.insert(0, alt)
        logger.info(f"  Path agregado (fallback): {alt}")
        return True

    logger.warning("  ⚠ No se pudo agregar path de SlicerDosimLib")
    return False


def show_progress(message: str):
    """
    Muestra mensaje en la status bar de Slicer (si estamos dentro).
    """
    try:
        import slicer
        slicer.util.showStatusMessage(message, 5000)
        slicer.app.processEvents()
    except ImportError:
        pass  # Fuera de Slicer, silencioso
