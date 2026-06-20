"""
pipeline_mcnp.py — Pipeline ULTRA-LIVIANO que carga escena .mrb y genera MCNP.

Flujo:
  1. Carga escena .mrb (con barra de progreso)
  2. Escanea nodos (CT, PET, Segmentacion)
  3. Genera input MCNP
  4. Reporta resultado

NO hereda de PipelineTestOrchestrator para evitar conflictos de checkpoint.
Usa MCNPInputGenerator directamente.
"""

import argparse
import logging
import os
import sys
import time

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("MCNP")

# ──────────────────────────────────────────────────────────
# Progress helper (barra simple para consola)
# ──────────────────────────────────────────────────────────

class ProgressBar:
    """Barra de progreso simple estilo Slicer."""
    def __init__(self, label="Procesando"):
        self.label = label
        self.start = time.time()

    def update(self, step, total, msg=""):
        pct = int(step / total * 100) if total else 0
        bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
        elapsed = time.time() - self.start
        print(f"\r  {self.label}: |{bar}| {pct}%  {msg}  [{elapsed:.0f}s]", end="")
        if pct >= 100:
            print()

    def done(self, msg="Completado"):
        self.update(100, 100, msg)


# ──────────────────────────────────────────────────────────
# Main pipeline
# ──────────────────────────────────────────────────────────

def setup_paths():
    """Agrega SlicerDosimLib al sys.path para importar MCNPInputGenerator."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    # Subir hasta SlicerDosimLib: Testing/PipelineOrchestrator/ -> Testing/ -> SlicerDosim/ -> Modules/Scripted/SlicerDosim/
    # Ruta real: .../Modules/Scripted/SlicerDosim/SlicerDosimLib/
    paths_to_try = [
        # Desde PipelineOrchestrator -> Testing -> SlicerDosim -> Modules/Scripted/SlicerDosim -> SlicerDosimLib
        os.path.abspath(os.path.join(script_dir, "..", "..", "Modules", "Scripted", "SlicerDosim")),
        # Version directa
        os.path.abspath(os.path.join(script_dir, "..", "..", "..", "Modules", "Scripted", "SlicerDosim", "SlicerDosimLib")),
        # Fallback: SlicerDosim/SlicerDosimLib/
        os.path.abspath(os.path.join(script_dir, "..", "..", "..", "..", "SlicerDosim", "SlicerDosimLib")),
    ]
    for p in paths_to_try:
        if p not in sys.path:
            sys.path.insert(0, p)


def load_scene(scene_path):
    """Carga escena .mrb con barra de progreso."""
    import slicer

    if not os.path.exists(scene_path):
        raise FileNotFoundError(f"Escena no encontrada: {scene_path}")

    size_mb = os.path.getsize(scene_path) / (1024 * 1024)
    logger.info(f"  Escena: {scene_path}")
    logger.info(f"  Tamano: {size_mb:.0f} MB")

    pb = ProgressBar("Cargando escena")
    pb.update(10, 100, "Iniciando...")

    # Para simular progreso, medimos tiempo (carga real no tiene callback)
    try:
        # Mostrar progreso mientras carga
        slicer.app.processEvents()
        pb.update(30, 100, "Leyendo archivo MRB...")
        slicer.app.processEvents()

        success = slicer.util.loadScene(scene_path)

        pb.update(80, 100, "Procesando nodos...")
        slicer.app.processEvents()

        if not success:
            raise RuntimeError("slicer.util.loadScene() devolvio False")
        pb.done("Escena cargada OK")
    except Exception as e:
        pb.done(f"ERROR: {e}")
        raise

    return True


def scan_scene():
    """Busca nodos CT, PET y Segmentacion en la escena cargada.
    
    Returns:
        dict con keys: ct, pet (opcional), seg, ct_masked (opcional)
    """
    import slicer
    import vtk

    vol_nodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
    seg_nodes_list = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
    lb_nodes = slicer.util.getNodesByClass("vtkMRMLLabelMapVolumeNode")

    logger.info(f"  Volumenes: {len(vol_nodes)}, Segmentaciones: {len(seg_nodes_list)}, LabelMaps: {len(lb_nodes)}")

    result = {}

    # ── CT ──
    ct_candidates = [n for n in vol_nodes if "CT" in n.GetName() or "ct" in n.GetName().lower()]
    if ct_candidates:
        preferred = [n for n in ct_candidates if "anon" in n.GetName().lower() or "sin_camilla" in n.GetName().lower()]
        result["ct"] = preferred[0] if preferred else ct_candidates[0]
        logger.info(f"  CT: '{result['ct'].GetName()}'")
    elif vol_nodes:
        result["ct"] = vol_nodes[0]
        logger.info(f"  CT (fallback): '{result['ct'].GetName()}'")
    else:
        raise RuntimeError("No se encontraron volumenes CT en la escena")

    # ── CT_masked (opcional) ──
    masked = [n for n in vol_nodes if "sin_camilla" in n.GetName().lower() or "masked" in n.GetName().lower()]
    if masked:
        result["ct_masked"] = masked[0]
        logger.info(f"  CT_masked: '{result['ct_masked'].GetName()}'")

    # ── PET (opcional) ──
    pet_candidates = [n for n in vol_nodes if "PET" in n.GetName() or "pet" in n.GetName().lower()]
    if pet_candidates:
        result["pet"] = pet_candidates[0]
        logger.info(f"  PET: '{result['pet'].GetName()}'")
    else:
        result["pet"] = None
        logger.info("  PET: No encontrado (fuente uniforme)")

    # ── Segmentacion ──
    seg_found = None
    if seg_nodes_list:
        ts_candidates = [n for n in seg_nodes_list if "TotalSegmentator" in n.GetName() or "Segmentation" in n.GetName()]
        seg_found = ts_candidates[0] if ts_candidates else seg_nodes_list[0]
        logger.info(f"  Segmentacion: '{seg_found.GetName()}'")
        # Contar segmentos
        seg_ids = vtk.vtkStringArray()
        seg_found.GetSegmentation().GetSegmentIDs(seg_ids)
        logger.info(f"    Segmentos: {seg_ids.GetNumberOfValues()}")
    elif lb_nodes:
        seg_found = lb_nodes[0]
        logger.info(f"  Segmentacion (labelmap): '{seg_found.GetName()}'")
    else:
        raise RuntimeError("No se encontraron nodos de segmentacion en la escena")

    result["seg"] = seg_found
    return result


def generate_mcnp(nodes, output_dir, isotope="Y-90", n_particles=int(1e7),
                  flip_rows=True, flip_z=False, refine_hu=False,
                  n_liver_tallies=5, n_tumor_tallies=10):
    """Genera archivo de entrada MCNP usando MCNPInputGenerator."""
    from SlicerDosimLib import MCNPInputGenerator

    generator = MCNPInputGenerator()

    logger.info(f"\n  Isotopo:       {isotope}")
    logger.info(f"  Particulas:    {n_particles:.0e}")
    logger.info(f"  Flip rows:     {flip_rows}")
    logger.info(f"  Output dir:    {output_dir}")

    os.makedirs(output_dir, exist_ok=True)

    pb = ProgressBar("Generando MCNP")
    pb.update(5, 100, "Iniciando...")

    input_path = generator.generate(
        ct_volume_node=nodes["ct"],
        pet_volume_node=nodes.get("pet"),
        segmentation_node=nodes["seg"],
        output_dir=output_dir,
        isotope=isotope,
        n_particles=n_particles,
        refine_hu=refine_hu,
        flip_rows=flip_rows,
        flip_z=flip_z,
        n_liver_tallies=n_liver_tallies,
        n_tumor_tallies=n_tumor_tallies,
    )

    pb.done("Archivo MCNP generado")

    file_size_kb = os.path.getsize(input_path) / 1024
    logger.info(f"\n  {'='*50}")
    logger.info(f"  ARCHIVO MCNP: {input_path}")
    logger.info(f"  Tamano: {file_size_kb:.1f} KB")
    logger.info(f"  {'='*50}\n")

    return input_path


def main():
    parser = argparse.ArgumentParser(description="Pipeline MCNP desde escena .mrb")
    parser.add_argument("--scene", default=None, help="Ruta al archivo .mrb")
    parser.add_argument("--output", default=None, help="Directorio de salida")
    parser.add_argument("--isotope", default="Y-90", help="Isotopo (Y-90, I-131, Lu-177, Tc-99m)")
    parser.add_argument("--n-particles", type=float, default=1e7, help="Numero de historias")
    parser.add_argument("--flip", action="store_true", default=True, help="Flip Y (default: True)")
    parser.add_argument("--no-flip", action="store_false", dest="flip", help="No flip Y")
    parser.add_argument("--flip-z", action="store_true", help="Flip Z")
    args, _ = parser.parse_known_args()

    setup_paths()

    # ── Scene path ──
    scene_path = args.scene
    if not scene_path:
        # Auto-buscar en escenas guardadas
        candidates = [
            "C:/MAT/3Dosim/ai-pipe/scenes/3Dosim_scene.mrb",
            "C:/MAT/3Dosim/pacientes-/pacientes/resultados_test/scenes/3Dosim_scene.mrb",
        ]
        for c in candidates:
            if os.path.exists(c):
                scene_path = c
                break
    if not scene_path or not os.path.exists(scene_path):
        logger.error("No se encontro escena .mrb. Use --scene <path>")
        sys.exit(1)

    # ── Output dir ──
    output_dir = args.output
    if not output_dir:
        output_dir = os.path.dirname(os.path.dirname(scene_path))  # scenes/ -> ai-pipe/
    mcnp_dir = os.path.join(output_dir, "mcnp_input")

    logger.info("=" * 55)
    logger.info(" PIPELINE MCNP DESDE ESCENA")
    logger.info("=" * 55)
    logger.info(f"  Scene:     {scene_path}")
    logger.info(f"  Output:    {mcnp_dir}")
    logger.info(f"  Isotopo:   {args.isotope}")
    logger.info(f"  Particulas: {int(args.n_particles):.0e}")
    logger.info(f"  Flip Y:    {args.flip}")
    logger.info(f"  Flip Z:    {args.flip_z}")
    logger.info("")

    # ── 1. Cargar escena ──
    print("")
    logger.info("[1/4] Cargando escena...")
    load_scene(scene_path)

    # ── 2. Escanear nodos ──
    print("")
    logger.info("[2/4] Escaneando nodos...")
    nodes = scan_scene()

    # ── 3. Generar MCNP ──
    print("")
    logger.info("[3/4] Generando entrada MCNP...")
    mcnp_path = generate_mcnp(
        nodes, mcnp_dir,
        isotope=args.isotope,
        n_particles=int(args.n_particles),
        flip_rows=args.flip,
        flip_z=args.flip_z,
    )

    # ── 4. Reporte ──
    print("")
    logger.info("[4/4] Reporte final")
    logger.info("=" * 55)
    logger.info(" PIPELINE COMPLETADO EXITOSAMENTE")
    logger.info("=" * 55)
    logger.info(f"  Archivo MCNP: {mcnp_path}")
    logger.info("")


if __name__ == "__main__":
    main()
