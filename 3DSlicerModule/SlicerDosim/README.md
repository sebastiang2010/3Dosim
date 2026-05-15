# SlicerDosim - Dosimetría 3D para Radioembolización Hepática

Extensión de [3D Slicer](https://www.slicer.org/) para el pipeline completo de
dosimetría en radioembolización con **Y-90** (y otros isotopos).

Basado en el software **3Dosim** (original en MATLAB, desarrollado para el
Instituto de Medicina Nuclear).

## Características

- **Carga de imágenes:** DICOM (CT + PET/SPECT) y NIfTI
- **Segmentación hepática:** Segment Editor manual, TotalSegmentator (IA),
  threshold + region growing
- **Registro:** CT ↔ PET/SPECT (BrainsFit, Elastix)
- **Generación MCNP:** Entrada voxelizada con materiales, fuente PET y tallies
- **Cálculo de dosis:** Procesamiento de output MCNP (MCTAL) + método MIRD
- **Análisis:** DVH, TCP, NTCP, BED/EQD2, micro-dosimetría
- **Reportes:** Exportación a PDF/CSV

## Requerimientos

| Software | Versión |
|---|---|
| 3D Slicer | >= 5.0 |
| Python | >= 3.8 |
| NumPy | >= 1.20 |
| SciPy | >= 1.7 |

### Opcionales
- [TotalSegmentator](https://github.com/wasserth/TotalSegmentator)
  (segmentación por IA, requiere GPU)
- [MONAI](https://monai.io/) + PyTorch (segmentación U-Net)
- [SlicerElastix](https://github.com/SlicerElastix/SlicerElastix)
  (registro no-rígido)
- MCNP 6.x (simulación Monte Carlo)
- ReportLab (reportes PDF)

## Instalación

### Desde Slicer Extension Manager (cuando esté publicado)
1. Abrir 3D Slicer
2. Ir a *View → Extension Manager*
3. Buscar "SlicerDosim"
4. Click *Install*

### Desde fuente
```bash
git clone https://github.com/example/SlicerDosim.git
cd SlicerDosim
mkdir build && cd build
cmake -DSlicer_DIR:PATH=/path/to/Slicer-SuperBuild/Slicer-build ..
cmake --build .
```

## Uso Rápido

1. Abrir **3D Slicer**
2. Ir a *Modules → Radiotherapy → SlicerDosim*
3. **Pestaña 1:** Cargar DICOM → Segmentar hígado y tumores
4. **Pestaña 2:** Registrar PET contra CT
5. **Pestaña 3:** Generar input MCNP → Ejecutar MCNP externamente
6. **Pestaña 4:** Cargar MCTAL → Calcular dosis 3D
7. **Pestaña 5:** Calcular DVH/TCP/NTCP → Exportar reporte

## Estructura del Proyecto

```
SlicerDosim/
├── CMakeLists.txt
├── README.md
├── LICENSE
├── Modules/
│   └── Scripted/
│       └── SlicerDosim/
│           ├── __init__.py
│           ├── SlicerDosim.py          # Módulo principal
│           ├── SlicerDosimLib/         # Librería interna
│           │   ├── segmentation.py     # Segmentación hepática
│           │   ├── registration.py     # Registro de imágenes
│           │   ├── mcnp_generator.py   # Generación MCNP
│           │   ├── dosimetry.py        # Cálculo de dosis
│           │   ├── dvh_analysis.py     # DVH/TCP/NTCP
│           │   └── utils.py            # Utilidades
│           └── Resources/
│               └── UI/
│                   ├── SlicerDosim.ui  # Interfaz de usuario
│                   └── Icons/
├── Testing/
├── Doc/
└── Resources/
```

## Licencia

Este proyecto está bajo licencia MIT. Ver `LICENSE` para más detalles.

## Créditos

- Desarrollado a partir de **3Dosim** (MATLAB)
- Instituto de Medicina Nuclear
