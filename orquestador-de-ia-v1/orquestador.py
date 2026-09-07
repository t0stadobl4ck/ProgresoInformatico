#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
LM Studio Chat - Interfaz gráfica con orquestador y búsqueda web.
Características:
- Selección automática de modelos según el tipo de tarea
- Selección manual con atajos (modelo: prompt, @modelo, usar modelo)
- Búsqueda web con DuckDuckGo
- Gestión de RAM para evitar modelos pesados
- Guardado automático de conversaciones en JSON
- Botón para borrar todo el historial
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, font, simpledialog
import requests
import threading
import re
import json
from pathlib import Path
from datetime import datetime

# Intentar importar duckduckgo-search
try:
    from duckduckgo_search import DDGS
    DDGS_AVAILABLE = True
except ImportError:
    DDGS_AVAILABLE = False
    print("⚠️ duckduckgo-search no está instalado. La búsqueda web no funcionará.")
    print("Instala con: pip install duckduckgo-search")

# ----------------------------------------------------------------------
# Configuración de modelos
# ----------------------------------------------------------------------
MODELS = {
    "qwen3-1.7b-abliterated": {
        "name": "Qwen Red Team",
        "icon": "🔴",
        "description": "Red Teaming sin censura",
        "keywords": [
            "red team", "pentest", "exploit", "payload", "malware",
            "virus", "troyano", "ransomware", "hack", "hacking",
            "fuerza bruta", "shell reversa", "bypass", "evadir",
            "comprometer sistema", "escalada privilegios",
            "comando y control", "rootkit", "keylogger"
        ],
        "aliases": ["qwen", "redteam", "rt", "qwen1.7"],
        "timeout": 60,
        "ram_required_mb": 2000
    },
    "llama3.2-3b-cybersecurity-abliterated": {
        "name": "Llama Defensa",
        "icon": "🔵",
        "description": "Ciberseguridad defensiva",
        "keywords": [
            "ciberseguridad", "seguridad", "phishing", "firewall",
            "encriptación", "cifrado", "contraseña", "password",
            "autenticación", "defensa", "mitigación", "parche",
            "vulnerabilidad", "riesgo", "auditoría", "blue team",
            "monitoreo", "detección", "respuesta incidente",
            "proteger", "protección", "asegurar", "blindar"
        ],
        "aliases": ["llama", "cyber", "defensa", "blueteam", "bt"],
        "timeout": 90,
        "ram_required_mb": 2500
    },
    "qwen/qwen3-4b-thinking-2507": {
        "name": "Qwen Thinking",
        "icon": "🧠",
        "description": "Razonamiento y programación",
        "keywords": [
            "razonamiento", "analizar", "lógica compleja",
            "problema complejo", "step by step", "paso a paso",
            "demostración", "teorema", "análisis profundo",
            "filosofía", "ética", "abstracto",
            "matemáticas avanzadas", "cálculo", "álgebra",
            "física", "química", "teoría",
            "resuelve esto", "resuelve este problema",
            "explica detalladamente", "análisis exhaustivo",
            "programación", "programar", "código", "script",
            "python", "javascript", "html", "css", "java",
            "c++", "c#", "php", "ruby", "go", "rust",
            "typescript", "sql", "debug", "bug", "algoritmo",
            "función", "clase", "api", "framework", "librería",
            "programame", "hazme", "crea", "desarrolla",
            "implementa", "construye"
        ],
        "aliases": ["thinking", "qwen4", "razon", "think", "code"],
        "timeout": 180,
        "ram_required_mb": 3500
    },
    "mistralai/ministral-3-3b": {
        "name": "Mistral Doc",
        "icon": "📄",
        "description": "Documentos y organización",
        "keywords": [
            "documento", "informe", "reporte", "artículo",
            "ensayo", "tesis", "investigación", "redacción",
            "correo", "carta formal", "resumen ejecutivo",
            "white paper", "documentación", "manual", "guía",
            "procedimiento", "organizar", "organización",
            "planificar", "plan", "agenda", "lista de tareas",
            "calendario", "cronograma", "gestión", "proyecto"
        ],
        "aliases": ["mistral", "doc", "texto", "organiza"],
        "timeout": 120,
        "ram_required_mb": 3500
    },
    "gemma-3-1b-it": {
        "name": "Gemma Chat",
        "icon": "💬",
        "description": "Chat rápido y preguntas simples",
        "keywords": [
            "hola", "hey", "buenas", "cómo estás", "qué tal",
            "chiste", "poema", "historia", "gracias", "ok",
            "qué es", "quién es", "dónde está", "cuándo",
            "cuánto", "cuál es", "definición", "significado",
            "dime", "cuéntame", "lista de", "ejemplos de",
            "tipos de", "características de", "para qué sirve",
            "uso de", "ventajas", "desventajas", "diferencia"
        ],
        "aliases": ["gemma", "chat", "casual", "rapido", "simple", "general"],
        "timeout": 60,
        "ram_required_mb": 1000
    }
}

DEFAULT_MODEL = "gemma-3-1b-it"
API_URL = "http://localhost:1234/v1/chat/completions"
MAX_TOKENS = 2000
MIN_RAM_FOR_HEAVY = 4000  # MB

# Archivo de conversaciones (mismo directorio que el script)
CONVERSATION_FILE = Path(__file__).parent / "conversaciones.json"


# ----------------------------------------------------------------------
# Utilidades del sistema
# ----------------------------------------------------------------------
def get_available_memory_mb():
    """Lee /proc/meminfo y devuelve MB disponibles, o None si no puede."""
    try:
        with open('/proc/meminfo', 'r') as f:
            for line in f:
                if line.startswith('MemAvailable:'):
                    kb = int(line.split()[1])
                    return kb // 1024
    except:
        pass
    return None


def is_heavy_model(model_name):
    """Determina si un modelo requiere mucha RAM (>=3 GB)."""
    config = MODELS.get(model_name)
    if config:
        return config.get("ram_required_mb", 0) >= 3000
    return False


# ----------------------------------------------------------------------
# Búsqueda web con DuckDuckGo
# ----------------------------------------------------------------------
def buscar_duckduckgo(query, max_resultados=5):
    """Busca en DuckDuckGo y retorna resultados formateados."""
    if not DDGS_AVAILABLE:
        return "⚠️ duckduckgo-search no está instalado. Ejecuta: pip install duckduckgo-search"
    try:
        with DDGS() as ddgs:
            resultados = list(ddgs.text(query, max_results=max_resultados))
        if not resultados:
            return "⚠️ Sin resultados"
        contexto = f"🔍 Resultados para: '{query}'\n\n"
        for i, r in enumerate(resultados, 1):
            contexto += f"[{i}] {r.get('title','')}\n    URL: {r.get('href','')}\n    {r.get('body','')[:300]}\n\n"
        return contexto
    except Exception as e:
        return f"⚠️ Error: {e}"


# ----------------------------------------------------------------------
# Clase principal de la interfaz gráfica
# ----------------------------------------------------------------------
class LMStudioChat:
    def __init__(self, root):
        self.root = root
        self.root.title("LM Studio Chat - Orquestador")
        self.root.geometry("1100x750")
        self.root.minsize(900, 650)

        self.forced_model = None
        self.processing = False
        self.conversation = []   # Lista para guardar la conversación

        self.setup_style()
        self.setup_ui()

        self.root.bind('<Control-Return>', lambda e: self.send_message())
        self.root.bind('<Escape>', lambda e: self.clear_input())

        self.add_system_message("Bienvenido. Escribe 'modelo: prompt' para forzar modelo.")
        self.add_system_message("Usa el botón 🌐 Buscar o escribe /buscar consulta")

        # Cargar conversación anterior si existe
        self.load_conversation()

    def setup_style(self):
        self.bg_color = "#1e1e1e"
        self.fg_color = "#ffffff"
        self.user_bubble = "#2b5278"
        self.assistant_bubble = "#2d2d2d"
        self.system_color = "#666666"
        self.sidebar_bg = "#252526"
        self.input_bg = "#333333"

        self.root.configure(bg=self.bg_color)

        self.font_normal = font.Font(family="Segoe UI", size=11)
        self.font_bold = font.Font(family="Segoe UI", size=11, weight="bold")
        self.font_small = font.Font(family="Segoe UI", size=9)
        self.font_title = font.Font(family="Segoe UI", size=14, weight="bold")

    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg=self.bg_color)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.create_sidebar(main_frame)

        right_frame = tk.Frame(main_frame, bg=self.bg_color)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        title_frame = tk.Frame(right_frame, bg=self.bg_color)
        title_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(title_frame, text="💬 Conversación", font=self.font_title,
                bg=self.bg_color, fg=self.fg_color).pack(side=tk.LEFT)

        search_btn = tk.Button(title_frame, text="🌐 Buscar", command=self.open_search_dialog,
                              bg="#4a4a4a", fg="white", relief=tk.FLAT,
                              font=self.font_small, cursor="hand2")
        search_btn.pack(side=tk.RIGHT, padx=5)

        self.create_chat_area(right_frame)
        self.create_input_area(right_frame)

    def create_sidebar(self, parent):
        sidebar = tk.Frame(parent, bg=self.sidebar_bg, width=230)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        tk.Label(sidebar, text="🤖 Modelos", font=self.font_title,
                bg=self.sidebar_bg, fg=self.fg_color).pack(pady=10)

        auto_btn = tk.Button(sidebar, text="✨ Auto-detección", command=self.reset_auto,
                            bg="#4a4a4a", fg="white", relief=tk.FLAT,
                            font=self.font_bold, cursor="hand2")
        auto_btn.pack(fill=tk.X, padx=10, pady=5)

        ttk.Separator(sidebar, orient='horizontal').pack(fill=tk.X, padx=10, pady=5)

        for model_key, model_info in MODELS.items():
            heavy = " ⚠️" if model_info.get("ram_required_mb", 0) >= 3000 else ""
            btn_text = f"{model_info['icon']} {model_info['name']}{heavy}"
            btn = tk.Button(sidebar, text=btn_text, command=lambda m=model_key: self.force_model(m),
                          bg="#3a3a3a", fg="white", relief=tk.FLAT,
                          font=self.font_small, cursor="hand2", anchor="w", padx=10, pady=5)
            btn.pack(fill=tk.X, padx=10, pady=2)

        ttk.Separator(sidebar, orient='horizontal').pack(fill=tk.X, padx=10, pady=5)

        # Botón limpiar chat visual
        clear_btn = tk.Button(sidebar, text="🗑️ Limpiar chat",
                            command=self.clear_chat,
                            bg="#5a3a3a", fg="white", relief=tk.FLAT,
                            font=self.font_small, cursor="hand2")
        clear_btn.pack(fill=tk.X, padx=10, pady=2)

        # Botón guardar conversación
        save_btn = tk.Button(sidebar, text="💾 Guardar conversación",
                           command=self.save_conversation,
                           bg="#3a5a3a", fg="white", relief=tk.FLAT,
                           font=self.font_small, cursor="hand2")
        save_btn.pack(fill=tk.X, padx=10, pady=2)

        # Botón cargar conversación
        load_btn = tk.Button(sidebar, text="📂 Cargar conversación",
                           command=self.load_conversation,
                           bg="#3a3a5a", fg="white", relief=tk.FLAT,
                           font=self.font_small, cursor="hand2")
        load_btn.pack(fill=tk.X, padx=10, pady=2)

        # Botón borrar todo (fuego)
        burn_btn = tk.Button(sidebar, text="🔥 Borrar todo",
                           command=self.clear_all_data,
                           bg="#5a1a1a", fg="#ff6666", relief=tk.FLAT,
                           font=self.font_small, cursor="hand2")
        burn_btn.pack(fill=tk.X, padx=10, pady=2)

        # Estado
        self.status_label = tk.Label(sidebar, text="Auto-detección",
                                   bg=self.sidebar_bg, fg="#aaffaa",
                                   font=self.font_small, wraplength=200)
        self.status_label.pack(side=tk.BOTTOM, pady=10)

        # RAM disponible
        self.ram_label = tk.Label(sidebar, text="", bg=self.sidebar_bg, fg="#cccccc",
                                  font=self.font_small)
        self.ram_label.pack(side=tk.BOTTOM, pady=5)
        self.update_ram_label()

    def update_ram_label(self):
        mb = get_available_memory_mb()
        self.ram_label.config(text=f"RAM libre: {mb if mb else 'N/D'} MB")
        self.root.after(5000, self.update_ram_label)

    def create_chat_area(self, parent):
        chat_frame = tk.Frame(parent, bg=self.bg_color)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.canvas = tk.Canvas(chat_frame, bg=self.bg_color, highlightthickness=0)
        scrollbar = ttk.Scrollbar(chat_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg=self.bg_color)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.canvas.bind("<Enter>", self._bind_mousewheel)
        self.canvas.bind("<Leave>", self._unbind_mousewheel)

    def _bind_mousewheel(self, event):
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _unbind_mousewheel(self, event):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def create_input_area(self, parent):
        input_frame = tk.Frame(parent, bg=self.bg_color)
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        self.input_text = tk.Text(input_frame, height=4,
                                 bg=self.input_bg, fg="white",
                                 insertbackground="white",
                                 font=self.font_normal,
                                 relief=tk.FLAT, padx=10, pady=5)
        self.input_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        send_btn = tk.Button(input_frame, text="➤", command=self.send_message,
                           bg="#007acc", fg="white", font=("Arial", 16),
                           relief=tk.FLAT, cursor="hand2", width=3)
        send_btn.pack(side=tk.RIGHT, padx=(5, 0))

        hint = "Ctrl+Enter enviar | 'modelo: prompt' forzar | 🌐 botón buscar"
        tk.Label(parent, text=hint, bg=self.bg_color, fg=self.system_color,
                font=self.font_small).pack(anchor=tk.W, padx=15, pady=(0, 5))

    # ---------- Métodos de interacción ----------
    def reset_auto(self):
        self.forced_model = None
        self.status_label.config(text="Auto-detección", fg="#aaffaa")
        self.add_system_message("✨ Detección automática activada")

    def force_model(self, model_key):
        self.forced_model = model_key
        model_info = MODELS[model_key]
        self.status_label.config(text=f"Forzado: {model_info['name']}", fg="#ffaa00")
        self.add_system_message(f"🔒 Modelo forzado: {model_info['icon']} {model_info['name']}")

    def clear_chat(self):
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        self.conversation = []

    def clear_all_data(self):
        """Borra la conversación visual y el archivo JSON."""
        if messagebox.askyesno("🔥 Borrar todo",
                               "¿Seguro que quieres borrar TODA la conversación y el archivo guardado?"):
            self.clear_chat()
            try:
                if CONVERSATION_FILE.exists():
                    CONVERSATION_FILE.unlink()
                    self.add_system_message("🔥 Archivo de conversaciones eliminado")
                else:
                    self.add_system_message("📂 No hay archivo guardado")
            except Exception as e:
                self.add_system_message(f"⚠️ Error al borrar: {e}")

    def save_conversation(self):
        """Guarda la conversación en un archivo JSON."""
        try:
            with open(CONVERSATION_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.conversation, f, ensure_ascii=False, indent=2, default=str)
            self.add_system_message(f"💾 Conversación guardada en {CONVERSATION_FILE.name}")
        except Exception as e:
            self.add_system_message(f"⚠️ Error al guardar: {e}")

    def load_conversation(self):
        """Carga la conversación desde JSON si existe."""
        if CONVERSATION_FILE.exists():
            try:
                with open(CONVERSATION_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                for msg in data:
                    if msg.get("type") == "user":
                        self.add_user_message(msg.get("content", ""), msg.get("model"))
                    elif msg.get("type") == "assistant":
                        self.add_assistant_message(msg.get("content", ""), msg.get("model"))
                    elif msg.get("type") == "system":
                        self.add_system_message(msg.get("content", ""))
                self.add_system_message(f"📂 Conversación cargada desde {CONVERSATION_FILE.name}")
            except Exception as e:
                self.add_system_message(f"⚠️ Error al cargar: {e}")

    def add_system_message(self, text):
        frame = tk.Frame(self.scrollable_frame, bg=self.bg_color)
        frame.pack(fill=tk.X, pady=5)
        tk.Label(frame, text=text, bg=self.bg_color, fg=self.system_color,
                font=self.font_small, wraplength=750, justify=tk.LEFT).pack(anchor=tk.W)
        self.canvas.yview_moveto(1.0)
        self.conversation.append({
            "type": "system",
            "content": text,
            "timestamp": datetime.now().isoformat()
        })

    def add_user_message(self, text, model_used=None):
        bubble = tk.Frame(self.scrollable_frame, bg=self.user_bubble, padx=10, pady=5)
        bubble.pack(anchor=tk.E, padx=10, pady=5, fill=tk.X)
        tk.Label(bubble, text="Tú:", bg=self.user_bubble, fg="white",
                font=self.font_bold).pack(anchor=tk.W)
        tk.Label(bubble, text=text, bg=self.user_bubble, fg="white",
                font=self.font_normal, wraplength=750, justify=tk.LEFT).pack(anchor=tk.W)
        if model_used:
            tk.Label(bubble, text=f"→ {model_used}", bg=self.user_bubble,
                    fg="#cccccc", font=self.font_small).pack(anchor=tk.E)
        self.canvas.yview_moveto(1.0)
        self.conversation.append({
            "type": "user",
            "content": text,
            "model": model_used,
            "timestamp": datetime.now().isoformat()
        })

    def add_assistant_message(self, text, model_used=None):
        bubble = tk.Frame(self.scrollable_frame, bg=self.assistant_bubble, padx=10, pady=5)
        bubble.pack(anchor=tk.W, padx=10, pady=5, fill=tk.X)
        tk.Label(bubble, text="Asistente:", bg=self.assistant_bubble, fg="#aaffaa",
                font=self.font_bold).pack(anchor=tk.W)
        tk.Label(bubble, text=text, bg=self.assistant_bubble, fg="white",
                font=self.font_normal, wraplength=750, justify=tk.LEFT).pack(anchor=tk.W)
        if model_used:
            tk.Label(bubble, text=f"→ {model_used}", bg=self.assistant_bubble,
                    fg="#cccccc", font=self.font_small).pack(anchor=tk.E)
        self.canvas.yview_moveto(1.0)
        self.conversation.append({
            "type": "assistant",
            "content": text,
            "model": model_used,
            "timestamp": datetime.now().isoformat()
        })

    def clear_input(self):
        self.input_text.delete("1.0", tk.END)
        return "break"

    def open_search_dialog(self):
        query = simpledialog.askstring("Búsqueda Web", "¿Qué quieres buscar?", parent=self.root)
        if query:
            self.add_user_message(f"🌐 Buscar: {query}")
            self.process_search_query(query)

    def send_message(self):
        if self.processing:
            messagebox.showinfo("Procesando", "Espera a que termine la respuesta actual.")
            return
        user_input = self.input_text.get("1.0", tk.END).strip()
        if not user_input:
            return
        self.clear_input()

        # Búsqueda web
        if user_input.lower().startswith("/buscar") or user_input.lower().startswith("/search"):
            parts = user_input.split(maxsplit=1)
            if len(parts) > 1:
                query = parts[1].strip()
                self.add_user_message(f"🌐 Buscar: {query}")
                self.process_search_query(query)
            else:
                self.add_system_message("⚠️ Uso: /buscar <consulta>")
            return

        prompt, manual_model = self.parse_manual_selection(user_input)
        if prompt is None:
            return

        if manual_model:
            selected_model = manual_model
            reason = "🎯 Manual"
        elif self.forced_model:
            selected_model = self.forced_model
            reason = "🔒 Forzado"
        else:
            selected_model, reason = self.select_model(prompt)

        model_info = MODELS.get(selected_model, {})
        model_display = f"{model_info.get('icon','')} {model_info.get('name', selected_model)}"
        self.add_user_message(prompt, model_display)
        self.add_system_message(f"{reason} → {model_display}")

        self.processing = True
        self.status_label.config(text="Procesando...", fg="#ffaa00")
        thread = threading.Thread(target=self.process_message,
                                  args=(prompt, selected_model, model_display))
        thread.daemon = True
        thread.start()

    def process_search_query(self, query):
        self.add_system_message(f"🔍 Buscando: {query}")
        self.status_label.config(text="Buscando...", fg="#ffaa00")
        def search_and_respond():
            contexto = buscar_duckduckgo(query)
            if contexto.startswith("⚠️"):
                self.root.after(0, self.add_system_message, contexto)
                self.root.after(0, self.status_label.config,
                               {"text": "Error", "fg": "#ff6666"})
                return
            prompt = f"{contexto}\n\nBasándote en la información anterior, responde: {query}\nCita las fuentes usando [1], [2], etc."
            model, reason = self.select_model(query)
            model_info = MODELS.get(model, {})
            model_display = f"{model_info.get('icon','')} {model_info.get('name', model)}"
            self.root.after(0, self.add_system_message, f"{reason} → {model_display}")
            self.root.after(0, self.process_message, prompt, model, model_display)
        threading.Thread(target=search_and_respond, daemon=True).start()

    def process_message(self, prompt, model, model_display):
        try:
            response = self.call_lm_studio(prompt, model)
            self.root.after(0, self.display_response, response, model_display)
        except Exception as e:
            self.root.after(0, self.display_error, str(e))

    def display_response(self, response, model_display):
        self.add_assistant_message(response, model_display)
        self.processing = False
        if self.forced_model:
            self.status_label.config(text=f"Forzado: {model_display}", fg="#ffaa00")
        else:
            self.status_label.config(text="Auto-detección", fg="#aaffaa")

    def display_error(self, error_msg):
        self.add_system_message(f"❌ Error: {error_msg}")
        self.processing = False
        self.status_label.config(text="Error", fg="#ff6666")

    def parse_manual_selection(self, user_input):
        patterns = [
            (r'^([a-zA-Z0-9./_-]+)\s*:\s*(.+)$', False),
            (r'^@([a-zA-Z0-9./_-]+)\s+(.+)$', False),
            (r'^(?:usar|usa|use|con)\s+([a-zA-Z0-9./_-]+)\s+(.+)$', True),
        ]
        for pattern, ignore_case in patterns:
            flags = re.IGNORECASE if ignore_case else 0
            match = re.match(pattern, user_input, flags)
            if match:
                alias = match.group(1)
                prompt = match.group(2).strip()
                model = self.find_model_by_alias(alias)
                if model:
                    return prompt, model
                else:
                    self.add_system_message(f"⚠️ Modelo '{alias}' no encontrado")
                    return None, None
        model = self.find_model_by_alias(user_input)
        if model and len(user_input.split()) <= 2:
            self.force_model(model)
            return None, None
        return user_input, None

    def find_model_by_alias(self, alias):
        alias_lower = alias.lower().strip()
        for model_key, model_info in MODELS.items():
            if alias_lower in model_key.lower() or model_key.lower() in alias_lower:
                return model_key
            for a in model_info.get("aliases", []):
                if alias_lower == a.lower() or alias_lower in a.lower():
                    return model_key
        return None

    def select_model(self, prompt):
        prompt_lower = prompt.lower()
        if self.is_programming(prompt_lower):
            model = "qwen/qwen3-4b-thinking-2507"
            reason = "💻 Programación"
        elif self.matches_keywords(prompt_lower, MODELS["qwen3-1.7b-abliterated"]["keywords"]):
            model = "qwen3-1.7b-abliterated"
            reason = "🔴 Red Teaming"
        elif self.matches_keywords(prompt_lower, MODELS["llama3.2-3b-cybersecurity-abliterated"]["keywords"]):
            model = "llama3.2-3b-cybersecurity-abliterated"
            reason = "🔵 Defensa"
        elif self.is_complex_reasoning(prompt_lower):
            model = "qwen/qwen3-4b-thinking-2507"
            reason = "🧠 Razonamiento"
        elif self.matches_keywords(prompt_lower, MODELS["mistralai/ministral-3-3b"]["keywords"]):
            model = "mistralai/ministral-3-3b"
            reason = "📄 Documento"
        elif self.is_simple_question(prompt_lower) or self.matches_keywords(prompt_lower, MODELS["gemma-3-1b-it"]["keywords"]):
            model = "gemma-3-1b-it"
            reason = "💬 Chat rápido"
        else:
            model = "gemma-3-1b-it"
            reason = "💬 General"

        # Gestión de RAM
        if is_heavy_model(model):
            available_mb = get_available_memory_mb()
            if available_mb is not None and available_mb < MIN_RAM_FOR_HEAVY:
                self.add_system_message(f"⚠️ RAM insuficiente ({available_mb} MB). Usando Gemma.")
                return "gemma-3-1b-it", "💬 Modelo ligero (RAM baja)"
        return model, reason

    def matches_keywords(self, prompt_lower, keywords):
        return any(kw in prompt_lower for kw in keywords)

    def is_programming(self, prompt_lower):
        verbs = ["programa", "programame", "programar", "codifica", "codificar",
                "desarrolla", "crea", "crear", "haz", "hazme", "hacer",
                "escribe", "escribir", "implementa", "construye", "genera",
                "script", "scripting", "automátiza", "automatiza"]
        langs = ["python", "javascript", "java", "c++", "c#", "php", "ruby",
                "go", "rust", "typescript", "html", "css", "sql", "bash",
                "shell", "powershell", "perl", "swift", "kotlin"]
        concepts = ["código", "codigo", "programación", "programacion",
                   "función", "clase", "método", "variable", "loop", "bucle",
                   "array", "lista", "algoritmo", "api", "framework",
                   "librería", "debug", "bug", "página web", "sitio web",
                   "web app", "aplicación web"]
        if any(lang in prompt_lower for lang in langs):
            return True
        if any(concept in prompt_lower for concept in concepts):
            return True
        if any(verb in prompt_lower for verb in verbs):
            return True
        return False

    def is_complex_reasoning(self, prompt_lower):
        patterns = [
            r'\b(resuelve|resolver)\s+(este|el|la|los|las)\s+\w+',
            r'\b(problema complejo|step by step|paso a paso)\b',
            r'\b(demostración|teorema|prueba matemática)\b',
            r'\b(análisis profundo|análisis exhaustivo)\b',
            r'\b(matemáticas avanzadas|cálculo avanzado)\b',
            r'\b(álgebra|geometría|trigonometría)\b',
            r'\b(ecuación diferencial|integral|derivada)\b',
            r'\b(física cuántica|química orgánica)\b',
            r'\b(filosofía|ética|metafísica)\b',
            r'\b(analiza|razona|piensa|deduce|evalúa)\s+\w+',
        ]
        return any(re.search(p, prompt_lower) for p in patterns)

    def is_simple_question(self, prompt_lower):
        patterns = [
            r'^(qué es|que es|qué significa)\s+\w+',
            r'^(quién es|quien es)\s+\w+',
            r'^(dónde|donde)\s+\w+',
            r'^(cuándo|cuando)\s+\w+',
            r'^(cuánto|cuanto)\s+\w+',
            r'^(cuál es|cual es)\s+\w+',
            r'^(definición|significado)\s+\w+',
            r'^(dime|cuéntame|explícame)\s+\w+',
            r'^(lista|ejemplos|tipos)\s+\w+',
        ]
        if any(re.search(p, prompt_lower) for p in patterns):
            return True
        if len(prompt_lower.split()) <= 10 and '?' in prompt_lower:
            return True
        return False

    def call_lm_studio(self, prompt, model):
        config = MODELS.get(model, {})
        timeout = config.get("timeout", 90)
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": MAX_TOKENS,
            "stream": False
        }
        response = requests.post(API_URL, json=payload, headers=headers, timeout=timeout)
        response.raise_for_status()
        data = response.json()
        if "choices" in data and data["choices"]:
            content = data["choices"][0].get("message", {}).get("content", "").strip()
            if content:
                return content
            else:
                raise ValueError("Respuesta vacía")
        else:
            raise ValueError("Formato inesperado")


# ----------------------------------------------------------------------
# Punto de entrada
# ----------------------------------------------------------------------
def main():
    root = tk.Tk()
    app = LMStudioChat(root)
    root.mainloop()


if __name__ == "__main__":
    try:
        import requests
        import tkinter
    except ImportError as e:
        print(f"Falta dependencia: {e}")
        print("Instala con: pip install requests")
        sys.exit(1)
    main()
