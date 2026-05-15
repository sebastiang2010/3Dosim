"""
Orchestrator de test del pipeline 3Dosim para 3D Slicer.

Uso desde terminal:
  Slicer.exe --python-script test_pipeline_orchestrator.py --data-dir "C:\ruta\datos"

O desde la consola Python de Slicer:
  exec(open("test_pipeline_orchestrator.py").read())

Requiere:
  - 3D Slicer >= 5.0
  - TotalSegmentator extension instalada
  - Directorio con CT + PET en DICOM o NIfTI
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time


def setup_logger():
    logger = logging.getLogger("3DosimTest")
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)-8s %(message)s", datefmt="%H:%M:%S"
    ))
    logger.addHandler(handler)
    return logger


logger = setup_logger()


class PipelineTestOrchestrator:
    """
    Orquesta y verifica el pipeline completo 3Dosim:
      1. Carga de datos (DICOM / NIfTI)
      2. Segmentacion con TotalSegmentator
      3. Mapeo a phantom 3Dosim (indices 1,30,50,80,90,100)
      4. Exportacion de NIfTI
      5. Generacion de entrada MCNP (Modulo 2)
      6. Verificacion del archivo .i
      7. Reporte final
    """

    def __init__(self, data_dir: str):
        self.data_dir = data_dir
        self.ct_dir = os.path.join(data_dir, "CT")
        self.pet_dir = os.path.join(data_dir, "PET")
        self.output_dir = os.path.join(data_dir, "..", "resultados_test")

        self.results = {
            "pasos": [],
            "errores": [],
            "tiempos": {},
        }

    # ==================================================================
    # EJECUCION
    # ==================================================================

    def run(self):
        logger.info("=" * 60)
        logger.info(" PIPELINE TEST ORCHESTRATOR - 3Dosim para 3D Slicer")
        logger.info("=" * 60)
        logger.info(f"Directorio de datos: {self.data_dir}")
        logger.info(f"CT: {self.ct_dir}")
        logger.info(f"PET: {self.pet_dir}")
        logger.info(f"Salida: {self.output_dir}")
        logger.info("")

        # Paso 0: Verificar entorno Slicer
        self._step("Verificando entorno Slicer", self._check_slicer)

        # Paso 1: Cargar DICOM
        self._step("Cargando DICOM", self._load_dicom)

        # Paso 2: Segmentar phantom completo
        self._step("Segmentando phantom (TotalSegmentator)", self._segment_phantom)

        # Paso 3: Exportar NIfTI
        self._step("Exportando phantom a NIfTI", self._export_nifti)

        # Paso 4: Generar entrada MCNP
        self._step("Generando entrada MCNP (Modulo 2)", self._generate_mcnp)

        # Reporte final
        self._report()

    def _step(self, name: str, func):
        logger.info(f"[{len(self.results['pasos'])+1}] {name}...")
        t0 = time.time()
        try:
            func()
            elapsed = time.time() - t0
            logger.info(f"  ✓ Completado en {elapsed:.1f}s")
            self.results["pasos"].append({"nombre": name, "ok": True, "tiempo": elapsed})
            self.results["tiempos"][name] = elapsed
        except Exception as e:
            elapsed = time.time() - t0
            logger.error(f"  ✗ FALLO: {e}")
            self.results["pasos"].append({"nombre": name, "ok": False, "tiempo": elapsed})
            self.results["errores"].append(f"{name}: {e}")

    # ==================================================================
    # PASOS DEL PIPELINE
    # ==================================================================

    def _check_slicer(self):
        """Verifica que estamos dentro de 3D Slicer."""
        try:
            import slicer
            logger.info(f"  Slicer version: {slicer.app.majorVersion}.{slicer.app.minorVersion}")
            logger.info(f"  Python: {sys.version}")
        except ImportError:
            raise RuntimeError("No se detecta 3D Slicer. Ejecutar dentro de Slicer.")

    def _load_dicom(self):
        """Carga DICOM desde los directorios CT y PET."""
        import slicer

        # Verificar directorios
        for d in [self.ct_dir, self.pet_dir]:
            if not os.path.isdir(d):
                raise FileNotFoundError(f"Directorio no encontrado: {d}")

        ct_files = [f for f in os.listdir(self.ct_dir) if f.endswith('.dcm') or f.isdigit()]
        pet_files = [f for f in os.listdir(self.pet_dir) if f.endswith('.dcm') or f.isdigit()]

        logger.info(f"  Archivos CT: {len(ct_files)} en {self.ct_dir}")
        logger.info(f"  Archivos PET: {len(pet_files)} en {self.pet_dir}")

        # Cargar DICOM
        logger.info("  Cargando DICOM (puede tomar varios segundos)...")

        # Usar DICOM browser integrado de Slicer
        # Para DICOM con subdirectorios CT/PET separados:
        # 1. Importar al DICOM database
        # 2. Luego cargar al escenario

        loaded_ct, loaded_pet = False, False

        # Intentar cargar cada serie por separado
        for dir_path, label in [(self.ct_dir, "CT"), (self.pet_dir, "PET")]:
            loaded_nodes = slicer.util.loadVolume(
                dir_path, singleFile=False
            )
            if loaded_nodes:
                nodes = list(loaded_nodes)
                logger.info(f"  {label}: {len(nodes)} nodos cargados")
                if label == "CT":
                    loaded_ct = True
                    self.ct_node = nodes[0]
                else:
                    loaded_pet = True
                    self.pet_node = nodes[0]
            else:
                # Fallback: intentar con DICOM browser
                logger.warning(f"  {label}: loadVolume fallo, intentando DICOM browser...")
                # Crear DICOM database e importar
                dicom_loaded = self._load_dicom_slicer_db(dir_path, label)
                if label == "CT":
                    loaded_ct = dicom_loaded
                else:
                    loaded_pet = dicom_loaded

        if not loaded_ct:
            raise RuntimeError("No se pudo cargar CT desde DICOM")
        if not loaded_pet:
            logger.warning("PET no cargado, se usara fuente uniforme en Modulo 2")

        # Obtener info del CT
        dims = self.ct_node.GetImageData().GetDimensions()
        spacing = self.ct_node.GetSpacing()
        logger.info(f"  CT dimensiones: {dims[0]}x{dims[1]}x{dims[2]}")
        logger.info(f"  CT espaciado: {spacing[0]:.3f}x{spacing[1]:.3f}x{spacing[2]:.3f} mm")

    def _load_dicom_slicer_db(self, dir_path: str, label: str) -> bool:
        """Carga DICOM usando la base de datos de Slicer (fallback)."""
        import slicer
        try:
            # Importar al DICOM database
            dicom_plugin = slicer.modules.dicom.widgetRepresentation().self()
            indexer = slicer.app.dicomIndexer()
            indexer.indexDirectory(str(dir_path))
            db = slicer.dicomDatabase

            # Buscar series cargadas
            series_uids = db.seriesForStudy(db.studies()[0]) if db.studies() else []
            if not series_uids:
                logger.warning(f"  {label}: no se encontraron series en DB")
                return False

            logger.info(f"  {label}: {len(series_uids)} series encontradas en DB")
            return True
        except Exception as e:
            logger.warning(f"  {label}: DICOM browser fallo: {e}")
            return False

    def _segment_phantom(self):
        """Ejecuta segmentacion con TotalSegmentator + mapeo a phantom."""
        import slicer
        from SlicerDosim.SlicerDosimLib import PhantomSegmenter

        segmenter = PhantomSegmenter()

        if not hasattr(self, 'ct_node') or self.ct_node is None:
            raise RuntimeError("CT no cargado, no se puede segmentar")

        logger.info("  Ejecutando TotalSegmentator task='total'...")
        result = segmenter.segment_full_phantom(
            ct_volume_node=self.ct_node,
            pet_volume_node=getattr(self, 'pet_node', None),
            output_dir=self.output_dir,
            detect_tumors_auto=True,
        )

        if "error" in result:
            raise RuntimeError(f"Segmentacion fallo: {result['error']}")

        self.segmentation_node = result.get("segmentation_node")
        self.phantom_path = result.get("phantom_path")

        stats = result.get("stats", {})
        logger.info(f"  ✓ Higado: {stats.get('liver_vol_ml', 0):.0f} ml")
        logger.info(f"  ✓ Tumor: {stats.get('tumor_vol_ml', 0):.0f} ml")
        logger.info(f"  ✓ Pulmon: {stats.get('lung_vol_ml', 0):.0f} ml")
        logger.info(f"  ✓ Hueso: {stats.get('bone_vol_ml', 0):.0f} ml")

        if self.segmentation_node is None:
            raise RuntimeError("No se genero segmentation node")

    def _export_nifti(self):
        """Exporta el phantom a NIfTI para verificacion."""
        import slicer

        if not hasattr(self, 'segmentation_node') or self.segmentation_node is None:
            raise RuntimeError("No hay segmentacion para exportar")

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # Exportar usando el metodo del segmenter
        from SlicerDosim.SlicerDosimLib import PhantomSegmenter
        segmenter = PhantomSegmenter()

        path = segmenter._export_phantom_to_nifti(
            self.segmentation_node, self.ct_node, self.output_dir
        )
        if path and os.path.exists(path):
            size_mb = os.path.getsize(path) / (1024 * 1024)
            logger.info(f"  Phantom exportado: {path} ({size_mb:.1f} MB)")
            self.phantom_nifti_path = path
        else:
            raise RuntimeError("Fallo exportacion a NIfTI")

    def _generate_mcnp(self):
        """Genera entrada MCNP (Modulo 2) y verifica el .i."""
        from SlicerDosim.SlicerDosimLib import MCNPInputGenerator

        generator = MCNPInputGenerator()

        if not hasattr(self, 'ct_node') or self.ct_node is None:
            raise RuntimeError("CT no disponible")

        mcnp_dir = os.path.join(self.output_dir, "mcnp")
        if not os.path.exists(mcnp_dir):
            os.makedirs(mcnp_dir)

        input_path = generator.generate(
            ct_volume_node=self.ct_node,
            pet_volume_node=getattr(self, 'pet_node', None),
            segmentation_node=self.segmentation_node,
            output_dir=mcnp_dir,
            isotope="Y-90",
            n_particles=int(1e7),
            refine_hu=True,
        )

        if not input_path or not os.path.exists(input_path):
            raise RuntimeError("No se genero archivo .i MCNP")

        # Verificar el archivo generado
        self._verify_mcnp_input(input_path)
        self.mcnp_path = input_path

    def _verify_mcnp_input(self, path: str):
        """Verifica que el archivo .i MCNP sea valido."""
        with open(path, "r") as f:
            content = f.read()

        checks = {
            "header": content.startswith("3Dosim"),
            "material_cards": "M" in content,
            "geometry_cards": "RPP" in content,
            "source_cards": "SDEF" in content,
            "tally_cards": "FMESH4" in content,
            "nps_card": "NPS" in content,
            "mode_card": "MODE" in content,
            "has_lattice": "fill" in content,
        }

        all_ok = True
        for check_name, ok in checks.items():
            status = "✓" if ok else "✗"
            if ok:
                logger.info(f"  Verificacion {check_name}: {status}")
            else:
                logger.warning(f"  Verificacion {check_name}: {status}")
                all_ok = False

        line_count = content.count("\n") + 1
        logger.info(f"  Archivo: {line_count} lineas, {len(content)} caracteres")

        if not all_ok:
            raise RuntimeError("Archivo MCNP no paso las verificaciones")

        logger.info("  ✓ Archivo MCNP valido")

    # ==================================================================
    # REPORTE
    # ==================================================================

    def _report(self):
        """Genera reporte final del test."""
        logger.info("")
        logger.info("=" * 60)
        logger.info(" REPORTE FINAL DEL PIPELINE TEST")
        logger.info("=" * 60)
        logger.info("")

        total = len(self.results["pasos"])
        ok = sum(1 for p in self.results["pasos"] if p["ok"])
        fails = total - ok

        logger.info(f"Pasos ejecutados: {total}")
        logger.info(f"Exitosos: {ok}")
        logger.info(f"Fallos: {fails}")

        if fails > 0:
            logger.info("")
            logger.info("ERRORES:")
            for err in self.results["errores"]:
                logger.info(f"  • {err}")

        logger.info("")
        logger.info("TIEMPOS:")
        for paso in self.results["pasos"]:
            status = "✓" if paso["ok"] else "✗"
            logger.info(f"  {status} {paso['nombre']}: {paso['tiempo']:.1f}s")

        logger.info("")
        logger.info(f"Directorios de salida:")
        if hasattr(self, 'phantom_nifti_path'):
            logger.info(f"  Phantom: {self.phantom_nifti_path}")
        if hasattr(self, 'mcnp_path'):
            logger.info(f"  MCNP:    {self.mcnp_path}")
        logger.info(f"  Output:  {self.output_dir}")

        logger.info("")
        logger.info("=" * 60)
        if fails == 0:
            logger.info(" RESULTADO: ✓ TODOS LOS PASOS EXITOSOS")
        else:
            logger.info(f" RESULTADO: {fails}/{total} PASOS FALLARON")
        logger.info("=" * 60)


# ==================================================================
# MAIN
# ==================================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Pipeline test orchestrator para SlicerDosim"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default=r"C:\MAT\3Dosim\pacientes-\pacientes\Paciente_2",
        help="Directorio con subdirectorios CT/ y PET/",
    )
    args = parser.parse_args()

    orchestrator = PipelineTestOrchestrator(args.data_dir)
    orchestrator.run()
