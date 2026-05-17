"""
Test de integracion: AgenteState + MCPClient + PanelIA.

Muestra el ciclo completo sin necesidad de GUI ni Slicer:
  1. Crear agente.json
  2. Simular ordenes
  3. Verificar historial
  4. Probar el flujo de aprobacion medica
"""

import os
import sys
import json
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from orchestrator.agente import AgenteState


def demo_ciclo_completo():
    """
    Demostracion del ciclo completo sin MCP:

    GUI (simulado) -> agente.json -> (simula MCP) -> agente.json -> GUI

    Esto es exactamente lo que hara PanelIA cuando este conectada a Slicer.
    """
    print("=" * 70)
    print(" 3Dosim - Demo del ciclo AgenteState (sin MCP)")
    print("=" * 70)

    tmp = os.path.join(tempfile.gettempdir(), "demo_agente.json")
    if os.path.exists(tmp):
        os.remove(tmp)

    state = AgenteState(tmp, auto_save=True)
    print(f"\n1. Estado inicial: {state.status}")
    print(f"   Session ID: {state.session_id[:8]}...")
    print(f"   agente.json: {state.filepath}")

    # ---- Paso 1: Cargar CT ----
    print(f"\n2. Enviando orden: execute_python(cargar CT)...")
    state.set_orden("execute_python", {"code": "slicer.util.loadVolume('/data/CT.nrrd')"})
    assert state.status == "busy"
    print(f"   Estado: {state.status}")
    print(f"   Orden ID: {(state.orden_actual or {}).get('id', '?')[:8]}...")

    # Simular ejecucion MCP exitosa
    print(f"   Ejecutando en Slicer via MCP...")
    state.set_resultado({"output": "", "result": "vtkMRMLVolumeNode1"})
    assert state.status == "idle"
    print(f"   Resultado: OK -> nodo vtkMRMLVolumeNode1")
    state.set_archivo("ct", "/data/CT.nrrd")

    # ---- Paso 2: Segmentar ----
    print(f"\n3. Enviando orden: execute_python(TotalSegmentator)...")
    state.set_orden("execute_python", {"code": "slicer.modules.segmentator(...)"})
    print(f"   Estado: {state.status}")

    # Simular resultado
    state.set_resultado({"output": "Segmentacion completa", "result": "segmentation_node"})
    state.set_archivo("segmentacion", "/data/seg.nrrd")
    print(f"   Resultado: OK")

    # ---- Paso 3: Solicitar aprobacion medica ----
    print(f"\n4. Solicitando aprobacion medica...")
    state.solicitar_aprobacion_medica(
        "Segmentacion de organos completada.\n"
        "Se detectaron: Higado, Pulmones, Rinones, Medula.\n"
        "Verifique en Slicer antes de continuar."
    )
    assert state.status == "waiting_approval"
    print(f"   Estado: {state.status}")
    print(f"   Notificacion: {state._state['medico']['notificacion'][:50]}...")

    # Simular que el medico aprueba
    print(f"   Medico hace clic en SI...")
    state.set_aprobacion_medica(True, "Todo correcto, continuar")
    assert state.status == "idle"
    print(f"   Aprobacion: CONFIRMADA")

    # ---- Paso 4: Generar MCNP ----
    print(f"\n5. Enviando orden: execute_python(generar MCNP)...")
    state.set_orden("execute_python", {"code": "mcnp_generator.run(...)"})
    state.set_resultado({"output": "MCNP input generado", "path": "/output/mcnp.i"})
    state.set_archivo("mcnp_input", "/output/mcnp.i")
    state.status = "done"
    print(f"   Resultado: MCNP input generado")

    # ---- Reporte final ----
    print(f"\n{'=' * 70}")
    print(f" RESUMEN DE LA SESION")
    print(f"{'=' * 70}")
    print(f"  Estado final:    {state.status}")
    print(f"  Ordenes ejec:    {len(state.historial)}")
    for i, h in enumerate(state.historial):
        status = "OK" if h["error"] is None else "ERROR"
        print(f"    {i+1}. [{status}] {h['tool']} -> {str(h['resultado'])[:60]}")
    print(f"  Archivos:")
    for k, v in state.archivos.items():
        print(f"    {k}: {v or '--'}")

    print(f"\n  agente.json guardado en: {state.filepath}")
    print(f"  Contenido ({os.path.getsize(tmp)} bytes):")
    with open(tmp) as f:
        raw = json.load(f)
    print(f"    session_id: {raw['session_id']}")
    print(f"    historial:  {len(raw['historial'])} entradas")
    print(f"    archivos:   {len(raw['archivos'])} entradas")

    # Limpiar
    os.remove(tmp)
    print(f"\n[OK] DEMO COMPLETADA EXITOSAMENTE")


if __name__ == "__main__":
    demo_ciclo_completo()
