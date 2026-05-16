"""
Anonimizacion de imagenes DICOM.

Copia los archivos DICOM a un directorio temporal, limpia los tags
del paciente con pydicom, y renombra los nodos en 3D Slicer.
"""

import logging
import os
import shutil

logger = logging.getLogger("3DosimTest")

# Tags DICOM que se limpian durante la anonimizacion
TAGS_TO_CLEAR = [
    "PatientName", "PatientID", "PatientBirthDate",
    "PatientAge", "PatientWeight", "PatientSize",
    "PatientAddress", "PatientTelephoneNumbers",
    "ReferringPhysicianName", "PhysiciansOfRecord",
    "OperatorsName", "InstitutionName",
    "InstitutionAddress", "StationName",
    "DeviceSerialNumber", "AccessionNumber",
    "StudyID", "OtherPatientIDs",
]

# Import absoluto de utils
from PipelineOrchestrator.utils import show_progress


def anonymize_dicom_nodes(ct_node, pet_node=None):
    """
    Anonimiza los nodos CT y PET ya cargados en Slicer.
    Les cambia el nombre a '3Dosim_CT_anon' / '3Dosim_PET_anon'.
    """
    import slicer

    logger.info("  Anonimizando nodos en Slicer...")

    for node, label in [(ct_node, "CT"), (pet_node, "PET")]:
        if node is None:
            continue
        old_name = node.GetName()
        node.SetName(f"3Dosim_{label}_anon")
        logger.info(f"  {label}: '{old_name}' -> '{node.GetName()}'")

    logger.info("  Nodos renombrados")


def anonymize_dicom_files_pydicom(ct_dir: str, pet_dir: str, anon_dir: str) -> bool:
    """
    Copia archivos DICOM a directorio temporal y limpia tags con pydicom.
    """
    try:
        import pydicom
    except ImportError:
        logger.warning("  pydicom no disponible, usando anonimizacion basica")
        return False

    if os.path.exists(anon_dir):
        shutil.rmtree(anon_dir)

    for src_dir, label in [(ct_dir, "CT"), (pet_dir, "PET")]:
        if not os.path.isdir(src_dir):
            logger.warning(f"  Directorio {label} no encontrado, saltando")
            continue

        dst_dir = os.path.join(anon_dir, label)
        os.makedirs(dst_dir, exist_ok=True)

        dcm_files = [
            f for f in os.listdir(src_dir)
            if f.endswith('.dcm') or f.isdigit() or not os.path.splitext(f)[1]
        ]
        logger.info(f"  Anonimizando {len(dcm_files)} archivos {label}...")

        for i, fname in enumerate(dcm_files):
            src_path = os.path.join(src_dir, fname)
            if not os.path.isfile(src_path):
                continue
            dst_path = os.path.join(dst_dir, fname)

            try:
                shutil.copy2(src_path, dst_path)
                ds = pydicom.dcmread(dst_path, force=True)
                for tag in TAGS_TO_CLEAR:
                    if tag in ds:
                        ds[tag].value = ""
                if "SeriesInstanceUID" in ds:
                    ds.SeriesInstanceUID = pydicom.uid.generate_uid()
                ds.save_as(dst_path)
            except Exception as e:
                logger.warning(f"  Error anonimizando {fname}: {e}")
                continue

            if (i + 1) % 20 == 0:
                logger.info(f"    {i+1}/{len(dcm_files)}")

    logger.info(f"  Archivos anonimizados en: {anon_dir}")
    return True


def anonymize(ct_node, ct_dir: str, pet_dir: str, anon_dir: str, pet_node=None):
    """
    Pipeline completo de anonimizacion.
    """
    show_progress("Anonimizando imagenes...")

    anonymize_dicom_nodes(ct_node, pet_node)

    ok = anonymize_dicom_files_pydicom(ct_dir, pet_dir, anon_dir)
    if not ok:
        logger.info("  Anonimizacion basica de nodos aplicada")
        logger.info("  Para anonimizacion completa: instalar pydicom en Slicer")

    logger.info("  Anonimizacion completada")
