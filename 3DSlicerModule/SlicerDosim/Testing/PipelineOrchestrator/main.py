"""
Entry point del PipelineOrchestrator 3Dosim para 3D Slicer.

Uso desde terminal:
  Slicer.exe --python-script main.py --data-dir "C:/ruta/datos"
  Slicer.exe --python-script main.py --data-dir "C:/ruta/datos" --reset
"""

import argparse
import os
import sys


def _add_parent_to_path():
    """Agrega Testing/ al sys.path para encontrar PipelineOrchestrator como paquete."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(script_dir)  # Testing/
    if parent not in sys.path:
        sys.path.insert(0, parent)
    return parent


def main():
    _add_parent_to_path()

    # Cerrar otras instancias de Slicer antes de comenzar
    from PipelineOrchestrator.utils import kill_existing_slicer
    kill_existing_slicer()

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
        choices=["simple", "totalsegmentator"],
        help="Metodo de segmentacion (simple=threshold, totalsegmentator=IA)",
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
    args, _ = parser.parse_known_args()

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
        mcnp_refine_hu=args.refine_hu,
        mcnp_flip_rows=args.flip,
    )
    orchestrator.run()


if __name__ == "__main__":
    main()
