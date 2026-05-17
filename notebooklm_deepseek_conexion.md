# NotebookLM + DeepSeek — Conexiones y Alternativas

> Guardado el 16-May-2026 para instalar luego

---

## 1. notebooklm-py ⭐ 13.3k — API Python para NotebookLM real

**Repo:** https://github.com/teng-lin/notebooklm-py

API no oficial de Google NotebookLM desde Python. Permite controlar NotebookLM programaticamente (subir fuentes, consultar, generar audio, etc.). Ideal para conectar DeepSeek con NotebookLM real.

```bash
pip install notebooklm-py
```

### Uso basico
```python
from notebooklm import NotebookLM

client = NotebookLM()
notebook = client.create_notebook("Mi notebook")
notebook.add_source("archivo.pdf")
respuesta = notebook.query("Resumen de este documento")
```

### Como agente de IA (Claude Code, Codex, etc.)
```bash
npx skills add teng-lin/notebooklm-py
```

---

## 2. opensource_notebooklm ⭐ 302 — Clon de NotebookLM con DeepSeek-V3

**Repo:** https://github.com/satvik314/opensource_notebooklm

Implementacion open-source de NotebookLM usando **DeepSeek-V3** como LLM + PlayHT para TTS. Genera conversaciones educativas tipo podcast. Corre en Google Colab.

### Requisitos
- Python 3.x
- API key de OpenRouter
- API key de FAL

### Instalacion
```bash
git clone https://github.com/satvik314/opensource_notebooklm.git
cd opensource_notebooklm
pip install -r requirements.txt
```

O directamente en Colab:
https://colab.research.google.com/drive/1lSzgEXw9F4X65qSSgOs47ejMGRDkbuZH?usp=sharing

---

## 3. KnowNote ⭐ 983 — Alternativa local-first a NotebookLM

**Repo:** https://github.com/MrSibe/KnowNote

App de escritorio Electron, local-first, sin Docker. Soporta DeepSeek, OpenAI, Ollama como providers. RAG con trazabilidad de fuentes.

### Instalacion
```bash
git clone https://github.com/MrSibe/KnowNote.git
cd KnowNote
pnpm install
pnpm dev
```

- Lanzamientos: v1.2.0 (Ene 2026)
- Licencia: GPL-3.0

---

## 4. open-notebook — NotebookLM open-source multi-provider

**Repo:** https://github.com/lfnovo/open_notebook

Soporta **Google (GenAI + Vertex AI) Y DeepSeek** como proveedores simultaneamente. RAG con citas, API REST completa.

### Providers soportados
| Provider | LLM | Embeddings | TTS |
|---|---|---|---|
| Google GenAI | ✅ | ✅ | ✅ |
| Vertex AI | ✅ | ✅ | ✅ |
| DeepSeek | ✅ | ❌ | ❌ |
| OpenAI | ✅ | ✅ | ✅ |
| Anthropic | ✅ | ❌ | ❌ |
| Ollama | ✅ | ✅ | ❌ |
| y mas... | | | |

### Instalacion
```bash
git clone https://github.com/lfnovo/open_notebook.git
cd open_notebook
# ver documentacion del repo para instrucciones detalladas
```

---

## 5. Notebook Toolkit — Extension Chrome

**Web:** https://notebooktoolkit.com/integrations/deepseek

Extension de Chrome que agrega un boton de **exportacion directa** desde DeepSeek a NotebookLM. Guarda conversaciones con code blocks y razonamiento intactos como fuentes buscables en NotebookLM.

### Instalacion
1. Instalar extension desde Chrome Web Store
2. Crear cuenta en notebooktoolkit.com (plan free disponible)
3. Navegar a chat.deepseek.com
4. Click en el boton de Notebook Toolkit → seleccionar conversacion → guardar en NotebookLM

Funciona en: Chrome, Edge, Brave, Arc.

---

## Resumen: cual usar segun tu caso

| Si quieres... | Usa esto |
|---|---|
| Controlar NotebookLM real desde Python | notebooklm-py |
| Exportar chats de DeepSeek a NotebookLM | Notebook Toolkit (extension) |
| Un clon de NotebookLM con DeepSeek como motor | opensource_notebooklm (Colab) |
| App desktop local sin depender de Google | KnowNote |
| Multi-provider (Google + DeepSeek juntos) | open-notebook |
