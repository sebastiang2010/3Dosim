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
Modules/Scripted/SlicerDosim/
├── SlicerDosimLib/
│   ├── __init__.py              # Exporta todas las clases publicas
│   ├── config.py                # [NUEVO] TissueConfig - carga tissue_config.json
│   ├── phantom_segmentation.py  # [MODIFICADO] Usa TissueConfig en vez de hardcodes
│   ├── segmentation.py          # Sin cambios
│   ├── registration.py          # Sin cambios
│   ├── mcnp_generator.py        # [MODIFICADO] Orquestador, delega a sub-modulos
│   ├── mcnp_materials.py        # [NUEVO] Indice phantom -> material MCNP
│   ├── mcnp_geometry.py         # [NUEVO] LIKE n BUT, RPP, lattice fill
│   ├── mcnp_source.py           # [NUEVO] SDEF desde PET
│   ├── mcnp_tallies.py          # [NUEVO] FMESH4, F6, modo, NPS
│   ├── dosimetry.py             # [MODIFICADO] Usa MCTALParser
│   ├── mctal_parser.py          # [NUEVO] Parseo de output MCNP
│   ├── dvh_analysis.py          # Sin cambios
│   └── utils.py                 # Sin cambios
├── Resources/
│   └── Config/
│       └── tissue_config.json   # [NUEVO] Config unica de tejidos/materiales
└── Testing/
    └── PipelineOrchestrator/    # (ver abajo)
```

## Modulos de Slicer (entradas separadas en dropdown 3Dosim)

| Categoria | Modulo | Funcion |
|---|---|---|
| 3Dosim | SlicerDosim | Modulo 1: Carga, segmentacion, registro |
| 3Dosim | SlicerDosimMod2 | Modulo 2: Generacion MCNP |
| 3Dosim | SlicerDosimMod3 | Modulo 3: Analisis dosimetrico |

Todos los modulos comparten SlicerDosimLib (en SlicerDosim/).

## Estado actual de trabajo

### Refactor SlicerDosim (COMPLETADO)
- Creado `tissue_config.json` con tejidos, colores, HU ranges y composiciones MCNP
- Creado `config.py` (TissueConfig singleton) que centraliza toda la config
- Modulo 2 (MCNP) dividido en 4 sub-modulos compartimentados: materials, geometry, source, tallies
- Modulos separados en dropdown: SlicerDosim (mod1), SlicerDosimMod2 (mod2), SlicerDosimMod3 (mod3)
- `phantom_segmentation.py` ahora usa TissueConfig en vez de dicts hardcodeados
- `dosimetry.py` ahora usa `mctal_parser.py` real en vez de placeholder
- `__init__.py` y `CMakeLists.txt` actualizados

### Pipeline Orchestrator + Features (COMPLETADO - May 2026)
`test_pipeline_orchestrator.py` mejorado con:

| Feature | Descripcion |
|---|---|
| ✅ **CheckpointManager** | Guarda estado en JSON tras cada paso. Si se corta, al reiniciar retoma desde el ultimo checkpoint. `--reset` para empezar fresco. |
| ✅ **Anonimizacion** | Al cargar DICOM, copia a directorio temporal y limpia tags (PatientName, PatientID, etc) con pydicom. Los nodos en Slicer se renombran. |
| ✅ **Sacar camilla + aire** | Threshold HU>-200 + cierre morfologico + componente conectada mas grande + eliminacion de camilla por corte axial. Aplica mascara al CT. |
| ✅ **Barra de progreso** | QProgressDialog durante TotalSegmentator con pasos y mensaje de "esta funcionando". Tambien muestra progreso en status bar de Slicer. |
| ✅ **Validacion medica** | Dialogo modal Qt con botones SI/NO. No continua sin aprobacion medica explicita. Mensaje claro de lo que se va a generar. |
| ✅ **Git commit prompt** | Al finalizar OK, pregunta si hacer commit. Busca el repo git, hace `git add -A` y `git commit -m "mensaje"`. |
| ✅ **Reporte mejorado** | Muestra tiempos, checkpoints reutilizados, errores, directorios de salida. Retorna bool para control de flujo. |

### Flujo actual del pipeline
```
1. check_slicer       → Verifica Slicer + paths de modulos
2. load_dicom         → Carga CT+PET con DB temporal
3. anonymize          → Anonimiza tags DICOM + renombra nodos
4. remove_couch_air   → Elimina camilla y aire del CT
5. segment_phantom    → TotalSegmentator con QProgressDialog
6. validate_segmentation → ⛔ MEDICO DEBE APROBAR
7. export_nifti       → Exporta a NIfTI
8. generate_mcnp      → Genera entrada MCNP + verifica .i
9. report + commit    → Reporte final + opcion de commit git
```

### PipelineOrchestrator - Estructura modular (NUEVA)
El pipeline de test ahora vive en su propia carpeta con arquitectura promocionable:

```
Testing/PipelineOrchestrator/
├── __init__.py              # Exporta API publica
├── main.py                  # Entry point CLI (argparse + --reset)
├── pipeline.py              # PipelineTestOrchestrator (orquestador)
├── checkpoint.py            # CheckpointManager (estado JSON persistente)
├── anonymize.py             # Anonimizacion DICOM con pydicom
├── couch_remover.py         # Eliminacion camilla + aire (threshold + morfologia)
├── segmentation.py          # TotalSegmentator + barra progreso + phantom sintetico
├── validation.py            # Dialogo Qt de validacion medica obligatoria
├── mcnp_builder.py          # Generacion + verificacion entrada MCNP
├── git_commit.py            # Prompt de commit git al finalizar
└── utils.py                 # Logger, paths, show_progress()
```

`test_pipeline_orchestrator.py` ahora es un wrapper delgado que importa y ejecuta `PipelineOrchestrator.main.main()`.

### Proximo paso promocion
Cuando el orquestador este maduro, mover la carpeta completa a:
```
SlicerDosimLib/orchestrator/    ← parte oficial de la herramienta
```
Y los modulos de Slicer (SlicerDosim, SlicerDosimMod2, SlicerDosimMod3) lo importaran desde ahi.

### Pendiente
- Agregar ruta en Slicer: Edit > Settings > Modules > Additional paths > `...\Modules\Scripted`
- Probar que los 3 modulos aparezcan bajo "3Dosim"
- Ejecutar `test_pipeline_orchestrator.py` dentro de Slicer con datos reales

## Datos de ejecucion (guardados para no repetir)

| Item | Valor |
|---|---|
| **Slicer.exe** | `C:\Users\Sebastian\AppData\Local\slicer.org\Slicer 5.8.1\Slicer.exe` |
| **Paciente 2** | `C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2` |
| **Pipeline entry** | `3DSlicerModule/SlicerDosim/Testing/PipelineOrchestrator/main.py` |
| **Entry legacy** | `3DSlicerModule/SlicerDosim/Testing/Python/test_pipeline_orchestrator.py` |
| **Directorio raiz** | `C:\programas\3Dosim\3Dosim_v_3.14` |
| **Repo git** | En el directorio raiz |
| **Modulos Slicer** | `3DSlicerModule/SlicerDosim/Modules/Scripted/` (SlicerDosim, SlicerDosimMod2, SlicerDosimMod3) |

### Comando para ejecutar el pipeline
```bash
& "C:\Users\Sebastian\AppData\Local\slicer.org\Slicer 5.8.1\Slicer.exe" --python-script "C:\programas\3Dosim\3Dosim_v_3.14\3DSlicerModule\SlicerDosim\Testing\PipelineOrchestrator\main.py" --data-dir "C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2"
```

### Para reiniciar checkpoints
```bash
& "C:\Users\Sebastian\AppData\Local\slicer.org\Slicer 5.8.1\Slicer.exe" --python-script "C:\programas\3Dosim\3Dosim_v_3.14\3DSlicerModule\SlicerDosim\Testing\PipelineOrchestrator\main.py" --data-dir "C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2" --reset
```

## Sesion 17-May 14:00 — Checkpoint (Actualizado)

### Log (sesiones acumuladas)
1. **Refactor externo→interno**:
   - `anonymize.py`: Sin pydicom, solo renombra nodos en escena
   - `pipeline.py`: Sin urllib/exec para MCP
2. **Flags**: `--force-cpu` (default True), `--segmenter {simple|totalsegmentator}`
3. **Screenshots + escenas MRB** por cada paso
4. **Consola interactiva** habilitada por defecto
5. **`ejecutar_pipeline.bat`**: launcher que mata Slicer y ejecuta pipeline
6. **BUG TS CORREGIDO**: `slicer.cli.run()` NO funciona con TS (ScriptedLoadableModule). Solucion: `TotalSegmentatorLogic.process()` directa:
   ```python
   from TotalSegmentator import TotalSegmentatorLogic
   logic = TotalSegmentatorLogic()
   logic.setupPythonRequirements()
   logic.process(inputVolume=ct_node, outputSegmentation=seg_node,
                 fast=True, cpu=True, task="total", interactive=False)
   ```
   **TS FUNCIONA** (probado: 173s, segmentacion completa con 104 organos).
7. **PERSISTENCIA AGREGADA**:
   - Cada paso guarda `data_func()` en checkpoint (nodos, paths, parametros)
   - `_restore_step_state()` restaura nodos al retomar desde checkpoint
   - `pipeline_results.json` en output_dir con historial completo de ejecuciones
8. **ESCENA GUARDADA TRAS CADA PASO**: `.mrb` con timestamp en `scenes/` tras carga_dicom, remove_couch, fusion, anonymize, segment, validate, export_nifti, generate_mcnp
9. **`kill_existing_slicer()` REWRITE**: ahora usa PowerShell `Get-Process`/`Stop-Process` en vez de tasklist (mas robusto, captura cualquier Slicer.exe)
10. **TS MODULE VISIBILITY**: `slicer.util.selectModule("TotalSegmentator")` antes de ejecutar TS para que el usuario vea progreso
11. **VALIDACION MEDICA NO MODAL**: El dialogo ya no bloquea Slicer. El medico puede:
    - Navegar slices axial/sagital/coronal
    - Ocultar PET (slider de opacidad)
    - Rotar vista 3D
    - Examinar segmentacion
    Luego hacer clic en APROBAR o RECHAZAR
12. **INSTRUCCIONES STOP-BEFORE-SEGMENT**: Actualizadas para `TotalSegmentatorLogic.process()` en vez de `slicer.cli.run()`

### Archivos modificados en esta sesion

| Archivo | Cambio |
|---|---|
| `segmentation.py` | `slicer.cli.run()` → `TotalSegmentatorLogic.process()` + switch a modulo TS |
| `validation.py` | Dialogo NO modal con instrucciones para medico, sin bloquear Slicer |
| `pipeline.py` | `_save_scene()` tras cada paso, `data_func` en checkpoints, `_restore_step_state()`, `_save_results_json()`, stop-before-segment actualizado |
| `utils.py` | `kill_existing_slicer()` rewrite con PowerShell |
| `AGENTS.md` | Actualizado |

### Pendiente
- Probar pipeline completo con TS y validacion medica (click SI)
- Confirmar `pipeline_results.json` con historial
- Confirmar que escenas .mrb se guardan tras cada paso
- Probar que `kill_existing_slicer()` cierra otros Slicer (correr con Slicer abierto)
- Si OK, git commit

### Lecciones aprendidas
- `TotalSegmentator` NO es CLI module. NO se usa con `slicer.cli.run()`. API correcta: `TotalSegmentatorLogic.process()`
- Dialogo modal bloquea Slicer → el medico no puede navegar. Solucion: `setModal(False)` + `show()` + `processEvents()` loop
- `tasklist` en Slicer a veces no detecta otros procesos Slicer. `PowerShell Get-Process` es mas confiable
- Guardar escena .mrb tras cada paso es esencial para BD futura y debug
- El pipeline termina despues de validacion medica. Los pasos MCNP se agregaran despues.
- Los screenshots se guardan en `resultados_test/screenshots/` y las escenas en `resultados_test/scenes/`
- `pipeline_results.json` en `resultados_test/` con historial completo de ejecuciones

### Archivos generados/fsdfsdfsdf

| Archivo | Proposito |
|---|---|
| `totalsegmentator_config.jsonc` | Config externa de TS (task, fast, force_cpu, subset, etc.) |
| `phantom_builder.py` | Paso futuro: convertir segmentacion TS → phantom tejidos |
| `source_builder.py` | Paso futuro: definir fuente desde PET |
| `geometry_builder.py` | Paso futuro: construir geometria voxelizada |
| `tally_builder.py` | Paso futuro: configurar detectores MCNP |

### Directorios de salida
- **Screenshots**: `resultados_test/screenshots/` — 6 PNG por ejecucion
- **Escenas MRB**: `resultados_test/scenes/` — 6 .mrb con timestamp
- **Checkpoints**: `resultados_test/.checkpoints/pipeline_checkpoint.json`
- **Historial BD**: `resultados_test/pipeline_results.json` (historial acumulado)

### Comandos
```bash
# Via batch (cierra Slicer automaticamente)
C:\programas\3Dosim\3Dosim_v_3.14\ejecutar_pipeline.bat

# Directo (segmentacion simple - rapido)
& "C:\Users\Sebastian\AppData\Local\slicer.org\Slicer 5.8.1\Slicer.exe" --python-script "C:\programas\3Dosim\3Dosim_v_3.14\3DSlicerModule\SlicerDosim\Testing\PipelineOrchestrator\main.py" --data-dir "C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2" --segmenter simple --reset

# Directo (TotalSegmentator via TotalSegmentatorLogic.process())
& "C:\Users\Sebastian\AppData\Local\slicer.org\Slicer 5.8.1\Slicer.exe" --python-script "C:\programas\3Dosim\3Dosim_v_3.14\3DSlicerModule\SlicerDosim\Testing\PipelineOrchestrator\main.py" --data-dir "C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2" --segmenter totalsegmentator --force-cpu --reset

# Reiniciar checkpoints
& "C:\Users\Sebastian\AppData\Local\slicer.org\Slicer 5.8.1\Slicer.exe" --python-script "C:\programas\3Dosim\3Dosim_v_3.14\3DSlicerModule\SlicerDosim\Testing\PipelineOrchestrator\main.py" --data-dir "C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2" --reset --segmenter simple
```

## Comandos utiles
- `/remember [tag] mensaje` - Guardar progreso en memoria persistente
