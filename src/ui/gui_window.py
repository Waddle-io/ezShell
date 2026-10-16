from __future__ import annotations

import os
from pathlib import Path
import re
import threading
from typing import List, Optional

import customtkinter as ctk
from PIL import Image

from src.core.assistant import ChatMessageResult, ChatSession
from src.core.config import EzShellConfig
from src.core.context import SystemContext, get_last_exit_code, get_last_shell_command
from src.core.pty_shell import PTYExecutor
from src.core.safety import RiskLevel, SafetyGuard, SafetyReport
from src.i18n import t


def clean_markdown_explanation(text: str) -> str:
    """Cleans raw markdown formatting from AI text for a clean, human-readable desktop UI."""
    if not text:
        return ""
    # Strip full fenced code blocks (```bash ... ```)
    cleaned = re.sub(r"```[a-zA-Z]*\n[\s\S]*?\n```", "", text)
    # Strip inline backticks `command` -> command
    cleaned = re.sub(r"`(.*?)`", r"\1", cleaned)
    # Strip bold asterisks **word** -> word
    cleaned = re.sub(r"\*\*(.*?)\*\*", r"\1", cleaned)
    # Strip repetitive section headers
    cleaned = re.sub(r"(?im)^\s*Command\s*:?\s*$", "", cleaned)
    cleaned = re.sub(r"(?im)^\s*What it does\s*:?\s*$", "", cleaned)
    cleaned = re.sub(r"(?im)^\s*Explication\s*:?\s*$", "", cleaned)
    cleaned = re.sub(r"(?im)^\s*Solution\s*:?\s*$", "", cleaned)
    # Format bullet points nicely
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


class EzShellDesktopApp(ctk.CTk):
    """Modern, clean desktop GUI popup window for ezShell AI Assistant.

    Theme: Refined developer palette (Royal Blue accent, deep slate background).
    NO cyberpunk styling, NO electric cyan.
    """

    # Typography & Font Families
    FONT_FAMILY_UI = "Inter"
    FONT_FAMILY_TITLE = "Inter Display"
    FONT_FAMILY_CODE = "JetBrains Mono"

    FONT_SIZE_APP_TITLE = 18
    FONT_SIZE_QUERY_CHEVRON = 16
    FONT_SIZE_QUERY_TEXT = 14
    FONT_SIZE_SECTION_HEADER = 11
    FONT_SIZE_CAUSE_BODY = 14
    FONT_SIZE_FIX_COMMAND = 14
    FONT_SIZE_RISK_BADGE = 12
    FONT_SIZE_INPUT_ENTRY = 13
    FONT_SIZE_PILL_KEY = 11
    FONT_SIZE_PILL_LABEL = 11
    FONT_SIZE_EXEC_OUTPUT = 12

    # Modern refined developer color palette
    COLOR_PRIMARY_BLUE = "#3B82F6"      # Refined royal blue accent
    COLOR_BLUE_HOVER = "#2563EB"        # Active button blue
    COLOR_LIGHT_BLUE = "#60A5FA"        # Light blue highlights
    COLOR_BG_WINDOW = "#0B0F17"         # Clean deep slate window background
    COLOR_BG_CARD = "#121826"           # Dark card background
    COLOR_BG_CARD_HOVER = "#182235"     # Interactive hover card
    COLOR_BG_CODE = "#090D14"           # Terminal dark code background
    COLOR_BG_INPUT = "#111827"          # Input entry background
    COLOR_BORDER = "#1E293B"            # Subtle card border
    COLOR_BORDER_FOCUS = "#3B82F6"      # Focused input border
    COLOR_TEXT_PRIMARY = "#F8FAFC"      # White primary text
    COLOR_TEXT_MUTED = "#94A3B8"        # Slate muted text
    COLOR_TEXT_SUBTLE = "#64748B"       # Subtle gray
    COLOR_SUCCESS = "#10B981"           # Emerald green for safe / exit 0
    COLOR_WARNING = "#F59E0B"           # Amber warning
    COLOR_DANGER = "#EF4444"            # Clean red for danger / failed

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
        self.chat_session: Optional[ChatSession] = None

        if self.config.get_effective_api_key():
            self.chat_session = ChatSession(config=self.config, context=self.context)

        # Window properties
        self.title("ezShell")
        self.configure(fg_color=self.COLOR_BG_WINDOW)

        # Dimensions & screen centering: Sleek compact launcher proportions
        win_w, win_h = 760, 500
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = max(0, (sw - win_w) // 2)
            y = max(0, (sh - win_h) // 2)
            self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        except Exception:
            self.geometry(f"{win_w}x{win_h}")

        self.minsize(700, 460)

        # Keyboard shortcuts
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<KeyPress>", self._handle_global_key)

        # Drag tracking
        self._drag_x = 0
        self._drag_y = 0

        # State
        self.current_query = initial_query or ""
        self.current_cause = ""
        self.current_cmd = ""
        self.current_risk_level = RiskLevel.SAFE
        self.current_risk_reason = ""
        self.last_detected_cmd = get_last_shell_command()
        self.last_exit_code = get_last_exit_code()

        # Load logo image (supports 28x28 pre-rendered PNG via Tk PhotoImage)
        self.logo_image = None
        logo_28_path = Path(__file__).resolve().parent.parent.parent / "assets" / "logo_28.png"
        if not logo_28_path.is_file():
            logo_orig = Path(__file__).resolve().parent.parent.parent / "assets" / "logo.png"
            if logo_orig.is_file():
                try:
                    Image.open(logo_orig).convert("RGBA").resize((28, 28), Image.Resampling.LANCZOS).save(logo_28_path)
                except Exception:
                    pass

        if logo_28_path.is_file():
            try:
                import tkinter as tk
                self.logo_image = tk.PhotoImage(file=str(logo_28_path))
            except Exception:
                pass

        self._build_ui()

        # If a real query was passed, analyze it immediately
        if initial_query:
            self._query_groq(initial_query)

    def _build_ui(self) -> None:
        """Constructs the application layout."""
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=20, pady=(16, 12))

        # 1. Header Bar: [Icon] ez (blue) Shell (white) ............ [Esc] to close
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent", height=32)
        self.header_frame.pack(fill="x", pady=(0, 10))

        # Drag support on header
        self.header_frame.bind("<ButtonPress-1>", self._start_drag)
        self.header_frame.bind("<B1-Motion>", self._on_drag)

        # Left: Logo icon + 'ez' in Blue + 'Shell' in White
        header_left = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_left.pack(side="left")
        header_left.bind("<ButtonPress-1>", self._start_drag)
        header_left.bind("<B1-Motion>", self._on_drag)

        if self.logo_image:
            logo_lbl = ctk.CTkLabel(header_left, text="", image=self.logo_image)
            logo_lbl.pack(side="left", padx=(0, 8))
            logo_lbl.bind("<ButtonPress-1>", self._start_drag)
            logo_lbl.bind("<B1-Motion>", self._on_drag)

        app_title_ez = ctk.CTkLabel(
            header_left,
            text="ez",
            text_color=self.COLOR_PRIMARY_BLUE,
            font=ctk.CTkFont(family=self.FONT_FAMILY_TITLE, size=self.FONT_SIZE_APP_TITLE, weight="bold"),
        )
        app_title_ez.pack(side="left")
        app_title_ez.bind("<ButtonPress-1>", self._start_drag)
        app_title_ez.bind("<B1-Motion>", self._on_drag)

        app_title_shell = ctk.CTkLabel(
            header_left,
            text="Shell",
            text_color=self.COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family=self.FONT_FAMILY_TITLE, size=self.FONT_SIZE_APP_TITLE, weight="bold"),
        )
        app_title_shell.pack(side="left")
        app_title_shell.bind("<ButtonPress-1>", self._start_drag)
        app_title_shell.bind("<B1-Motion>", self._on_drag)

        # Right: [Esc] to close pill
        close_pill = ctk.CTkFrame(
            self.header_frame,
            fg_color=self.COLOR_BG_CARD,
            border_color=self.COLOR_BORDER,
            border_width=1,
            corner_radius=6,
            height=26,
        )
        close_pill.pack(side="right")

        esc_badge = ctk.CTkLabel(
            close_pill,
            text="Esc",
            text_color="#CBD5E1",
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=11, weight="bold"),
            fg_color="#1E293B",
            corner_radius=4,
            width=32,
            height=20,
        )
        esc_badge.pack(side="left", padx=(3, 5), pady=3)

        close_text = ctk.CTkLabel(
            close_pill,
            text=t("esc_to_close"),
            text_color=self.COLOR_TEXT_SUBTLE,
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=11),
        )
        close_text.pack(side="left", padx=(0, 7), pady=3)

        close_pill.bind("<Button-1>", lambda e: self.destroy())
        esc_badge.bind("<Button-1>", lambda e: self.destroy())
        close_text.bind("<Button-1>", lambda e: self.destroy())

        # Top divider line
        ctk.CTkFrame(self.main_container, fg_color=self.COLOR_BORDER, height=1).pack(fill="x", pady=(0, 12))

        # Dynamic body container
        self.body_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.body_container.pack(fill="both", expand=True)

        # Bottom divider + persistent footer status bar
        ctk.CTkFrame(self.main_container, fg_color=self.COLOR_BORDER, height=1).pack(fill="x", pady=(10, 8))

        self.footer_bar = ctk.CTkFrame(self.main_container, fg_color="transparent", height=24)
        self.footer_bar.pack(fill="x")
        self._build_footer_status()

        if self.current_query:
            self._render_result_view()
        else:
            self._render_launcher_view()

    def _build_footer_status(self) -> None:
        """Renders the refined bottom status bar with shortcuts and model info."""
        for w in self.footer_bar.winfo_children():
            w.destroy()

        # Left: Keyboard shortcuts hint
        ctk.CTkLabel(
            self.footer_bar,
            text=t("status_footer_hint"),
            text_color=self.COLOR_TEXT_SUBTLE,
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=10),
            anchor="w",
        ).pack(side="left")

        # Right: Active Provider & Model pill
        provider_name = getattr(self.config, "provider", "groq").capitalize()
        model_name = getattr(self.config, "get_effective_model", lambda: self.config.model)()

        provider_frame = ctk.CTkFrame(self.footer_bar, fg_color="transparent")
        provider_frame.pack(side="right")

        # Green online dot
        ctk.CTkLabel(
            provider_frame,
            text="●",
            text_color=self.COLOR_SUCCESS,
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=9),
        ).pack(side="left", padx=(0, 4))

        ctk.CTkLabel(
            provider_frame,
            text=f"{provider_name} · {model_name}  (ezShell v0.1.0)",
            text_color=self.COLOR_TEXT_SUBTLE,
            font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=10),
            anchor="e",
        ).pack(side="left")

    def _render_launcher_view(self) -> None:
        """Renders clean, focused launcher mode with high-end developer dashboard layout."""
        for w in self.body_container.winfo_children():
            w.destroy()

        # 1. Primary Search / Query Entry Card
        search_card = ctk.CTkFrame(
            self.body_container,
            fg_color=self.COLOR_BG_INPUT,
            border_color=self.COLOR_BORDER,
            border_width=1,
            corner_radius=10,
            height=48,
        )
        search_card.pack(fill="x", pady=(2, 14))
        search_card.pack_propagate(False)

        prompt_icon = ctk.CTkLabel(
            search_card,
            text="›",
            text_color=self.COLOR_PRIMARY_BLUE,
            font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=18, weight="bold"),
        )
        prompt_icon.pack(side="left", padx=(12, 6))

        self.input_entry = ctk.CTkEntry(
            search_card,
            placeholder_text=t("input_placeholder"),
            placeholder_text_color="#475569",
            fg_color="transparent",
            border_width=0,
            text_color=self.COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=self.FONT_SIZE_INPUT_ENTRY),
        )
        self.input_entry.pack(side="left", fill="both", expand=True, padx=(0, 8))
        self.input_entry.bind("<Return>", lambda e: self._on_submit_input())
        self.input_entry.focus()

        # Focus ring animation
        def _on_entry_focus(e):
            search_card.configure(border_color=self.COLOR_PRIMARY_BLUE)

        def _on_entry_blur(e):
            search_card.configure(border_color=self.COLOR_BORDER)

        self.input_entry.bind("<FocusIn>", _on_entry_focus)
        self.input_entry.bind("<FocusOut>", _on_entry_blur)

        # Sleek Send / Enter badge button
        ask_btn = ctk.CTkButton(
            search_card,
            text=f"↵ {t('btn_send')}",
            fg_color="#1E293B",
            hover_color=self.COLOR_PRIMARY_BLUE,
            text_color="#CBD5E1",
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=11, weight="bold"),
            width=84,
            height=30,
            corner_radius=6,
            command=self._on_submit_input,
        )
        ask_btn.pack(side="right", padx=(0, 8), pady=8)

        # 2. Context Card: Detected Last Shell Command OR Clean System Status
        if self.last_detected_cmd:
            last_cmd_card = ctk.CTkFrame(
                self.body_container,
                fg_color=self.COLOR_BG_CARD,
                border_color=self.COLOR_BORDER,
                border_width=1,
                corner_radius=8,
            )
            last_cmd_card.pack(fill="x", pady=(0, 14))

            # Header row inside card
            row_top = ctk.CTkFrame(last_cmd_card, fg_color="transparent")
            row_top.pack(fill="x", padx=12, pady=(10, 6))

            ctk.CTkLabel(
                row_top,
                text=f"› {t('last_cmd_detected')}",
                text_color=self.COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=11, weight="bold"),
                anchor="w",
            ).pack(side="left")

            # Exit code pill
            if self.last_exit_code is not None:
                is_err = self.last_exit_code != 0
                badge_bg = "#2B1216" if is_err else "#0F291E"
                badge_fg = self.COLOR_DANGER if is_err else self.COLOR_SUCCESS
                badge_text = f"✘ Code {self.last_exit_code}" if is_err else "✓ Code 0"

                ctk.CTkLabel(
                    row_top,
                    text=badge_text,
                    text_color=badge_fg,
                    fg_color=badge_bg,
                    corner_radius=4,
                    font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=10, weight="bold"),
                    padx=6,
                    pady=2,
                ).pack(side="right")

            # Monospace command container
            cmd_box = ctk.CTkFrame(
                last_cmd_card,
                fg_color=self.COLOR_BG_CODE,
                border_color=self.COLOR_BORDER,
                border_width=1,
                corner_radius=6,
                height=34,
            )
            cmd_box.pack(fill="x", padx=12, pady=(0, 10))
            cmd_box.pack_propagate(False)

            cmd_mono = ctk.CTkLabel(
                cmd_box,
                text=f"  $ {self.last_detected_cmd}",
                text_color=self.COLOR_LIGHT_BLUE,
                font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=12, weight="bold"),
                anchor="w",
            )
            cmd_mono.pack(fill="both", expand=True, padx=6)

            # Action buttons row
            btn_row = ctk.CTkFrame(last_cmd_card, fg_color="transparent")
            btn_row.pack(fill="x", padx=12, pady=(0, 10))

            diag_btn = ctk.CTkButton(
                btn_row,
                text=f"⚡ {t('btn_diagnose_error')}",
                fg_color=self.COLOR_PRIMARY_BLUE,
                hover_color=self.COLOR_BLUE_HOVER,
                text_color="#FFFFFF",
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=11, weight="bold"),
                height=28,
                corner_radius=5,
                command=lambda: self._query_groq(f"diagnose failed command: {self.last_detected_cmd}"),
            )
            diag_btn.pack(side="left", padx=(0, 8))

            explain_btn = ctk.CTkButton(
                btn_row,
                text=f"ℹ {t('btn_explain_command')}",
                fg_color="#1E293B",
                hover_color="#334155",
                border_color="#334155",
                border_width=1,
                text_color=self.COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=11),
                height=28,
                corner_radius=5,
                command=lambda: self._query_groq(f"explain what this command does: {self.last_detected_cmd}"),
            )
            explain_btn.pack(side="left")
        else:
            # Clean System Context Card when no prior failure is in history
            status_card = ctk.CTkFrame(
                self.body_container,
                fg_color=self.COLOR_BG_CARD,
                border_color=self.COLOR_BORDER,
                border_width=1,
                corner_radius=8,
            )
            status_card.pack(fill="x", pady=(0, 14))

            top_row = ctk.CTkFrame(status_card, fg_color="transparent")
            top_row.pack(fill="x", padx=12, pady=(8, 4))

            ctk.CTkLabel(
                top_row,
                text=f"› {t('status_ready')}",
                text_color=self.COLOR_TEXT_PRIMARY,
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=11, weight="bold"),
                anchor="w",
            ).pack(side="left")

            ctk.CTkLabel(
                top_row,
                text="● Online",
                text_color=self.COLOR_SUCCESS,
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=10, weight="bold"),
            ).pack(side="right")

            # System info pills row
            chips_row = ctk.CTkFrame(status_card, fg_color="transparent")
            chips_row.pack(fill="x", padx=12, pady=(0, 8))

            cur_dir_name = Path(self.context.current_directory).name or "/"
            chips = [
                f"OS: {self.context.os_name} ({self.context.architecture})",
                f"Shell: {self.context.shell_name}",
                f"Cwd: {cur_dir_name}",
            ]
            if self.context.git_branch:
                chips.append(f"Git: {self.context.git_branch}")

            for c in chips:
                chip_lbl = ctk.CTkLabel(
                    chips_row,
                    text=c,
                    text_color=self.COLOR_TEXT_MUTED,
                    fg_color="#0F172A",
                    corner_radius=4,
                    font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=10),
                    padx=6,
                    pady=2,
                )
                chip_lbl.pack(side="left", padx=(0, 6))

        # 3. Quick Actions — Refined 2x2 Interactive Grid
        ctk.CTkLabel(
            self.body_container,
            text=f"› {t('quick_suggestions')}",
            text_color=self.COLOR_TEXT_SUBTLE,
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=10, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 6))

        grid_frame = ctk.CTkFrame(self.body_container, fg_color="transparent")
        grid_frame.pack(fill="x", expand=True)
        grid_frame.columnconfigure(0, weight=1)
        grid_frame.columnconfigure(1, weight=1)

        actions = [
            (
                "⚡",
                t("action_ports_title"),
                t("action_ports_desc"),
                "List all open listening ports and their associated process PIDs",
                0,
                0,
            ),
            (
                "💾",
                t("action_disk_title"),
                t("action_disk_desc"),
                "Show disk space usage of files and folders in current directory",
                0,
                1,
            ),
            (
                "🐳",
                t("action_docker_title"),
                t("action_docker_desc"),
                "Clean up stopped docker containers, unused volumes, and dangling images",
                1,
                0,
            ),
            (
                "↩",
                t("action_git_title"),
                t("action_git_desc"),
                "Safely undo the last git commit while keeping local changes unstaged",
                1,
                1,
            ),
        ]

        for icon, title, desc, query, r, c in actions:
            card = ctk.CTkFrame(
                grid_frame,
                fg_color=self.COLOR_BG_CARD,
                border_color=self.COLOR_BORDER,
                border_width=1,
                corner_radius=8,
                height=52,
            )
            card.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")
            card.pack_propagate(False)

            # Inner content
            card_inner = ctk.CTkFrame(card, fg_color="transparent")
            card_inner.pack(fill="both", expand=True, padx=10, pady=6)

            # Left icon
            icon_lbl = ctk.CTkLabel(
                card_inner,
                text=icon,
                text_color=self.COLOR_LIGHT_BLUE,
                font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=14, weight="bold"),
            )
            icon_lbl.pack(side="left", padx=(0, 8))

            text_col = ctk.CTkFrame(card_inner, fg_color="transparent")
            text_col.pack(side="left", fill="both", expand=True)

            title_lbl = ctk.CTkLabel(
                text_col,
                text=title,
                text_color=self.COLOR_TEXT_PRIMARY,
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=11, weight="bold"),
                anchor="w",
            )
            title_lbl.pack(fill="x")

            desc_lbl = ctk.CTkLabel(
                text_col,
                text=desc,
                text_color=self.COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=10),
                anchor="w",
            )
            desc_lbl.pack(fill="x")

            # Hover & Click events for entire tile
            def _make_hover(target_card):
                def _enter(e):
                    target_card.configure(fg_color=self.COLOR_BG_CARD_HOVER, border_color=self.COLOR_PRIMARY_BLUE)

                def _leave(e):
                    target_card.configure(fg_color=self.COLOR_BG_CARD, border_color=self.COLOR_BORDER)

                return _enter, _leave

            enter_fn, leave_fn = _make_hover(card)
            for w in (card, card_inner, icon_lbl, text_col, title_lbl, desc_lbl):
                w.bind("<Enter>", enter_fn)
                w.bind("<Leave>", leave_fn)
                w.bind("<Button-1>", lambda e, q=query: self._query_groq(q))

    def _render_result_view(self) -> None:
        """Renders the clean diagnostic and result view with command prioritized at the top."""
        for w in self.body_container.winfo_children():
            w.destroy()

        content_scroll = ctk.CTkScrollableFrame(
            self.body_container,
            fg_color="transparent",
            scrollbar_button_color="#1E293B",
            scrollbar_button_hover_color=self.COLOR_PRIMARY_BLUE,
        )
        content_scroll.pack(fill="both", expand=True, pady=(0, 8))

        # 1. User Query Pill Banner: > {query}
        query_card = ctk.CTkFrame(
            content_scroll,
            fg_color=self.COLOR_BG_CARD,
            border_color=self.COLOR_BORDER,
            border_width=1,
            corner_radius=8,
            height=38,
        )
        query_card.pack(fill="x", pady=(0, 12))
        query_card.pack_propagate(False)

        q_inner = ctk.CTkFrame(query_card, fg_color="transparent")
        q_inner.pack(fill="both", expand=True, padx=12, pady=6)

        ctk.CTkLabel(
            q_inner,
            text="›",
            text_color=self.COLOR_PRIMARY_BLUE,
            font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=self.FONT_SIZE_QUERY_CHEVRON, weight="bold"),
        ).pack(side="left", padx=(0, 8))

        self.query_label = ctk.CTkLabel(
            q_inner,
            text=self.current_query,
            text_color=self.COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=self.FONT_SIZE_QUERY_TEXT),
            anchor="w",
        )
        self.query_label.pack(side="left", fill="x", expand=True)

        # 2. Section: FIX / COMMANDE RECOMMANDEE (Prominently placed at top so it's instantly visible!)
        if self.current_cmd:
            ctk.CTkLabel(
                content_scroll,
                text=t("section_fix"),
                text_color=self.COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=self.FONT_SIZE_SECTION_HEADER, weight="bold"),
                anchor="w",
            ).pack(fill="x", pady=(0, 4))

            self.cmd_box = ctk.CTkFrame(
                content_scroll,
                fg_color=self.COLOR_BG_CODE,
                border_color=self.COLOR_BORDER,
                border_width=1,
                corner_radius=8,
                height=46,
            )
            self.cmd_box.pack(fill="x", pady=(0, 8))
            self.cmd_box.pack_propagate(False)

            cmd_inner = ctk.CTkFrame(self.cmd_box, fg_color="transparent")
            cmd_inner.pack(fill="both", expand=True, padx=12, pady=6)

            ctk.CTkLabel(
                cmd_inner,
                text="$",
                text_color=self.COLOR_TEXT_SUBTLE,
                font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=self.FONT_SIZE_FIX_COMMAND),
            ).pack(side="left", padx=(0, 8))

            self.cmd_text_lbl = ctk.CTkLabel(
                cmd_inner,
                text=self.current_cmd,
                text_color="#60A5FA",
                font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=self.FONT_SIZE_FIX_COMMAND, weight="bold"),
                anchor="w",
            )
            self.cmd_text_lbl.pack(side="left", fill="x", expand=True)

            # Quick Copy Button inside the code box
            self.quick_copy_btn = ctk.CTkButton(
                cmd_inner,
                text="Copier",
                fg_color="#1E293B",
                hover_color=self.COLOR_PRIMARY_BLUE,
                text_color="#CBD5E1",
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=11),
                width=60,
                height=26,
                corner_radius=4,
                command=self.copy_current_command,
            )
            self.quick_copy_btn.pack(side="right")

            # Action Pills Bar: [Enter run] [c copy] [e edit]
            actions_bar = ctk.CTkFrame(content_scroll, fg_color="transparent")
            actions_bar.pack(fill="x", pady=(0, 10))

            self.btn_run = self._create_action_pill(
                actions_bar,
                key_text="Enter",
                label_text=t("action_run"),
                command=self.run_current_command,
                accent=True,
            )
            self.btn_run.pack(side="left", padx=(0, 8))

            self.btn_copy = self._create_action_pill(
                actions_bar,
                key_text="c",
                label_text=t("action_copy"),
                command=self.copy_current_command,
            )
            self.btn_copy.pack(side="left", padx=(0, 8))

            self.btn_edit = self._create_action_pill(
                actions_bar,
                key_text="e",
                label_text=t("action_edit"),
                command=self.edit_current_command,
            )
            self.btn_edit.pack(side="left", padx=(0, 8))

            # Risk Badge Row
            risk_row = ctk.CTkFrame(content_scroll, fg_color="transparent")
            risk_row.pack(fill="x", pady=(0, 12))

            risk_color = (
                self.COLOR_DANGER
                if self.current_risk_level == RiskLevel.DANGEROUS
                else (self.COLOR_WARNING if self.current_risk_level == RiskLevel.WARNING else self.COLOR_SUCCESS)
            )
            risk_label = (
                t("risk_high")
                if self.current_risk_level == RiskLevel.DANGEROUS
                else (t("risk_medium") if self.current_risk_level == RiskLevel.WARNING else t("risk_low"))
            )

            ctk.CTkLabel(
                risk_row,
                text="●",
                text_color=risk_color,
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=10),
            ).pack(side="left", padx=(0, 4))

            ctk.CTkLabel(
                risk_row,
                text=risk_label,
                text_color=risk_color,
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=self.FONT_SIZE_RISK_BADGE, weight="bold"),
            ).pack(side="left", padx=(0, 8))

            ctk.CTkLabel(
                risk_row,
                text=self.current_risk_reason or t("risk_reason_default"),
                text_color=self.COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=self.FONT_SIZE_RISK_BADGE),
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

        # 3. Section: EXPLANATION or CAUSE (Cleaned of raw markdown syntax)
        is_error = any(w in self.current_query.lower() for w in ("diagnose", "error", "failed", "échec", "fail"))
        section_title = t("section_cause") if is_error else t("section_explanation")

        ctk.CTkLabel(
            content_scroll,
            text=section_title,
            text_color=self.COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=self.FONT_SIZE_SECTION_HEADER, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        cleaned_body = clean_markdown_explanation(self.current_cause)

        expl_card = ctk.CTkFrame(
            content_scroll,
            fg_color=self.COLOR_BG_CARD,
            border_color=self.COLOR_BORDER,
            border_width=1,
            corner_radius=8,
        )
        expl_card.pack(fill="x", pady=(0, 12))

        self.cause_body = ctk.CTkLabel(
            expl_card,
            text=cleaned_body or t("thinking"),
            text_color=self.COLOR_TEXT_PRIMARY if self.current_cause else self.COLOR_PRIMARY_BLUE,
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=self.FONT_SIZE_CAUSE_BODY),
            anchor="w",
            justify="left",
            wraplength=680,
        )
        self.cause_body.pack(fill="x", padx=12, pady=10)

        # Execution Result Box (appears when Enter/run is clicked)
        self.exec_box = ctk.CTkFrame(content_scroll, fg_color=self.COLOR_BG_CODE, border_color=self.COLOR_BORDER, border_width=1, corner_radius=6)
        self.exec_label = ctk.CTkLabel(
            self.exec_box,
            text="",
            font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=self.FONT_SIZE_EXEC_OUTPUT),
            justify="left",
            anchor="w",
        )
        self.exec_label.pack(fill="both", expand=True, padx=10, pady=8)

        # 4. Bottom Controls: Follow-up Input Entry
        ctk.CTkFrame(self.body_container, fg_color=self.COLOR_BORDER, height=1).pack(fill="x", pady=(0, 8))

        bottom_input_box = ctk.CTkFrame(
            self.body_container,
            fg_color=self.COLOR_BG_INPUT,
            border_color=self.COLOR_BORDER,
            border_width=1,
            corner_radius=8,
            height=40,
        )
        bottom_input_box.pack(fill="x")
        bottom_input_box.pack_propagate(False)

        ctk.CTkLabel(
            bottom_input_box,
            text="›",
            text_color=self.COLOR_PRIMARY_BLUE,
            font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=16, weight="bold"),
        ).pack(side="left", padx=(10, 6))

        self.input_entry = ctk.CTkEntry(
            bottom_input_box,
            placeholder_text=t("input_placeholder"),
            placeholder_text_color="#475569",
            fg_color="transparent",
            border_width=0,
            text_color=self.COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=self.FONT_SIZE_INPUT_ENTRY),
        )
        self.input_entry.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.input_entry.bind("<Return>", lambda e: self._on_submit_input())

        # Focus ring animation on bottom input
        def _on_bottom_focus(e):
            bottom_input_box.configure(border_color=self.COLOR_PRIMARY_BLUE)

        def _on_bottom_blur(e):
            bottom_input_box.configure(border_color=self.COLOR_BORDER)

        self.input_entry.bind("<FocusIn>", _on_bottom_focus)
        self.input_entry.bind("<FocusOut>", _on_bottom_blur)

        # Back to launcher button
        back_btn = ctk.CTkButton(
            bottom_input_box,
            text="← Retour",
            fg_color="#1E293B",
            hover_color=self.COLOR_PRIMARY_BLUE,
            text_color="#94A3B8",
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=11),
            width=70,
            height=28,
            corner_radius=5,
            command=self._reset_to_launcher,
        )
        back_btn.pack(side="right", padx=(0, 6), pady=6)

    def _reset_to_launcher(self) -> None:
        """Returns from result view back to launcher view."""
        self.current_query = ""
        self.current_cause = ""
        self.current_cmd = ""
        self._render_launcher_view()

    def _create_action_pill(
        self,
        parent: ctk.CTkFrame,
        key_text: str,
        label_text: str,
        command,
        accent: bool = False,
    ) -> ctk.CTkFrame:
        """Creates a sleek key action pill."""
        bg_col = self.COLOR_PRIMARY_BLUE if accent else self.COLOR_BG_CARD
        border_col = self.COLOR_BLUE_HOVER if accent else self.COLOR_BORDER

        pill = ctk.CTkFrame(
            parent,
            fg_color=bg_col,
            border_color=border_col,
            border_width=1,
            corner_radius=6,
            height=28,
        )
        pill.pack_propagate(False)

        key_lbl = ctk.CTkLabel(
            pill,
            text=key_text,
            text_color="#FFFFFF" if accent else "#CBD5E1",
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=self.FONT_SIZE_PILL_KEY, weight="bold"),
            fg_color=self.COLOR_BLUE_HOVER if accent else "#1E293B",
            corner_radius=4,
            width=28 if len(key_text) <= 2 else 42,
            height=20,
        )
        key_lbl.pack(side="left", padx=(3, 5), pady=3)

        lbl = ctk.CTkLabel(
            pill,
            text=label_text,
            text_color="#FFFFFF" if accent else self.COLOR_TEXT_MUTED,
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=self.FONT_SIZE_PILL_LABEL, weight="bold" if accent else "normal"),
        )
        lbl.pack(side="left", padx=(0, 8), pady=3)

        def _on_enter(e):
            if not accent:
                pill.configure(fg_color="#1E293B", border_color=self.COLOR_PRIMARY_BLUE)

        def _on_leave(e):
            if not accent:
                pill.configure(fg_color=self.COLOR_BG_CARD, border_color=self.COLOR_BORDER)

        for w in (pill, key_lbl, lbl):
            w.bind("<Button-1>", lambda e: command())
            w.bind("<Enter>", _on_enter)
            w.bind("<Leave>", _on_leave)

        return pill

    def _handle_global_key(self, event) -> None:
        """Handles single-key shortcuts when the text entry is not focused."""
        if hasattr(self, "input_entry") and self.focus_get() == self.input_entry._entry:
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

    def run_current_command(self) -> None:
        """Executes the fix command via PTYExecutor and displays terminal output."""
        cmd = self.current_cmd.strip()
        if not cmd:
            return

        result = PTYExecutor.execute(cmd, cwd=os.getcwd(), forward_output=False)

        is_ok = result.exit_code == 0
        status_col = self.COLOR_SUCCESS if is_ok else self.COLOR_DANGER
        status_text = (
            f"› {t('cmd_success')}\n{result.clean_output.strip() or t('cmd_no_output')}"
            if is_ok
            else f"✘ Command exited with code {result.exit_code}\n{result.clean_output.strip() or t('cmd_no_output')}"
        )

        self.exec_label.configure(text=status_text, text_color=status_col)
        self.exec_box.pack(fill="x", pady=(0, 10))

    def copy_current_command(self) -> None:
        """Copies the fix command to clipboard."""
        try:
            self.clipboard_clear()
            self.clipboard_append(self.current_cmd)
        except Exception:
            pass

        if hasattr(self, "quick_copy_btn"):
            self.quick_copy_btn.configure(text="✓ Copié !", fg_color=self.COLOR_SUCCESS)
            self.after(1200, lambda: self.quick_copy_btn.configure(text="Copier", fg_color="#1E293B"))

        if hasattr(self, "cmd_box"):
            self.cmd_box.configure(border_color=self.COLOR_PRIMARY_BLUE)
            self.after(500, lambda: self.cmd_box.configure(border_color=self.COLOR_BORDER))

    def edit_current_command(self) -> None:
        """Populates the input entry with the current command."""
        self.input_entry.delete(0, "end")
        self.input_entry.insert(0, self.current_cmd)
        self.input_entry.focus()

    def _on_submit_input(self) -> None:
        """Queries AI with the text from input_entry."""
        query = self.input_entry.get().strip()
        if not query:
            return

        self.input_entry.delete(0, "end")
        self._query_groq(query)

    def _query_groq(self, query: str) -> None:
        """Sends query to active LLM in a background thread and updates the UI."""
        self.current_query = query
        self.current_cause = ""
        self.current_cmd = ""
        self.current_risk_reason = ""
        self._render_result_view()

        def _worker():
            try:
                if not self.chat_session:
                    self.after(
                        0,
                        lambda: self._apply_error(t("error_no_api_key")),
                    )
                    return

                result: ChatMessageResult = self.chat_session.send_message(query)
                self.after(0, lambda: self._apply_result(result))
            except Exception as e:
                self.after(0, lambda: self._apply_error(str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_result(self, result: ChatMessageResult) -> None:
        """Parses and renders AI diagnosis and suggested command."""
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
        """Renders API error message."""
        self.current_cause = f"{t('error_api_generic')}{err_msg}"
        self.current_cmd = ""
        self._render_result_view()

    def _start_drag(self, event) -> None:
        """Records mouse offset for window dragging."""
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event) -> None:
        """Updates window position as mouse is dragged."""
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")
