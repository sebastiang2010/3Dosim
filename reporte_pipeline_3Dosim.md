# Reporte de Analisis - Pipeline 3Dosim a 3D Slicer

**Fecha:** 15/05/2026
**Paciente:** Paciente 2 (ID: 4090159)
**Actividad administrada:** 2.22 GBq (Y-90)
**Datos historicos (MATLAB 3Dosim v2.8):** Nov 2022

---

## 1. Datos encontrados

| Directorio | Contenido | Formato |
|---|---|---|
| `CT/` | 171 archivos | DICOM |
| `PET/` | 127 archivos | DICOM |
| `Fusion/` | 1 archivo (48 MB) | Volumen 3D registrado |
| `MAT/` | `3Dosim_MCNP_Y90.i` (vacio), `cont_.i`, `CT.tif`, `Reporte.txt` | Resultados MATLAB |
| `segmentation liver/` | `liver.nii`, `tumor.nii` (89 MB c/u, 512x512x171 vox) | NIfTI |
| `resultados/` | DVH, reportes, isodosis | BMP/TXT/PPTX |
| `dicom/` | 1 archivo | DICOM dir |

**Dimensiones CT:** 512 x 512 x 171 vox, espaciado 0.98 x 0.98 x 1.5 mm

---

## 2. Pipeline 3Dosim (Slicer) - Estado

| Modulo | Componente | Archivo | Estado |
|---|---|---|---|
| **Mod 1** | Carga DICOM | `SlicerDosim.py` | ✅ Implementado |
| **Mod 1** | Segmentacion TS | `phantom_segmentation.py` | ✅ Implementado (usa TissueConfig) |
| **Mod 1** | Registro CT-PET | `registration.py` | ✅ Implementado |
| **Mod 2** | Asignacion materiales | `mcnp_materials.py` | ✅ Implementado |
| **Mod 2** | Geometria LIKE n BUT | `mcnp_geometry.py` | ✅ Implementado |
| **Mod 2** | Fuente PET -> SDEF | `mcnp_source.py` | ✅ Implementado |
| **Mod 2** | Tallies FMESH4/F6 | `mcnp_tallies.py` | ✅ Implementado |
| **Mod 2** | Orquestador MCNP | `mcnp_generator.py` | ✅ Implementado |
| **Mod 3** | Analisis dosimetrico | `SlicerDosimMod3` | ⏸️ Pausado |

### Dependencias del Mod 2

| Dependencia | Tipo | Estado |
|---|---|---|
| `config.py` + `tissue_config.json` | Interna | ✅ 6 tejidos definidos |
| `TissueConfig` singleton | Interna | ✅ Carga unica del JSON |
| `MCNPMaterialMapper` | Interna | ✅ Sin dependencias Slicer |
| `MCNPGeometryBuilder` | Interna | ✅ Sin dependencias Slicer |
| `MCNPSourceBuilder` | Interna (Slicer para PET) | ✅ Fallback uniforme |
| `MCNPTallyBuilder` | Interna | ✅ Sin dependencias Slicer |
| `MCTALParser` | Interna | ✅ Sin dependencias Slicer |

---

## 3. Datos historicos de referencia (MATLAB)

Del `Reporte.txt` (MATLAB 3Dosim v2.8):

| Parametro | Higado sano | Tumor |
|---|---|---|
| Dosis promedio | 13.8 Gy | 208.9 Gy |
| Dosis min | 0 Gy | 0 Gy |
| Dosis max | 902.8 Gy | 887.9 Gy |
| BED promedio | 65.0 Gy-BED | 461.0 Gy-BED |
| EUD | 5.9 Gy | 125.4 Gy |
| Dosis MIRD | 21.8 Gy | 231.6 Gy |
| Volumen | 4247.1 cm³ | 37.2 cm³ |

**Observacion:** El MCNP input original (`3Dosim_MCNP_Y90.i`) esta vacio (0 bytes). La simulacion MCNP no se ejecuto o los archivos se perdieron.

---

## 4. Script de test: `test_pipeline_orchestrator.py`

**Ubicacion:** `Testing/Python/test_pipeline_orchestrator.py`

### Como ejecutar:

```bash
# Opcion 1: Desde terminal
C:/.../Slicer.exe --python-script "C:/.../test_pipeline_orchestrator.py" --data-dir "C:/MAT/3Dosim/pacientes-/pacientes/Paciente_2"

# Opcion 2: Desde Python console de Slicer
exec(open("C:/.../test_pipeline_orchestrator.py").read())
```

### Pasos del test:

| # | Paso | Que verifica |
|---|---|---|
| 0 | Entorno Slicer | Version, Python |
| 1 | Carga DICOM | CT + PET, dimensiones |
| 2 | Segmentacion TS | Phantom indices, volumenes |
| 3 | Export NIfTI | Archivo .nii.gz valido |
| 4 | Generacion MCNP | .i con M, RPP, SDEF, FMESH4, NPS |
| 5 | Verificacion .i | 8 checks de formato |

### Salida esperada:

```
[00:00] ============================================================
[00:00]  PIPELINE TEST ORCHESTRATOR - 3Dosim para 3D Slicer
[00:00] ============================================================
[00:00] CT dimensiones: 512x512x171
[00:00] CT espaciado: 0.977x0.977x1.500 mm
[00:05] [1] Cargando DICOM... ✓
[02:30] [2] Segmentando phantom (TotalSegmentator)... ✓
[02:31] [3] Exportando phantom a NIfTI... ✓
[02:32] [4] Generando entrada MCNP (Modulo 2)... ✓
[02:32]   Verificacion header: ✓
[02:32]   Verificacion material_cards: ✓
[02:32]   Verificacion geometry_cards: ✓
[02:32]   Verificacion source_cards: ✓
[02:32]   Verificacion tally_cards: ✓
[02:32]   Verificacion nps_card: ✓
[02:32]   Verificacion mode_card: ✓
[02:32]   Verificacion has_lattice: ✓
[02:32] RESULTADO: ✓ TODOS LOS PASOS EXITOSOS
```

---

## 5. Archivos creados/modificados

| Archivo | Tipo | Descripcion |
|---|---|---|
| `Testing/Python/test_pipeline_orchestrator.py` | **NUEVO** | Orchestrator de test automatico |
| `reporte_pipeline_3Dosim.md` | **NUEVO** | Este reporte |

---

## 6. Proximo paso recomendado

Ejecutar el orchestrator dentro de 3D Slicer:

```bash
"C:\Program Files\Slicer 5.6\Slicer.exe" --python-script ^
  "C:\programas\3Dosim\3Dosim_v_3.14\3DSlicerModule\SlicerDosim\Testing\Python\test_pipeline_orchestrator.py" ^
  --data-dir "C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2"
```

Luego de eso:
- Si pasa OK → el pipeline Mod1+Mod2 esta funcional con datos reales
- Si falla → revisar el error reportado y corregir
