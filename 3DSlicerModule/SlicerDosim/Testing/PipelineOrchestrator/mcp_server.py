"""
MCP Server para 3Dosim Pipeline.

Inicia un servidor TCP en puerto 2026 que acepta comandos JSON.
Permite monitorear remotamente el pipeline desde scripts externos.

Tambien incluye helper para tomar screenshots de Slicer.

Uso externo (otra terminal):
  from mcp_helper import MCP
  mcp = MCP()
  mcp.connect()
  mcp.ejecutar("slicer.app.majorVersion")
"""

import json
import logging
import os
import socket
import threading
import traceback

logger = logging.getLogger("3DosimTest")

MCP_PORT = 2026


class MCPServer:
    """
    Servidor MCP simple: escucha en puerto TCP, recibe comandos JSON,
    los ejecuta en el contexto de Slicer y retorna resultado.
    """

    def __init__(self, port: int = MCP_PORT):
        self.port = port
        self.server = None
        self.running = False
        self._thread = None

    def start(self):
        """Arranca el servidor MCP en un hilo daemon."""
        if self.running:
            logger.info("  MCP server ya iniciado")
            return

        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind(("127.0.0.1", self.port))
            self.server.listen(1)
            self.server.settimeout(1.0)  # timeout para poder frenar limpio
            self.running = True
            self._thread = threading.Thread(target=self._accept_loop, daemon=True)
            self._thread.start()
            logger.info(f"  MCP server escuchando en 127.0.0.1:{self.port}")
        except Exception as e:
            logger.warning(f"  MCP server NO pudo iniciar: {e}")
            self.running = False

    def stop(self):
        """Detiene el servidor MCP."""
        self.running = False
        if self.server:
            try:
                self.server.close()
            except Exception:
                pass
            self.server = None
        logger.info("  MCP server detenido")

    def _accept_loop(self):
        """Bucle principal: acepta conexiones y procesa comandos."""
        while self.running:
            try:
                client, addr = self.server.accept()
                handler = ConnectionHandler(client, addr)
                handler.handle()
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.warning(f"  MCP error accept: {e}")


class ConnectionHandler:
    """Maneja una conexion MCP individual."""

    def __init__(self, client, addr):
        self.client = client
        self.addr = addr
        self.client.settimeout(30.0)

    def handle(self):
        """Lee JSON, ejecuta comando, retorna JSON."""
        try:
            data = self.client.recv(65536)
            if not data:
                return
            msg = json.loads(data.decode("utf-8"))

            command = msg.get("command", "")
            request_id = msg.get("id", None)

            result = self._execute(command)

            response = {
                "id": request_id,
                "result": result,
                "status": "ok",
            }
            self.client.sendall(json.dumps(response).encode("utf-8"))

        except json.JSONDecodeError as e:
            self._send_error(f"JSON invalido: {e}")
        except Exception as e:
            self._send_error(f"Error: {e}\n{traceback.format_exc()}")
        finally:
            try:
                self.client.close()
            except Exception:
                pass

    def _execute(self, command: str):
        """Ejecuta un comando Python dentro de Slicer usando exec/eval."""
        import slicer

        # Comandos especiales de monitoreo
        if command == "ping":
            return "pong"
        if command == "status":
            return {
                "pipeline_running": self._is_pipeline_running(),
                "slicer_version": f"{slicer.app.majorVersion}.{slicer.app.minorVersion}",
            }

        # Ejecutar cualquier otro comando Python
        try:
            # Intentar eval primero (expresion que retorna valor)
            return eval(command, {"slicer": slicer, "__builtins__": __builtins__})
        except SyntaxError:
            # Si es statement, usar exec
            local_vars = {}
            exec(command, {"slicer": slicer, "__builtins__": __builtins__}, local_vars)
            return str(local_vars) if local_vars else "ok"

    def _is_pipeline_running(self):
        """Detecta si el pipeline esta corriendo (heuristica)."""
        try:
            import slicer
            nodes = slicer.mrmlScene.GetNodesByClass("vtkMRMLScriptedModuleNode")
            for i in range(nodes.GetNumberOfItems()):
                node = nodes.GetItemAsObject(i)
                if "PipelineOrchestrator" in node.GetName():
                    return True
        except Exception:
            pass
        return False

    def _send_error(self, msg):
        try:
            response = {"status": "error", "result": str(msg), "id": None}
            self.client.sendall(json.dumps(response).encode("utf-8"))
        except Exception:
            pass


def take_screenshot(output_dir: str, step_name: str) -> str:
    """
    Toma un screenshot de la ventana principal de Slicer y lo guarda.

    Args:
        output_dir: Directorio donde guardar (se crea subdir screenshots/)
        step_name: Nombre del paso (para el filename)

    Returns:
        Ruta al PNG generado, o None si falla.
    """
    try:
        import slicer
        import time

        screenshot_dir = os.path.join(output_dir, "screenshots")
        os.makedirs(screenshot_dir, exist_ok=True)

        # Sanitizar nombre para filename
        safe_name = step_name.lower().replace(" ", "_").replace("/", "-")[:50]
        timestamp = time.strftime("%H%M%S")
        filename = f"{timestamp}_{safe_name}.png"
        filepath = os.path.join(screenshot_dir, filename)

        # Tomar screenshot
        slicer.app.processEvents()
        time.sleep(0.3)
        main_window = slicer.util.mainWindow()
        if main_window:
            pixmap = main_window.grab()
            pixmap.save(filepath)
            logger.info(f"  Screenshot: {os.path.basename(filepath)}")
            return filepath
        else:
            logger.warning("  No se pudo tomar screenshot (sin mainWindow)")
            return None
    except Exception as e:
        logger.warning(f"  Error tomando screenshot: {e}")
        return None
