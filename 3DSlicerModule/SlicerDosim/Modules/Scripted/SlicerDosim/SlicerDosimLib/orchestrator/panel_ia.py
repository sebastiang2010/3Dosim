"""
PanelIA - GUI tkinter para controlar 3D Slicer via MCP.

Conecta AgenteState (agente.json) + MCPClient (slicer-mcp-server.py)
en un panel de control que permite:

  - Enviar comandos Python a Slicer
  - Tomar capturas de pantalla de las vistas de Slicer
  - Listar nodos MRML
  - Ver historial de ordenes ejecutadas
  - Aprobacion medica explicita (dialogo SI/NO)
  - Monitorear estado del pipeline en tiempo real

Uso:
    from orchestrator.panel_ia import PanelIA
    app = PanelIA()
    app.run()
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
from datetime import datetime
from typing import Any

# tkinter solo esta disponible fuera de Slicer (Slicer usa Qt).
# Slicer no tiene _tkinter, asi que hacemos import condicional.
try:
    import tkinter as tk
    from tkinter import ttk, messagebox, scrolledtext, filedialog
    TKINTER_AVAILABLE = True
except ImportError:
    TKINTER_AVAILABLE = False

from .agente import AgenteState
from .mcp_client import MCPClient, MCPConnectionError

logger = logging.getLogger("3Dosim.PanelIA")

# ---------------------------------------------------------------------------
# Constantes de UI
# ---------------------------------------------------------------------------
COLOR_IDLE           = "#f0f0f0"
COLOR_BUSY           = "#fff3cd"
COLOR_ERROR          = "#f8d7da"
COLOR_DONE           = "#d4edda"
COLOR_WAITING        = "#cce5ff"
COLOR_CONNECTED      = "#28a745"
COLOR_DISCONNECTED   = "#dc3545"

COLOR_BG             = "#2b2b2b"
COLOR_FG             = "#ffffff"
COLOR_ENTRY_BG       = "#3c3c3c"
COLOR_BUTTON_BG      = "#0d6efd"
COLOR_BUTTON_FG      = "#ffffff"

# ---------------------------------------------------------------------------
# PanelIA
# ---------------------------------------------------------------------------

class PanelIA:
    """Panel de control de IA para 3Dosim.

    Args:
        agente_filepath: Ruta a agente.json (se crea si no existe).
        mcp_url: URL base del servidor MCP de Slicer.
        title: Titulo de la ventana.
        theme: 'light' o 'dark'.
    """

    def __init__(
        self,
        agente_filepath: str | None = None,
        mcp_url: str = "http://localhost:2026",
        title: str = "3Dosim - Panel de Control IA",
        theme: str = "dark",
    ):
        # Estado
        self._agente_filepath = agente_filepath or self._default_agente_path()
        self._mcp_url = mcp_url
        self._theme = theme

        # Componentes
        self._agente = AgenteState(self._agente_filepath, auto_save=True)
        self._mcp = MCPClient(mcp_url)

        # UI
        self._root = tk.Tk()
        self._root.title(title)
        self._root.geometry("960x720")
        self._root.minsize(720, 540)

        # Icono (si existe)
        try:
            self._root.iconbitmap(default=self._resource_path("icon.ico"))
        except Exception:
            pass

        # Widgets (se crean en _build_ui)
        self._status_bar = None
        self._mcp_indicator = None
        self._code_text = None
        self._output_text = None
        self._history_list = None
        self._screenshot_label = None
        self._file_frame = None

        # Callbacks
        self._on_aprobacion_medica = None
        self._poll_job = None

        self._build_ui()
        self._update_ui()
        self._start_poller()

    # ------------------------------------------------------------------
    # Lanzamiento
    # ------------------------------------------------------------------

    def run(self):
        """Inicia el bucle principal de tkinter."""
        logger.info("PanelIA iniciado. agente.json: %s", self._agente_filepath)
        self._root.mainloop()

    def close(self):
        """Cierra la aplicacion ordenadamente."""
        self._stop_poller()
        self._mcp.disconnect()
        self._agente.save()
        self._root.destroy()

    # ------------------------------------------------------------------
    # Ruta default de agente.json
    # ------------------------------------------------------------------

    @staticmethod
    def _default_agente_path() -> str:
        return os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..", "..", "..", "workspace", "agente.json"
        )

    @staticmethod
    def _resource_path(rel: str) -> str:
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), rel)

    # ------------------------------------------------------------------
    # Construccion de UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = self._root

        if self._theme == "dark":
            root.tk_setPalette(
                background=COLOR_BG,
                foreground=COLOR_FG,
                activeBackground="#3a3a3a",
                activeForeground=COLOR_FG,
                highlightBackground="#3a3a3a",
                highlightColor=COLOR_FG,
            )

        # ---- Barra superior: estado + MCP ----
        top_frame = ttk.Frame(root, padding="4")
        top_frame.pack(fill=tk.X)

        self._status_bar = ttk.Label(top_frame, text="Estado: idle", font=("Segoe UI", 10, "bold"))
        self._status_bar.pack(side=tk.LEFT, padx=4)

        self._mcp_indicator = ttk.Label(top_frame, text="MCP: desconectado", font=("Segoe UI", 9))
        self._mcp_indicator.pack(side=tk.RIGHT, padx=4)

        # ---- Botones de conexion ----
        btn_frame = ttk.Frame(root, padding="2")
        btn_frame.pack(fill=tk.X)

        self._btn_connect = ttk.Button(btn_frame, text="🔌 Conectar MCP", command=self._on_connect)
        self._btn_connect.pack(side=tk.LEFT, padx=2)

        self._btn_disconnect = ttk.Button(btn_frame, text="Desconectar", command=self._on_disconnect, state=tk.DISABLED)
        self._btn_disconnect.pack(side=tk.LEFT, padx=2)

        self._btn_reset = ttk.Button(btn_frame, text="🔄 Reset agente.json", command=self._on_reset)
        self._btn_reset.pack(side=tk.LEFT, padx=2)

        self._btn_open_agente = ttk.Button(btn_frame, text="📂 Abrir agente.json", command=self._on_open_agente)
        self._btn_open_agente.pack(side=tk.LEFT, padx=2)

        # ---- Panel principal (paned) ----
        paned = ttk.PanedWindow(root, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=4, pady=2)

        # -- Frame superior: Comando + Output --
        top_panel = ttk.Frame(paned)
        paned.add(top_panel, weight=3)

        # Codigo Python
        code_frame = ttk.LabelFrame(top_panel, text="Comando Python / Orden MCP", padding="4")
        code_frame.pack(fill=tk.BOTH, expand=True, pady=2)

        self._code_text = scrolledtext.ScrolledText(
            code_frame, height=6,
            font=("Consolas", 10),
            bg=COLOR_ENTRY_BG if self._theme == "dark" else "#ffffff",
            fg=COLOR_FG if self._theme == "dark" else "#000000",
            insertbackground=COLOR_FG if self._theme == "dark" else "#000000",
        )
        self._code_text.pack(fill=tk.BOTH, expand=True)
        self._code_text.insert("1.0", "# Escribe codigo Python para Slicer aqui\n")
        self._code_text.bind("<Control-Return>", lambda e: self._on_execute())

        # Botones de accion rapida
        action_frame = ttk.Frame(code_frame)
        action_frame.pack(fill=tk.X, pady=2)

        ttk.Button(action_frame, text="▶ Ejecutar", command=self._on_execute).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="📷 Screenshot 3D", command=lambda: self._on_screenshot("3D")).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="📷 Screenshot Red", command=lambda: self._on_screenshot("Red")).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="📋 List Nodes", command=self._on_list_nodes).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="🧹 Limpiar Output", command=self._on_clear_output).pack(side=tk.RIGHT, padx=2)

        # Output / Screenshot
        output_frame = ttk.LabelFrame(top_panel, text="Resultado / Screenshot", padding="4")
        output_frame.pack(fill=tk.BOTH, expand=True, pady=2)

        # Notebook con pestañas: Texto | Imagen
        output_notebook = ttk.Notebook(output_frame)
        output_notebook.pack(fill=tk.BOTH, expand=True)

        # Pestana texto
        text_tab = ttk.Frame(output_notebook)
        output_notebook.add(text_tab, text="Texto")
        self._output_text = scrolledtext.ScrolledText(
            text_tab, height=8,
            font=("Consolas", 9),
            bg=COLOR_ENTRY_BG if self._theme == "dark" else "#ffffff",
            fg=COLOR_FG if self._theme == "dark" else "#000000",
            state=tk.DISABLED,
        )
        self._output_text.pack(fill=tk.BOTH, expand=True)

        # Pestana imagen
        img_tab = ttk.Frame(output_notebook)
        output_notebook.add(img_tab, text="Imagen")
        self._screenshot_label = ttk.Label(img_tab, text="(sin screenshot)", anchor=tk.CENTER)
        self._screenshot_label.pack(fill=tk.BOTH, expand=True)

        # -- Frame inferior: Historial + Archivos --
        bottom_panel = ttk.Frame(paned)
        paned.add(bottom_panel, weight=2)

        # Historial
        hist_frame = ttk.LabelFrame(bottom_panel, text="Historial de Ordenes", padding="4")
        hist_frame.pack(fill=tk.BOTH, expand=True, pady=2)

        list_frame = ttk.Frame(hist_frame)
        list_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._history_list = tk.Listbox(
            list_frame,
            yscrollcommand=scrollbar.set,
            font=("Consolas", 9),
            height=6,
            bg=COLOR_ENTRY_BG if self._theme == "dark" else "#ffffff",
            fg=COLOR_FG if self._theme == "dark" else "#000000",
            selectbackground="#0d6efd",
        )
        self._history_list.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self._history_list.yview)
        self._history_list.bind("<Double-Button-1>", self._on_history_select)

        # Archivos
        self._file_frame = ttk.LabelFrame(bottom_panel, text="Archivos Generados", padding="4")
        self._file_frame.pack(fill=tk.X, pady=2)

        self._file_labels = {}
        for key, label in [
            ("ct", "CT"),
            ("pet", "PET"),
            ("segmentacion", "Segmentation"),
            ("mcnp_input", "MCNP Input"),
            ("reporte", "Reporte"),
        ]:
            lbl = ttk.Label(self._file_frame, text=f"  {label}: —", font=("Segoe UI", 8))
            lbl.pack(anchor=tk.W)
            self._file_labels[key] = lbl

        # ---- Barra inferior: hints ----
        hint_frame = ttk.Frame(root, padding="2")
        hint_frame.pack(fill=tk.X)
        ttk.Label(
            hint_frame,
            text="Ctrl+Enter para ejecutar | Doble-click en historial para ver detalle",
            font=("Segoe UI", 7),
            foreground="#888888",
        ).pack(side=tk.LEFT)

        # Bind de cierre
        root.protocol("WM_DELETE_WINDOW", self.close)

    # ------------------------------------------------------------------
    # Eventos de UI
    # ------------------------------------------------------------------

    def _on_connect(self):
        """Conecta al servidor MCP de Slicer en background."""
        self._log_output("Conectando a MCP Slicer...\n")

        def _connect():
            ok = self._mcp.connect()
            self._root.after(0, lambda: self._on_connect_result(ok))

        threading.Thread(target=_connect, daemon=True).start()

    def _on_connect_result(self, ok: bool):
        if ok:
            self._agente.mcp_connected = True
            self._log_output(f"✅ MCP conectado: {self._mcp.server_info}\n")
            info = self._mcp.server_info
            tools = self._mcp.list_tools()
            self._log_output(f"   Tools disponibles ({len(tools)}):\n")
            for t in tools:
                self._log_output(f"     - {t.get('name', '?')}: {t.get('description', '')[:80]}\n")
            self._btn_connect.config(state=tk.DISABLED)
            self._btn_disconnect.config(state=tk.NORMAL)
        else:
            self._agente.mcp_connected = False
            self._log_output("❌ No se pudo conectar a MCP. ¿Slicer esta corriendo?\n")
            self._log_output(f"   URL: {self._mcp_url}\n")
            self._log_output("   Ejecute slicer-mcp-server.py dentro de Slicer primero.\n")
        self._update_ui()

    def _on_disconnect(self):
        self._mcp.disconnect()
        self._agente.mcp_connected = False
        self._btn_connect.config(state=tk.NORMAL)
        self._btn_disconnect.config(state=tk.DISABLED)
        self._log_output("MCP desconectado.\n")
        self._update_ui()

    def _on_reset(self):
        if messagebox.askyesno("Reset", "¿Reiniciar agente.json? Se perderan todas las ordenes."):
            self._agente.reset()
            self._log_output("agente.json reiniciado.\n")
            self._update_ui()

    def _on_open_agente(self):
        """Abre el archivo agente.json con el editor default."""
        try:
            os.startfile(self._agente_filepath)
        except Exception as e:
            messagebox.showerror("Error", f"No se pudo abrir agente.json:\n{e}")

    def _on_execute(self):
        """Ejecuta el codigo Python del editor."""
        code = self._code_text.get("1.0", tk.END).strip()
        if not code:
            return

        self._ejecutar_herramienta_mcp("execute_python", {"code": code})

    def _on_screenshot(self, view: str = "3D"):
        """Toma un screenshot de Slicer."""
        self._ejecutar_herramienta_mcp("screenshot", {"view": view})

    def _on_list_nodes(self):
        """Lista nodos MRML de Slicer."""
        self._ejecutar_herramienta_mcp("list_nodes", {})

    def _on_clear_output(self):
        """Limpia el panel de output."""
        self._output_text.config(state=tk.NORMAL)
        self._output_text.delete("1.0", tk.END)
        self._output_text.config(state=tk.DISABLED)

    def _on_history_select(self, event):
        """Muestra detalle de una orden del historial."""
        sel = self._history_list.curselection()
        if not sel:
            return
        idx = sel[0]
        # Recuperar del state
        historial = self._agente.historial
        if idx < len(historial):
            entry = historial[idx]
            detail = json.dumps(entry, indent=2, ensure_ascii=False)
            self._log_output(f"\n--- Detalle orden #{idx+1} ---\n{detail}\n")

    # ------------------------------------------------------------------
    # MCP: ejecutar herramienta (el corazon del sistema)
    # ------------------------------------------------------------------

    def _ejecutar_herramienta_mcp(self, tool: str, arguments: dict):
        """Ejecuta una herramienta MCP y actualiza agente.json + UI.

        Este es el metodo central que conecta:
            GUI (boton) -> agente.json (registra orden) -> MCP (ejecuta) -> agente.json (resultado) -> UI (muestra)

        Args:
            tool: Nombre del tool MCP.
            arguments: Dict con argumentos.
        """
        if tool != "list_nodes" and not self._mcp.connected:
            self._log_output("❌ No hay conexion MCP. Presione 'Conectar MCP' primero.\n")
            return

        # 1. Registrar orden en agente.json
        self._agente.set_orden(tool, arguments)
        self._update_ui()

        # 2. Ejecutar en background
        def _run():
            try:
                # 2a. Llamar al MCP
                if tool == "execute_python":
                    result = self._mcp.execute_python(arguments.get("code", ""))
                elif tool == "screenshot":
                    img_data = self._mcp.screenshot(arguments.get("view", "3D"))
                    result = {"image_bytes": len(img_data), "view": arguments.get("view", "3D")}
                    # Mostrar en UI
                    self._root.after(0, lambda: self._show_screenshot(img_data))
                elif tool == "list_nodes":
                    nodes = self._mcp.list_nodes(arguments.get("filter", ""))
                    result = {"nodes": nodes, "count": len(nodes)}
                else:
                    result = self._mcp.call_tool(tool, arguments)

                # 2b. Actualizar agente.json con exito
                self._agente.set_resultado(result)
                self._root.after(0, lambda: self._log_output(
                    f"✅ {tool} OK: {json.dumps(result, indent=2, ensure_ascii=False)[:500]}\n"
                ))

            except MCPConnectionError as e:
                error_msg = f"Error de conexion MCP: {e}"
                self._agente.set_resultado(None, error=str(e))
                self._root.after(0, lambda: self._log_output(f"❌ {error_msg}\n"))

            except Exception as e:
                error_msg = f"Error ejecutando {tool}: {e}"
                self._agente.set_resultado(None, error=str(e))
                self._root.after(0, lambda: self._log_output(f"❌ {error_msg}\n"))

            finally:
                self._root.after(0, self._update_ui)

        threading.Thread(target=_run, daemon=True).start()

    # ------------------------------------------------------------------
    # UI: actualizacion periodica
    # ------------------------------------------------------------------

    def _start_poller(self):
        """Polling cada 1s para reflejar cambios de agente.json."""
        self._poll_ui()

    def _stop_poller(self):
        if self._poll_job:
            self._root.after_cancel(self._poll_job)
            self._poll_job = None

    def _poll_ui(self):
        """Actualiza UI con el estado actual de agente.json."""
        try:
            self._update_ui()
        except Exception as e:
            logger.warning("Error en poll_ui: %s", e)
        self._poll_job = self._root.after(1000, self._poll_ui)

    def _update_ui(self):
        """Refleja el estado actual de AgenteState en los widgets."""
        agente = self._agente

        # -- Status --
        status = agente.status
        status_text = f"Estado: {status}"
        if agente.orden_actual:
            status_text += f" | Orden: {agente.orden_actual['tool']}"
        self._status_bar.config(text=status_text)

        # Color segun estado
        color_map = {
            "idle": COLOR_IDLE,
            "busy": COLOR_BUSY,
            "error": COLOR_ERROR,
            "done": COLOR_DONE,
            "waiting_approval": COLOR_WAITING,
        }
        bg = color_map.get(status, COLOR_IDLE)
        self._status_bar.config(background=bg)

        # -- MCP indicator --
        if self._mcp.connected:
            self._mcp_indicator.config(text="MCP: ✅ conectado", foreground=COLOR_CONNECTED)
        else:
            self._mcp_indicator.config(text="MCP: ❌ desconectado", foreground=COLOR_DISCONNECTED)

        # -- Archivos --
        for key, lbl in self._file_labels.items():
            path = agente.archivos.get(key)
            if path:
                lbl.config(text=f"  {key.capitalize()}: ✅ {os.path.basename(path)}")
            else:
                lbl.config(text=f"  {key.capitalize()}: —")

        # -- Historial --
        historial = agente.historial
        self._history_list.delete(0, tk.END)
        for i, entry in enumerate(historial):
            tool = entry.get("tool", "?")
            status_char = "✅" if entry.get("error") is None else "❌"
            ts = entry.get("timestamp_envio", "")[11:19]  # HH:MM:SS
            preview = str(entry.get("arguments", {}))[:40]
            self._history_list.insert(tk.END, f"  {status_char} [{ts}] {tool}({preview})")

        # -- Notificacion medica --
        if agente.medico_aprobacion_requerida and not agente.medico_aprobada:
            self._mostrar_dialogo_aprobacion()

    # ------------------------------------------------------------------
    # Screenshot
    # ------------------------------------------------------------------

    def _show_screenshot(self, img_data: bytes):
        """Muestra un screenshot en el panel de imagen."""
        try:
            # Guardar temporal y cargar con PIL
            tmp_path = os.path.join(
                os.path.dirname(self._agente_filepath),
                f"_screenshot_{int(time.time())}.png"
            )
            os.makedirs(os.path.dirname(tmp_path), exist_ok=True)
            with open(tmp_path, "wb") as f:
                f.write(img_data)

            # Cargar con PIL si disponible
            try:
                from PIL import Image, ImageTk
                img = Image.open(tmp_path)
                # Redimensionar para el panel (max 400px ancho)
                max_w = 400
                w, h = img.size
                if w > max_w:
                    ratio = max_w / w
                    img = img.resize((max_w, int(h * ratio)), Image.LANCZOS)
                # Usar LANCZOS si disponible, sino ANTIALIAS (PIL compat)
                resample = getattr(Image, "LANCZOS", Image.ANTIALIAS)
                img = img.resize((max_w, int(h * ratio)), resample)
                photo = ImageTk.PhotoImage(img)
                self._screenshot_label.config(image=photo, text="")
                self._screenshot_label.image = photo  # mantener referencia
            except ImportError:
                # Sin PIL, mostrar solo ruta
                self._screenshot_label.config(
                    text=f"Screenshot guardado en:\n{tmp_path}\n({len(img_data)} bytes)",
                    image="",
                )

            self._log_output(f"📷 Screenshot: {tmp_path} ({len(img_data)} bytes)\n")

        except Exception as e:
            self._log_output(f"Error mostrando screenshot: {e}\n")

    # ------------------------------------------------------------------
    # Aprobacion medica
    # ------------------------------------------------------------------

    def _mostrar_dialogo_aprobacion(self):
        """Dialogo modal de aprobacion medica."""
        notificacion = self._agente._state["medico"].get("notificacion", "")
        msg = (
            "⚠️ APROBACION MEDICA REQUERIDA\n\n"
            f"{notificacion}\n\n"
            "¿La segmentacion es correcta?\n"
            "Se generara la entrada MCNP con los materiales asignados."
        )
        respuesta = messagebox.askyesno("Aprobacion Medica - 3Dosim", msg)

        if respuesta:
            self._agente.set_aprobacion_medica(True, "Aprobado por medico")
            self._log_output("✅ Aprobacion medica CONFIRMADA. Continuando...\n")
        else:
            self._agente.set_aprobacion_medica(False, "Rechazado por medico")
            self._log_output("❌ Aprobacion medica RECHAZADA. Pipeline detenido.\n")

        self._update_ui()

    # ------------------------------------------------------------------
    # Logging en UI
    # ------------------------------------------------------------------

    def _log_output(self, text: str):
        """Agrega texto al panel de output."""
        self._output_text.config(state=tk.NORMAL)
        self._output_text.insert(tk.END, text)
        self._output_text.see(tk.END)
        self._output_text.config(state=tk.DISABLED)

    # ------------------------------------------------------------------
    # Utils
    # ------------------------------------------------------------------

    def set_aprobacion_callback(self, callback):
        """Registra callback para cuando se requiere aprobacion medica.

        El callback recibe (aprobada: bool, notificacion: str).
        """
        self._on_aprobacion_medica = callback

    @property
    def agente(self) -> AgenteState:
        return self._agente

    @property
    def mcp(self) -> MCPClient:
        return self._mcp


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    """Lanza PanelIA como aplicacion independiente."""
    import argparse

    parser = argparse.ArgumentParser(description="3Dosim - Panel de Control IA")
    parser.add_argument("--agente", help="Ruta a agente.json")
    parser.add_argument("--mcp-url", default="http://localhost:2026", help="URL del MCP server de Slicer")
    parser.add_argument("--theme", choices=["light", "dark"], default="dark", help="Tema visual")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    app = PanelIA(
        agente_filepath=args.agente,
        mcp_url=args.mcp_url,
        theme=args.theme,
    )
    app.run()


if __name__ == "__main__":
    main()
