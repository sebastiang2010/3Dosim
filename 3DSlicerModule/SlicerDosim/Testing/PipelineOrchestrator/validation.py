"""
Validacion medica obligatoria de la segmentacion.

Muestra un dialogo Qt NO MODAL que permite al medico navegar Slicer
libremente (mover slices, ocultar PET, rotar 3D) mientras revisa.
Solo cuando hace clic en APROBAR o RECHAZAR se continua.
"""

import logging
import time

logger = logging.getLogger("3DosimTest")

from PipelineOrchestrator.utils import show_progress


def validate_segmentation():
    """
    VALIDACION MEDICA OBLIGATORIA.

    Dialogo NO modal: el medico puede usar 3D Slicer para navegar
    las imagenes, ocultar PET, examinar la segmentacion en 3D, etc.
    Solo cuando hace clic en APROBAR o RECHAZAR se continua.

    Raises:
        RuntimeError: Si el medico rechaza la segmentacion
    """
    logger.info("")
    logger.info("  ╔════════════════════════════════════════════════════╗")
    logger.info("  ║   VALIDACION MEDICA REQUERIDA                     ║")
    logger.info("  ║                                                  ║")
    logger.info("  ║   Un medico debe revisar la segmentacion         ║")
    logger.info("  ║   antes de continuar con los calculos            ║")
    logger.info("  ║   dosimetricos.                                  ║")
    logger.info("  ╚════════════════════════════════════════════════════╝")
    logger.info("")

    show_progress("VALIDACION MEDICA PENDIENTE")

    approved = _show_validation_dialog()

    if approved:
        logger.info("")
        logger.info("  ╔════════════════════════════════════════════════════╗")
        logger.info("  ║   SEGMENTACION APROBADA POR MEDICO                ║")
        logger.info("  ║   Continuando con el pipeline...                  ║")
        logger.info("  ╚════════════════════════════════════════════════════╝")
        logger.info("")
        show_progress("Segmentacion aprobada - continuando")
    else:
        logger.info("")
        logger.info("  ╔════════════════════════════════════════════════════╗")
        logger.info("  ║   SEGMENTACION RECHAZADA                          ║")
        logger.info("  ║   Pipeline detenido.                              ║")
        logger.info("  ║   Corrija la segmentacion y reinicie.             ║")
        logger.info("  ╚════════════════════════════════════════════════════╝")
        logger.info("")
        raise RuntimeError(
            "Segmentacion rechazada por el medico. "
            "Corrija la segmentacion y ejecute con --reset para reiniciar."
        )


def _show_validation_dialog() -> bool:
    """
    Muestra dialogo NO MODAL. El medico puede usar Slicer libremente.

    Returns:
        True si el medico aprueba, False si rechaza.
    """
    try:
        from qt import QLabel, QVBoxLayout, QDialog, QPushButton, Qt
        import slicer

        app = slicer.app

        dialog = QDialog(slicer.util.mainWindow())
        dialog.setWindowTitle("3Dosim - Validacion Medica")
        dialog.setMinimumWidth(600)
        dialog.setModal(False)  # ★ CLAVE: NO MODAL - medico usa Slicer
        # Mantener sobre otras ventanas pero sin bloquear
        dialog.setWindowFlags(dialog.windowFlags() | Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout()
        layout.setSpacing(20)

        titulo = QLabel(
            '<h2 style="color:#2c3e50; text-align:center;">Validar Segmentacion</h2>'
            '<hr>'
            '<p style="font-size:16px; text-align:center;">'
            '&iquest;La segmentacion es correcta?</p>'
        )
        titulo.setWordWrap(True)
        layout.addWidget(titulo)

        layout.addSpacing(10)

        btn_yes = QPushButton("APROBAR")
        btn_no = QPushButton("RECHAZAR")

        layout.addWidget(btn_yes)
        layout.addWidget(btn_no)

        dialog.setLayout(layout)

        btn_yes.setStyleSheet(
            "QPushButton {"
            "  background-color: #27ae60; color: white; font-weight: bold;"
            "  padding: 16px; font-size: 15px; border-radius: 6px; min-height: 20px;"
            "}"
            "QPushButton:hover { background-color: #2ecc71; }"
        )
        btn_no.setStyleSheet(
            "QPushButton {"
            "  background-color: #c0392b; color: white; font-weight: bold;"
            "  padding: 16px; font-size: 15px; border-radius: 6px; min-height: 20px;"
            "}"
            "QPushButton:hover { background-color: #e74c3c; }"
        )

        resultado = [None]

        def on_yes():
            resultado[0] = True
            dialog.close()

        def on_no():
            resultado[0] = False
            dialog.close()

        def on_dialog_closed(exit_code):
            if resultado[0] is None:
                resultado[0] = False

        btn_yes.clicked.connect(on_yes)
        btn_no.clicked.connect(on_no)
        dialog.finished.connect(on_dialog_closed)

        logger.info("  Dialogo NO modal abierto — el medico navega Slicer libremente")
        logger.info("  Haga clic en APROBAR o RECHAZAR para continuar")

        dialog.show()

        # Loop no bloqueante: procesa eventos Qt, Slicer sigue respondiendo
        while resultado[0] is None:
            app.processEvents()
            time.sleep(0.05)

        return resultado[0]

    except ImportError:
        # Fallback a consola
        logger.info("  (Interfaz Qt no disponible, usando consola)")
        respuesta = input("  La segmentacion es correcta? (si/no): ").strip().lower()
        return respuesta in ("si", "s", "yes", "y")
