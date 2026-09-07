# 🤖 Orquestador D3 1A

Interfaz gráfica para LM Studio con orquestador inteligente de modelos y búsqueda web.

## ✨ Características

- 🎯 **Selección automática de modelos** según el tipo de tarea
- 🔒 **Selección manual** con atajos (`modelo: prompt`, `@modelo`, `usar modelo`)
- 🌐 **Búsqueda web** con DuckDuckGo
- 🧠 **Gestión de RAM** para evitar modelos pesados
- 💾 **Guardado de conversaciones** en JSON
- 🔥 **Borrado de datos** con un clic
- 🖥️ **Interfaz gráfica** tipo ChatGPT

## 📦 Requisitos

- Python 3.8+
- LM Studio corriendo en `http://localhost:1234`
- Dependencias: `requests`, `duckduckgo-search`

Instalación:

```bash
pip install requests duckduckgo-search
