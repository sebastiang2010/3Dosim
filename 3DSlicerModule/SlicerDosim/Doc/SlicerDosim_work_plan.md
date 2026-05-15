# Plan de Trabajo: SlicerDosim - Módulo de Dosimetría 3D en 3D Slicer

## Resumen Ejecutivo

Migrar el pipeline de dosimetría de 3Dosim (MATLAB) a un módulo nativo de
3D Slicer (Python/C++), aprovechando las capacidades de segmentación,
registro y visualización de Slicer, más herramientas de IA disponibles.

**Duración estimada:** 6-8 meses (desarrollo incremental por fases)
**Equipo recomendado:** 2-3 desarrolladores (1 Slicer/Python, 1 física médica,
1 opcional ML)

---

## Fase 0: Fundación (Mes 1)

### Objetivos
- Configurar entorno de desarrollo 3D Slicer
- Crear esqueleto del módulo funcional
- Establecer CI/CD y tests

### Tareas
| # | Tarea | Esfuerzo |
|---|---|---|
| 0.1 | Instalar 3D Slicer, configurar build environment | 3 días |
| 0.2 | Crear extensión vacía con CMakeLists | 2 días |
| 0.3 | Implementar Widget básico con tabs | 3 días |
| 0.4 | Conectar pipeline lógico (esqueleto) | 3 días |
| 0.5 | Tests unitarios y CI (GitHub Actions) | 3 días |
| 0.6 | Documentación inicial y README | 2 días |

**Entregable:** Módulo instalable en Slicer con UI funcional (botones sin lógica).

---

## Fase 1: Carga y Segmentación (Mes 2)

### Objetivos
- Carga de DICOM / NIfTI
- Segmentación hepática con TotalSegmentator y Segment Editor

### Tareas
| # | Tarea | Esfuerzo |
|---|---|---|
| 1.1 | Integrar lector DICOM de Slicer | 3 días |
| 1.2 | Implementar interfaz de carga con tabla de volúmenes | 4 días |
| 1.3 | Integrar TotalSegmentator (python_api) | 5 días |
| 1.4 | Implementar threshold + region growing (legado) | 4 días |
| 1.5 | Segmentación de tumores (PET threshold + IA) | 5 días |
| 1.6 | Cálculo de volúmenes y estadísticas | 3 días |
| 1.7 | Tests de segmentación con datos sintéticos | 3 días |

**Entregable:** Segmentación funcional del hígado y tumores con 3 métodos.

---

## Fase 2: Registro de Imágenes (Mes 3)

### Objetivos
- Registro CT ↔ PET/SPECT
- Remuestreo a geometría común

### Tareas
| # | Tarea | Esfuerzo |
|---|---|---|
| 2.1 | Integrar BrainsFit (CLI Slicer) | 5 días |
| 2.2 | Integrar Elastix (si disponible) | 5 días |
| 2.3 | Remuestreo de PET a espacio CT | 3 días |
| 2.4 | Validación visual con checkerboard | 2 días |
| 2.5 | Tests de registro con fantomas | 3 días |

**Entregable:** Registro funcional CT-PET con superposición visual.

---

## Fase 3: Generación MCNP (Meses 4-5)

### Objetivos
- Generación de entrada MCNP completa
- Voxelización, materiales, fuente, tallies
- Ejecución y monitoreo

### Tareas
| # | Tarea | Esfuerzo |
|---|---|---|
| 3.1 | Implementar voxelización (repeated structures) | 8 días |
| 3.2 | Tabla de materiales HU → MCNP | 5 días |
| 3.3 | Generación de fuente desde PET | 5 días |
| 3.4 | Configuración de tallies (F6, FMESH4) | 5 días |
| 3.5 | Escribir archivo .i formateado | 3 días |
| 3.6 | Integración con MCNP externo (subprocess) | 5 días |
| 3.7 | Monitoreo de progreso (lectura output) | 3 días |
| 3.8 | Generación para verificación (check_register) | 3 días |
| 3.9 | Generación para validación MIRD (esferas) | 4 días |
| 3.10 | Tests de generación contra archivos conocidos | 5 días |

**Entregable:** Generación de inputs MCNP válidos, ejecutables externamente.

---

## Fase 4: Cálculo de Dosis (Mes 6)

### Objetivos
- Parseo de archivos MCTAL
- Cálculo de dosis 3D en Gy
- Visualización superpuesta

### Tareas
| # | Tarea | Esfuerzo |
|---|---|---|
| 4.1 | Parser MCTAL (binario/texto) | 8 días |
| 4.2 | Conversión a dosis en Gy | 3 días |
| 4.3 | Creación de volumen escalar en Slicer | 3 días |
| 4.4 | Visualización: superposición dosis/CT | 3 días |
| 4.5 | Cálculo MIRD analítico | 3 días |
| 4.6 | Validación contra 3Dosim MATLAB | 5 días |
| 4.7 | Tests con datos de validación | 3 días |

**Entregable:** Mapas de dosis 3D en Slicer, validados contra MATLAB.

---

## Fase 5: Análisis Clínico (Mes 7)

### Objetivos
- DVH diferencial y acumulativo
- TCP / NTCP
- Métricas clínicas (D98, V30, etc.)
- Micro-dosimetría

### Tareas
| # | Tarea | Esfuerzo |
|---|---|---|
| 5.1 | DVH diferencial y acumulativo | 5 días |
| 5.2 | Métricas D98, D70, D50, V30, V20 | 3 días |
| 5.3 | TCP (modelo logístico) | 3 días |
| 5.4 | NTCP (modelo LKB) | 3 días |
| 5.5 | BED/EQD2 | 2 días |
| 5.6 | Micro-dosimetría hepática | 5 días |
| 5.7 | Exportación de gráficos DVH | 3 días |
| 5.8 | Tests contra valores conocidos | 3 días |

**Entregable:** DVH, TCP, NTCP funcionales y exportables.

---

## Fase 6: Reportes y Pulido (Mes 8)

### Objetivos
- Reportes PDF/CSV
- Mejora de UX
- Validación clínica
- Documentación final

### Tareas
| # | Tarea | Esfuerzo |
|---|---|---|
| 6.1 | Generación de reportes PDF | 5 días |
| 6.2 | Exportación CSV de datos | 2 días |
| 6.3 | Mejoras de UI/UX | 5 días |
| 6.4 | Validación con casos clínicos reales | 8 días |
| 6.5 | Corrección de bugs | 5 días |
| 6.6 | Documentación de usuario | 5 días |
| 6.7 | Publicación en Slicer Extension Manager | 3 días |

**Entregable:** Extensión publicada, documentada y validada.

---

## Hitos y Cronograma

```
M1     M2     M3     M4     M5     M6     M7     M8
├──────┼──────┼──────┼──────┼──────┼──────┼──────┼──────┤
│  F0  │  F1  │  F2  │     F3      │  F4  │  F5  │  F6  │
│ Base │ Carga│  Reg │    MCNP     │ Dosis│ Anal │  Pub │
│      │ + Seg│      │             │      │      │      │
```

## Riesgos y Mitigación

| Riesgo | Impacto | Probabilidad | Mitigación |
|---|---|---|---|
| MCNP no instalado en hospitales | Alto | Media | Soporte para kernel de dosis precalculado (sin MCNP) |
| TotalSegmentator requiere GPU | Medio | Alta | Fallback a threshold + segmentación manual |
| Formatos MCTAL cambian entre MCNP versiones | Alto | Baja | Parser modular + tests de regresión |
| Datos DICOM heterogéneos | Medio | Alta | Validación temprana con datos reales |

## Entregables Finales

1. Código fuente en GitHub (público)
2. Extensión publicada en Slicer Extension Manager
3. Documentación de usuario + técnica
4. Tests automatizados
5. Validación contra casos clínicos (n >= 10)
6. Publicación en congreso de física médica (opcional)
