"""
AgenteState - Gestiona el archivo agente.json.

Es el "diario de abordo" compartido entre la GUI (PanelIA) y la IA.
Contiene:
  - Estado actual de la sesion (idle/busy/error/done/waiting_approval)
  - Orden actual que se esta ejecutando
  - Historial completo de ordenes ejecutadas
  - Estado de aprobacion medica
  - Rutas de archivos generados

Uso:
    state = AgenteState("./workspace/agente.json")
    state.set_orden("execute_python", {"code": "print('hi')"})
    state.set_resultado({"output": "hi"})
    state.set_aprobacion_medica(True, "Segmentacion correcta")
"""

from __future__ import annotations

import json
import os
import logging
from datetime import datetime, timezone
from uuid import uuid4

logger = logging.getLogger("3Dosim.Orquestador")

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
SCHEMA_VERSION = "1.0"

ESTADOS_VALIDOS = frozenset({
    "idle",            # Esperando orden
    "busy",            # Ejecutando orden
    "error",           # Error en ultima orden
    "done",            # Pipeline completo
    "waiting_approval" # Esperando aprobacion medica
})

TOOLS_VALIDOS = frozenset({
    "execute_python",
    "screenshot",
    "list_nodes",
    "write_file",
    "read_file"
})

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ahora() -> str:
    """ISO timestamp con timezone."""
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _estado_valido(e: str) -> bool:
    return e in ESTADOS_VALIDOS


def _nueva_orden(tool: str, arguments: dict) -> dict:
    return {
        "id": str(uuid4()),
        "tool": tool,
        "arguments": arguments,
        "resultado": None,
        "error": None,
        "timestamp_envio": _ahora(),
        "timestamp_respuesta": None,
    }


# ---------------------------------------------------------------------------
# AgenteState
# ---------------------------------------------------------------------------

class AgenteState:
    """Lee, escribe y manipula agente.json.

    Args:
        filepath: Ruta absoluta al archivo agente.json.
                  Si no existe, se crea con estado inicial.
        auto_save: Si True, persiste automaticamente tras cada cambio.
    """

    def __init__(self, filepath: str, auto_save: bool = True):
        self._filepath = os.path.abspath(filepath)
        self._auto_save = auto_save
        self._state = self._load()

    # ------------------------------------------------------------------
    # Persistencia
    # ------------------------------------------------------------------

    def _state_inicial(self) -> dict:
        return {
            "version": SCHEMA_VERSION,
            "session_id": str(uuid4()),
            "created_at": _ahora(),
            "updated_at": _ahora(),
            "status": "idle",
            "interrupted": False,
            "pipeline_step": None,
            "mcp_connected": False,
            "orden_actual": None,
            "historial": [],
            "medico": {
                "aprobacion_requerida": False,
                "aprobada": False,
                "pendiente_desde": None,
                "notificacion": "",
            },
            "archivos": {
                "ct": None,
                "pet": None,
                "segmentacion": None,
                "mcnp_input": None,
                "reporte": None,
            },
        }

    def _load(self) -> dict:
        """Carga agente.json del disco, o crea estado inicial.

        Detecta cortes abruptos: si el estado guardado indica "busy"
        o "waiting_approval", la sesion anterior se interrumpio.
        Resetea a "idle" y marca el flag interrupted=True.
        """
        if os.path.exists(self._filepath):
            try:
                with open(self._filepath, "r", encoding="utf-8") as f:
                    state = json.load(f)
                # Detectar corte abrupto: sesion anterior en busy/waiting_approval
                if state.get("status") in ("busy", "waiting_approval"):
                    logger.warning(
                        "Sesion anterior se corto abruptamente "
                        "(status=%s). Reseteando a idle.",
                        state.get("status"),
                    )
                    state["status"] = "idle"
                    state["interrupted"] = True
                    # Si habia una orden en ejecucion, moverla al historial como fallida
                    if state.get("orden_actual") is not None:
                        orden = state["orden_actual"]
                        orden["error"] = "Sesion interrumpida"
                        orden["timestamp_respuesta"] = _ahora()
                        state["historial"].append(orden)
                        state["orden_actual"] = None
                if state.get("version") == SCHEMA_VERSION:
                    return state
                logger.warning("Version de agente.json incompatible, reiniciando")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Error leyendo agente.json: %s. Creando nuevo.", e)
        return self._state_inicial()

    def save(self):
        """Persiste el estado actual a agente.json."""
        self._state["updated_at"] = _ahora()
        os.makedirs(os.path.dirname(self._filepath), exist_ok=True)
        with open(self._filepath, "w", encoding="utf-8") as f:
            json.dump(self._state, f, indent=2, ensure_ascii=False)
        logger.debug("agente.json guardado: %s", self._filepath)

    def reset(self):
        """Borra el estado y empieza de cero."""
        self._state = self._state_inicial()
        self.save()
        logger.info("agente.json reiniciado")

    # ------------------------------------------------------------------
    # Propiedades
    # ------------------------------------------------------------------

    @property
    def filepath(self) -> str:
        return self._filepath

    @property
    def session_id(self) -> str:
        return self._state["session_id"]

    @property
    def status(self) -> str:
        return self._state["status"]

    @status.setter
    def status(self, nuevo: str):
        if not _estado_valido(nuevo):
            raise ValueError(f"Estado invalido: {nuevo}. Validos: {sorted(ESTADOS_VALIDOS)}")
        self._state["status"] = nuevo
        self._maybe_save()

    @property
    def pipeline_step(self) -> str | None:
        return self._state["pipeline_step"]

    @pipeline_step.setter
    def pipeline_step(self, step: str | None):
        self._state["pipeline_step"] = step
        self._maybe_save()

    @property
    def mcp_connected(self) -> bool:
        return self._state["mcp_connected"]

    @mcp_connected.setter
    def mcp_connected(self, val: bool):
        self._state["mcp_connected"] = val
        self._maybe_save()

    @property
    def medico_aprobacion_requerida(self) -> bool:
        return self._state["medico"]["aprobacion_requerida"]

    @medico_aprobacion_requerida.setter
    def medico_aprobacion_requerida(self, val: bool):
        self._state["medico"]["aprobacion_requerida"] = val
        self._maybe_save()

    @property
    def medico_aprobada(self) -> bool:
        return self._state["medico"]["aprobada"]

    @property
    def historial(self) -> list:
        return list(self._state["historial"])

    @property
    def archivos(self) -> dict:
        return dict(self._state["archivos"])

    # ------------------------------------------------------------------
    # Ordenes
    # ------------------------------------------------------------------

    @property
    def orden_actual(self) -> dict | None:
        """Orden actual (None si no hay)."""
        return self._state["orden_actual"]

    def set_orden(self, tool: str, arguments: dict | None = None):
        """Registra una nueva orden a ejecutar.

        Args:
            tool: Nombre del tool MCP ('execute_python', 'screenshot', etc.)
            arguments: Dict con argumentos del tool.
        """
        if tool not in TOOLS_VALIDOS:
            raise ValueError(
                f"Tool invalido: {tool}. Validos: {sorted(TOOLS_VALIDOS)}"
            )
        orden = _nueva_orden(tool, arguments or {})
        self._state["orden_actual"] = orden
        self.status = "busy"
        logger.info("Nueva orden [%s]: %s(%s)", orden["id"][:8], tool, arguments)

    def set_resultado(self, resultado: object, error: str | None = None):
        """Actualiza el resultado de la orden actual y la mueve al historial.

        Args:
            resultado: Datos devueltos por el tool (dict, str, list, etc.)
            error: Mensaje de error si fallo.
        """
        if self._state["orden_actual"] is None:
            raise RuntimeError("No hay orden actual para actualizar")

        orden = self._state["orden_actual"]
        orden["resultado"] = resultado
        orden["error"] = error
        orden["timestamp_respuesta"] = _ahora()

        # Mover al historial
        self._state["historial"].append(orden)
        self._state["orden_actual"] = None

        if error:
            self.status = "error"
        else:
            self.status = "idle"

        logger.info("Orden completada: %s (error=%s)", orden["id"][:8], bool(error))

    # ------------------------------------------------------------------
    # Aprobacion medica
    # ------------------------------------------------------------------

    def solicitar_aprobacion_medica(self, notificacion: str = ""):
        """Marca que se necesita aprobacion medica.

        La GUI debe mostrar un dialogo. La IA no puede continuar hasta
        que el medico apruebe explicitamente.
        """
        self._state["medico"]["aprobacion_requerida"] = True
        self._state["medico"]["aprobada"] = False
        self._state["medico"]["pendiente_desde"] = _ahora()
        self._state["medico"]["notificacion"] = notificacion
        self.status = "waiting_approval"
        logger.info("Aprobacion medica REQUERIDA: %s", notificacion)

    def set_aprobacion_medica(self, aprobada: bool, notificacion: str = ""):
        """El medico responde SI/NO.

        Args:
            aprobada: True si el medico aprueba.
            notificacion: Comentario del medico.
        """
        self._state["medico"]["aprobacion_requerida"] = False
        self._state["medico"]["aprobada"] = aprobada
        self._state["medico"]["pendiente_desde"] = None
        self._state["medico"]["notificacion"] = notificacion
        self.status = "idle" if aprobada else "error"
        logger.info("Aprobacion medica: %s - %s", "APROBADA" if aprobada else "RECHAZADA", notificacion)

    # ------------------------------------------------------------------
    # Archivos
    # ------------------------------------------------------------------

    def set_archivo(self, key: str, path: str | None):
        """Actualiza la ruta de un archivo generado.

        Args:
            key: 'ct', 'pet', 'segmentacion', 'mcnp_input', 'reporte'
            path: Ruta absoluta al archivo.
        """
        if key not in self._state["archivos"]:
            raise ValueError(f"Clave de archivo invalida: {key}")
        self._state["archivos"][key] = path
        self._maybe_save()

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def to_json(self, indent: int = 2) -> str:
        """Serializa el estado a string JSON."""
        return json.dumps(self._state, indent=indent, ensure_ascii=False)

    def __repr__(self) -> str:
        return (
            f"<AgenteState status={self.status!r}"
            f" ordenes={len(self._state['historial'])}"
            f" archivo={os.path.basename(self._filepath)}>"
        )

    def _maybe_save(self):
        if self._auto_save:
            self.save()
