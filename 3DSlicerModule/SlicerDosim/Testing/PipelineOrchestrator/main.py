"""
Entry point del PipelineOrchestrator 3Dosim para 3D Slicer.

Uso desde terminal:
  # Legacy (pipeline completo original)
  Slicer.exe --python-script main.py --data-dir "C:/ruta/datos"

  # Modulo 1: carga, segmentacion, tumor (sin MCNP)
  Slicer.exe --python-script main.py --modulo 1 --data-dir "C:/ruta/datos"

  # Modulo 2: generacion MCNP desde escena .mrb (desde Mod1)
  Slicer.exe --python-script main.py --modulo 2 --scene "C:/ruta/escena.mrb"

  # Modulo 3: analisis dosimetrico (proximamente)
  Slicer.exe --python-script main.py --modulo 3 --mcnp-output "C:/ruta/output"
"""

import argparse
import logging
import os
import sys

logger = logging.getLogger("3DosimMain")


def _add_parent_to_path():
    """Agrega Testing/ al sys.path para encontrar PipelineOrchestrator como paquete."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(script_dir)  # Testing/
    if parent not in sys.path:
        sys.path.insert(0, parent)
    return parent


def run_mod1(args):
    """Ejecuta PipelineMod1: carga, segmentacion, tumor (sin MCNP)."""
    from PipelineOrchestrator.pipeline_mod1 import PipelineMod1

    orchestrator = PipelineMod1(
        data_dir=args.data_dir,
        reset=args.reset,
        mcp_port=args.mcp_port,
        no_consola=args.no_consola,
        segmenter=args.segmenter,
        stop_before_segment=args.stop_before_segment,
        force_cpu=args.force_cpu,
        patient_id=args.patient_id,
    )
    orchestrator.run()


def run_mod2(args):
    """Ejecuta PipelineMod2: genera MCNP desde escena .mrb de Mod1."""
    from PipelineOrchestrator.pipeline_mod2 import PipelineMod2

    # Si no se especifico --scene, auto-detectar con PipelineMod2
    scene_path = args.scene
    if not scene_path:
        scene_path = PipelineMod2._auto_detect_scene()

    orchestrator = PipelineMod2(
        scene_path=scene_path,
        output_dir=args.output,
        reset=args.reset,
        isotope=args.isotope or "Y-90",
        n_particles=int(args.n_particles) if args.n_particles else int(1e7),
        flip_rows=args.flip if hasattr(args, 'flip') else True,
        flip_z=args.flip_z if hasattr(args, 'flip_z') else False,
        refine_hu=args.refine_hu if hasattr(args, 'refine_hu') else False,
    )
    orchestrator.run()


def run_mod3(args):
    """Ejecuta PipelineMod3: analisis dosimetrico desde escena + MCTAL."""
    from PipelineOrchestrator.pipeline_mod3 import PipelineMod3

    # Auto-detectar paths si no se especificaron
    scene_path = args.scene
    if not scene_path:
        scene_path = PipelineMod3._auto_detect_scene()

    orchestrator = PipelineMod3(
        scene_path=scene_path,
        mctal_path=args.mctal,
        activity_gbq=args.activity,
        output_dir=args.output,
        reset=args.reset,
        flip=args.flip if hasattr(args, 'flip') else True,
        no_consola=args.no_consola,
        patient_id=args.patient_id,
    )
    orchestrator.run()


def run_legacy(args):
    """Ejecuta el pipeline legacy completo (PipelineTestOrchestrator)."""
    from PipelineOrchestrator.pipeline import PipelineTestOrchestrator

    orchestrator = PipelineTestOrchestrator(
        args.data_dir,
        reset=args.reset,
        mcp_port=args.mcp_port,
        no_consola=args.no_consola,
        segmenter=args.segmenter,
        stop_before_segment=args.stop_before_segment,
        force_cpu=args.force_cpu,
        mcnp_isotope=args.isotope,
        mcnp_n_particles=int(args.n_particles) if args.n_particles else None,
        mcnp_refine_hu=args.refine_hu if hasattr(args, 'refine_hu') else False,
        mcnp_flip_rows=args.flip if hasattr(args, 'flip') else False,
    )
    orchestrator.run()


def main():
    _add_parent_to_path()

    # Cerrar otras instancias de Slicer antes de comenzar
    from PipelineOrchestrator.utils import kill_existing_slicer
    kill_existing_slicer()

    parser = argparse.ArgumentParser(
        description="Pipeline orchestrator para SlicerDosim"
    )

    # ── Seleccion de modulo ──
    parser.add_argument(
        "--modulo",
        type=int,
        default=None,
        choices=[1, 2, 3],
        help="Modulo a ejecutar: 1=carga+segmentacion+tumor, 2=generacion MCNP, "
             "3=analisis dosimetrico (default: pipeline legacy completo)",
    )

    # ── Argumentos Mod1 / Legacy ──
    parser.add_argument(
        "--data-dir",
        type=str,
        default=r"C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2",
        help="Directorio con subdirectorios CT/ y PET/ (Mod1 y legacy)",
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
        "--segmenter",
        type=str,
        default="totalsegmentator",
        choices=["totalsegmentator"],
        help="Motor de segmentacion (totalsegmentator)",
    )
    parser.add_argument(
        "--no-consola",
        action="store_true",
        help="Deshabilita la consola interactiva de comandos",
    )
    parser.add_argument(
        "--stop-before-segment",
        action="store_true",
        help="Ejecuta hasta antes de segmentacion, luego muestra parametros TS y sale",
    )
    parser.add_argument(
        "--patient-id",
        type=str,
        default=None,
        help="ID del paciente para nombrar escenas guardadas",
    )
    parser.add_argument(
        "--force-cpu",
        action="store_true",
        default=True,
        help="Fuerza CPU en TotalSegmentator (desactiva GPU)",
    )
    parser.add_argument(
        "--no-force-cpu",
        action="store_false",
        dest="force_cpu",
        help="Permite GPU en TotalSegmentator si esta disponible",
    )

    # ── Argumentos Mod2 / Legacy ──
    parser.add_argument(
        "--scene",
        type=str,
        default=None,
        help="Ruta al archivo .mrb de escena (Mod2: carga desde Mod1)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Directorio de salida (Mod2: MCNP output)",
    )
    parser.add_argument(
        "--isotope",
        type=str,
        default=None,
        choices=["Y-90", "I-131", "Lu-177", "Tc-99m"],
        help="Isotopo para fuente MCNP (default: desde config o Y-90)",
    )
    parser.add_argument(
        "--n-particles",
        type=float,
        default=None,
        help="Numero de historias MCNP (default: desde config o 1e7)",
    )
    parser.add_argument(
        "--refine-hu",
        action="store_true",
        default=False,
        help="Refinar mapeo HU -> materiales en MCNP",
    )
    parser.add_argument(
        "--flip",
        action="store_true",
        default=False,
        help="Invertir eje Y antes de RLE (compatibilidad MATLAB)",
    )
    parser.add_argument(
        "--flip-z",
        action="store_true",
        default=False,
        help="Invertir eje Z",
    )

    # ── Argumentos Mod3 (analisis dosimetrico) ──
    parser.add_argument(
        "--mctal",
        type=str,
        default=None,
        help="Ruta al archivo MCTAL (Mod3: salida MCNP)",
    )
    parser.add_argument(
        "--labelmap",
        type=str,
        default=None,
        help="Ruta a labelmap NIfTI (solo legacy; Mod3 obtiene labelmap desde escena)",
    )
    parser.add_argument(
        "--activity",
        type=float,
        default=None,
        help="Actividad en GBq (Mod3: si no se especifica, computa desde PET)",
    )
    args, _ = parser.parse_known_args()

    # ── Dispatch por modulo ──
    if args.modulo == 1:
        logger.info("  Modo: Modulo 1 — Carga, Segmentacion, Tumor")
        run_mod1(args)
    elif args.modulo == 2:
        logger.info("  Modo: Modulo 2 — Generacion MCNP desde escena")
        run_mod2(args)
    elif args.modulo == 3:
        logger.info("  Modo: Modulo 3 — Analisis dosimetrico")
        run_mod3(args)
    else:
        logger.info("  Modo: Legacy (pipeline completo)")
        run_legacy(args)


if __name__ == "__main__":
    main()
