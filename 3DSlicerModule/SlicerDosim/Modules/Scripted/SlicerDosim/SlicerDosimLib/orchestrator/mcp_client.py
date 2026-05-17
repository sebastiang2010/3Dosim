"""
MCPClient - Cliente para el servidor MCP de 3D Slicer.

Comunicacion via Model Context Protocol (JSON-RPC 2.0 sobre HTTP)
con slicer-mcp-server.py (pieper/slicer-skill) o mcp-slicer (zhaoyouj).

Herramientas expuestas:
    execute_python(code: str) -> dict
        Ejecuta codigo Python en la consola de Slicer.
    screenshot(view: str = "3D") -> bytes
        Captura pantalla de una vista de Slicer.
    list_nodes(filter: str = "") -> list[dict]
        Lista nodos MRML en la escena de Slicer.
    write_file(path: str, content: str) -> bool
        Escribe contenido en un archivo del host.
    read_file(path: str) -> str
        Lee contenido de un archivo del host.

Uso:
    client = MCPClient("http://localhost:2026")
    client.connect()
    result = client.execute_python("slicer.app.majorVersion")
    print(result["output"])
"""

import json
import logging
import time
import urllib.request
import urllib.error
import base64
from typing import Any

logger = logging.getLogger("3Dosim.MCP")

# ---------------------------------------------------------------------------
# Constantes MCP
# ---------------------------------------------------------------------------
JSON_RPC_VERSION = "2.0"
MCP_PROTOCOL_VERSION = "2025-03-26"

# ---------------------------------------------------------------------------
# Errores
# ---------------------------------------------------------------------------

class MCPError(Exception):
    """Error general del MCP client."""
    pass


class MCPConnectionError(MCPError):
    """No se puede conectar al servidor MCP de Slicer."""
    pass


class MCPToolError(MCPError):
    """El tool MCP devolvio un error."""
    def __init__(self, message: str, code: int = -1):
        self.code = code
        super().__init__(f"[{code}] {message}")


# ---------------------------------------------------------------------------
# MCPClient
# ---------------------------------------------------------------------------

class MCPClient:
    """Cliente MCP para 3D Slicer.

    Args:
        base_url: URL base del servidor MCP
                  (default: http://localhost:2026)
        timeout_s: Timeout en segundos para requests HTTP.
    """

    # Endpoints
    MCP_ENDPOINT = "/mcp"
    FILE_ENDPOINT = "/file"

    def __init__(self, base_url: str = "http://localhost:2026", timeout_s: int = 30):
        self._base_url = base_url.rstrip("/")
        self._mcp_url = f"{self._base_url}{self.MCP_ENDPOINT}"
        self._timeout = timeout_s
        self._connected = False
        self._server_info = {}
        self._tools_cache = None
        self._request_id = 0

    # ------------------------------------------------------------------
    # Conexion
    # ------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def server_info(self) -> dict:
        return dict(self._server_info)

    def connect(self) -> bool:
        """Inicializa conexion con el servidor MCP.

        Envia 'initialize' y 'tools/list' para verificar
        que el servidor responde correctamente.

        Returns:
            True si la conexion fue exitosa.
        """
        try:
            logger.info("Conectando a MCP Slicer: %s", self._mcp_url)

            # Paso 1: initialize
            resp = self._jsonrpc_request("initialize", {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {
                    "name": "3Dosim-Orquestador",
                    "version": "3.14.0",
                },
            })

            if "serverInfo" in resp:
                self._server_info = resp["serverInfo"]
                logger.info("MCP conectado: %s v%s",
                            resp["serverInfo"].get("name", "?"),
                            resp["serverInfo"].get("version", "?"))
            else:
                logger.info("MCP conectado (sin serverInfo)")

            # Paso 2: listar tools (calienta cache)
            self._tools_cache = self._list_tools_raw()
            logger.info("MCP tools disponibles: %d", len(self._tools_cache))

            self._connected = True
            return True

        except (urllib.error.URLError, ConnectionError, OSError, json.JSONDecodeError) as e:
            logger.warning("No se pudo conectar a MCP: %s", e)
            self._connected = False
            return False

    def disconnect(self):
        """Cierra la conexion (libera cache)."""
        self._connected = False
        self._server_info = {}
        self._tools_cache = None
        logger.info("MCP desconectado")

    # ------------------------------------------------------------------
    # Tools: descubrimiento
    # ------------------------------------------------------------------

    def list_tools(self) -> list[dict]:
        """Retorna la lista de tools disponibles (con cache)."""
        if self._tools_cache is None:
            self._tools_cache = self._list_tools_raw()
        return list(self._tools_cache)

    def _list_tools_raw(self) -> list[dict]:
        """Consulta los tools al servidor MCP."""
        return self._jsonrpc_request("tools/list", {}).get("tools", [])

    # ------------------------------------------------------------------
    # Tools: ejecucion
    # ------------------------------------------------------------------

    def call_tool(self, name: str, arguments: dict | None = None) -> dict:
        """Ejecuta un tool MCP generico.

        Args:
            name: Nombre del tool ('execute_python', 'screenshot', etc.)
            arguments: Dict con argumentos del tool.

        Returns:
            Dict con el resultado del tool.
            Tipicamente contiene 'content' (lista de mensajes).

        Raises:
            MCPConnectionError: Si no hay conexion.
            MCPToolError: Si el tool devuelve error.
        """
        if not self._connected:
            raise MCPConnectionError("No conectado a MCP. Llame connect() primero.")

        logger.info("MCP call: %s(%s)", name, arguments)
        resp = self._jsonrpc_request("tools/call", {
            "name": name,
            "arguments": arguments or {},
        })

        if "isError" in resp and resp["isError"]:
            error_msg = str(resp.get("content", "Error desconocido"))
            raise MCPToolError(error_msg)

        return resp

    # ------------------------------------------------------------------
    # Tools especificos de Slicer
    # ------------------------------------------------------------------

    def execute_python(self, code: str) -> dict:
        """Ejecuta codigo Python en la consola de Slicer.

        Args:
            code: Codigo Python a ejecutar.

        Returns:
            Dict con 'output' (stdout) y 'result' (valor retornado).
        """
        resp = self.call_tool("execute_python", {"code": code})
        return self._parse_content(resp)

    def screenshot(self, view: str = "3D") -> bytes:
        """Captura screenshot de una vista de Slicer.

        Args:
            view: '3D', 'Red', 'Yellow', 'Green' o 'all'.

        Returns:
            Bytes de la imagen PNG.
        """
        resp = self.call_tool("screenshot", {"view": view})
        content = self._parse_content(resp)

        # El screenshot puede venir como base64 en content
        if isinstance(content, dict) and "data" in content:
            return base64.b64decode(content["data"])
        if isinstance(content, str):
            return base64.b64decode(content)

        # O como lista de content parts
        raise MCPToolError("Formato de screenshot inesperado")

    def list_nodes(self, filter_str: str = "") -> list[dict]:
        """Lista nodos MRML en la escena de Slicer.

        Args:
            filter_str: Filtro opcional por nombre de nodo.

        Returns:
            Lista de dicts con info de cada nodo.
        """
        args = {}
        if filter_str:
            args["filter"] = filter_str
        resp = self.call_tool("list_nodes", args)
        parsed = self._parse_content(resp)
        if isinstance(parsed, list):
            return parsed
        return []

    def write_file(self, path: str, content: str) -> bool:
        """Escribe contenido en un archivo del host Slicer.

        Args:
            path: Ruta absoluta del archivo a escribir.
            content: Contenido del archivo.

        Returns:
            True si se escribio correctamente.
        """
        # Intentar via endpoint /file primero (mas rapido)
        try:
            self._http_post_raw(
                f"{self._base_url}{self.FILE_ENDPOINT}",
                content.encode("utf-8"),
                params={"path": path},
            )
            return True
        except Exception:
            logger.debug("File endpoint fallo, usando tool MCP write_file")
            resp = self.call_tool("write_file", {"path": path, "content": content})
            return not resp.get("isError", False)

    def read_file(self, path: str) -> str:
        """Lee contenido de un archivo del host Slicer.

        Args:
            path: Ruta absoluta del archivo a leer.

        Returns:
            Contenido del archivo como string.
        """
        resp = self.call_tool("read_file", {"path": path})
        parsed = self._parse_content(resp)
        if isinstance(parsed, str):
            return parsed
        return str(parsed)

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _jsonrpc_request(self, method: str, params: dict) -> dict:
        """Envia un request JSON-RPC y parsea la respuesta."""
        payload = json.dumps({
            "jsonrpc": JSON_RPC_VERSION,
            "id": self._next_id(),
            "method": method,
            "params": params,
        }).encode("utf-8")

        try:
            req = urllib.request.Request(
                self._mcp_url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8")
        except urllib.error.HTTPError as e:
            raise MCPConnectionError(f"HTTP {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            raise MCPConnectionError(str(e.reason))
        except OSError as e:
            raise MCPConnectionError(str(e))

        data: dict = json.loads(raw)

        if "error" in data and data["error"] is not None:
            err = data["error"]
            raise MCPToolError(err.get("message", "Error MCP"), err.get("code", -1))

        return data.get("result", data)

    def _http_post_raw(self, url: str, data: bytes, params: dict | None = None):
        """HTTP POST directo (para file transfer)."""
        if params:
            from urllib.parse import urlencode
            qs = urlencode(params)
            url = f"{url}?{qs}"

        req = urllib.request.Request(
            url, data=data, method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:
            resp.read()

    @staticmethod
    def _parse_content(resp: dict) -> Any:
        """Extrae contenido de la respuesta MCP.

        MCP devuelve 'content' como lista de partes con tipo.
        """
        content = resp.get("content", [])
        if isinstance(content, list):
            # Extraer texto de todas las partes de tipo 'text'
            texts = [
                p.get("text", "") for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            ]
            # Intentar parsear JSON si todo es un unico texto
            if len(texts) == 1:
                try:
                    return json.loads(texts[0])
                except (json.JSONDecodeError, TypeError):
                    return texts[0]
            if len(texts) > 1:
                return texts
            # Si no hay text, devolver raw content
            return content
        return content

    def __repr__(self) -> str:
        status = "conectado" if self._connected else "desconectado"
        return f"<MCPClient {self._mcp_url} [{status}]>"
