"""
Validacion medica obligatoria de la segmentacion.

Muestra un dialogo modal Qt que requiere aprobacion explicita
de un medico antes de continuar con los calculos dosimetricos.
"""

import logging

logger = logging.getLogger("3DosimTest")


def validate_segmentation():
    """
    VALIDACION MEDICA OBLIGATORIA.

    La segmentacion debe ser revisada y aprobada por un medico
    antes de continuar con la generacion de entrada MCNP.

    Muestra un dialogo modal con botones SI/NO.
    NO se puede continuar sin aprobacion medica explicita.

    Raises:
        RuntimeError: Si el medico rechaza la segmentacion
    """
    from .utils import show_progress

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
    Muestra el dialogo de validacion.
    Primero intenta con Qt (Slicer), fallback a consola.

    Returns:
        True si el medico aprueba, False si rechaza
    """
    try:
        from qt import QLabel, QVBoxLayout, QDialog, QPushButton, QApplication

        dialog = QDialog()
        dialog.setWindowTitle("3Dosim - Validacion Medica Obligatoria")
        dialog.setMinimumWidth(500)
        dialog.setModal(True)

        layout = QVBoxLayout()

        msg = QLabel(
            "VALIDACION MEDICA REQUERIDA\n\n"
            "La segmentacion anatomica se ha completado.\n\n"
            "Un medico especialista DEBE revisar y aprobar\n"
            "la segmentacion antes de continuar con:\n"
            "  - Generacion de entrada MCNP\n"
            "  - Calculo de dosis\n"
            "  - Analisis dosimetrico\n\n"
            "La segmentacion es correcta y puede continuar?"
        )
        msg.setWordWrap(True)
        layout.addWidget(msg)

        btn_yes = QPushButton("SI, aprobado - Continuar")
        btn_no = QPushButton("NO, rechazado - Detener pipeline")

        layout.addSpacing(20)
        layout.addWidget(btn_yes)
        layout.addWidget(btn_no)

        dialog.setLayout(layout)

        result = [False]

        def on_yes():
            result[0] = True
            dialog.accept()

        def on_no():
            result[0] = False
            dialog.reject()

        btn_yes.clicked.connect(on_yes)
        btn_no.clicked.connect(on_no)

        btn_yes.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 10px;"
        )
        btn_no.setStyleSheet(
            "background-color: #f44336; color: white; font-weight: bold; padding: 10px;"
        )

        logger.info("  Esperando validacion del medico...")
        dialog.exec_()

        return result[0]

    except ImportError:
        # Fallback: consola
        logger.info("  (Interfaz Qt no disponible, usando consola)")
        respuesta = input("  La segmentacion es correcta? (si/no): ").strip().lower()
        return respuesta in ("si", "s", "yes", "y")
