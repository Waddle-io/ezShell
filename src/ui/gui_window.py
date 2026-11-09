"""Desktop GUI window for ezShell — CustomTkinter.

Fenêtre de bureau moderne, concise et épurée pour ezShell.
Design inspiré des standards de Raycast, Warp et macOS Spotlight :
- Bouton '···' dans le coin supérieur droit ouvrant le menu popover
- Menu popover avec sélecteur de thème (Auto/Clair/Sombre), zoom (- / +) et options (Préférences, Raccourcis, À propos)
- Barre de saisie épurée avec prompt chevron, placeholder persistant et badge keycap [↵]
- Carte de contexte avec boutons en pilules (🩺 Diagnostiquer l'erreur, 📄 Expliquer la commande)
- Footer avec badges de touches keycaps dédiés ([↵], [Esc], [Alt+E])
"""
from __future__ import annotations

import os
import re
import threading
import warnings
from pathlib import Path
from typing import Optional

# Suppress spurious CustomTkinter HighDPI warning when using native tk.PhotoImage
warnings.filterwarnings("ignore", message=".*Given image is not CTkImage.*")

import customtkinter as ctk
import tkinter as tk
from PIL import Image

try:
    from PIL import ImageTk
    HAS_IMAGETK = True
except ImportError:
    ImageTk = None
    HAS_IMAGETK = False

from src import __version__
from src.core import chat_bridge
from src.core.assistant import ChatMessageResult
from src.core.config import EzShellConfig
from src.core.context import SystemContext, get_last_exit_code, get_last_shell_command
from src.core.provider import get_provider
from src.core.pty_shell import PTYExecutor
from src.core.safety import RiskLevel
from src.i18n import t


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clean_markdown(text: str) -> str:
    """Nettoie le markdown brut pour un affichage lisible et soigné."""
    if not text:
        return ""
    cleaned = re.sub(r"```[a-zA-Z]*\n[\s\S]*?\n```", "", text)
    cleaned = re.sub(r"`(.*?)`", r"\1", cleaned)
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    cleaned = re.sub(r"(?im)^\s*Command\s*:?\s*$", "", cleaned)
    cleaned = re.sub(r"(?im)^\s*What it does\s*:?\s*$", "", cleaned)
    cleaned = re.sub(r"(?im)^\s*Explication\s*:?\s*$", "", cleaned)
    cleaned = re.sub(r"(?im)^\s*Solution\s*:?\s*$", "", cleaned)
    lines = []
    for line in cleaned.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("- ") or s.startswith("* "):
            lines.append("  • " + s[2:].strip())
        else:
            lines.append(s)
    return "\n".join(lines).strip()


# ---------------------------------------------------------------------------
# Menu Popover (Trois petits points '···')
# ---------------------------------------------------------------------------

class MenuPopover(ctk.CTkFrame):
    """Menu popover contextuel affiché au clic sur le bouton '···'."""

    def __init__(self, master, app: EzShellDesktopApp, **kwargs):
        super().__init__(
            master,
            fg_color="#0F1117",
            border_color="#222632",
            border_width=1,
            corner_radius=12,
            width=240,
            **kwargs,
        )
        self.app = app
        self._build_content()

    def _build_content(self) -> None:
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=14, pady=14)

        # 1. Rangée Thèmes : Système (Auto), Clair, Sombre
        themes_row = ctk.CTkFrame(container, fg_color="transparent")
        themes_row.pack(fill="x", pady=(0, 12))

        self.btn_theme_sys = self._create_theme_circle(themes_row, mode="system", label="Auto", symbol="🌓")
        self.btn_theme_sys.pack(side="left", expand=True, padx=4)

        self.btn_theme_light = self._create_theme_circle(themes_row, mode="light", label="Clair", symbol="☀️")
        self.btn_theme_light.pack(side="left", expand=True, padx=4)

        self.btn_theme_dark = self._create_theme_circle(themes_row, mode="dark", label="Sombre", symbol="🌙")
        self.btn_theme_dark.pack(side="left", expand=True, padx=4)

        self._refresh_theme_selection()

        # 2. Rangée Zoom / Échelle : [-] [100%] [+]
        zoom_row = ctk.CTkFrame(
            container,
            fg_color="#151821",
            border_color="#222632",
            border_width=1,
            corner_radius=8,
            height=34,
        )
        zoom_row.pack(fill="x", pady=(0, 12))
        zoom_row.pack_propagate(False)

        btn_minus = ctk.CTkButton(
            zoom_row,
            text="−",
            width=32,
            height=28,
            fg_color="transparent",
            hover_color="#232734",
            text_color="#CBD5E1",
            font=ctk.CTkFont(family=EzShellDesktopApp.FONT_UI, size=15, weight="bold"),
            command=self.app.zoom_out,
        )
        btn_minus.pack(side="left", padx=3, pady=3)

        self.zoom_lbl = ctk.CTkLabel(
            zoom_row,
            text=f"{int(self.app.scale_factor * 100)}%",
            text_color="#CBD5E1",
            font=ctk.CTkFont(family=EzShellDesktopApp.FONT_UI, size=11, weight="bold"),
        )
        self.zoom_lbl.pack(side="left", fill="x", expand=True)

        btn_plus = ctk.CTkButton(
            zoom_row,
            text="+",
            width=32,
            height=28,
            fg_color="transparent",
            hover_color="#232734",
            text_color="#CBD5E1",
            font=ctk.CTkFont(family=EzShellDesktopApp.FONT_UI, size=15, weight="bold"),
            command=self.app.zoom_in,
        )
        btn_plus.pack(side="right", padx=3, pady=3)

        # Séparateur fin
        ctk.CTkFrame(container, fg_color="#1E232E", height=1).pack(fill="x", pady=(0, 10))

        # 3. Liste des options avec raccourcis
        self._add_menu_item(container, "⚙  Préférences", "Ctrl+,", self.app.open_preferences)
        self._add_menu_item(container, "⌨  Raccourcis clavier", "Ctrl+?", self.app.open_shortcuts)
        self._add_menu_item(container, "↻  Vérifier les MàJ", "", self.app.check_updates)
        self._add_menu_item(container, "ℹ  À propos d'ezShell", f"v{__version__}", self.app.open_about)

    def _create_theme_circle(self, parent, mode: str, label: str, symbol: str) -> ctk.CTkButton:
        btn = ctk.CTkButton(
            parent,
            text=symbol,
            width=40,
            height=40,
            corner_radius=20,
            fg_color="#151821",
            hover_color="#252A36",
            border_color="#222632",
            border_width=1,
            text_color="#F8FAFC",
            font=ctk.CTkFont(family=EzShellDesktopApp.FONT_UI, size=14),
            command=lambda: self._select_theme(mode),
        )
        return btn

    def _select_theme(self, mode: str) -> None:
        self.app.set_theme(mode)
        self._refresh_theme_selection()

    def _refresh_theme_selection(self) -> None:
        mode = self.app.current_theme
        for btn, btn_mode in (
            (self.btn_theme_sys, "system"),
            (self.btn_theme_light, "light"),
            (self.btn_theme_dark, "dark"),
        ):
            if btn_mode == mode:
                btn.configure(border_color="#94A3B8", border_width=1.5, fg_color="#1E232E")
            else:
                btn.configure(border_color="#222632", border_width=1, fg_color="#151821")

    def _add_menu_item(self, parent, label: str, shortcut: str, command) -> None:
        item = ctk.CTkFrame(parent, fg_color="transparent", height=28, corner_radius=6)
        item.pack(fill="x", pady=(0, 2))

        lbl_text = ctk.CTkLabel(
            item,
            text=label,
            text_color="#E2E8F0",
            font=ctk.CTkFont(family=EzShellDesktopApp.FONT_UI, size=11),
            anchor="w",
        )
        lbl_text.pack(side="left", padx=8, pady=4)

        if shortcut:
            lbl_sc = ctk.CTkLabel(
                item,
                text=shortcut,
                text_color="#64748B",
                font=ctk.CTkFont(family=EzShellDesktopApp.FONT_UI, size=10),
                anchor="e",
            )
            lbl_sc.pack(side="right", padx=8, pady=4)

        def _hover_enter(e):
            item.configure(fg_color="#1A1E29")

        def _hover_leave(e):
            item.configure(fg_color="transparent")

        def _click(e):
            self.app.hide_menu()
            command()

        for w in (item, lbl_text):
            w.bind("<Enter>", _hover_enter)
            w.bind("<Leave>", _hover_leave)
            w.bind("<Button-1>", _click)

        if shortcut:
            lbl_sc.bind("<Enter>", _hover_enter)
            lbl_sc.bind("<Leave>", _hover_leave)
            lbl_sc.bind("<Button-1>", _click)


# ---------------------------------------------------------------------------
# Main Application Window
# ---------------------------------------------------------------------------

class EzShellDesktopApp(ctk.CTk):
    """Fenêtre desktop concise, moderne et épurée pour ezShell."""

    # Typographie
    FONT_UI = "Inter"
    FONT_TITLE = "Inter Display"
    FONT_CODE = "JetBrains Mono"

    # Palette Obsidian & Sky Blue (fidèle à la maquette)
    COLOR_BG = "#0B0C10"           # Fond obsidian très sombre
    COLOR_CARD = "#12141A"         # Cartes et conteneurs
    COLOR_CODE = "#08090D"         # Blocs monospace
    COLOR_INPUT = "#14161D"        # Fond de la barre de saisie
    COLOR_BORDER = "#1E222B"       # Bordures fines et douces

    COLOR_ACCENT = "#38BDF8"       # Cyan clair
    COLOR_PRIMARY = "#3B82F6"      # Bleu royal d'action
    COLOR_PRIMARY_HOVER = "#2563EB"

    COLOR_TEXT = "#F8FAFC"         # Blanc cassé principal
    COLOR_TEXT_MUTED = "#94A3B8"   # Slate moyen
    COLOR_TEXT_DIM = "#64748B"     # Placeholders & astuces
    COLOR_TEXT_KEY = "#CBD5E1"     # Touches keycaps

    COLOR_SUCCESS = "#10B981"      # Vert émeraude statut
    COLOR_WARNING = "#F59E0B"      # Orange avertissement
    COLOR_DANGER = "#EF4444"       # Rouge erreur / danger

    # Dimensions généreuses et aérées (style Raycast / macOS)
    WIDTH = 760
    HEIGHT_LAUNCHER = 440
    HEIGHT_RESULT = 560

    def __init__(
        self,
        config: Optional[EzShellConfig] = None,
        initial_query: Optional[str] = None,
        error_context: Optional[str] = None,
    ):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        super().__init__()

        self.config = config or EzShellConfig.load()
        self.context = SystemContext.collect()
        self.provider = get_provider(self.config)

        # État
        self.current_query = initial_query or ""
        self.current_cause = ""
        self.current_cmd = ""
        self.current_risk_level = RiskLevel.SAFE
        self.current_risk_reason = ""

        # Détection de la dernière commande de la session de terminal courante
        from src.core.capture import read_last_run
        last_run = read_last_run()
        if last_run and last_run.command:
            self.last_detected_cmd = last_run.command.strip()
            self.last_exit_code = last_run.exit_code
        else:
            self.last_detected_cmd = ""
            self.last_exit_code = None

        self.is_loading = False

        # Thème et Échelle
        self.current_theme = "dark"
        self.scale_factor = 1.0

        # Menu Popover instance
        self.menu_popover: Optional[MenuPopover] = None

        # Configuration de la fenêtre
        self.title("ezShell")
        self.configure(fg_color=self.COLOR_BG)
        self._apply_os_window_decorations()

        # Dimensionnement initial
        init_h = self.HEIGHT_RESULT if initial_query else self.HEIGHT_LAUNCHER
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = max(0, (sw - self.WIDTH) // 2)
            y = max(0, (sh - init_h) // 2)
            self.geometry(f"{self.WIDTH}x{init_h}+{x}+{y}")
        except Exception:
            self.geometry(f"{self.WIDTH}x{init_h}")

        self.minsize(680, 380)

        # Raccourcis globaux
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<KeyPress>", self._handle_global_key)
        self.bind("<Button-1>", self._on_global_click, add="+")

        # Déplacement à la souris
        self._drag_x = 0
        self._drag_y = 0

        self._build_layout()

        if initial_query:
            if hasattr(self, "input_entry"):
                self.input_entry.insert(0, initial_query)
            self._query_groq(initial_query)

    # -----------------------------------------------------------------------
    # Layout global
    # -----------------------------------------------------------------------

    def _build_layout(self) -> None:
        """Construit le cadre global : Header → Séparateur → Body → Séparateur → Footer."""
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=(12, 10))

        # 1. Header supérieur (hauteur 30 px)
        self._build_header()
        self._divider(self.main_container, pad=(0, 10))

        # 2. Footer inférieur (hauteur 24 px)
        self.footer_bar = ctk.CTkFrame(self.main_container, fg_color="transparent", height=24)
        self.footer_bar.pack(side="bottom", fill="x")
        self._build_footer()
        self._divider(self.main_container, pad=(4, 8), side="bottom")

        # 3. Corps dynamique central
        self.body_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.body_container.pack(fill="both", expand=True)

        if self.current_query:
            self._render_result_view()
        else:
            self._render_launcher_view()

    def _divider(self, parent, pad=(0, 0), side="top") -> None:
        ctk.CTkFrame(parent, fg_color=self.COLOR_BORDER, height=1).pack(
            side=side, fill="x", pady=pad
        )

    # -----------------------------------------------------------------------
    # Header épuré avec bouton '···'
    # -----------------------------------------------------------------------

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self.main_container, fg_color="transparent", height=30)
        hdr.pack(fill="x", pady=(0, 6))

        for w in (hdr,):
            w.bind("<ButtonPress-1>", self._start_drag)
            w.bind("<B1-Motion>", self._on_drag)

        # Gauche : Logo '>_' en gras blanc + ezShell
        left = ctk.CTkFrame(hdr, fg_color="transparent")
        left.pack(side="left")
        left.bind("<ButtonPress-1>", self._start_drag)
        left.bind("<B1-Motion>", self._on_drag)

        logo_prompt = ctk.CTkLabel(
            left,
            text="❯_",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=self.FONT_CODE, size=18, weight="bold"),
        )
        logo_prompt.pack(side="left", padx=(0, 8))
        logo_prompt.bind("<ButtonPress-1>", self._start_drag)
        logo_prompt.bind("<B1-Motion>", self._on_drag)

        title_text = ctk.CTkLabel(
            left,
            text="ezShell",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=self.FONT_TITLE, size=17, weight="bold"),
        )
        title_text.pack(side="left")
        title_text.bind("<ButtonPress-1>", self._start_drag)
        title_text.bind("<B1-Motion>", self._on_drag)

        # Droite : Bouton circulaire '···' (Options / Popover)
        self.btn_menu = ctk.CTkButton(
            hdr,
            text="···",
            width=30,
            height=30,
            corner_radius=15,
            fg_color="#161820",
            hover_color="#242834",
            border_color="#262A36",
            border_width=1,
            text_color=self.COLOR_TEXT_KEY,
            font=ctk.CTkFont(family=self.FONT_UI, size=14, weight="bold"),
            command=self.toggle_menu,
        )
        self.btn_menu.pack(side="right")

    # -----------------------------------------------------------------------
    # Footer dynamique unifié style Hyprland (Keycaps contextuels)
    # -----------------------------------------------------------------------

    def _build_footer(self, is_result: bool = False) -> None:
        for w in self.footer_bar.winfo_children():
            w.destroy()

        left = ctk.CTkFrame(self.footer_bar, fg_color="transparent")
        left.pack(side="left")

        if is_result and self.current_cmd:
            self._add_footer_keycap(left, "↵", t("action_run"), command=self.run_current_command, accent=True)
            self._add_footer_keycap(left, "c", t("action_copy"), command=self.copy_current_command)
            self._add_footer_keycap(left, "e", t("action_edit"), command=self.edit_current_command)
            self._add_footer_keycap(left, "Esc", t("action_back"), command=self._reset_to_launcher)
        elif is_result:
            self._add_footer_keycap(left, "Esc", t("action_back"), command=self._reset_to_launcher)
        else:
            self._add_footer_keycap(left, "↵", "Entrée  Poser / Exécuter", command=self._on_submit_input)
            self._add_footer_keycap(left, "Esc", "Fermer", is_esc=True)
            self._add_footer_keycap(left, "Alt+E", "Raccourci")

    def _add_footer_keycap(
        self,
        parent,
        key: str,
        label: str,
        command=None,
        is_esc: bool = False,
        accent: bool = False,
    ) -> None:
        item = ctk.CTkFrame(parent, fg_color="transparent")
        item.pack(side="left", padx=(0, 12))

        cap_bg = self.COLOR_PRIMARY if accent else "#171A27"
        cap_border = self.COLOR_PRIMARY_HOVER if accent else "#293044"
        cap = ctk.CTkFrame(
            item,
            fg_color=cap_bg,
            border_color=cap_border,
            border_width=1,
            corner_radius=5,
        )
        cap.pack(side="left", padx=(0, 5))

        cap_lbl = ctk.CTkLabel(
            cap,
            text=key,
            text_color="#FFFFFF" if accent else self.COLOR_TEXT_KEY,
            font=ctk.CTkFont(family=self.FONT_UI, size=9, weight="bold"),
        )
        cap_lbl.pack(padx=6, pady=2)

        lbl = ctk.CTkLabel(
            item,
            text=label,
            text_color="#FFFFFF" if accent else self.COLOR_TEXT_DIM,
            font=ctk.CTkFont(family=self.FONT_UI, size=9, weight="bold" if accent else "normal"),
        )
        lbl.pack(side="left")

        def _hover_enter(e):
            if not accent:
                cap.configure(border_color=self.COLOR_ACCENT)
                lbl.configure(text_color=self.COLOR_TEXT)

        def _hover_leave(e):
            if not accent:
                cap.configure(border_color=cap_border)
                lbl.configure(text_color=self.COLOR_TEXT_DIM)

        click_target = (lambda e: self.destroy()) if is_esc else (lambda e: command() if command else None)
        for w in (item, cap, cap_lbl, lbl):
            if is_esc or command:
                w.bind("<Button-1>", click_target)
                w.bind("<Enter>", _hover_enter)
                w.bind("<Leave>", _hover_leave)

    # -----------------------------------------------------------------------
    # VUE 1 : Launcher / Accueil
    # -----------------------------------------------------------------------

    def _render_launcher_view(self) -> None:
        """Affiche le launcher épuré fidèle à la maquette."""
        self._resize_window(self.HEIGHT_LAUNCHER)
        self._build_footer(is_result=False)

        for w in self.body_container.winfo_children():
            w.destroy()

        # 1. Barre de saisie centrale épurée (sans bordure ni focus ring)
        search_card = ctk.CTkFrame(
            self.body_container,
            fg_color=self.COLOR_INPUT,
            border_width=0,
            corner_radius=10,
            height=48,
        )
        search_card.pack(fill="x", pady=(2, 12))
        search_card.pack_propagate(False)

        # Chevron prompt '❯' en gris clair
        ctk.CTkLabel(
            search_card,
            text="❯",
            text_color=self.COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=self.FONT_CODE, size=15, weight="bold"),
        ).pack(side="left", padx=(14, 8))

        # Champ de saisie réactif avec placeholder natif CTkEntry
        self.input_entry = ctk.CTkEntry(
            search_card,
            placeholder_text=t("input_placeholder"),
            placeholder_text_color=self.COLOR_TEXT_DIM,
            fg_color="transparent",
            border_width=0,
            text_color=self.COLOR_TEXT,
            font=ctk.CTkFont(family=self.FONT_UI, size=13),
        )
        self.input_entry.pack(side="left", fill="both", expand=True, padx=(0, 6))

        self.input_entry.bind("<Return>", self._on_input_return)

        # Clic n'importe où sur la barre pour activer le focus
        search_card.bind("<Button-1>", lambda e: self._focus_input())

        # Focus automatique dès le chargement de la vue
        self.after(50, self._focus_input)

        # Keycap de validation [ ↵ ] à droite
        keycap = ctk.CTkFrame(
            search_card,
            fg_color="#181B24",
            border_color="#2A2E3B",
            border_width=1,
            corner_radius=4,
            width=28,
            height=22,
        )
        keycap.pack(side="right", padx=(0, 10))

        keycap_lbl = ctk.CTkLabel(
            keycap,
            text="↵",
            text_color=self.COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=self.FONT_UI, size=11, weight="bold"),
        )
        keycap_lbl.pack(fill="both", expand=True, padx=4, pady=1)

        def _on_keycap_enter(e):
            keycap.configure(fg_color=self.COLOR_PRIMARY, border_color=self.COLOR_PRIMARY_HOVER)
            keycap_lbl.configure(text_color="#FFFFFF")

        def _on_keycap_leave(e):
            keycap.configure(fg_color="#181B24", border_color="#2A2E3B")
            keycap_lbl.configure(text_color=self.COLOR_TEXT_MUTED)

        for w in (keycap, keycap_lbl):
            w.bind("<Button-1>", lambda e: self._on_submit_input())
            w.bind("<Enter>", _on_keycap_enter)
            w.bind("<Leave>", _on_keycap_leave)

        # 2. Carte de contexte terminal
        if self.last_detected_cmd:
            self._render_last_cmd_card()
        else:
            self._render_system_card()

    def _render_last_cmd_card(self) -> None:
        """Carte de la dernière commande avec boutons pilules conformes à la maquette."""
        card = ctk.CTkFrame(
            self.body_container,
            fg_color=self.COLOR_CARD,
            border_color=self.COLOR_BORDER,
            border_width=1,
            corner_radius=10,
        )
        card.pack(fill="x", pady=(0, 10))

        # En-tête : ● Last command detected in terminal:
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=16, pady=(12, 6))

        ctk.CTkLabel(
            top,
            text="●",
            text_color=self.COLOR_SUCCESS,
            font=ctk.CTkFont(family=self.FONT_UI, size=8),
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            top,
            text=t("last_cmd_detected"),
            text_color=self.COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=self.FONT_UI, size=11),
            anchor="w",
        ).pack(side="left")

        if self.last_exit_code is not None:
            is_err = self.last_exit_code != 0
            bg = "#2B1216" if is_err else "#0F291E"
            fg = self.COLOR_DANGER if is_err else self.COLOR_SUCCESS
            txt = f"✘ Exit {self.last_exit_code}" if is_err else "✓ Exit 0"

            ctk.CTkLabel(
                top,
                text=txt,
                text_color=fg,
                fg_color=bg,
                corner_radius=4,
                font=ctk.CTkFont(family=self.FONT_CODE, size=10, weight="bold"),
                padx=6,
                pady=1,
            ).pack(side="right")

        # Bloc monospace de la commande
        cmd_box = ctk.CTkFrame(
            card,
            fg_color=self.COLOR_CODE,
            border_color="#181A22",
            border_width=1,
            corner_radius=8,
            height=46,
        )
        cmd_box.pack(fill="x", padx=16, pady=(0, 12))
        cmd_box.pack_propagate(False)

        cmd_inner = ctk.CTkFrame(cmd_box, fg_color="transparent")
        cmd_inner.pack(fill="both", expand=True, padx=12, pady=8)

        ctk.CTkLabel(
            cmd_inner,
            text="$",
            text_color=self.COLOR_ACCENT,
            font=ctk.CTkFont(family=self.FONT_CODE, size=12, weight="bold"),
        ).pack(side="left", padx=(0, 8))

        cmd_lbl = ctk.CTkLabel(
            cmd_inner,
            text=self.last_detected_cmd,
            text_color=self.COLOR_TEXT,
            font=ctk.CTkFont(family=self.FONT_CODE, size=12, weight="bold"),
            anchor="w",
        )
        cmd_lbl.pack(side="left", fill="x", expand=True)
        self._autowrap(cmd_lbl, 20)

        # Ligne de boutons pilules (rounded-full)
        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(fill="x", padx=16, pady=(0, 14))

        is_error = self.last_exit_code is not None and self.last_exit_code != 0

        if is_error:
            # Bouton 1 : 🩺 Diagnose this error (affiché uniquement en cas d'erreur)
            btn_diag = ctk.CTkButton(
                btns,
                text="🩺  Diagnose this error",
                height=34,
                corner_radius=17,
                fg_color="#282D39",
                hover_color="#363C4C",
                border_color="#3B4252",
                border_width=1,
                text_color="#FFFFFF",
                font=ctk.CTkFont(family=self.FONT_UI, size=11, weight="bold"),
                command=lambda: self._query_groq(
                    f"diagnose failed command: {self.last_detected_cmd}",
                    mode="explain_error",
                ),
            )
            btn_diag.pack(side="left", padx=(0, 10))

        # Bouton : 📄 Explain command
        btn_expl = ctk.CTkButton(
            btns,
            text="📄  Explain command",
            height=34,
            corner_radius=17,
            fg_color="#282D39" if not is_error else "#14171E",
            hover_color="#363C4C" if not is_error else "#1C212B",
            border_color="#3B4252" if not is_error else "#242835",
            border_width=1,
            text_color="#FFFFFF" if not is_error else self.COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=self.FONT_UI, size=11, weight="bold" if not is_error else "normal"),
            command=lambda: self._query_groq(
                f"explain what this command does: {self.last_detected_cmd}",
                mode="explain_command",
            ),
        )
        btn_expl.pack(side="left")

    def _render_system_card(self) -> None:
        """Carte de statut système épurée."""
        card = ctk.CTkFrame(
            self.body_container,
            fg_color=self.COLOR_CARD,
            border_color=self.COLOR_BORDER,
            border_width=1,
            corner_radius=8,
        )
        card.pack(fill="x", pady=(0, 4))

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(8, 4))

        ctk.CTkLabel(
            top,
            text="●",
            text_color=self.COLOR_SUCCESS,
            font=ctk.CTkFont(family=self.FONT_UI, size=8),
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            top,
            text=t("status_ready"),
            text_color=self.COLOR_TEXT,
            font=ctk.CTkFont(family=self.FONT_UI, size=11, weight="bold"),
            anchor="w",
        ).pack(side="left")

        ctk.CTkLabel(
            top,
            text="Ready",
            text_color=self.COLOR_SUCCESS,
            font=ctk.CTkFont(family=self.FONT_UI, size=10, weight="bold"),
        ).pack(side="right")

        chips = ctk.CTkFrame(card, fg_color="transparent")
        chips.pack(fill="x", padx=14, pady=(0, 10))

        cwd_name = Path(self.context.current_directory).name or "/"
        items = [
            f"OS: {self.context.os_name} ({self.context.architecture})",
            f"Shell: {self.context.shell_name}",
            f"Dir: {cwd_name}",
        ]
        if self.context.git_branch:
            items.append(f"Git: {self.context.git_branch}")

        for it in items:
            ctk.CTkLabel(
                chips,
                text=it,
                text_color=self.COLOR_TEXT_MUTED,
                fg_color=self.COLOR_INPUT,
                corner_radius=4,
                font=ctk.CTkFont(family=self.FONT_CODE, size=10),
                padx=8,
                pady=2,
            ).pack(side="left", padx=(0, 6), pady=2)

    # -----------------------------------------------------------------------
    # VUE 2 : Diagnostic & Résultat
    # -----------------------------------------------------------------------

    def _render_result_view(self) -> None:
        """Affiche la vue complète et lisible de diagnostic."""
        self._resize_window(self.HEIGHT_RESULT)
        self._build_footer(is_result=True)

        for w in self.body_container.winfo_children():
            w.destroy()

        # Zone inférieure fixe (relance)
        bottom_area = ctk.CTkFrame(self.body_container, fg_color="transparent")
        bottom_area.pack(side="bottom", fill="x", pady=(2, 0))

        # Champ de relance épuré
        input_box = ctk.CTkFrame(
            bottom_area,
            fg_color=self.COLOR_INPUT,
            border_width=0,
            corner_radius=8,
            height=38,
        )
        input_box.pack(fill="x", pady=(0, 4))
        input_box.pack_propagate(False)

        ctk.CTkLabel(
            input_box,
            text="❯",
            text_color=self.COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=self.FONT_CODE, size=14, weight="bold"),
        ).pack(side="left", padx=(10, 4))

        self.followup_entry = ctk.CTkEntry(
            input_box,
            placeholder_text=t("input_placeholder"),
            placeholder_text_color=self.COLOR_TEXT_DIM,
            fg_color="transparent",
            border_width=0,
            text_color=self.COLOR_TEXT,
            font=ctk.CTkFont(family=self.FONT_CODE, size=12),
        )
        self.followup_entry.pack(side="left", fill="both", expand=True, padx=(0, 4))
        self.followup_entry.bind("<Return>", self._on_followup_return)
        input_box.bind("<Button-1>", lambda e: self.followup_entry.focus_set())

        # Bouton retour vers le launcher (icône discrète)
        back_btn = ctk.CTkButton(
            input_box,
            text="↩",
            width=26,
            height=22,
            corner_radius=4,
            fg_color="transparent",
            hover_color="#1E222B",
            border_width=0,
            text_color=self.COLOR_TEXT_DIM,
            font=ctk.CTkFont(family=self.FONT_UI, size=13),
            command=self._reset_to_launcher,
        )
        back_btn.pack(side="right", padx=(0, 8), pady=4)

        # Zone centrale défilante (Query, CAUSE, FIX, RISQUE)
        scroll = ctk.CTkScrollableFrame(
            self.body_container,
            fg_color="transparent",
            scrollbar_button_color=self.COLOR_CARD,
            scrollbar_button_hover_color=self.COLOR_PRIMARY,
        )
        scroll.pack(fill="both", expand=True, pady=(0, 6))

        # 1. Question posée : > {query}
        q_frame = ctk.CTkFrame(scroll, fg_color="transparent")
        q_frame.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            q_frame,
            text="❯",
            text_color=self.COLOR_ACCENT,
            font=ctk.CTkFont(family=self.FONT_CODE, size=15, weight="bold"),
        ).pack(side="left", padx=(0, 8))

        self.query_label = ctk.CTkLabel(
            q_frame,
            text=self.current_query,
            text_color=self.COLOR_TEXT,
            font=ctk.CTkFont(family=self.FONT_CODE, size=13),
            anchor="w",
            justify="left",
        )
        self.query_label.pack(side="left", fill="x", expand=True)
        self._autowrap(self.query_label, 10)

        # 2. Section CAUSE / EXPLICATION
        is_error = any(w in self.current_query.lower() for w in ("diagnose", "error", "failed", "échec", "fail"))
        cause_title = t("section_cause") if is_error else t("section_explanation")

        ctk.CTkLabel(
            scroll,
            text=cause_title,
            text_color="#3D4A5C",
            font=ctk.CTkFont(family=self.FONT_UI, size=9, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        cleaned_cause = _clean_markdown(self.current_cause)
        self.cause_body = ctk.CTkLabel(
            scroll,
            text=cleaned_cause or (t("thinking") if self.is_loading else ""),
            text_color=self.COLOR_TEXT if self.current_cause else self.COLOR_ACCENT,
            font=ctk.CTkFont(family=self.FONT_UI, size=12),
            anchor="w",
            justify="left",
        )
        self.cause_body.pack(fill="x", pady=(0, 14))
        self._autowrap(self.cause_body, 10)

        # 3. Section FIX / COMMANDE RECOMMANDÉE
        if self.current_cmd:
            ctk.CTkLabel(
                scroll,
                text=t("section_fix"),
                text_color="#3D4A5C",
                font=ctk.CTkFont(family=self.FONT_UI, size=9, weight="bold"),
                anchor="w",
            ).pack(fill="x", pady=(0, 4))

            self.cmd_box = ctk.CTkFrame(
                scroll,
                fg_color=self.COLOR_CODE,
                border_color=self.COLOR_BORDER,
                border_width=1,
                corner_radius=8,
                height=42,
            )
            self.cmd_box.pack(fill="x", pady=(0, 8))

            cmd_inner = ctk.CTkFrame(self.cmd_box, fg_color="transparent")
            cmd_inner.pack(fill="both", expand=True, padx=12, pady=8)

            ctk.CTkLabel(
                cmd_inner,
                text="$",
                text_color=self.COLOR_ACCENT,
                font=ctk.CTkFont(family=self.FONT_CODE, size=12, weight="bold"),
            ).pack(side="left", padx=(0, 8))

            self.cmd_text_lbl = ctk.CTkLabel(
                cmd_inner,
                text=self.current_cmd,
                text_color=self.COLOR_TEXT,
                font=ctk.CTkFont(family=self.FONT_CODE, size=12, weight="bold"),
                anchor="w",
                justify="left",
            )
            self.cmd_text_lbl.pack(side="left", fill="x", expand=True)
            self._autowrap(self.cmd_text_lbl, 8)

            # Bouton copy sobre : juste une icône discrète à droite
            self.quick_copy_btn = ctk.CTkButton(
                cmd_inner,
                text="⎘",
                width=26,
                height=22,
                corner_radius=4,
                fg_color="transparent",
                hover_color="#1A1E29",
                border_width=0,
                text_color=self.COLOR_TEXT_DIM,
                font=ctk.CTkFont(family=self.FONT_UI, size=13),
                command=self.copy_current_command,
            )
            self.quick_copy_btn.pack(side="right", padx=(4, 0))

            # 4. Niveau de risque
            risk_row = ctk.CTkFrame(scroll, fg_color="transparent")
            risk_row.pack(fill="x", pady=(0, 8))

            risk_col = (
                self.COLOR_DANGER
                if self.current_risk_level == RiskLevel.DANGEROUS
                else (self.COLOR_WARNING if self.current_risk_level == RiskLevel.WARNING else self.COLOR_SUCCESS)
            )
            risk_txt = (
                t("risk_high")
                if self.current_risk_level == RiskLevel.DANGEROUS
                else (t("risk_medium") if self.current_risk_level == RiskLevel.WARNING else t("risk_low"))
            )

            ctk.CTkLabel(
                risk_row,
                text="●",
                text_color=risk_col,
                font=ctk.CTkFont(family=self.FONT_UI, size=9),
            ).pack(side="left", padx=(0, 4))

            ctk.CTkLabel(
                risk_row,
                text=risk_txt,
                text_color=risk_col,
                font=ctk.CTkFont(family=self.FONT_UI, size=10, weight="bold"),
            ).pack(side="left", padx=(0, 6))

            reason_lbl = ctk.CTkLabel(
                risk_row,
                text=self.current_risk_reason or t("risk_reason_default"),
                text_color=self.COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family=self.FONT_UI, size=10),
                anchor="w",
                justify="left",
            )
            reason_lbl.pack(side="left", fill="x", expand=True)
            self._autowrap(reason_lbl, 6)

        # 5. Zone de sortie d'exécution (quand Run est pressé)
        self.exec_box = ctk.CTkFrame(
            scroll,
            fg_color=self.COLOR_CODE,
            border_color=self.COLOR_BORDER,
            border_width=1,
            corner_radius=6,
        )
        self.exec_label = ctk.CTkLabel(
            self.exec_box,
            text="",
            font=ctk.CTkFont(family=self.FONT_CODE, size=11),
            justify="left",
            anchor="w",
        )
        self.exec_label.pack(fill="both", expand=True, padx=10, pady=8)
        self._autowrap(self.exec_label, 16)

    # -----------------------------------------------------------------------
    # Utilitaires d'Affichage
    # -----------------------------------------------------------------------

    def _autowrap(self, label: ctk.CTkLabel, margin: int = 0) -> None:
        """Adapte dynamiquement le wraplength d'un label à la largeur de son conteneur."""
        container = label.master

        def _on_resize(event):
            scaling = ctk.ScalingTracker.get_widget_scaling(label)
            width = max(80, int((event.width - margin) / scaling))
            try:
                label.configure(wraplength=width)
            except Exception:
                pass

        container.bind("<Configure>", _on_resize, add="+")

    def _resize_window(self, target_h: int) -> None:
        """Adapte la hauteur de la fenêtre selon la vue (launcher compact vs résultat)."""
        try:
            curr_w = self.winfo_width()
            w = curr_w if curr_w > 100 else self.WIDTH
            self.geometry(f"{w}x{target_h}")
        except Exception:
            pass

    # -----------------------------------------------------------------------
    # Gestion du Menu Popover
    # -----------------------------------------------------------------------

    def toggle_menu(self) -> None:
        """Ouvre ou ferme le menu contextuel '···'."""
        if hasattr(self, "menu_popover") and self.menu_popover is not None and self.menu_popover.winfo_ismapped():
            self.hide_menu()
        else:
            self.show_menu()

    def show_menu(self) -> None:
        if not hasattr(self, "menu_popover") or self.menu_popover is None:
            self.menu_popover = MenuPopover(self, app=self)
        self.menu_popover.place(relx=1.0, y=44, x=-20, anchor="ne")
        self.menu_popover.lift()

    def hide_menu(self) -> None:
        if hasattr(self, "menu_popover") and self.menu_popover is not None:
            self.menu_popover.place_forget()

    def _on_global_click(self, event) -> None:
        """Ferme le menu si on clique en dehors du popover ou du bouton menu."""
        if hasattr(self, "menu_popover") and self.menu_popover is not None and self.menu_popover.winfo_ismapped():
            w = event.widget
            while w is not None:
                if w in (self.menu_popover, self.btn_menu):
                    return
                w = getattr(w, "master", None)
            self.hide_menu()

    # -----------------------------------------------------------------------
    # Fonctions du Menu Popover
    # -----------------------------------------------------------------------

    def set_theme(self, mode: str) -> None:
        """Change le thème de l'application (system, light, dark)."""
        self.current_theme = mode
        ctk.set_appearance_mode(mode)

    def zoom_in(self) -> None:
        """Agrandit l'échelle d'affichage."""
        if self.scale_factor < 1.4:
            self.scale_factor = round(self.scale_factor + 0.1, 1)
            ctk.set_widget_scaling(self.scale_factor)
            if hasattr(self, "menu_popover") and self.menu_popover:
                self.menu_popover.zoom_lbl.configure(text=f"{int(self.scale_factor * 100)}%")

    def zoom_out(self) -> None:
        """Réduit l'échelle d'affichage."""
        if self.scale_factor > 0.7:
            self.scale_factor = round(self.scale_factor - 0.1, 1)
            ctk.set_widget_scaling(self.scale_factor)
            if hasattr(self, "menu_popover") and self.menu_popover:
                self.menu_popover.zoom_lbl.configure(text=f"{int(self.scale_factor * 100)}%")

    def open_preferences(self) -> None:
        """Affiche un panneau de préférences propre et structuré style Hyprland."""
        from src.core.suggest import detect_lang
        lang = detect_lang()
        lang_str = "Français (FR)" if lang == "fr" else "English (US)"
        prov_str = chat_bridge.provider_label(self.provider, self.config)
        model_str = self.config.get_effective_model()
        shell_str = self.context.shell_name or "sh"

        modal = self._create_modal_frame("⚙  Préférences", width=540, height=360)

        content = ctk.CTkFrame(modal, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=18, pady=(2, 14))

        # Section 1 : Fournisseur & Modèle
        self._add_pref_section_header(content, "FOURNISSEUR & MODÈLE IA")
        card1 = ctk.CTkFrame(content, fg_color="#141724", border_color=self.COLOR_BORDER, border_width=1, corner_radius=8)
        card1.pack(fill="x", pady=(0, 10))

        self._add_pref_row(card1, "Fournisseur actif", prov_str, badge_color=self.COLOR_SUCCESS, badge_prefix="● ")
        self._add_pref_divider(card1)
        self._add_pref_row(card1, "Modèle d'inférence", model_str, badge_color=self.COLOR_PRIMARY)

        # Section 2 : Système & Langue
        self._add_pref_section_header(content, "ENVIRONNEMENT SYSTÈME")
        card2 = ctk.CTkFrame(content, fg_color="#141724", border_color=self.COLOR_BORDER, border_width=1, corner_radius=8)
        card2.pack(fill="x", pady=(0, 10))

        self._add_pref_row(card2, "Langue d'interface", lang_str)
        self._add_pref_divider(card2)
        self._add_pref_row(card2, "Shell détecté", shell_str)

        # Section 3 : Astuces CLI
        self._add_pref_section_header(content, "COMMANDES CLI RAPIDES")
        tip_box = ctk.CTkFrame(content, fg_color=self.COLOR_CODE, border_color="#1C2132", border_width=1, corner_radius=6)
        tip_box.pack(fill="x")
        ctk.CTkLabel(
            tip_box,
            text="$ ezsh --set-key <clé>     # Configurer la clé Groq\n"
                 "$ ezsh --model <modèle>      # Changer de modèle LLM\n"
                 "$ ezsh shortcuts             # Personnaliser le raccourci Alt+E",
            text_color="#94A3B8",
            font=ctk.CTkFont(family=self.FONT_CODE, size=10),
            justify="left",
            anchor="w",
        ).pack(fill="x", padx=12, pady=6)

    def open_shortcuts(self) -> None:
        """Affiche la liste des raccourcis clavier dans une grille élégante."""
        modal = self._create_modal_frame("⌨  Raccourcis clavier", width=540, height=350)

        content = ctk.CTkFrame(modal, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=18, pady=(2, 14))

        card = ctk.CTkFrame(content, fg_color="#141724", border_color=self.COLOR_BORDER, border_width=1, corner_radius=8)
        card.pack(fill="both", expand=True)

        shortcuts = [
            ("↵  Entrée", "Valider la question ou exécuter la commande proposée"),
            ("Esc", "Fermer la fenêtre ezShell ou revenir à l'accueil"),
            ("Alt + E", "Déclencheur shell interactif inline dans le terminal"),
            ("c", "Copier la commande recommandée dans le presse-papiers"),
            ("e", "Placer la commande dans le champ pour la modifier"),
            ("q", "Quitter immédiatement la fenêtre"),
        ]

        for i, (key, desc) in enumerate(shortcuts):
            if i > 0:
                self._add_pref_divider(card)
            row = ctk.CTkFrame(card, fg_color="transparent", height=28)
            row.pack(fill="x", padx=12, pady=4)

            cap = ctk.CTkFrame(row, fg_color="#1A1E2D", border_color="#283045", border_width=1, corner_radius=4)
            cap.pack(side="left", padx=(0, 10))
            ctk.CTkLabel(
                cap,
                text=key,
                text_color=self.COLOR_TEXT_KEY,
                font=ctk.CTkFont(family=self.FONT_UI, size=9, weight="bold"),
            ).pack(padx=7, pady=1)

            ctk.CTkLabel(
                row,
                text=desc,
                text_color=self.COLOR_TEXT,
                font=ctk.CTkFont(family=self.FONT_UI, size=10),
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

    def check_updates(self) -> None:
        """Vérifie l'état des mises à jour."""
        try:
            from src.core.updater import version_hint

            hint = version_hint()
            msg = hint or f"ezShell v{__version__} est à jour !"
        except Exception:
            msg = f"ezShell v{__version__} (version actuelle)"

        modal = self._create_modal_frame("🔄  Mises à jour", width=420, height=220)
        content = ctk.CTkFrame(modal, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=20, pady=(10, 16))

        card = ctk.CTkFrame(content, fg_color="#141724", border_color=self.COLOR_BORDER, border_width=1, corner_radius=8)
        card.pack(fill="both", expand=True)

        ctk.CTkLabel(
            card,
            text=f"Version installée : v{__version__}",
            text_color="#CBD5E1",
            font=ctk.CTkFont(family=self.FONT_UI, size=11, weight="bold"),
        ).pack(pady=(16, 6))

        ctk.CTkLabel(
            card,
            text=msg,
            text_color=self.COLOR_SUCCESS if "à jour" in msg else self.COLOR_ACCENT,
            font=ctk.CTkFont(family=self.FONT_CODE, size=11),
        ).pack(pady=(0, 16))

    def open_about(self) -> None:
        """Affiche les informations À propos d'ezShell façon carte moderne."""
        modal = self._create_modal_frame("ℹ  À propos d'ezShell", width=520, height=360)

        content = ctk.CTkFrame(modal, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=18, pady=(2, 14))

        # En-tête avec logo et version
        top = ctk.CTkFrame(content, fg_color="transparent")
        top.pack(fill="x", pady=(0, 6))

        ctk.CTkLabel(
            top,
            text="❯_ ezShell",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=self.FONT_TITLE, size=17, weight="bold"),
        ).pack(side="left")

        ctk.CTkLabel(
            top,
            text=f"v{__version__}",
            text_color=self.COLOR_ACCENT,
            fg_color="#142233",
            corner_radius=4,
            font=ctk.CTkFont(family=self.FONT_CODE, size=10, weight="bold"),
            padx=6,
            pady=1,
        ).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(
            content,
            text="Ton terminal t'explique ses erreurs.",
            text_color=self.COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=self.FONT_UI, size=11, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        # Tuile de fonctionnalités
        card = ctk.CTkFrame(content, fg_color="#141724", border_color=self.COLOR_BORDER, border_width=1, corner_radius=8)
        card.pack(fill="x", pady=(0, 8))

        bullets = [
            "Diagnostic immédiat des commandes échouées (FR / EN)",
            "Correction insérée directement dans votre prompt shell",
            "Traduction langage naturel → commandes shell sécurisées",
            "Protection proactive : secrets masqués, niveaux de risque",
        ]
        for b in bullets:
            b_row = ctk.CTkFrame(card, fg_color="transparent")
            b_row.pack(fill="x", padx=12, pady=2)
            ctk.CTkLabel(b_row, text="•", text_color=self.COLOR_ACCENT, font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 6))
            ctk.CTkLabel(b_row, text=b, text_color="#CBD5E1", font=ctk.CTkFont(family=self.FONT_UI, size=10), anchor="w").pack(side="left")

        # Liens et copyright
        foot = ctk.CTkFrame(content, fg_color="transparent")
        foot.pack(fill="x", pady=(2, 0))

        ctk.CTkLabel(
            foot,
            text="GitHub : github.com/Waddle-io/ezShell   •   Site : ezshell.vercel.app",
            text_color=self.COLOR_TEXT_DIM,
            font=ctk.CTkFont(family=self.FONT_CODE, size=9),
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            foot,
            text="Licence MIT  •  © 2026 Waddle",
            text_color=self.COLOR_TEXT_DIM,
            font=ctk.CTkFont(family=self.FONT_UI, size=9),
            anchor="w",
        ).pack(fill="x", pady=(1, 0))

    def _create_modal_frame(self, title: str, width: int = 540, height: int = 360) -> ctk.CTkFrame:
        """Crée un conteneur modal centré et bien dimensionné style Hyprland."""
        modal = ctk.CTkFrame(
            self.main_container,
            fg_color="#0F121C",
            border_color="#283045",
            border_width=1,
            corner_radius=12,
            width=width,
            height=height,
        )
        modal.place(relx=0.5, rely=0.5, anchor="center")
        modal.pack_propagate(False)
        modal.lift()

        # En-tête modal
        top = ctk.CTkFrame(modal, fg_color="transparent")
        top.pack(fill="x", padx=18, pady=(12, 6))

        ctk.CTkLabel(
            top,
            text=title,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=self.FONT_TITLE, size=14, weight="bold"),
            anchor="w",
        ).pack(side="left")

        close_btn = ctk.CTkButton(
            top,
            text="✕",
            width=24,
            height=24,
            corner_radius=12,
            fg_color="#181B26",
            hover_color="#252A3C",
            border_color="#2B334B",
            border_width=1,
            text_color="#CBD5E1",
            font=ctk.CTkFont(family=self.FONT_UI, size=10, weight="bold"),
            command=modal.destroy,
        )
        close_btn.pack(side="right")

        ctk.CTkFrame(modal, fg_color=self.COLOR_BORDER, height=1).pack(fill="x", padx=14, pady=(0, 6))
        modal.bind("<Escape>", lambda e: modal.destroy())
        return modal

    def _add_pref_section_header(self, parent, text: str) -> None:
        ctk.CTkLabel(
            parent,
            text=text,
            text_color="#64748B",
            font=ctk.CTkFont(family=self.FONT_UI, size=9, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(1, 3))

    def _add_pref_row(self, parent, label: str, value: str, badge_color=None, badge_prefix="") -> None:
        row = ctk.CTkFrame(parent, fg_color="transparent", height=28)
        row.pack(fill="x", padx=12, pady=4)

        ctk.CTkLabel(
            row,
            text=label,
            text_color="#CBD5E1",
            font=ctk.CTkFont(family=self.FONT_UI, size=11),
            anchor="w",
        ).pack(side="left")

        color = badge_color or "#FFFFFF"
        text_val = f"{badge_prefix}{value}"
        badge = ctk.CTkLabel(
            row,
            text=text_val,
            text_color=color,
            font=ctk.CTkFont(family=self.FONT_CODE, size=10, weight="bold"),
            anchor="e",
        )
        badge.pack(side="right")

    def _add_pref_divider(self, parent) -> None:
        ctk.CTkFrame(parent, fg_color="#1C2132", height=1).pack(fill="x", padx=8)

    # -----------------------------------------------------------------------
    # Actions & Exécution
    # -----------------------------------------------------------------------

    def _reset_to_launcher(self) -> None:
        self.current_query = ""
        self.current_cause = ""
        self.current_cmd = ""
        self.current_risk_reason = ""
        self.is_loading = False
        self._render_launcher_view()

    def run_current_command(self) -> None:
        cmd = self.current_cmd.strip()
        if not cmd:
            return

        result = PTYExecutor.execute(cmd, cwd=os.getcwd(), forward_output=False)
        is_ok = result.exit_code == 0
        col = self.COLOR_SUCCESS if is_ok else self.COLOR_DANGER
        out = (
            f"› {t('cmd_success')}\n{result.clean_output.strip() or t('cmd_no_output')}"
            if is_ok
            else f"✘ Exit code {result.exit_code}\n{result.clean_output.strip() or t('cmd_no_output')}"
        )

        self.exec_label.configure(text=out, text_color=col)
        self.exec_box.pack(fill="x", pady=(0, 8))

    def copy_current_command(self) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(self.current_cmd)
        except Exception:
            pass

        if hasattr(self, "quick_copy_btn"):
            self.quick_copy_btn.configure(text="✓ Copié !", fg_color=self.COLOR_SUCCESS)
            self.after(1200, lambda: self.quick_copy_btn.configure(
                text=t("action_copy"), fg_color=self.COLOR_CARD
            ))

        if hasattr(self, "cmd_box"):
            self.cmd_box.configure(border_color=self.COLOR_ACCENT)
            self.after(500, lambda: self.cmd_box.configure(border_color=self.COLOR_BORDER))

    def edit_current_command(self) -> None:
        if hasattr(self, "followup_entry"):
            self.followup_entry.delete(0, "end")
            self.followup_entry.insert(0, self.current_cmd)
            self.followup_entry.focus_set()

    # -----------------------------------------------------------------------
    # Saisie & Requêtes
    # -----------------------------------------------------------------------

    def _focus_input(self) -> None:
        """Assure l'activation réelle du focus clavier sur le champ texte."""
        try:
            if hasattr(self, "input_entry") and self.input_entry.winfo_exists():
                self.input_entry.focus_set()
                if hasattr(self.input_entry, "_entry"):
                    self.input_entry._entry.focus_set()
        except Exception:
            pass

    def _apply_os_window_decorations(self) -> None:
        """Applique les attributs natifs de l'OS (coins arrondis Windows 11, dark titlebar)."""
        import sys
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = self.winfo_id()
                dark_mode = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 20, ctypes.byref(dark_mode), ctypes.sizeof(dark_mode)
                )
                corner_pref = ctypes.c_int(2)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(
                    hwnd, 33, ctypes.byref(corner_pref), ctypes.sizeof(corner_pref)
                )
            except Exception:
                pass


    def _on_submit_input(self) -> None:
        query = self.input_entry.get().strip() if hasattr(self, "input_entry") else ""
        if not query:
            return
        self._query_groq(query)

    def _on_input_return(self, _event=None) -> str:
        self._on_submit_input()
        return "break"

    def _on_followup_return(self, _event=None) -> str:
        query = self.followup_entry.get().strip() if hasattr(self, "followup_entry") else ""
        if not query:
            return "break"
        if hasattr(self, "followup_entry"):
            self.followup_entry.delete(0, "end")
        self._query_groq(query)
        return "break"

    def _handle_global_key(self, event) -> None:
        # En mode launcher : toute frappe clavier est orientée vers le champ de saisie
        if hasattr(self, "input_entry") and self.input_entry.winfo_exists() and self.input_entry.winfo_ismapped():
            focused = self.focus_get()
            if focused not in (self.input_entry, getattr(self.input_entry, "_entry", None)):
                self._focus_input()
            return

        # En mode résultat : si le champ de relance a le focus, ne pas intercepter
        focused = self.focus_get()
        if hasattr(self, "followup_entry") and focused in (self.followup_entry, getattr(self.followup_entry, "_entry", None)):
            return

        k = event.keysym.lower()
        if k == "q":
            self.destroy()
        elif k == "c" and self.current_cmd:
            self.copy_current_command()
        elif k == "e" and self.current_cmd:
            self.edit_current_command()
        elif k == "return" and self.current_cmd:
            self.run_current_command()

    def _query_groq(self, query: str, mode: str = "translate") -> None:
        self.current_query = query
        self.current_cause = ""
        self.current_cmd = ""
        self.current_risk_reason = ""
        self.is_loading = True
        self._render_result_view()

        def _worker():
            try:
                result = chat_bridge.ask(
                    query if mode == "translate" else "",
                    mode=mode,
                    command=self.last_detected_cmd or (get_last_shell_command() or ""),
                    provider=self.provider,
                )
                self.after(0, lambda: self._apply_result(result))
            except Exception as e:
                msg = chat_bridge.describe_error(e)
                self.after(0, lambda: self._apply_error(msg))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_result(self, result: ChatMessageResult) -> None:
        self.is_loading = False
        self.current_cause = result.content.strip()

        if result.suggested_commands:
            self.current_cmd = result.suggested_commands[0]
            if result.safety_reports:
                report = result.safety_reports[0]
                self.current_risk_level = report.risk_level
                self.current_risk_reason = report.reason or t("risk_reason_default")
        else:
            self.current_cmd = ""
            self.current_risk_reason = ""

        self._render_result_view()

    def _apply_error(self, err_msg: str) -> None:
        self.is_loading = False
        self.current_cause = err_msg
        self.current_cmd = ""
        self._render_result_view()

    # -----------------------------------------------------------------------
    # Déplacement de la fenêtre
    # -----------------------------------------------------------------------

    def _start_drag(self, event) -> None:
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event) -> None:
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")
