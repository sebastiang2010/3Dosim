# 3Dosim v3.14 - Dosimetria 3D para Medicina Nuclear

## Stack
- MATLAB (.m) - modulos principales
- Python (.py) - Slicer module, registro
- 3D Slicer integration

## Modulos
1. **modulo 1** - Segmentacion y registro de imagenes (CT/SPECT)
2. **modulo 2** - Generacion de input MCNP (geometria voxelizada, fuentes, materiales)
3. **modulo 3** - Post-procesamiento (dosis, DVH, BED, EUD, NTCP, TCP)
4. **kernel** - Calculo de kernel de dosis
5. **espectro** - Procesamiento de espectros
6. **estep** - Estimacion de step size

## SlicerDosim - Estructura compartimentada (3DSlicerModule)

```
SlicerDosimLib/
├── __init__.py                  # Exporta todas las clases publicas
├── config.py                    # [NUEVO] TissueConfig - carga tissue_config.json
├── phantom_segmentation.py     # [MODIFICADO] Usa TissueConfig en vez de hardcodes
├── segmentation.py             # Sin cambios
├── registration.py             # Sin cambios
├── mcnp_generator.py           # [MODIFICADO] Orquestador, delega a sub-modulos
├── mcnp_materials.py           # [NUEVO] Indice phantom -> material MCNP
├── mcnp_geometry.py            # [NUEVO] LIKE n BUT, RPP, lattice fill
├── mcnp_source.py              # [NUEVO] SDEF desde PET
├── mcnp_tallies.py             # [NUEVO] FMESH4, F6, modo, NPS
├── dosimetry.py                # [MODIFICADO] Usa MCTALParser
├── mctal_parser.py             # [NUEVO] Parseo de output MCNP
├── dvh_analysis.py             # Sin cambios
└── utils.py                    # Sin cambios

Resources/Config/
└── tissue_config.json          # [NUEVO] Config unica de tejidos/materiales
```

## Modulos de Slicer (entradas separadas en dropdown 3Dosim)

| Categoria | Modulo | Funcion |
|---|---|---|
| 3Dosim | SlicerDosim | Modulo 1: Carga, segmentacion, registro |
| 3Dosim | SlicerDosimMod2 | Modulo 2: Generacion MCNP |
| 3Dosim | SlicerDosimMod3 | Modulo 3: Analisis dosimetrico |

Todos los modulos comparten SlicerDosimLib (en SlicerDosim/).

## Estado actual de trabajo
Refactor completa del SlicerDosim para Slicer:
- Creado `tissue_config.json` con tejidos, colores, HU ranges y composiciones MCNP
- Creado `config.py` (TissueConfig singleton) que centraliza toda la config
- Modulo 2 (MCNP) dividido en 4 sub-modulos compartimentados: materials, geometry, source, tallies
- Modulos separados en dropdown: SlicerDosim (mod1), SlicerDosimMod2 (mod2), SlicerDosimMod3 (mod3)
- `phantom_segmentation.py` ahora usa TissueConfig en vez de dicts hardcodeados
- `dosimetry.py` ahora usa `mctal_parser.py` real en vez de placeholder
- `__init__.py` y `CMakeLists.txt` actualizados

Pendiente:
- Agregar ruta en Slicer: Edit > Settings > Modules > Additional paths > `...\Modules\Scripted`
- Probar que los 3 modulos aparezcan bajo "3Dosim"

## Comandos utiles
- `/remember [tag] mensaje` - Guardar progreso en memoria persistente
