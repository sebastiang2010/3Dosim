"""
run_mcnp.py - Genera input MCNP desde la ultima escena guardada.

Uso:
  Slicer.exe --python-script run_mcnp.py
  Slicer.exe --python-script run_mcnp.py --isotope Y-90
  Slicer.exe --python-script run_mcnp.py --n-particles 1e7
"""

import argparse
import os
import sys
import glob
import traceback


def _add_parent_to_path():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    parent = os.path.dirname(script_dir)
    if parent not in sys.path:
        sys.path.insert(0, parent)
    return parent


def find_last_scene():
    """Busca la ultima escena .mrb guardada."""
    search_dirs = [
        r"C:\MAT\3Dosim\ai-pipe\imagenes",
        r"C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2\resultados_test\scenes",
    ]
    
    mrb_files = []
    for d in search_dirs:
        if os.path.exists(d):
            pattern = os.path.join(d, "*.mrb")
            mrb_files.extend(glob.glob(pattern))
    
    if not mrb_files:
        return None
    
    # Ordenar por fecha (mas reciente primero)
    mrb_files.sort(key=lambda x: os.path.getmtime(x), reverse=True)
    return mrb_files[0]


def main():
    _add_parent_to_path()
    
    # Cargar defaults desde config unificada (si disponible)
    try:
        from SlicerDosim.SlicerDosimLib.config import load_unified_config
        cfg = load_unified_config()
        default_isotope = cfg.get("mcnp_source", {}).get("isotope", "Y-90")
        default_npart = cfg.get("mcnp_run", {}).get("n_particles", int(1e7))
        default_mcnp_out = cfg.get("paths", {}).get("mcnp_output_dir", None)
        default_n_liver = cfg.get("mcnp_tallies", {}).get("n_liver_tallies", 5)
        default_n_tumor = cfg.get("mcnp_tallies", {}).get("n_tumor_tallies", 10)
        default_flip_y = cfg.get("geometry", {}).get("flip_y", False)
        default_flip_z = cfg.get("geometry", {}).get("flip_z", False)
    except Exception:
        default_isotope = "Y-90"
        default_npart = int(1e7)
        default_mcnp_out = None
        default_n_liver = 5
        default_n_tumor = 10
        default_flip_y = False
        default_flip_z = False

    parser = argparse.ArgumentParser(description="Genera input MCNP desde escena guardada")
    parser.add_argument("--scene", type=str, default=None, help="Ruta a escena .mrb especifica")
    parser.add_argument("--isotope", type=str, default=default_isotope, help="Isotopo")
    parser.add_argument("--n-particles", type=float, default=default_npart, help="Numero de particulas")
    parser.add_argument("--output-dir", type=str, default=default_mcnp_out, help="Directorio de salida para MCNP")
    parser.add_argument("--refine-hu", action="store_true", help="Refinar mapeo HU->materiales")
    parser.add_argument("--flip", action="store_true", default=default_flip_y, help="Invertir eje Y antes de RLE (como MATLAB)")
    parser.add_argument("--no-flip", action="store_true", default=False, help="No invertir eje Y (sobrescribe config)")
    parser.add_argument("--flip-z", action="store_true", default=default_flip_z, help="Invertir eje Z antes de RLE")
    parser.add_argument("--n-liver", type=int, default=default_n_liver, help="Numero de tallies *f8 aleatorios en higado")
    parser.add_argument("--n-tumor", type=int, default=default_n_tumor, help="Numero de tallies *f8 aleatorios en tumor")
    args, _ = parser.parse_known_args()
    
    # Buscar escena
    scene_path = args.scene or find_last_scene()
    if not scene_path or not os.path.exists(scene_path):
        print("ERROR: No se encontro escena .mrb")
        return
    
    print(f"Escena: {scene_path}")
    print(f"Tamano: {os.path.getsize(scene_path) / 1024 / 1024:.1f} MB")
    
    # Directorio de salida
    output_dir = args.output_dir or os.path.join(
        os.path.dirname(scene_path), "..", "mcnp_input"
    )
    os.makedirs(output_dir, exist_ok=True)
    print(f"Output: {output_dir}")
    
    # Cargar escena en Slicer
    import slicer
    slicer.util.showStatusMessage("Cargando escena...", 3000)
    print("\nCargando escena...")
    success = slicer.util.loadScene(scene_path)
    if not success:
        print("ERROR: No se pudo cargar la escena")
        return
    slicer.util.showStatusMessage("Escena cargada OK", 3000)
    print("Escena cargada OK")
    
    # Buscar nodos necesarios
    import vtk
    
    slicer.util.showStatusMessage("Buscando nodos en escena...", 3000)
    vol_nodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")
    seg_nodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")
    
    print(f"\nNodos en escena: {len(vol_nodes)} volumenes, {len(seg_nodes)} segmentaciones")
    
    # Buscar CT
    ct_node = None
    for n in vol_nodes:
        if "CT" in n.GetName().upper():
            ct_node = n
            break
    if not ct_node:
        print("ERROR: No se encontro volumen CT en la escena")
        return
    print(f"CT: {ct_node.GetName()}")
    
    # Buscar PET
    pet_node = None
    for n in vol_nodes:
        if "PET" in n.GetName().upper() or "PT" in n.GetName().upper():
            pet_node = n
            break
    if pet_node:
        print(f"PET: {pet_node.GetName()}")
    else:
        print("AVISO: No se encontro PET (se usara solo CT)")
    
    # Buscar labelmap existente (3Dosim_Labelmap)
    labelmap_nodes = slicer.util.getNodesByClass("vtkMRMLLabelMapVolumeNode")
    seg_node = None
    for n in labelmap_nodes:
        if "Labelmap" in n.GetName() or "labelmap" in n.GetName():
            seg_node = n
            print(f"Labelmap encontrado: {n.GetName()} - usandolo directamente")
            break
    
    if not seg_node:
        # Buscar segmentacion
        for n in seg_nodes:
            name = n.GetName()
            if "TotalSegmentator" in name or "Segmentation" in name:
                seg_node = n
                break
        if not seg_node:
            # Usar la primera que tenga segmentos
            for n in seg_nodes:
                seg_ids = vtk.vtkStringArray()
                n.GetSegmentation().GetSegmentIDs(seg_ids)
                if seg_ids.GetNumberOfValues() > 0:
                    seg_node = n
                    break
    if not seg_node:
        print("ERROR: No se encontro segmentacion ni labelmap en la escena")
        return
    
    if seg_node.IsA("vtkMRMLLabelMapVolumeNode"):
        n_seg = "N/A (labelmap)"
    else:
        seg_ids = vtk.vtkStringArray()
        seg_node.GetSegmentation().GetSegmentIDs(seg_ids)
        n_seg = seg_ids.GetNumberOfValues()
    print(f"Segmentacion: {seg_node.GetName()} ({n_seg} segmentos)")
    
    slicer.util.showStatusMessage(f"Segmentacion encontrada: {seg_node.GetName()}", 3000)
    
    # Determinar flip_rows antes de usarlo
    flip_rows = args.flip and not args.no_flip
    
    # Mostrar dialogo de inicio
    import qt
    msg_start = qt.QMessageBox()
    msg_start.setWindowTitle("Generando Input MCNP")
    msg_start.setText("Generando entrada para MCNP...")
    flip_text = "SI" if flip_rows else "NO"
    flipz_text = "SI" if args.flip_z else "NO"
    msg_start.setInformativeText(
        f"Isotopo: {args.isotope}\n"
        f"Particulas: {args.n_particles:.0e}\n"
        f"Flip Y: {flip_text}\n"
        f"Flip Z: {flipz_text}\n"
        f"Tallies: liver={args.n_liver}, tumor={args.n_tumor}\n\n"
        f"Por favor espere..."
    )
    msg_start.setIcon(qt.QMessageBox.Information)
    msg_start.setStandardButtons(qt.QMessageBox.NoButton)
    msg_start.show()
    qt.QApplication.processEvents()
    
    # Generar MCNP
    slicer.util.showStatusMessage(f"Generando input MCNP ({args.isotope})...", 0)
    print(f"\nGenerando input MCNP...")
    print(f"  Isotopo: {args.isotope}")
    print(f"  Particulas: {args.n_particles:.0e}")
    print(f"  Flip Y: {'SI' if flip_rows else 'NO'}")
    print(f"  Flip Z: {'SI' if args.flip_z else 'NO'}")
    print(f"  Tallies liver: {args.n_liver}, tumor: {args.n_tumor}")
    
    from SlicerDosim.SlicerDosimLib import MCNPInputGenerator
    
    generator = MCNPInputGenerator()
    
    try:
        input_path = generator.generate(
            ct_volume_node=ct_node,
            pet_volume_node=pet_node,
            segmentation_node=seg_node,
            output_dir=output_dir,
            isotope=args.isotope,
            n_particles=int(args.n_particles),
            refine_hu=args.refine_hu,
            flip_rows=flip_rows,
            flip_z=args.flip_z,
            n_liver_tallies=args.n_liver,
            n_tumor_tallies=args.n_tumor,
        )
        
        # Cerrar dialogo de inicio
        msg_start.close()
        
        if input_path:
            # Copiar archivo fuente .src (si no esta ya en el mismo dir)
            import shutil
            src_source = r"C:\MAT\3Dosim\ai-pipe\mcnp_input\Y90cel3D.src"
            dst_source = os.path.join(output_dir, "Y90cel3D.src")
            if os.path.exists(src_source):
                if os.path.abspath(src_source) != os.path.abspath(dst_source):
                    shutil.copy2(src_source, dst_source)
                    print(f"  Archivo fuente copiado: {dst_source}")
                else:
                    print(f"  Archivo fuente ya en destino: {dst_source}")
            
            slicer.util.showStatusMessage(f"MCNP generado: {os.path.basename(input_path)}", 5000)
            
            # Dialogo de exito
            msg_done = qt.QMessageBox()
            msg_done.setWindowTitle("MCNP Generado")
            msg_done.setText("Input MCNP generado exitosamente!")
            msg_done.setInformativeText(
                f"<b>Archivo:</b> {os.path.basename(input_path)}<br>"
                f"<b>Ubicacion:</b> {output_dir}<br>"
                f"<b>Tamano:</b> {os.path.getsize(input_path) / 1024:.1f} KB<br><br>"
                f"<b>Isotopo:</b> {args.isotope}<br>"
                f"<b>Particulas:</b> {args.n_particles:.0e}<br>"
                f"<b>Flip Z:</b> {'Si' if args.flip_z else 'No'}<br>"
                f"<b>Tallies liver:</b> {args.n_liver}<br>"
                f"<b>Tallies tumor:</b> {args.n_tumor}"
            )
            msg_done.setDetailedText(
                f"Para ejecutar MCNP:\n"
                f"  cd {output_dir}\n"
                f"  mcnp6 i={os.path.basename(input_path)} o={os.path.basename(input_path)}.o"
            )
            msg_done.setIcon(qt.QMessageBox.Information)
            msg_done.exec_()
            
            print(f"\n{'='*60}")
            print(f"MCNP INPUT GENERADO EXITOSAMENTE")
            print(f"{'='*60}")
            print(f"Archivo: {input_path}")
            print(f"Tamano: {os.path.getsize(input_path) / 1024:.1f} KB")
        else:
            slicer.util.showStatusMessage("Error generando MCNP", 5000)
            # Dialogo de error
            msg_error = qt.QMessageBox()
            msg_error.setWindowTitle("Error")
            msg_error.setText("No se pudo generar el input MCNP")
            msg_error.setInformativeText("Verifique que la segmentacion sea valida.")
            msg_error.setIcon(qt.QMessageBox.Critical)
            msg_error.exec_()
            
    except Exception as e:
        slicer.util.showStatusMessage("Error durante generacion MCNP", 5000)
        # Cerrar dialogo de inicio en caso de error
        try:
            msg_start.close()
        except:
            pass
        
        print(f"ERROR durante generacion MCNP: {e}")
        traceback.print_exc()
        
        # Dialogo de error
        msg_error = qt.QMessageBox()
        msg_error.setWindowTitle("Error")
        msg_error.setText("Error durante generacion MCNP")
        msg_error.setInformativeText(str(e))
        msg_error.setDetailedText(traceback.format_exc())
        msg_error.setIcon(qt.QMessageBox.Critical)
        msg_error.exec_()
    
    slicer.util.showStatusMessage("Proceso MCNP completado", 5000)
    print("\nProceso completado")


if __name__ == "__main__":
    main()
