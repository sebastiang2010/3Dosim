"""
Modulo de registro de imagenes para SlicerDosim.

Implementa registro entre CT (anatomico) y PET/SPECT (funcional)
para alineacion precisa antes del calculo dosimetrico.
"""

from __future__ import annotations

import logging


class DosimetryRegistration:
    """
    Registro de imagenes para dosimetria.

    Soportes:
      - BrainsFit (rigido + afin)
      - Elastix (BSpline no rigido)
    """

    METHOD_BRAINSFIT = "brainsfit"
    METHOD_ELASTIX = "elastix"

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def register(
        self,
        fixed_node,
        moving_node,
        method: str = METHOD_BRAINSFIT,
        output_volume_node=None,
    ):
        """
        Ejecuta el registro de imagenes.

        Args:
            fixed_node: volumen fijo (ej. CT)
            moving_node: volumen a mover (ej. PET)
            method: metodo de registro
            output_volume_node: nodo de salida (opcional)

        Returns:
            nodo de volumen registrado
        """
        method_map = {
            self.METHOD_BRAINSFIT: self._register_brainsfit,
            self.METHOD_ELASTIX: self._register_elastix,
        }

        register_fn = method_map.get(method)
        if register_fn is None:
            raise ValueError(f"Metodo no reconocido: {method}")

        self.logger.info(f"Registrando imagenes con metodo: {method}")
        return register_fn(fixed_node, moving_node, output_volume_node)

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

            # Ejecutar BrainsFit
            cli_node = slicer.cli.run(
                slicer.modules.brainsfit, None, params, wait_for_completion=True
            )
            self.logger.info("Registro BrainsFit completado")
            return cli_node.GetOutputNode("outputVolume")

        except Exception as e:
            self.logger.error(f"Error en BrainsFit: {e}")
            raise

    def _register_elastix(self, fixed_node, moving_node, output_node=None):
        """
        Registro usando Elastix (BSpline no rigido).
        Requiere el modulo SlicerElastix.
        """
        try:
            import slicer

            params = {
                "fixedVolume": fixed_node.GetID(),
                "movingVolume": moving_node.GetID(),
                "outputVolume": output_node.GetID() if output_node else "",
                "registrationType": "nonrigid",
                "numberOfResolutions": 4,
                "finalGridSpacingInPhysicalUnits": 10,
            }

            cli_node = slicer.cli.run(
                slicer.modules.elastix, None, params, wait_for_completion=True
            )
            self.logger.info("Registro Elastix completado")
            return cli_node.GetOutputNode("outputVolume")

        except Exception as e:
            self.logger.error(f"Error en Elastix: {e}")
            raise

    def apply_transform(self, volume_node, transform_node) -> object:
        """
        Aplica una transformacion a un volumen.
        Util para re-muestrear la PET a la geometria del CT.
        """
        try:
            import slicer

            params = {
                "inputVolume": volume_node.GetID(),
                "outputVolume": "",
                "transform": transform_node.GetID(),
                "interpolationMode": "Linear",
            }
            cli_node = slicer.cli.run(
                slicer.modules.resamplescalarvolume, None, params, wait_for_completion=True
            )
            return cli_node.GetOutputNode("outputVolume")

        except Exception as e:
            self.logger.error(f"Error al aplicar transformada: {e}")
            raise
