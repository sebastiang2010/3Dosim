"""
SlicerDosim - Modulo de dosimetria 3D para radioembolizacion hepatica.

Integra en 3D Slicer el pipeline completo de 3Dosim:
  1. Carga DICOM / NIfTI + Segmentacion IA (TotalSegmentator)
  2. Registro CT-PET/SPECT
  3. Generacion de entrada MCNP (Monte Carlo)
  4. Calculo de dosis 3D (MCNP + MIRD)
  5. Analisis DVH / TCP / NTCP
  6. Reportes

Requerimientos:
  - 3D Slicer (>= 5.0)
  - Extensiones: TotalSegmentator, SegmentEditorExtraEffects
  - Opcional: MONAI Auto3DSeg, PETTumorSegmentation
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import qt
import slicer
from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
    ScriptedLoadableModuleWidget,
    ScriptedLoadableModuleLogic,
    ScriptedLoadableModuleTest,
)

from .SlicerDosimLib import (
    LiverSegmenter,
    DosimetryRegistration,
    MCNPInputGenerator,
    DoseCalculator,
    DVHAnalyzer,
    SlicerDosimUtils,
    PhantomSegmenter,
)


# ============================================================================
# MODULO PRINCIPAL
# ============================================================================
class SlicerDosim(ScriptedLoadableModule):
    """Registra el modulo en 3D Slicer."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title = "SlicerDosim"
        self.description = (
            "Dosimetria 3D para radioembolizacion hepatica (Y-90). "
            "Segmentacion IA, registro, MCNP, DVH, TCP/NTCP."
        )
        self.categories = ["3Dosim"]
        self.contributors = ["3Dosim Team"]
        self.homepage = "https://github.com/example/SlicerDosim"
        self.acknowledgementText = "Basado en 3Dosim (MATLAB) - Dosimetria 3D"


# ============================================================================
# LOGICA DE NEGOCIO
# ============================================================================
class SlicerDosimLogic(ScriptedLoadableModuleLogic):
    """Logica del modulo. Orquesta los sub-modulos especializados."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger(__name__)

        # Sub-modulos
        self.segmenter = LiverSegmenter()
        self.phantom_segmenter = PhantomSegmenter()
        self.registration = DosimetryRegistration()
        self.mcnp_gen = MCNPInputGenerator()
        self.dose_calc = DoseCalculator()
        self.dvh_analyzer = DVHAnalyzer()
        self.utils = SlicerDosimUtils()

        # Estado del pipeline
        self.pipeline_state = {
            "ct_loaded": False,
            "pet_loaded": False,
            "liver_segmented": False,
            "tumor_segmented": False,
            "tumor_detected_auto": False,
            "phantom_ready": False,
            "registered": False,
            "mcnp_generated": False,
            "dose_calculated": False,
            "dvh_computed": False,
        }

        # Nodos almacenados
        self.nodes = {
            "ct": None,
            "pet": None,
            "liver_seg": None,
            "tumor_seg": None,
            "phantom_seg": None,
            "dose_3d": None,
            "pet_registered": None,
        }

        self.mctal_path = None

    # ------------------------------------------------------------------
    # CARGA DE DATOS
    # ------------------------------------------------------------------
    def load_dicom(self, dicom_dir: str) -> bool:
        """Carga volumenes desde directorio DICOM."""
        try:
            loaded_nodes = slicer.util.loadVolume(dicom_dir, singleFile=False)
            if loaded_nodes:
                self.nodes["ct"] = loaded_nodes[0]
                self.pipeline_state["ct_loaded"] = True
                if len(loaded_nodes) > 1:
                    self.nodes["pet"] = loaded_nodes[1]
                    self.pipeline_state["pet_loaded"] = True
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error cargando DICOM: {e}")
            return False

    def load_nifti(self, file_path: str) -> str:
        """
        Carga un archivo NIfTI y determina si es CT o PET
        por el nombre del archivo.

        Returns:
            'ct', 'pet', o 'unknown'
        """
        try:
            node = slicer.util.loadNodeFromFile(file_path, "NiftiFile")
            if node is None:
                return "unknown"

            fname = os.path.basename(file_path).upper()
            if "CT" in fname or "CT_" in fname:
                self.nodes["ct"] = node
                self.pipeline_state["ct_loaded"] = True
                return "ct"
            elif "PET" in fname or "PET_" in fname or "PT" in fname:
                self.nodes["pet"] = node
                self.pipeline_state["pet_loaded"] = True
                return "pet"
            else:
                # Si no hay CT cargado, asumir CT
                if not self.pipeline_state["ct_loaded"]:
                    self.nodes["ct"] = node
                    self.pipeline_state["ct_loaded"] = True
                    return "ct"
                return "unknown"
        except Exception as e:
            self.logger.error(f"Error cargando NIfTI: {e}")
            return "unknown"

    # ------------------------------------------------------------------
    # PIPELINE COMPLETO DE SEGMENTACION
    # ------------------------------------------------------------------
    def segment_full_phantom(
        self,
        pet_volume_node=None,
        suv_threshold: float = 2.5,
        output_dir: Optional[str] = None,
        detect_tumors_auto: bool = True,
    ) -> dict:
        """
        Ejecuta el pipeline completo:
          1. TotalSegmentator task="total" (cuerpo completo, 104 clases)
          2. Mapeo de labels TS -> phantom 3Dosim (1,30,50,80,90)
          3. TotalSegmentator task="liver_lesions" (tumores, si detect_tumors_auto=True)
          4. Estadisticas volumetricas

        Args:
            pet_volume_node: (reservado para futuro)
            suv_threshold: (reservado para futuro)
            output_dir: directorio para exportar NIfTI (opcional)
            detect_tumors_auto: si True, detecta tumores con liver_lesions de TS

        Returns:
            dict con resultados del pipeline
        """
        if not self.pipeline_state["ct_loaded"] or self.nodes["ct"] is None:
            return {"error": "No hay CT cargado"}

        result = self.phantom_segmenter.segment_full_phantom(
            ct_volume_node=self.nodes["ct"],
            pet_volume_node=pet_volume_node or self.nodes.get("pet"),
            suv_threshold=suv_threshold,
            output_dir=output_dir,
            detect_tumors_auto=detect_tumors_auto,
        )

        if result.get("segmentation_node"):
            self.nodes["phantom_seg"] = result["segmentation_node"]
            self.pipeline_state["phantom_ready"] = True
            self.nodes["liver_seg"] = result["segmentation_node"]
            self.pipeline_state["liver_segmented"] = True
            if result.get("tumor_vol_ml", 0) > 0:
                self.pipeline_state["tumor_segmented"] = True
                self.pipeline_state["tumor_detected_auto"] = True

        return result

    def segment_tumor_guided(self):
        """
        Abre el Segment Editor para segmentacion manual guiada del tumor.
        Usa PET como overlay si esta disponible.
        """
        if not self.pipeline_state["phantom_ready"]:
            self.logger.warning("Segmente el higado primero (pipeline completo)")
            return False

        self.phantom_segmenter.open_tumor_segmentation_guide(
            self.nodes["ct"], self.nodes["phantom_seg"]
        )
        return True

    # ------------------------------------------------------------------
    # SEGMENTACION INDIVIDUAL
    # ------------------------------------------------------------------
    def segment_liver(self, method: str = "totalsegmentator") -> bool:
        """Segmenta el higado."""
        if not self.pipeline_state["ct_loaded"]:
            self.logger.warning("No hay CT cargado")
            return False

        seg = self.segmenter.segment_liver(self.nodes["ct"], method=method)
        if seg:
            self.nodes["liver_seg"] = seg
            self.pipeline_state["liver_segmented"] = True
            return True
        return False

    def segment_tumor(
        self,
        method: str = "pet_suv",
        suv_threshold: float = 2.5,
    ) -> bool:
        """Segmenta tumores hepaticos."""
        seg = self.segmenter.segment_tumors(
            ct_volume_node=self.nodes.get("ct"),
            liver_segmentation_node=self.nodes.get("liver_seg"),
            pet_volume_node=self.nodes.get("pet") or self.nodes.get("pet_registered"),
            method=method,
            suv_threshold=suv_threshold,
        )
        if seg:
            self.nodes["tumor_seg"] = seg
            self.pipeline_state["tumor_segmented"] = True
            return True
        return False

    def load_liver_nifti(self) -> bool:
        """Carga segmentacion hepatica desde NIfTI externo."""
        seg = self.segmenter.load_nifti_as_segmentation("liver")
        if seg:
            self.nodes["liver_seg"] = seg
            self.pipeline_state["liver_segmented"] = True
            return True
        return False

    def load_tumor_nifti(self) -> bool:
        """Carga segmentacion tumoral desde NIfTI externo."""
        seg = self.segmenter.load_nifti_as_segmentation("tumor")
        if seg:
            self.nodes["tumor_seg"] = seg
            self.pipeline_state["tumor_segmented"] = True
            return True
        return False

    # ------------------------------------------------------------------
    # REGISTRO
    # ------------------------------------------------------------------
    def register_images(self, method: str = "brainsfit") -> bool:
        """Registra PET contra CT."""
        if not all([self.nodes["ct"], self.nodes["pet"]]):
            self.logger.warning("CT y PET necesarios para registro")
            return False
        result = self.registration.register(
            self.nodes["ct"], self.nodes["pet"], method=method
        )
        if result:
            self.nodes["pet_registered"] = result
            self.pipeline_state["registered"] = True
            return True
        return False

    # ------------------------------------------------------------------
    # MCNP
    # ------------------------------------------------------------------
    def generate_mcnp(
        self, output_dir: str, isotope: str = "Y-90"
    ) -> Optional[str]:
        """Genera archivo de entrada MCNP."""
        if not all([
            self.nodes["ct"],
            self.nodes["pet"],
            self.nodes["liver_seg"],
        ]):
            self.logger.warning("Faltan datos para generar MCNP")
            return None

        input_path = self.mcnp_gen.generate(
            ct_volume_node=self.nodes["ct"],
            pet_volume_node=self.nodes["pet"],
            segmentation_node=self.nodes["liver_seg"],
            output_dir=output_dir,
            isotope=isotope,
        )
        if input_path:
            self.pipeline_state["mcnp_generated"] = True
        return input_path

    # ------------------------------------------------------------------
    # DOSIS
    # ------------------------------------------------------------------
    def compute_dose(self, mctal_path: str, activity_gbq: float) -> bool:
        """Calcula dosis 3D desde MCTAL."""
        mctal_data = self.dose_calc.load_mctal(mctal_path)
        dose_node = self.dose_calc.compute_dose_3d(
            mctal_data, self.nodes["ct"], activity_gbq
        )
        if dose_node:
            self.nodes["dose_3d"] = dose_node
            self.pipeline_state["dose_calculated"] = True
            return True
        return False

    def compute_dvh(self, structure_name: str = "liver") -> dict:
        """Calcula DVH para una estructura."""
        if not self.pipeline_state["dose_calculated"]:
            return {}

        seg_node = self.nodes.get("phantom_seg") or self.nodes.get(f"{structure_name}_seg")
        if not seg_node:
            return {}

        return self.dvh_analyzer.compute_dvh(
            self.nodes["dose_3d"], seg_node, structure_name
        )

    # ------------------------------------------------------------------
    # LIMPIEZA
    # ------------------------------------------------------------------
    def clear(self):
        """Limpia toda la sesion."""
        for node in self.nodes.values():
            if node:
                try:
                    slicer.mrmlScene.RemoveNode(node)
                except Exception:
                    pass
        self.nodes = {
            "ct": None, "pet": None, "liver_seg": None,
            "tumor_seg": None, "phantom_seg": None,
            "dose_3d": None, "pet_registered": None,
        }
        self.pipeline_state = {k: False for k in self.pipeline_state}
        self.pipeline_state["tumor_detected_auto"] = False
        self.mctal_path = None


# ============================================================================
# INTERFAZ DE USUARIO
# ============================================================================
class SlicerDosimWidget(ScriptedLoadableModuleWidget):
    """Widget principal del modulo SlicerDosim."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.logic = SlicerDosimLogic()
        self.logger = logging.getLogger(__name__)

    def setup(self):
        """Configura la interfaz de usuario."""
        super().setup()

        # Cargar layout desde archivo UI
        ui_path = os.path.join(
            os.path.dirname(__file__), "Resources", "UI", "SlicerDosim.ui"
        )
        if os.path.exists(ui_path):
            self.ui = slicer.util.loadUI(ui_path)
            self.layout.addWidget(self.ui)
        else:
            self.logger.warning(f"UI no encontrado: {ui_path}")
            self._build_fallback_ui()

        self._connect_signals()
        self._update_ui_state()

    def _build_fallback_ui(self):
        """Construye UI basica por si falla la carga del .ui."""
        from slicer.util import VTKWidget
        vtk_widget = VTKWidget()
        self.layout.addWidget(vtk_widget)

    def _connect_signals(self):
        """Conecta eventos de UI a los handlers."""
        try:
            self.ui.btnCargarDicom.connect("clicked()", self._on_cargar_dicom)
            self.ui.btnCargarNifti.connect("clicked()", self._on_cargar_nifti)
            self.ui.btnSegmentarHigado.connect("clicked()", self._on_segmentar_higado)
            self.ui.btnSegmentarTumor.connect("clicked()", self._on_segmentar_tumor)
            self.ui.btnPipelineCompleto.connect("clicked()", self._on_pipeline_completo)
            self.ui.btnPipelineConTumor.connect("clicked()", self._on_pipeline_con_tumor)
            self.ui.btnSegmentarTumorGuiado.connect("clicked()", self._on_segmentar_tumor_guiado)
            self.ui.btnCargarNiftiHigado.connect("clicked()", self._on_cargar_nifti_higado)
            self.ui.btnCargarNiftiTumor.connect("clicked()", self._on_cargar_nifti_tumor)
            self.ui.btnEjecutarRegistro.connect("clicked()", self._on_ejecutar_registro)
            self.ui.btnGenerarMCNP.connect("clicked()", self._on_generar_mcnp)
            self.ui.btnEjecutarMCNP.connect("clicked()", self._on_ejecutar_mcnp)
            self.ui.btnCargarMCTAL.connect("clicked()", self._on_cargar_mctal)
            self.ui.btnCalcularDosis.connect("clicked()", self._on_calcular_dosis)
            self.ui.btnCalcularMIRD.connect("clicked()", self._on_calcular_mird)
            self.ui.btnCalcularDVH.connect("clicked()", self._on_calcular_dvh)
            self.ui.btnCalcularTCP.connect("clicked()", self._on_calcular_tcp)
            self.ui.btnCalcularNTCP.connect("clicked()", self._on_calcular_ntcp)
            self.ui.btnMicroDosimetria.connect("clicked()", self._on_micro_dosimetria)
            self.ui.btnVisualizarDosis.connect("clicked", self._on_visualizar_dosis)
            self.ui.btnExportarReporte.connect("clicked()", self._on_exportar_reporte)
        except AttributeError as e:
            self.logger.error(f"Error conectando senales UI: {e}")

    # ------------------------------------------------------------------
    # HANDLERS
    # ------------------------------------------------------------------
    def _on_cargar_dicom(self):
        """Cargar DICOM."""
        dir_path = qt.QFileDialog.getExistingDirectory(
            self.parent, "Seleccionar directorio DICOM"
        )
        if dir_path:
            slicer.util.showStatusMessage("Cargando DICOM...", 3000)
            success = self.logic.load_dicom(dir_path)
            if success:
                slicer.util.showStatusMessage("DICOM cargado exitosamente", 3000)
            else:
                slicer.util.errorDisplay("Error cargando DICOM")
            self._update_ui_state()

    def _on_cargar_nifti(self):
        """Cargar NIfTI."""
        file_path = qt.QFileDialog.getOpenFileName(
            self.parent, "Seleccionar NIfTI", "", "NIfTI (*.nii *.nii.gz)"
        )
        if file_path:
            result = self.logic.load_nifti(file_path)
            if result != "unknown":
                slicer.util.showStatusMessage(
                    f"NIfTI cargado como {result.upper()}", 3000
                )
            else:
                slicer.util.showStatusMessage("NIfTI cargado (tipo no detectado)", 3000)
            self._update_ui_state()

    def _on_segmentar_higado(self):
        """Segmentar higado con el metodo seleccionado."""
        method_idx = self.ui.comboMetodoSeg.currentIndex
        method_map = {
            0: "segment_editor",
            1: "totalsegmentator",
            2: "monai_unet",
            3: "threshold_region",
        }
        method = method_map.get(method_idx, "totalsegmentator")

        slicer.util.showStatusMessage(f"Segmentando higado ({method})...", 5000)
        success = self.logic.segment_liver(method=method)
        if success:
            slicer.util.showStatusMessage("Higado segmentado exitosamente", 3000)
        else:
            slicer.util.errorDisplay(
                "Error en segmentacion. Verifique que TotalSegmentator este instalado "
                "(Extension Manager -> TotalSegmentator)."
            )
        self._update_ui_state()

    def _on_segmentar_tumor(self):
        """Segmentar tumor por PET SUV."""
        suv = float(self.ui.spinSUVThreshold.value) if hasattr(self.ui, 'spinSUVThreshold') else 2.5

        slicer.util.showStatusMessage(f"Segmentando tumor (SUV > {suv})...", 5000)
        success = self.logic.segment_tumor(method="pet_suv", suv_threshold=suv)
        if success:
            slicer.util.showStatusMessage("Tumor segmentado por SUV", 3000)
        else:
            slicer.util.warningDisplay(
                "No se detecto tumor. Pruebe con un umbral SUV menor "
                "o cargue una segmentacion manual (NIfTI)."
            )
        self._update_ui_state()

    def _on_pipeline_completo(self):
        """
        Ejecuta el pipeline de segmentacion SIN deteccion automatica de tumores:
        TotalSegmentator -> Phantom (solo higado, pulmon, hueso, blando, aire).
        El tumor se segmenta manualmente despues.
        """
        slicer.util.showStatusMessage(
            "Pipeline basico: TotalSegmentator + Phantom...", 10000
        )
        self.logger.info("=== PIPELINE BASICO (sin deteccion de tumores) ===")

        result = self.logic.segment_full_phantom(
            suv_threshold=2.5,
            detect_tumors_auto=False,
        )

        if result.get("segmentation_node"):
            msg = (
                "Pipeline basico completado:\n"
                f"  Higado: {result.get('liver_vol_ml', 0):.0f} ml\n"
            )
            stats = result.get("stats", {})
            for key, val in stats.items():
                if val > 0:
                    name = key.replace("_vol_ml", "").replace("_", " ")
                    msg += f"  {name.title()}: {val:.0f} ml\n"
            msg += "\nAhora segmente el tumor manualmente."

            if hasattr(self.ui, 'txtReporte'):
                self.ui.txtReporte.append(msg)

            if result["segmentation_node"]:
                slicer.util.setSliceViewerLayers(
                    background=self.logic.nodes.get("ct"),
                )
            self.logger.info(f"\n{msg}")
        else:
            error = result.get("error", "Error desconocido")
            slicer.util.errorDisplay(
                f"Pipeline fallo: {error}\n"
                "Verifique que TotalSegmentator este instalado."
            )

        self._update_ui_state()

    def _on_pipeline_con_tumor(self):
        """
        Pipeline COMPLETO con deteccion automatica de tumores:
        TotalSegmentator task='total' + task='liver_lesions'.
        Detecta lesiones hepaticas automaticamente desde el CT.
        """
        slicer.util.showStatusMessage(
            "Pipeline completo con deteccion IA de tumores...", 15000
        )
        self.logger.info("=== PIPELINE COMPLETO (con deteccion de tumores) ===")

        result = self.logic.segment_full_phantom(
            suv_threshold=2.5,
            detect_tumors_auto=True,
        )

        if result.get("segmentation_node"):
            msg = (
                "Pipeline completo con deteccion IA:\n"
                f"  Higado: {result.get('liver_vol_ml', 0):.0f} ml\n"
                f"  Tumor automatico: {result.get('tumor_vol_ml', 0):.0f} ml\n"
            )
            stats = result.get("stats", {})
            for key, val in stats.items():
                if val > 0:
                    name = key.replace("_vol_ml", "").replace("_", " ")
                    msg += f"  {name.title()}: {val:.0f} ml\n"
            msg += "\nRevise la segmentacion con el Segment Editor."

            if hasattr(self.ui, 'txtReporte'):
                self.ui.txtReporte.append(msg)

            if result["segmentation_node"]:
                slicer.util.setSliceViewerLayers(
                    background=self.logic.nodes.get("ct"),
                )
            self.logger.info(f"\n{msg}")
        else:
            error = result.get("error", "Error desconocido")
            slicer.util.errorDisplay(
                f"Pipeline fallo: {error}\n"
                "Verifique TotalSegmentator (task liver_lesions requiere "
                "TS version >= 2.0)."
            )

        self._update_ui_state()

    def _on_segmentar_tumor_guiado(self):
        """
        Abre el Segment Editor y guia al usuario para segmentar
        el tumor manualmente. Muestra PET como overlay si existe.
        """
        if not self.logic.pipeline_state.get("phantom_ready"):
            slicer.util.warningDisplay(
                "Ejecute el pipeline completo primero para segmentar "
                "higado, pulmones y huesos."
            )
            return

        self.logger.info("Abriendo Segment Editor para segmentacion guiada del tumor...")
        self.logic.segment_tumor_guided()

    def _on_cargar_nifti_higado(self):
        """Cargar segmentacion hepatica desde NIfTI externo."""
        success = self.logic.load_liver_nifti()
        if success:
            slicer.util.showStatusMessage("Higado cargado desde NIfTI", 3000)
        self._update_ui_state()

    def _on_cargar_nifti_tumor(self):
        """Cargar segmentacion tumoral desde NIfTI externo."""
        success = self.logic.load_tumor_nifti()
        if success:
            slicer.util.showStatusMessage("Tumor cargado desde NIfTI", 3000)
        self._update_ui_state()

    def _on_ejecutar_registro(self):
        """Ejecutar registro CT-PET."""
        method_idx = self.ui.comboMetodoReg.currentIndex
        method = "brainsfit" if method_idx == 0 else "elastix"

        slicer.util.showStatusMessage(f"Registrando ({method})...", 10000)
        success = self.logic.register_images(method=method)
        if success:
            slicer.util.showStatusMessage("Registro completado", 3000)
        else:
            slicer.util.errorDisplay(
                "Error en registro. Asegurese de tener CT y PET cargados."
            )
        self._update_ui_state()

    def _on_generar_mcnp(self):
        """Generar entrada MCNP."""
        output_dir = qt.QFileDialog.getExistingDirectory(
            self.parent, "Directorio para archivos MCNP"
        )
        if output_dir:
            isotope = self.ui.comboIsotopo.currentText
            slicer.util.showStatusMessage("Generando entrada MCNP...", 5000)
            input_path = self.logic.generate_mcnp(output_dir, isotope)
            if input_path:
                slicer.util.showStatusMessage(f"MCNP generado: {input_path}", 5000)
            else:
                slicer.util.errorDisplay("Error generando MCNP")

    def _on_ejecutar_mcnp(self):
        """Ejecutar MCNP externo."""
        slicer.util.showStatusMessage(
            "Ejecutar MCNP manualmente desde la terminal", 5000
        )

    def _on_cargar_mctal(self):
        """Cargar archivo MCTAL."""
        file_path = qt.QFileDialog.getOpenFileName(
            self.parent, "Seleccionar MCTAL", "", "MCTAL (*.mctal);;All (*)"
        )
        if file_path:
            self.logic.mctal_path = file_path
            slicer.util.showStatusMessage(f"MCTAL cargado: {file_path}", 3000)
            self._update_ui_state()

    def _on_calcular_dosis(self):
        """Calcular dosis 3D."""
        activity, ok = qt.QInputDialog.getDouble(
            self.parent, "Actividad", "Actividad (GBq):", 1.0, 0.01, 100.0, 2
        )
        if ok and self.logic.mctal_path:
            slicer.util.showStatusMessage("Calculando dosis 3D...", 10000)
            self.logic.compute_dose(self.logic.mctal_path, activity)
            slicer.util.showStatusMessage("Dosis calculada", 3000)
        self._update_ui_state()

    def _on_calcular_mird(self):
        """Calculo MIRD."""
        liver_vol = self.logic.pipeline_state.get("liver_vol_ml", 1500.0)
        tumor_vol = self.logic.pipeline_state.get("tumor_vol_ml", 100.0)

        mird = self.logic.dose_calc.compute_mird(
            liver_volume_ml=liver_vol if liver_vol > 0 else 1500.0,
            tumor_volume_ml=tumor_vol if tumor_vol > 0 else 100.0,
        )
        msg = (
            f"MIRD: Actividad = {mird['activity_gbq']:.2f} GBq, "
            f"D_higado = {mird['liver_dose_gy']:.1f} Gy"
        )
        slicer.util.showStatusMessage(msg, 5000)
        self.ui.txtReporte.append(msg)

    def _on_calcular_dvh(self):
        """Calcular DVH."""
        dvh = self.logic.compute_dvh("liver")
        if dvh:
            msg = (
                f"DVH: D_mean = {dvh.get('d_mean_gy', 0):.1f} Gy, "
                f"D70 = {dvh.get('d70_gy', 0):.1f} Gy"
            )
            self.ui.txtReporte.append(msg)
        else:
            slicer.util.warningDisplay("Calcule la dosis primero")

    def _on_calcular_tcp(self):
        """Calcular TCP."""
        tcp_result = self.logic.dvh_analyzer.compute_tcp(
            self.logic.nodes.get("dose_3d"),
            self.logic.nodes.get("tumor_seg"),
        )
        self.ui.txtReporte.append(
            f"TCP = {tcp_result.get('tcp', 0)*100:.1f}%"
        )

    def _on_calcular_ntcp(self):
        """Calcular NTCP."""
        ntcp_result = self.logic.dvh_analyzer.compute_ntcp(
            self.logic.nodes.get("dose_3d"),
            self.logic.nodes.get("liver_seg"),
        )
        self.ui.txtReporte.append(
            f"NTCP = {ntcp_result.get('ntcp', 0)*100:.1f}%"
        )

    def _on_micro_dosimetria(self):
        """Dosimetria de microestructuras."""
        micro = self.logic.dvh_analyzer.compute_micro_dosimetry(
            self.logic.nodes.get("dose_3d"),
            self.logic.nodes.get("liver_seg"),
        )
        self.ui.txtReporte.append(
            f"Micro-dosis: media = {micro.get('d_micro_mean_gy', 0):.1f} Gy"
        )

    def _on_visualizar_dosis(self):
        """Visualizar mapa de dosis."""
        dose_node = self.logic.nodes.get("dose_3d")
        ct_node = self.logic.nodes.get("ct")
        if dose_node and ct_node:
            slicer.util.setSliceViewerLayers(
                background=ct_node,
                foreground=dose_node,
                foregroundOpacity=0.5,
            )
            slicer.util.showStatusMessage("Mapa de dosis superpuesto", 3000)

    def _on_exportar_reporte(self):
        """Exportar reporte."""
        output_path = qt.QFileDialog.getSaveFileName(
            self.parent, "Guardar reporte", "", "PDF (*.pdf);;Text (*.txt)"
        )
        if output_path:
            text = self.ui.txtReporte.toPlainText()
            SlicerDosimUtils.export_report_to_pdf(text, output_path)
            slicer.util.showStatusMessage(
                f"Reporte exportado: {output_path}", 3000
            )

    # ------------------------------------------------------------------
    # UI STATE
    # ------------------------------------------------------------------
    def _update_ui_state(self):
        """Actualiza la UI segun el estado del pipeline."""
        state = self.logic.pipeline_state
        try:
            # Volumenes
            if state["phantom_ready"]:
                stats = self.logic.phantom_segmenter._compute_phantom_stats(
                    self.logic.nodes["phantom_seg"]
                ) if self.logic.nodes.get("phantom_seg") else {}
                liver_vol = stats.get("liver_vol_ml", 0)
                tumor_vol = stats.get("tumor_vol_ml", 0)
                self.ui.lblVolHigado.setText(
                    f"Volumen higado: {liver_vol:.0f} ml"
                )
                self.ui.lblVolTumor.setText(
                    f"Volumen tumor: {tumor_vol:.0f} ml"
                )
            elif state["liver_segmented"]:
                self.ui.lblVolHigado.setText("Volumen higado: segmentado")
            else:
                self.ui.lblVolHigado.setText("Volumen higado: --")
                self.ui.lblVolTumor.setText("Volumen tumor: --")

            # Mostrar si se detectaron tumores automaticamente
            if hasattr(self.ui, 'lblEstadoTumor'):
                if state.get("tumor_detected_auto"):
                    self.ui.lblEstadoTumor.setText(
                        "Tumor: detectado automaticamente (revise con Segment Editor)"
                    )
                elif state.get("tumor_segmented"):
                    self.ui.lblEstadoTumor.setText("Tumor: segmentado (manual)")
                else:
                    self.ui.lblEstadoTumor.setText("Tumor: no segmentado")

            # Label de estado del pipeline
            if hasattr(self.ui, 'lblEstadoPipeline'):
                steps_done = sum(1 for v in state.values() if v)
                self.ui.lblEstadoPipeline.setText(
                    f"Pipeline: {steps_done}/{len(state)} pasos completados"
                )

        except AttributeError as e:
            self.logger.debug(f"UI state update error: {e}")


# ============================================================================
# TEST
# ============================================================================
class SlicerDosimTest(ScriptedLoadableModuleTest):
    """Tests del modulo."""

    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_SlicerDosim_load()
        self.test_SlicerDosim_mird()

    def test_SlicerDosim_load(self):
        self.delayDisplay("Probando carga del modulo...")
        logic = SlicerDosimLogic()
        self.assertIsNotNone(logic)
        self.delayDisplay("Modulo cargado OK")

    def test_SlicerDosim_mird(self):
        self.delayDisplay("Probando calculo MIRD...")
        logic = SlicerDosimLogic()
        mird = logic.dose_calc.compute_mird(
            liver_volume_ml=1500.0,
            tumor_volume_ml=100.0,
        )
        self.assertIsNotNone(mird)
        self.assertGreater(mird["activity_gbq"], 0)
        self.delayDisplay(
            f"MIRD OK: {mird['activity_gbq']:.2f} GBq, "
            f"{mird['liver_dose_gy']:.1f} Gy al higado"
        )
