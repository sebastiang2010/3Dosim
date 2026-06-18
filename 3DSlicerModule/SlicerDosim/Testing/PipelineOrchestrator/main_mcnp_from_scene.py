r"""
Entry point del MCNPFromScenePipeline para 3D Slicer.

Carga una escena .mrb guardada (con CT, PET y segmentacion) y genera
el archivo de entrada MCNP para simulacion dosimetrica.

Uso desde terminal:
  Slicer.exe --python-script main_mcnp_from_scene.py --scene "ruta/a/escena.mrb"
  Slicer.exe --python-script main_mcnp_from_scene.py --scene "escena.mrb" --output "C:/salida"
  Slicer.exe --python-script main_mcnp_from_scene.py                         # auto-busca escena
  Slicer.exe --python-script main_mcnp_from_scene.py --scene "escena.mrb" --reset --isotope Lu-177

Ejemplos:
  # Usar la escena mas reciente y salida por defecto
  & "C:\Users\Sebastian\AppData\Local\slicer.org\Slicer 5.8.1\Slicer.exe" ^
      --python-script ".../main_mcnp_from_scene.py"

  # Escena especifica con isotopo Y-90, 20M particulas
  & "C:\Users\Sebastian\AppData\Local\slicer.org\Slicer 5.8.1\Slicer.exe" ^
      --python-script ".../main_mcnp_from_scene.py" ^
      --scene "C:/MAT/3Dosim/ai-pipe/scenes/3Dosim_scene.mrb" ^
      --output "C:/MAT/3Dosim/ai-pipe" ^
      --isotope Y-90 --n-particles 20000000

  # Reiniciar checkpoints
  & "C:\Users\Sebastian\AppData\Local\slicer.org\Slicer 5.8.1\Slicer.exe" ^
      --python-script ".../main_mcnp_from_scene.py" ^
      --reset
"""

import argparse
import os
import sys


def _add_parent_to_path():
    """Agrega Testing/ al sys.path para encontrar PipelineOrchestrator como paquete.

    PipelineOrchestrator vive en:
        .../SlicerDosim/Testing/PipelineOrchestrator/
    Al agregar Testing/ al path, puede importarse como:
        from PipelineOrchestrator.pipeline_mcnp_from_scene import ...
    """
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(script_dir)  # Testing/
    if parent not in sys.path:
        sys.path.insert(0, parent)
    return parent


def main():
    _add_parent_to_path()

    parser = argparse.ArgumentParser(
        description=(
            "Pipeline MCNP desde escena guardada (.mrb). "
            "Carga una escena de 3D Slicer, extrae nodos CT/PET/Segmentacion "
            "y genera el archivo de entrada MCNP."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  # Auto-buscar escena mas reciente y usar config por defecto
  python main_mcnp_from_scene.py

  # Escena especifica con isotopo personalizado
  python main_mcnp_from_scene.py --scene "C:/ruta/escena.mrb" --isotope Lu-177

  # Directorio de salida explicito con 50M particulas
  python main_mcnp_from_scene.py --output "C:/salida" --n-particles 50000000
        """,
    )

    # Argumentos principales
    parser.add_argument(
        "--scene",
        type=str,
        default=None,
        metavar="PATH",
        help="Ruta al archivo .mrb de la escena guardada. Si no se especifica, "
             "busca automaticamente el mas reciente en scene_output_dir del config.",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        metavar="DIR",
        help="Directorio de salida para los archivos MCNP y resultados. "
             "Si no se especifica, usa el valor de pipeline_config.jsonc "
             "o el default: 'C:/MAT/3Dosim/ai-pipe/mcnp_input'.",
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        metavar="PATH",
        help="Ruta al archivo pipeline_config.jsonc. "
             "Si no se especifica, busca en el directorio de PipelineOrchestrator.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reiniciar checkpoints. Ignora el estado guardado de ejecuciones "
             "anteriores y ejecuta todos los pasos desde cero.",
    )

    # Parametros MCNP
    parser.add_argument(
        "--isotope",
        type=str,
        default=None,
        choices=["Y-90", "I-131", "Lu-177", "Tc-99m"],
        metavar="ISOTOPE",
        help="Isotopo para la fuente MCNP. Opciones: Y-90, I-131, Lu-177, Tc-99m. "
             "Default: desde pipeline_config.jsonc o Y-90.",
    )
    parser.add_argument(
        "--n-particles",
        type=float,
        default=None,
        metavar="N",
        help="Numero de historias (particulas) para la simulacion MCNP. "
             "Default: desde pipeline_config.jsonc o 10,000,000 (1e7).",
    )
    parser.add_argument(
        "--refine-hu",
        action="store_true",
        default=False,
        help="Refinar el mapeo HU -> materiales. Mas lento pero mas preciso "
             "para la asignacion de materiales en la geometria voxelizada.",
    )
    parser.add_argument(
        "--flip",
        action="store_true",
        default=False,
        help="Invertir eje Y antes de RLE. Necesario para compatibilidad con "
             "el formato MATLAB de entrada MCNP.",
    )
    parser.add_argument(
        "--flip-z",
        action="store_true",
        default=False,
        help="Invertir eje Z antes de RLE.",
    )

    # Tallies personalizados
    parser.add_argument(
        "--liver-tallies",
        type=int,
        default=None,
        metavar="N",
        help="Numero de tallies (detectores) para el higado. Default: 5.",
    )
    parser.add_argument(
        "--tumor-tallies",
        type=int,
        default=None,
        metavar="N",
        help="Numero de tallies (detectores) para el tumor. Default: 10.",
    )

    # Parsear (con known_args para compatibilidad con args de Slicer)
    args, _ = parser.parse_known_args()

    # Log de parametros recibidos
    print("=" * 60)
    print(" MCNPFromScenePipeline - Parametros")
    print("=" * 60)
    print(f"  Scene:       {args.scene or 'auto-buscar'}")
    print(f"  Output:      {args.output or 'default del config'}")
    print(f"  Config:      {args.config or 'default'}")
    print(f"  Reset:       {'SI' if args.reset else 'NO'}")
    print(f"  Isotopo:     {args.isotope or 'default'}")
    print(f"  Particulas:  {int(args.n_particles) if args.n_particles else 'default'}")
    print(f"  Refinar HU:  {'SI' if args.refine_hu else 'NO'}")
    print(f"  Flip Y:      {'SI' if args.flip else 'NO'}")
    print(f"  Flip Z:      {'SI' if args.flip_z else 'NO'}")
    print(f"  Tallies higado: {args.liver_tallies or 'default'}")
    print(f"  Tallies tumor:  {args.tumor_tallies or 'default'}")
    print("")

    # Construir y ejecutar pipeline
    from PipelineOrchestrator.pipeline_mcnp_from_scene import MCNPFromScenePipeline

    pipeline = MCNPFromScenePipeline(
        scene_path=args.scene,
        output_dir=args.output,
        config_path=args.config,
        reset=args.reset,
        mcnp_isotope=args.isotope,
        mcnp_n_particles=int(args.n_particles) if args.n_particles else None,
        mcnp_refine_hu=args.refine_hu,
        mcnp_flip_rows=args.flip,
        mcnp_flip_z=args.flip_z,
        mcnp_n_liver_tallies=args.liver_tallies,
        mcnp_n_tumor_tallies=args.tumor_tallies,
    )
    pipeline.run()


if __name__ == "__main__":
    main()
