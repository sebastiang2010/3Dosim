"""
Segmentacion con TotalSegmentator (via TotalSegmentatorLogic.process()) o simple.

Modos:
  - "totalsegmentator": ejecuta TotalSegmentator a traves de la API interna de Slicer:
      slicer.modules.totalsegmentator.logic().process(inputVolume, outputSegmentation, ...)
      El modulo maneja internamente la exportacion/importacion de archivos temporales.
  - "simple": threshold HU > -200 + cierre morfologico + componente conectada.
"""

import logging
import time

logger = logging.getLogger("3DosimTest")


def check_totalsegmentator() -> bool:
    """Verifica si TotalSegmentator esta instalado como modulo de Slicer."""
    import slicer
    try:
        has_module = hasattr(slicer.modules, 'totalsegmentator')
        if has_module:
            logger.info("  TotalSegmentator (modulo de Slicer) detectado")
        else:
            logger.info("  TotalSegmentator NO disponible como modulo de Slicer")
            logger.info("  -> Instalar: Extension Manager -> TotalSegmentator")
        return has_module
    except Exception:
        logger.info("  TotalSegmentator NO disponible")
        return False


def load_ts_config(config_path=None) -> dict:
    """
    Carga la configuracion de TotalSegmentator desde un archivo JSONC.

    Args:
        config_path: Ruta al .jsonc. Si es None, busca en el directorio del script.

    Returns:
        dict con parametros: task, fast, force_cpu, subset, interactive, ...
    """
    import json
    import os
    import re

    if config_path is None:
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "totalsegmentator_config.jsonc"
        )

    defaults = {
        "task": "total",
        "fast": True,
        "force_cpu": True,
        "subset": None,
        "interactive": False,
        "use_standard_segment_names": True,
    }

    if not os.path.exists(config_path):
        logger.info(f"  Config JSONC no encontrado: {config_path}")
        logger.info(f"  Usando valores por defecto: {defaults}")
        return defaults

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Eliminar comentarios // y /* */ del JSONC
        content = re.sub(r'//.*', '', content)
        content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
        config = json.loads(content)
        defaults.update(config)
        logger.info(f"  Config cargada desde: {config_path}")
        for k, v in defaults.items():
            logger.info(f"    {k}: {v}")
    except Exception as e:
        logger.warning(f"  Error cargando config JSONC: {e}")
        logger.info(f"  Usando valores por defecto: {defaults}")

    return defaults


def run_segmentation_totalsegmentator(ct_node_name: str, output_dir: str, force_cpu: bool = True):
    """
    Ejecuta TotalSegmentator via TotalSegmentatorLogic.process() (API interna de Slicer).
    Busca el volumen por su NOMBRE en la escena de Slicer.
    Carga la config desde totalsegmentator_config.jsonc.

    Referencia: TotalSegmentator.py → TotalSegmentatorLogic.process()
    (NO usar slicer.cli.run() - TS no es CLI module, no tiene CreateNodeInScene)

    Args:
        ct_node_name: Nombre del volumen CT en la escena de Slicer (ej: "3Dosim_CT_anon")
        output_dir: Directorio de salida (para buscar config)
        force_cpu: True fuerza CPU, False permite GPU si disponible
    """
    import slicer

    logger.info("")
    logger.info("  ========================================================")
    logger.info("  TotalSegmentator via TotalSegmentatorLogic.process()")
    logger.info("  ========================================================")
    logger.info("")

    t_start = time.time()

    # Cargar config desde JSONC
    config = load_ts_config()
    task = config.get("task", "total")
    fast = config.get("fast", True)
    cpu = config.get("force_cpu", force_cpu)
    subset = config.get("subset", None)
    interactive = config.get("interactive", False)

    # Buscar el volumen CT por su nombre en la escena de Slicer
    ct_node = slicer.util.getNode(ct_node_name)
    if ct_node is None:
        raise RuntimeError(f"No se encontro volumen '{ct_node_name}' en la escena")
    logger.info(f"  Volumen CT encontrado: '{ct_node.GetName()}'")

    # Cambiar al modulo TotalSegmentator para que el usuario vea el progreso
    try:
        slicer.util.selectModule("TotalSegmentator")
        slicer.app.processEvents()
        logger.info("  Cambiado al modulo TotalSegmentator")
    except Exception:
        pass  # No critico

    # Crear nodo de segmentacion de salida
    seg_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    seg_node.SetName("TotalSegmentator_Seg")
    seg_node.CreateDefaultDisplayNodes()

    try:
        # Instanciar TotalSegmentatorLogic directamente (NO slicer.modules.totalsegmentator.logic()
        # que devuelve ScriptedLoadableModuleLogic generico sin process())
        from TotalSegmentator import TotalSegmentatorLogic

        logic = TotalSegmentatorLogic()
        logic.logCallback = lambda msg: logger.info(f"  [TS] {msg}")
        logic.clearOutputFolder = True
        logic.useStandardSegmentNames = config.get("use_standard_segment_names", True)

        device_str = "CPU" if cpu else "auto (GPU si disponible)"
        logger.info(f"  Device: {device_str}")
        logger.info(f"  Task: {task} (fast={fast})")
        if subset:
            logger.info(f"  Subset: {subset}")

        # Paso 1: asegurar que los paquetes Python de TS esten instalados
        logger.info("  Verificando/instalando dependencias Python de TotalSegmentator...")
        logic.setupPythonRequirements()
        logger.info("  Dependencias OK")

        # Paso 2: ejecutar segmentacion
        logger.info("  Ejecutando TotalSegmentator (Slicer no responde hasta terminar)...")
        logic.process(
            inputVolume=ct_node,
            outputSegmentation=seg_node,
            fast=fast,
            cpu=cpu,
            task=task,
            subset=subset,
            interactive=interactive,
        )
        logger.info("  TotalSegmentator completado")

    except Exception as e:
        logger.error(f"  TotalSegmentator FALLO: {e}")
        raise RuntimeError(f"TotalSegmentator fallo: {e}")

    elapsed = int(time.time() - t_start)
    logger.info(f"  TotalSegmentator completado en {elapsed}s")
    logger.info(f"  Nodo: {seg_node.GetName()}")

    return seg_node


def run_segmentation_simple(ct_node, output_dir: str):
    """
    Segmentacion rapida por threshold + morfologia (sin TotalSegmentator).

    Flujo:
      1. Threshold: voxels > -200 HU (cuerpo, sin aire)
      2. Cierre morfologico para rellenar huecos
      3. Componente conectada mas grande
      4. Crear segmentacion en Slicer via ImportLabelmapToSegmentationNode
    """
    import slicer
    import numpy as np
    from scipy import ndimage as ndi

    logger.info("")
    logger.info("  ========================================================")
    logger.info("  Segmentacion SIMPLE (threshold + morfologia)")
    logger.info("  ========================================================")
    logger.info("")

    t_start = time.time()

    # ---- 1. Obtener array del CT ----
    logger.info("  Leyendo volumen CT...")
    ct_array = slicer.util.arrayFromVolume(ct_node)  # (K, J, I)
    logger.info(f"  Dimensiones CT: {ct_array.shape}")

    # ---- 2. Threshold: cuerpo = HU > -200 ----
    logger.info("  Threshold: HU > -200...")
    body_mask = ct_array > -200

    # ---- 3. Cierre morfologico 3D ----
    logger.info("  Cierre morfologico 3D...")
    struct = ndi.generate_binary_structure(3, 2)
    body_mask = ndi.binary_closing(body_mask, structure=struct, iterations=3)

    # ---- 4. Componente conectada mas grande ----
    logger.info("  Extrayendo componente mas grande...")
    labeled, num_features = ndi.label(body_mask, structure=struct)
    if num_features == 0:
        raise RuntimeError("No se encontro ninguna componente conectada")

    sizes = ndi.sum(body_mask, labeled, range(1, num_features + 1))
    largest = np.argmax(sizes) + 1
    body_mask = (labeled == largest)

    pct = 100 * np.sum(body_mask) / body_mask.size
    logger.info(f"  Voxeles cuerpo: {np.sum(body_mask)} / {body_mask.size} ({pct:.1f}%)")
    logger.info(f"  Mascara generada en {time.time() - t_start:.2f}s")

    # ---- 5. Crear segmentation node ----
    logger.info("  Creando segmentation node en Slicer...")

    # 5a. Crear label map volume desde la mascara
    label_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLLabelMapVolumeNode")
    label_node.SetName("_body_mask_tmp")

    # Copiar geometria del CT
    import vtk
    mat = vtk.vtkMatrix4x4()
    ct_node.GetIJKToRASMatrix(mat)
    label_node.SetIJKToRASMatrix(mat)
    label_node.SetSpacing(ct_node.GetSpacing())
    label_node.SetOrigin(ct_node.GetOrigin())

    # Convertir numpy a vtkImageData
    import vtk.util.numpy_support as np_support
    label_array = body_mask.astype(np.uint8)  # 0/1
    # vtkImageData espera IJK, numpy da KJI -> reordenar
    label_array_ijk = np.transpose(label_array, (2, 1, 0))  # (I, J, K)
    flat = label_array_ijk.ravel(order='C')
    vtk_arr = np_support.numpy_to_vtk(flat, deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)

    vtk_img = vtk.vtkImageData()
    dims = ct_node.GetImageData().GetDimensions()
    vtk_img.SetDimensions(dims)
    vtk_img.SetSpacing(ct_node.GetSpacing())
    vtk_img.SetOrigin(ct_node.GetOrigin())
    vtk_img.GetPointData().SetScalars(vtk_arr)
    label_node.SetAndObserveImageData(vtk_img)

    logger.info("  Label map creado")

    # 5b. Importar label map a segmentation
    seg_node = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode")
    seg_node.SetName("Cuerpo_SimpleSeg")

    try:
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
            label_node, seg_node
        )
        logger.info("  ImportLabelmapToSegmentationNode OK")
    except Exception as e:
        logger.warning(f"  Fallo import: {e}")
        seg_node.CreateDefaultDisplayNodes()
        # Intentar crear segmento vacio
        seg_node.GetSegmentation().AddEmptySegment(
            "Body", "Cuerpo completo", [0.8, 0.6, 0.2]
        )

    # Limpiar
    slicer.mrmlScene.RemoveNode(label_node)

    seg_node.CreateDefaultDisplayNodes()

    # Renombrar segmento si existe
    seg = seg_node.GetSegmentation().GetSegment("Body")
    if seg:
        seg.SetColor(0.8, 0.6, 0.2)

    elapsed = int(time.time() - t_start)
    logger.info(f"  Segmentacion completada en {elapsed}s")
    logger.info(f"  Nodo: {seg_node.GetName()}")

    return seg_node


def run_segmentation(ct_node, output_dir: str, mode: str = "simple",
                     force_cpu: bool = True):
    """
    Punto de entrada unificado.

    Args:
        ct_node: vtkMRMLScalarVolumeNode del CT (o nombre del nodo en TS mode)
        output_dir: Directorio de salida
        mode: "simple" | "totalsegmentator"
        force_cpu: True fuerza CPU en TotalSegmentator

    Returns:
        segmentation_node: vtkMRMLSegmentationNode
    """
    if mode == "totalsegmentator":
        if not check_totalsegmentator():
            logger.warning("  TotalSegmentator no instalado, fallback a simple")
            mode = "simple"
        else:
            # Para TS mode, ct_node debe ser el NOMBRE del nodo en la escena
            ct_name = ct_node if isinstance(ct_node, str) else ct_node.GetName()
            return run_segmentation_totalsegmentator(
                ct_name, output_dir, force_cpu=force_cpu
            )

    # simple por defecto
    return run_segmentation_simple(ct_node, output_dir)


# Mantener compatibilidad
def get_ijk_to_ras_numpy(volume_node):
    import numpy as np
    import vtk
    mat = vtk.vtkMatrix4x4()
    volume_node.GetIJKToRASMatrix(mat)
    m = np.eye(4)
    for i in range(4):
        for j in range(4):
            m[i, j] = mat.GetElement(i, j)
    return m
