# Arquitectura de SlicerDosim

## Visión General

SlicerDosim es una extensión de [3D Slicer](https://www.slicer.org/) que implementa
el pipeline completo de dosimetría 3D para radioembolización hepática con Y-90,
originalmente desarrollado en MATLAB como [3Dosim](3Dosim).

## Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────┐
│                 3D Slicer                            │
│  ┌───────────────────────────────────────────────┐  │
│  │           SlicerDosim Widget (UI)             │  │
│  │  ┌─────┐ ┌──────┐ ┌────┐ ┌────────┐ ┌─────┐  │  │
│  │  │Carga │ │Segm. │ │Reg │ │ MCNP   │ │Anál.│  │  │
│  │  └──┬──┘ └──┬───┘ └──┬─┘ └───┬────┘ └──┬──┘  │  │
│  └─────┼────────┼────────┼───────┼──────────┼─────┘  │
│        ▼        ▼        ▼       ▼          ▼       │
│  ┌───────────────────────────────────────────────┐  │
│  │          SlicerDosimLogic (Orquestador)       │  │
│  └───┬────┬────┬────┬────┬────┬────┬────┬────┬───┘  │
│      │    │    │    │    │    │    │    │    │       │
│      ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼       │
│  ┌────┐┌───┐┌────┐┌──┐┌───┐┌───┐┌──┐┌──┐┌───┐    │
│  │Seg.││Reg││MCNP││Dos││DVH││TCP││NTCP││μ ││Rpt│    │
│  └────┘└───┘└────┘└──┘└───┘└───┘└──┘└──┘└───┘    │
└─────────────────────────────────────────────────────┘
```

## Stack Tecnológico

| Componente | Tecnología |
|---|---|
| Plataforma | 3D Slicer >= 5.0 |
| UI | Qt (PyQt) via `qMRMLWidget` |
| Visualización 3D | VTK / Slicer渲染 |
| Registro | BrainsFit (Slicer), Elastix |
| Segmentación | SegmentEditor, TotalSegmentator, MONAI |
| Monte Carlo | MCNP 6.x externo |
| Análisis | NumPy, SciPy |
| Reportes | ReportLab |

## Flujo del Pipeline

```
DICOM ──► Carga ──► Segmentación ──► Registro ──► MCNP ──► Dosis 3D ──► DVH/TCP/NTCP ──► Reporte
  │                  │               │           │         │              │
  ▼                  ▼               ▼           ▼         ▼              ▼
 Vol. CT          Mascara         PET reg.     Input    Mapa de      Histogramas
 + PET            hígado +       al CT        MCNP     dosis 3D     y métricas
                  tumor                      (.i)      (Gy)         clínicas
```

## Módulos Internos

### `segmentation.py`
- Segmentación hepática y de tumores
- Múltiples métodos: manual, TotalSegmentator, MONAI, threshold
- Cálculo de volúmenes

### `registration.py`
- Registro rígido + afin (BrainsFit)
- Registro no-rígido (Elastix)
- Remuestreo de PET a geometría CT

### `mcnp_generator.py`
- Voxelización de geometría
- Asignación de materiales por UH
- Configuración de fuente PET
- Tallies de dosis (F6, FMESH4)
- Soporte multi-isótopo

### `dosimetry.py`
- Parseo de archivos MCTAL (output MCNP)
- Cálculo de dosis 3D (MCNP + MIRD analítico)
- Convolución con kernel de dosis

### `dvh_analysis.py`
- DVH diferencial y acumulativo
- TCP (modelo logístico)
- NTCP (modelo LKB)
- BED/EQD2
- Micro-dosimetría

### `utils.py`
- Conversión HU → densidad
- Conversión de unidades
- Exportación DICOM → NIfTI
- Reportes PDF

## Dependencias Externas

### Requeridas
- 3D Slicer >= 5.0
- NumPy, SciPy
- Python >= 3.8

### Opcionales
- TotalSegmentator (segmentación por IA)
- MONAI + PyTorch (segmentación U-Net)
- SlicerElastix (registro no-rígido)
- SlicerRT (herramientas RT)
- ReportLab (reportes PDF)
