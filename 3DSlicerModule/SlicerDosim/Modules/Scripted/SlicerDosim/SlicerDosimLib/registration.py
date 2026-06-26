"""
Modulo de registro de imagenes para SlicerDosim.

Implementa registro entre CT (anatomico) y PET/SPECT (funcional)
para alineacion precisa antes del calculo dosimetrico.

Usa ElastixLogic (API real de SlicerElastix) en vez de slicer.cli.run,
ya que Elastix NO es un modulo CLI sino ScriptedLoadableModule.
"""

from __future__ import annotations

import logging


class DosimetryRegistration:
    """
    Registro de imagenes para dosimetria.

    Soportes:
      - BrainsFit (rigido + afin + BSpline) via CLI
      - Elastix via ElastixLogic con presets:
        * elastix_rigid   → preset "default-rigid" (Parameters_Rigid.txt)
        * elastix_affine  → preset con affine (si existe) o rigido+afin
        * elastix_bspline → preset "default0" (Rigid + BSpline)
    """

    METHOD_BRAINSFIT = "brainsfit"
    METHOD_ELASTIX = "elastix"
    METHOD_ELASTIX_RIGID = "elastix_rigid"
    METHOD_ELASTIX_AFFINE = "elastix_affine"

    # IDs de presets de SlicerElastix
    PRESET_DEFAULT_RIGID = "default-rigid"   # solo Parameters_Rigid.txt
    PRESET_DEFAULT_ALL = "default0"           # Parameters_Rigid.txt + Parameters_BSpline.txt
    PRESET_PAR0043 = "par0043"                # rigid para pelvis CT/MR

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._ultima_conservacion = None  # Se llena tras register() si activity_conservation=True
        self.activity_conservation = False
        self.activity_threshold = 0.0

    def register(
        self,
        fixed_node,
        moving_node,
        method: str = METHOD_BRAINSFIT,
        output_volume_node=None,
        activity_conservation: bool = False,
        activity_threshold: float = 0.0,
    ):
        """
        Ejecuta el registro de imagenes.

        Args:
            fixed_node: volumen fijo (ej. CT)
            moving_node: volumen a mover (ej. PET)
            method: metodo de registro
            output_volume_node: nodo de salida (opcional)
            activity_conservation: si True, conserva la actividad total del PET
                                   usando mascara corporal implicita (threshold)
            activity_threshold: valor minimo para considerar un voxel como
                                "dentro del cuerpo" (default 0.0)

        Returns:
            nodo de volumen registrado
        """
        self.activity_conservation = activity_conservation
        self.activity_threshold = activity_threshold
        self._ultima_conservacion = None

        method_map = {
            self.METHOD_BRAINSFIT: self._register_brainsfit,
            self.METHOD_ELASTIX: self._register_elastix_bspline,
            self.METHOD_ELASTIX_RIGID: self._register_elastix_rigid,
            self.METHOD_ELASTIX_AFFINE: self._register_elastix_affine,
        }

        register_fn = method_map.get(method)
        if register_fn is None:
            raise ValueError(f"Metodo no reconocido: {method}")

        self.logger.info(f"Registrando imagenes con metodo: {method}")
        return register_fn(fixed_node, moving_node, output_volume_node)

    def _get_elastix_preset_files(self, preset_id: str):
        """
        Obtiene los archivos de parametros (.txt) para un preset de Elastix.

        Usa BuiltinElastixDatabase para acceder a los presets incluidos.
        """
        from ElastixLib.database import BuiltinElastixDatabase
        db = BuiltinElastixDatabase()
        presets = db.getRegistrationPresets()
        for preset in presets:
            if preset.getID() == preset_id:
                return preset.getParameterFiles()
        raise ValueError(f"Preset '{preset_id}' no encontrado en la base de datos de Elastix")

    def _run_elastix(self, fixed_node, moving_node, output_node, preset_id: str):
        """
        Ejecuta Elastix usando ElastixLogic con un preset especifico.
        """
        import slicer
        from Elastix import ElastixLogic

        self.logger.info(f"  Usando preset Elastix: {preset_id}")

        # Obtener archivos de parametros del preset
        param_files = self._get_elastix_preset_files(preset_id)
        for f in param_files:
            self.logger.info(f"    Param file: {f}")

        # Si no hay output_node, crear uno
        if output_node is None:
            output_node = slicer.mrmlScene.AddNewNodeByClass(
                "vtkMRMLScalarVolumeNode",
                f"{moving_node.GetName()}_registered"
            )

        # Ejecutar Elastix usando la API real (no CLI)
        logic = ElastixLogic()
        logic.logCallback = lambda msg: self.logger.info(f"  Elastix: {msg}")

        # No borrar temporales si queremos debug
        logic.deleteTemporaryFiles = True

        # ProcessEvents ANTES de registerVolumes para que Slicer no se cuelgue
        slicer.app.processEvents()

        logic.registerVolumes(
            fixedVolumeNode=fixed_node,
            movingVolumeNode=moving_node,
            parameterFilenames=param_files,
            outputVolumeNode=output_node,
            outputTransformNode=None,
            fixedVolumeMaskNode=None,
            movingVolumeMaskNode=None,
        )

        self.logger.info(f"  Registro Elastix completado con preset '{preset_id}'")

        # Conservacion de actividad post-registro
        if self.activity_conservation:
            metrica = self._conservar_actividad(moving_node, output_node, self.activity_threshold)
            self._ultima_conservacion = metrica

        return output_node

    # ------------------------------------------------------------------
    # Metodos especificos
    # ------------------------------------------------------------------

    def _register_brainsfit(self, fixed_node, moving_node, output_node=None):
        """
        Registro usando BrainsFit (rigido + afin + BSpline).
        Metodo integrado en 3D Slicer.
        """
        try:
            import slicer

            params = {
                "fixedVolume": fixed_node.GetID(),
                "movingVolume": moving_node.GetID(),
                "outputVolume": output_node.GetID() if output_node else "",
                "transformType": "Rigid,Affine,BSpline",
                "numberOfIterations": "1500",
                "initializeTransformMode": "useCenterOfHeadAlign",
            }

            cli_node = slicer.cli.run(
                slicer.modules.brainsfit, None, params, wait_for_completion=True
            )
            output_node = cli_node.GetOutputNode("outputVolume")
            self.logger.info("Registro BrainsFit completado")

            # Conservacion de actividad post-registro
            if self.activity_conservation:
                metrica = self._conservar_actividad(moving_node, output_node, self.activity_threshold)
                self._ultima_conservacion = metrica

            return output_node

        except Exception as e:
            self.logger.error(f"Error en BrainsFit: {e}")
            raise

    def _register_elastix_rigid(self, fixed_node, moving_node, output_node=None):
        """
        Registro rigido con Elastix (solo traslacion + rotacion).
        Usa el preset 'default-rigid' → Parameters_Rigid.txt (EulerTransform, MI, ASGD)
        """
        return self._run_elastix(fixed_node, moving_node, output_node,
                                 preset_id=self.PRESET_DEFAULT_RIGID)

    def _register_elastix_affine(self, fixed_node, moving_node, output_node=None):
        """
        Registro afin con Elastix (rigido + escala + shear).
        Busca un preset que incluya affine.
        """
        # Intentar presets con affine. Si no existe uno generico, usamos el default-rigid
        # como fallback por ahora.
        try:
            return self._run_elastix(fixed_node, moving_node, output_node,
                                     preset_id="par0043")
        except ValueError:
            self.logger.warning("  Preset affine no encontrado, usando rigid como fallback")
            return self._register_elastix_rigid(fixed_node, moving_node, output_node)

    def _register_elastix_bspline(self, fixed_node, moving_node, output_node=None):
        """
        Registro no rigido con Elastix (rigido + BSpline).
        Usa el preset 'default0' → Parameters_Rigid.txt + Parameters_BSpline.txt
        """
        return self._run_elastix(fixed_node, moving_node, output_node,
                                 preset_id=self.PRESET_DEFAULT_ALL)

    # ------------------------------------------------------------------
    # Conservacion de actividad
    # ------------------------------------------------------------------

    def _conservar_actividad(self, pet_original_node, pet_registrado_node, activity_threshold: float = 0.0) -> dict:
        """
        Conserva la actividad total del PET usando mascara corporal implicita.

        La mascara corporal se define como voxeles con valor > activity_threshold
        (default 0.0 = cualquier actividad detectable).

        Args:
            pet_original_node: nodo PET antes del registro
            pet_registrado_node: nodo PET despues del registro
            activity_threshold: umbral minimo para considerar "cuerpo"

        Returns:
            dict con:
                - 'actividad_original_bq': actividad total pre-registro (solo mascara)
                - 'actividad_sin_corregir_bq': actividad post-registro sin correccion
                - 'actividad_final_bq': actividad post-registro con correccion
                - 'factor_conservacion': factor multiplicativo aplicado
                - 'diff_pct': error de conservacion %
                - 'body_voxels_original': cantidad de voxeles en mascara original
                - 'body_voxels_registrado': cantidad de voxeles en mascara registrada
        """
        import numpy as np
        import slicer

        # Extraer arrays
        arr_orig = slicer.util.arrayFromVolume(pet_original_node)
        arr_reg = slicer.util.arrayFromVolume(pet_registrado_node)

        spacing_orig = pet_original_node.GetSpacing()
        spacing_reg = pet_registrado_node.GetSpacing()

        # Volumen de voxel en mL
        voxel_vol_orig_mL = spacing_orig[0] * spacing_orig[1] * spacing_orig[2] / 1000.0
        voxel_vol_reg_mL = spacing_reg[0] * spacing_reg[1] * spacing_reg[2] / 1000.0

        # Mascara corporal implicita: voxeles con actividad > threshold
        mask_orig = arr_orig > activity_threshold
        mask_reg = arr_reg > activity_threshold

        # Actividad total solo dentro de la mascara
        act_orig = float(np.sum(arr_orig[mask_orig])) * voxel_vol_orig_mL
        act_sin_corregir = float(np.sum(arr_reg[mask_reg])) * voxel_vol_reg_mL

        if act_sin_corregir > 0:
            factor = act_orig / act_sin_corregir
        else:
            factor = 1.0
            self.logger.warning("PET registrado sin actividad detectable - no se puede conservar")

        # Aplicar factor
        arr_reg_corregido = arr_reg * factor

        # Escribir de vuelta al nodo
        slicer.util.updateVolumeFromArray(pet_registrado_node, arr_reg_corregido)

        # Verificar conservacion
        act_final = float(np.sum(arr_reg_corregido[mask_reg])) * voxel_vol_reg_mL
        diff_pct = abs(act_final - act_orig) / max(act_orig, 1.0) * 100

        metrica = {
            'actividad_original_bq': act_orig,
            'actividad_sin_corregir_bq': act_sin_corregir,
            'actividad_final_bq': act_final,
            'factor_conservacion': factor,
            'diff_pct': diff_pct,
            'body_voxels_original': int(mask_orig.sum()),
            'body_voxels_registrado': int(mask_reg.sum()),
        }

        self.logger.info(f"  Conservacion de actividad (mascara corporal, threshold={activity_threshold}):")
        self.logger.info(f"    Actividad original:       {act_orig:.4e}")
        self.logger.info(f"    Actividad sin corregir:   {act_sin_corregir:.4e}")
        self.logger.info(f"    Factor de conservacion:   {factor:.6f}")
        self.logger.info(f"    Actividad final:          {act_final:.4e}")
        self.logger.info(f"    Error de conservacion:    {diff_pct:.4f}%")

        return metrica

    @property
    def ultima_conservacion(self):
        """Retorna las metricas de la ultima conservacion de actividad (None si no se ejecuto)."""
        return self._ultima_conservacion
