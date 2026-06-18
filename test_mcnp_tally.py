"""
Script minimo para verificar generacion de input MCNP con tally corregido.
Carga la escena guardada y solo ejecuta el paso de generacion MCNP.
"""
import sys
import os

# Agregar path de SlicerDosimLib
sys.path.insert(0, r"C:\programas\3Dosim\3Dosim_v_3.14\3DSlicerModule\SlicerDosim\Modules\Scripted\SlicerDosim\SlicerDosimLib")

import slicer
from mcnp_generator import MCNPInputGenerator

def generar_mcnp_desde_escena():
    """Genera archivo MCNP desde nodos en escena."""
    
    # Obtener nodos de la escena
    ct_node = slicer.util.getNode("CT_sin_camilla")
    pet_node = slicer.util.getNode("*PET*") if slicer.util.getNodes("*PET*") else None
    seg_node = slicer.util.getNode("segmentation") if slicer.util.getNode("segmentation") else None
    
    if not ct_node:
        print("ERROR: No se encontro CT_sin_camilla en la escena")
        return False
    
    print(f"CT encontrado: {ct_node.GetName()}")
    print(f"PET encontrado: {pet_node.GetName() if pet_node else 'Ninguno'}")
    print(f"Segmentacion encontrada: {seg_node.GetName() if seg_node else 'Ninguno'}")
    
    # Obtener dimensiones y spacing del CT
    image_data = ct_node.GetImageData()
    dims = image_data.GetDimensions()
    spacing = ct_node.GetSpacing()
    
    print(f"\nDimensiones CT: {dims}")
    print(f"Spacing CT: {spacing}")
    
    # Calcular dimensiones esperadas del RPP y tally
    nx, ny, nz = dims
    sx, sy, sz = [s/10.0 for s in spacing]  # mm -> cm
    xm = nx * sx
    ym = ny * sy
    zm = nz * sz
    
    print(f"\nDimensiones esperadas RPP 1 / Tally:")
    print(f"  X: 0 a {xm:.6f} cm ({nx} voxels x {sx:.6f} cm)")
    print(f"  Y: 0 a {ym:.6f} cm ({ny} voxels x {sy:.6f} cm)")
    print(f"  Z: 0 a {zm:.6f} cm ({nz} voxels x {sz:.6f} cm)")
    
    # Generar MCNP
    generator = MCNPInputGenerator()
    output_dir = r"C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2\..\resultados_test\mcnp_input"
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\nGenerando archivo MCNP en: {output_dir}")
    input_path = generator.generate(
        ct_volume_node=ct_node,
        pet_volume_node=pet_node,
        segmentation_node=seg_node,
        output_dir=output_dir,
        isotope="Y-90",
        n_particles=int(1e7),
        flip_rows=True,
        flip_z=False,
    )
    
    print(f"\nArchivo generado: {input_path}")
    
    # Verificar tallies en el archivo generado
    print("\n" + "="*60)
    print("VERIFICACION DE TALLIES")
    print("="*60)
    
    with open(input_path, 'r') as f:
        content = f.read()
        
    # Buscar seccion de tallies
    in_tally_section = False
    tally_lines = []
    for line in content.split('\n'):
        if 'rmesh1' in line.lower():
            in_tally_section = True
        if in_tally_section:
            tally_lines.append(line)
            if 'endmd' in line.lower():
                break
    
    print("\nTallies generados:")
    for line in tally_lines:
        print(f"  {line}")
    
    # Buscar RPP 1
    print("\nRPP 1 (superficie bounding box):")
    for line in content.split('\n'):
        if line.strip().startswith('1   rpp'):
            print(f"  {line}")
            break
    
    # Verificar coincidencia
    print("\n" + "="*60)
    print("COMPROBACION")
    print("="*60)
    print(f"Dimensiones calculadas: X={xm:.6f}, Y={ym:.6f}, Z={zm:.6f}")
    print(f"Verificar que los tallies usen LOS MISMOS valores exactos.")
    
    return True

if __name__ == "__main__":
    print("="*60)
    print("Test de generacion MCNP - Verificacion de tallies")
    print("="*60)
    
    success = generar_mcnp_desde_escena()
    
    if success:
        print("\n[OK] Generacion completada. Verificar archivo 3Dosim_mcnp.i")
    else:
        print("\n[ERROR] Fallo la generacion")
    
    sys.exit(0 if success else 1)