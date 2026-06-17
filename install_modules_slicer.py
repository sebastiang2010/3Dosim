"""
Script unico: instala SlicerDosimMod2 y SlicerDosimMod3 en Slicer.
Ejecutar UNA VEZ para que persistan los modulos.
Luego lanzar Slicer normalmente para usarlos.
"""
import sys, os

# Ruta a nuestros modulos
our_path = r'C:\programas\3Dosim\3Dosim_v_3.14\3DSlicerModule\SlicerDosim\Modules\Scripted'

if not os.path.isdir(our_path):
    print(f'ERROR: no existe {our_path}')
    sys.exit(1)

# Verificar que los modulos esten alli
expected = ['SlicerDosim', 'SlicerDosimMod2', 'SlicerDosimMod3']
for m in expected:
    if not os.path.isdir(os.path.join(our_path, m)):
        print(f'ERROR: falta {m}/ en {our_path}')
        sys.exit(1)

print(f'Directorio de modulos encontrado: {our_path}')

# Usar QSettings de Slicer para guardar la ruta permanentemente
settings = slicer.app.settings()
existing_paths = settings.value('Modules/AdditionalModulePaths')

if existing_paths is None:
    paths = []
elif isinstance(existing_paths, str):
    paths = [existing_paths]
else:
    paths = list(existing_paths)

if our_path in paths:
    print(f'La ruta YA esta configurada:')
else:
    paths.append(our_path)
    settings.setValue('Modules/AdditionalModulePaths', paths)
    settings.sync()
    print(f'Ruta AGREGADA a Slicer Settings:')

print(f'\nRutas de modulos adicionales:')
for i, p in enumerate(paths):
    print(f'  {i+1}. {p}')

print(f'\nMODULOS DISPONIBLES:')
for m in expected:
    py_path = os.path.join(our_path, m, f'{m}.py')
    if os.path.isfile(py_path):
        print(f'  ✅ {m} ({py_path})')
    else:
        print(f'  ❌ {m} (FALTA {py_path})')

print(f'\n✅ Instalacion completada. Reinicia Slicer.')
print(f'Los modulos apareceran en Modules > 3Dosim:')
print(f'  - SlicerDosim     (Segmentacion)')
print(f'  - SlicerDosimMod2 (Generacion MCNP)')
print(f'  - SlicerDosimMod3 (Analisis)')
