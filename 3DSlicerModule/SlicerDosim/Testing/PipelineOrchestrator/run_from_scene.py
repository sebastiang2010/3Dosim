"""
run_from_scene.py - Carga la ultima escena guardada y ejecuta el pipeline desde ahi.

Uso:
  Slicer.exe --python-script run_from_scene.py
  Slicer.exe --python-script run_from_scene.py --scene "C:/ruta/escena.mrb"
  Slicer.exe --python-script run_from_scene.py --reset
"""

import argparse
import os
import sys
import glob


def _add_parent_to_path():
    """Agrega Testing/ al sys.path para encontrar PipelineOrchestrator como paquete."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(script_dir)  # Testing/
    if parent not in sys.path:
        sys.path.insert(0, parent)
    return parent


def find_last_scene(data_dir=None):
    """Busca la ultima escena .mrb guardada."""
    # Buscar en varias ubicaciones posibles
    search_dirs = []
    
    # 1. Directorio de imagenes del pipeline
    img_dir = r"C:\MAT\3Dosim\ai-pipe\imagenes"
    if os.path.exists(img_dir):
        search_dirs.append(img_dir)
    
    # 2. Directorio de resultados del paciente
    if data_dir:
        resultados = os.path.join(data_dir, "..", "resultados_test", "scenes")
        if os.path.exists(resultados):
            search_dirs.append(resultados)
    
    # 3. Escaneo recursivo en el directorio de datos
    if data_dir:
        for root, dirs, files in os.walk(data_dir):
            if "scenes" in root.lower():
                search_dirs.append(root)
    
    # Buscar archivos .mrb en todos los directorios
    mrb_files = []
    for d in search_dirs:
        pattern = os.path.join(d, "*.mrb")
        mrb_files.extend(glob.glob(pattern))
    
    if not mrb_files:
        return None
    
    # Ordenar por fecha de modificacion (mas reciente primero)
    mrb_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    
    return mrb_files[0]


def main():
    _add_parent_to_path()
    
    parser = argparse.ArgumentParser(
        description="Carga ultima escena y ejecuta pipeline desde ahi"
    )
    parser.add_argument(
        "--scene",
        type=str,
        default=None,
        help="Ruta a archivo .mrb especifico (default: buscar la ultima escena)"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=r"C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2",
        help="Directorio con datos del paciente (para buscar escenas)"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reiniciar checkpoints (ignora estado guardado)"
    )
    parser.add_argument(
        "--steps",
        type=str,
        nargs="+",
        default=None,
        help="Pasos especificos a ejecutar (default: todos los pendientes)"
    )
    parser.add_argument(
        "--segmenter",
        type=str,
        default="totalsegmentator",
        choices=["simple", "totalsegmentator"],
        help="Metodo de segmentacion"
    )
    parser.add_argument(
        "--force-cpu",
        action="store_true",
        default=True,
        help="Fuerza CPU en TotalSegmentator"
    )
    parser.add_argument(
        "--mcp-port",
        type=int,
        default=0,
        help="Puerto para servidor MCP"
    )
    parser.add_argument(
        "--no-consola",
        action="store_true",
        help="Deshabilita consola interactiva"
    )
    parser.add_argument(
        "--export-labelmap",
        action="store_true",
        default=False,
        help="Exportar labelmap despues de cargar escena"
    )
    parser.add_argument(
        "--export-nifti",
        action="store_true",
        default=False,
        help="Exportar segmentaciones a NIfTI"
    )
    
    args, _ = parser.parse_known_args()
    
    # Buscar escena
    scene_path = args.scene
    if not scene_path:
        print("Buscando ultima escena guardada...")
        scene_path = find_last_scene(args.data_dir)
        if scene_path:
            print(f"Escena encontrada: {scene_path}")
        else:
            print("No se encontro ninguna escena .mrb")
            print("Especifique una ruta con --scene o ejecute el pipeline normal")
            return
    
    # Verificar que la escena existe
    if not os.path.exists(scene_path):
        print(f"Error: Escena no encontrada: {scene_path}")
        return
    
    print(f"Cargando escena: {scene_path}")
    print(f"Tamano: {os.path.getsize(scene_path) / 1024 / 1024:.1f} MB")
    
    # Importar y ejecutar pipeline
    from PipelineOrchestrator.pipeline import PipelineTestOrchestrator
    
    # Crear orquestador con la escena
    orchestrator = PipelineTestOrchestrator(
        data_dir=args.data_dir,
        reset=args.reset,
        mcp_port=args.mcp_port,
        no_consola=args.no_consola,
        segmenter=args.segmenter,
        stop_before_segment=False,
        force_cpu=args.force_cpu,
    )
    
    # Cargar la escena especifica
    import slicer
    
    print("Cargando escena en Slicer...")
    success = slicer.util.loadScene(scene_path)
    
    if not success:
        print("Error: No se pudo cargar la escena")
        return
    
    print("Escena cargada correctamente")
    
    # Escanear escena para restaurar nodos
    orchestrator._scan_scene_for_nodes()
    
    # Mostrar nodos restaurados
    print("\nNodos restaurados:")
    if orchestrator.ct_node:
        print(f"  CT: {orchestrator.ct_node.GetName()}")
    if orchestrator.pet_node:
        print(f"  PET: {orchestrator.pet_node.GetName()}")
    if orchestrator.segmentation_node:
        print(f"  Segmentacion: {orchestrator.segmentation_node.GetName()}")
        # Contar segmentos
        import vtk
        seg_ids = vtk.vtkStringArray()
        orchestrator.segmentation_node.GetSegmentation().GetSegmentIDs(seg_ids)
        print(f"    Segmentos: {seg_ids.GetNumberOfValues()}")
    if orchestrator.body_node:
        print(f"  Body: {orchestrator.body_node.GetName()}")
    
    # Ejecutar pasos especificos o todos los pendientes
    if args.steps:
        print(f"\nEjecutando pasos: {args.steps}")
        # Ejecutar pasos especificos
        for step in args.steps:
            step_method = getattr(orchestrator, f"_do_{step}", None)
            if step_method:
                print(f"\nEjecutando paso: {step}")
                try:
                    step_method()
                    print(f"  Paso {step} completado")
                except Exception as e:
                    print(f"  Error en paso {step}: {e}")
            else:
                print(f"  Paso {step} no encontrado")
    else:
        # Ejecutar pipeline completo (retomara desde donde quedo)
        print("\nEjecutando pipeline completo...")
        orchestrator.run()
    
    # Exportar si se solicito
    if args.export_labelmap:
        print("\nExportando labelmap...")
        try:
            orchestrator._export_labelmap()
            print("Labelmap exportado")
        except Exception as e:
            print(f"Error exportando labelmap: {e}")
    
    if args.export_nifti:
        print("\nExportando NIfTI...")
        try:
            # Buscar paso de exportacion
            if hasattr(orchestrator, '_export_nifti'):
                orchestrator._export_nifti()
            else:
                print("Paso de exportacion NIfTI no encontrado")
        except Exception as e:
            print(f"Error exportando NIfTI: {e}")
    
    print("\nPipeline completado")
    
    # Mantener Slicer abierto
    print("\nSlicer permanecera abierto. Cierre manualmente cuando termine.")


if __name__ == "__main__":
    main()
