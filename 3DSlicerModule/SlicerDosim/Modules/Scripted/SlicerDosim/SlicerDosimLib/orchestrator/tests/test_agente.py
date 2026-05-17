"""Tests unitarios para AgenteState."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from orchestrator.agente import AgenteState


def test_agente_state():
    tmp = os.path.join(tempfile.gettempdir(), "test_agente.json")
    if os.path.exists(tmp):
        os.remove(tmp)

    state = AgenteState(tmp, auto_save=True)
    print(f"Session: {state.session_id}")
    print(f"Status:  {state.status}")
    assert state.status == "idle"
    assert state.orden_actual is None
    assert len(state.historial) == 0

    # Test set_orden
    state.set_orden("execute_python", {"code": 'print("hello")'})
    print(f"Status despues de orden: {state.status}")
    assert state.status == "busy"
    assert state.orden_actual is not None

    # Test set_resultado
    state.set_resultado({"output": "hello\n"})
    print(f"Status despues de resultado: {state.status}")
    assert state.status == "idle"
    assert state.orden_actual is None
    assert len(state.historial) == 1

    # Test aprobacion medica
    state.solicitar_aprobacion_medica("Segmentacion de higado completada")
    print(f"Status despues de solicitar aprobacion: {state.status}")
    assert state.status == "waiting_approval"

    state.set_aprobacion_medica(True, "Todo correcto")
    print(f"Status despues de aprobar: {state.status}")
    assert state.status == "idle"

    # Test archivos
    state.set_archivo("ct", "/data/ct.nrrd")
    state.set_archivo("pet", "/data/pet.nrrd")
    assert state.archivos["ct"] == "/data/ct.nrrd"

    # Test persistencia
    state.save()
    state2 = AgenteState(tmp, auto_save=False)
    assert state2.session_id == state.session_id
    assert len(state2.historial) == 1
    print("Historial guardado correctamente")

    # Test reset
    state2.reset()
    assert state2.status == "idle"
    assert len(state2.historial) == 0

    # Cleanup
    os.remove(tmp)

    print("\n=== TODOS LOS TESTS DE AGENTESTATE PASARON ===")


if __name__ == "__main__":
    test_agente_state()
