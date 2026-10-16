from __future__ import annotations

import os
from pathlib import Path
import re
import threading
from typing import List, Optional

import customtkinter as ctk
from PIL import Image

from src.core.assistant import ChatMessageResult, ChatSession, extract_bash_commands
from src.core.config import EzShellConfig
from src.core.context import SystemContext, get_last_shell_command
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

    FONT_SIZE_APP_TITLE = 20
    FONT_SIZE_QUERY_CHEVRON = 18
    FONT_SIZE_QUERY_TEXT = 16
    FONT_SIZE_SECTION_HEADER = 12
    FONT_SIZE_CAUSE_BODY = 15
    FONT_SIZE_FIX_COMMAND = 15
    FONT_SIZE_RISK_BADGE = 13
    FONT_SIZE_INPUT_ENTRY = 14
    FONT_SIZE_PILL_KEY = 12
    FONT_SIZE_PILL_LABEL = 12
    FONT_SIZE_EXEC_OUTPUT = 13

    # Modern refined developer color palette
    COLOR_PRIMARY_BLUE = "#3B82F6"      # Refined royal blue accent
    COLOR_BLUE_HOVER = "#2563EB"        # Active button blue
    COLOR_LIGHT_BLUE = "#60A5FA"        # Light blue highlights
    COLOR_BG_WINDOW = "#0B0F17"         # Clean deep slate window background
    COLOR_BG_CARD = "#111827"           # Dark card background
    COLOR_BG_INPUT = "#0F172A"          # Input entry background
    COLOR_BORDER = "#1F2937"            # Subtle card border
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

        # Dimensions & screen centering
        win_w, win_h = 820, 580
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = max(0, (sw - win_w) // 2)
            y = max(0, (sh - win_h) // 2)
            self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        except Exception:
            self.geometry(f"{win_w}x{win_h}")

        self.minsize(700, 480)

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

        # Load logo image (supports 28x28 pre-rendered PNG via Tk PhotoImage)
        self.logo_image = None
        logo_28_path = Path(__file__).resolve().parent.parent.parent / "assets" / "logo_28.png"
        if not logo_28_path.is_file():
            # Auto-generate 28x28 if only original exists
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
        self.main_container.pack(fill="both", expand=True, padx=24, pady=20)

        # 1. Header Bar: [Icon] ez (blue) Shell (white) ............ [Esc] to close
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent", height=36)
        self.header_frame.pack(fill="x", pady=(0, 14))

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
            logo_lbl.pack(side="left", padx=(0, 10))
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
            height=30,
        )
        close_pill.pack(side="right")

        esc_badge = ctk.CTkLabel(
            close_pill,
            text="Esc",
            text_color="#CBD5E1",
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=self.FONT_SIZE_PILL_KEY, weight="bold"),
            fg_color="#1E293B",
            corner_radius=4,
            width=34,
            height=22,
        )
        esc_badge.pack(side="left", padx=(4, 6), pady=4)

        close_text = ctk.CTkLabel(
            close_pill,
            text=t("esc_to_close"),
            text_color=self.COLOR_TEXT_SUBTLE,
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=self.FONT_SIZE_PILL_LABEL),
        )
        close_text.pack(side="left", padx=(0, 8), pady=4)

        close_pill.bind("<Button-1>", lambda e: self.destroy())
        esc_badge.bind("<Button-1>", lambda e: self.destroy())
        close_text.bind("<Button-1>", lambda e: self.destroy())

        # Top divider line
        ctk.CTkFrame(self.main_container, fg_color=self.COLOR_BORDER, height=1).pack(fill="x", pady=(0, 16))

        # Dynamic body container
        self.body_container = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.body_container.pack(fill="both", expand=True)

        if self.current_query:
            self._render_result_view()
        else:
            self._render_launcher_view()

    def _render_launcher_view(self) -> None:
        """Renders clean, focused launcher mode when no query has been asked yet."""
        for w in self.body_container.winfo_children():
            w.destroy()

        # 1. Primary Search / Query Entry
        search_card = ctk.CTkFrame(
            self.body_container,
            fg_color=self.COLOR_BG_INPUT,
            border_color=self.COLOR_PRIMARY_BLUE,
            border_width=1.5,
            corner_radius=10,
            height=54,
        )
        search_card.pack(fill="x", pady=(8, 20))
        search_card.pack_propagate(False)

        prompt_icon = ctk.CTkLabel(
            search_card,
            text="›",
            text_color=self.COLOR_PRIMARY_BLUE,
            font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=20, weight="bold"),
        )
        prompt_icon.pack(side="left", padx=(14, 8))

        self.input_entry = ctk.CTkEntry(
            search_card,
            placeholder_text=t("input_placeholder"),
            placeholder_text_color="#475569",
            fg_color="transparent",
            border_width=0,
            text_color=self.COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=self.FONT_SIZE_INPUT_ENTRY),
        )
        self.input_entry.pack(side="left", fill="both", expand=True, padx=(0, 10))
        self.input_entry.bind("<Return>", lambda e: self._on_submit_input())
        self.input_entry.focus()

        ask_btn = ctk.CTkButton(
            search_card,
            text=t("btn_send"),
            fg_color=self.COLOR_PRIMARY_BLUE,
            hover_color=self.COLOR_BLUE_HOVER,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=13, weight="bold"),
            width=80,
            height=36,
            corner_radius=6,
            command=self._on_submit_input,
        )
        ask_btn.pack(side="right", padx=(0, 8), pady=8)

        # 2. Context Card: Detected Last Shell Command (if available)
        if self.last_detected_cmd:
            last_cmd_card = ctk.CTkFrame(
                self.body_container,
                fg_color=self.COLOR_BG_CARD,
                border_color=self.COLOR_BORDER,
                border_width=1,
                corner_radius=8,
            )
            last_cmd_card.pack(fill="x", pady=(0, 18))

            row_top = ctk.CTkFrame(last_cmd_card, fg_color="transparent")
            row_top.pack(fill="x", padx=14, pady=(10, 6))

            ctk.CTkLabel(
                row_top,
                text=f"› {t('last_cmd_detected')}",
                text_color=self.COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=12, weight="bold"),
                anchor="w",
            ).pack(side="left")

            cmd_mono = ctk.CTkLabel(
                last_cmd_card,
                text=f"  $ {self.last_detected_cmd}",
                text_color=self.COLOR_LIGHT_BLUE,
                font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=13, weight="bold"),
                anchor="w",
            )
            cmd_mono.pack(fill="x", padx=14, pady=(0, 10))

            btn_row = ctk.CTkFrame(last_cmd_card, fg_color="transparent")
            btn_row.pack(fill="x", padx=14, pady=(0, 12))

            diag_btn = ctk.CTkButton(
                btn_row,
                text=f"› {t('btn_diagnose_error')}",
                fg_color="#1E293B",
                hover_color="#334155",
                border_color=self.COLOR_PRIMARY_BLUE,
                border_width=1,
                text_color=self.COLOR_LIGHT_BLUE,
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=12, weight="bold"),
                height=30,
                corner_radius=6,
                command=lambda: self._query_groq(f"diagnose failed command: {self.last_detected_cmd}"),
            )
            diag_btn.pack(side="left", padx=(0, 10))

            explain_btn = ctk.CTkButton(
                btn_row,
                text=t("btn_explain_command"),
                fg_color="#1E293B",
                hover_color="#334155",
                text_color=self.COLOR_TEXT_MUTED,
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=12),
                height=30,
                corner_radius=6,
                command=lambda: self._query_groq(f"explain what this command does: {self.last_detected_cmd}"),
            )
            explain_btn.pack(side="left")

        # 3. Quick Suggestions Section
        ctk.CTkLabel(
            self.body_container,
            text=t("quick_suggestions"),
            text_color=self.COLOR_TEXT_SUBTLE,
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=11, weight="bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        suggestions_grid = ctk.CTkFrame(self.body_container, fg_color="transparent")
        suggestions_grid.pack(fill="x")

        quick_actions = [
            ("Ports", "List open listening ports and their processes"),
            ("Disk", "Show disk space usage of current folder"),
            ("Docker", "Clean up stopped docker containers and unused images"),
            ("Git Undo", "Undo last git commit while keeping local changes"),
        ]

        for label, query in quick_actions:
            btn = ctk.CTkButton(
                suggestions_grid,
                text=f"› {label}",
                fg_color=self.COLOR_BG_CARD,
                hover_color="#1E293B",
                border_color=self.COLOR_BORDER,
                border_width=1,
                text_color=self.COLOR_TEXT_PRIMARY,
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=12),
                height=32,
                corner_radius=6,
                command=lambda q=query: self._query_groq(q),
            )
            btn.pack(side="left", padx=(0, 8), pady=2)

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
        content_scroll.pack(fill="both", expand=True, pady=(0, 10))

        # 1. User Query Row: > {query}
        query_row = ctk.CTkFrame(content_scroll, fg_color="transparent")
        query_row.pack(fill="x", pady=(0, 14))

        ctk.CTkLabel(
            query_row,
            text=">",
            text_color=self.COLOR_PRIMARY_BLUE,
            font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=self.FONT_SIZE_QUERY_CHEVRON, weight="bold"),
        ).pack(side="left", padx=(0, 8))

        self.query_label = ctk.CTkLabel(
            query_row,
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
            ).pack(fill="x", pady=(0, 6))

            self.cmd_box = ctk.CTkFrame(
                content_scroll,
                fg_color=self.COLOR_BG_CARD,
                border_color=self.COLOR_BORDER,
                border_width=1,
                corner_radius=8,
                height=48,
            )
            self.cmd_box.pack(fill="x", pady=(0, 10))
            self.cmd_box.pack_propagate(False)

            cmd_inner = ctk.CTkFrame(self.cmd_box, fg_color="transparent")
            cmd_inner.pack(fill="both", expand=True, padx=14, pady=8)

            ctk.CTkLabel(
                cmd_inner,
                text="$",
                text_color=self.COLOR_TEXT_SUBTLE,
                font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=self.FONT_SIZE_FIX_COMMAND),
            ).pack(side="left", padx=(0, 10))

            self.cmd_text_lbl = ctk.CTkLabel(
                cmd_inner,
                text=self.current_cmd,
                text_color=self.COLOR_TEXT_PRIMARY,
                font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=self.FONT_SIZE_FIX_COMMAND, weight="bold"),
                anchor="w",
            )
            self.cmd_text_lbl.pack(side="left", fill="x", expand=True)

            # Section: RISK BADGE
            risk_row = ctk.CTkFrame(content_scroll, fg_color="transparent")
            risk_row.pack(fill="x", pady=(0, 14))

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
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=self.FONT_SIZE_RISK_BADGE),
            ).pack(side="left", padx=(0, 6))

            ctk.CTkLabel(
                risk_row,
                text=risk_label,
                text_color=risk_color,
                font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=self.FONT_SIZE_RISK_BADGE, weight="bold"),
            ).pack(side="left", padx=(0, 12))

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
        ).pack(fill="x", pady=(0, 6))

        cleaned_body = clean_markdown_explanation(self.current_cause)

        self.cause_body = ctk.CTkLabel(
            content_scroll,
            text=cleaned_body or t("thinking"),
            text_color=self.COLOR_TEXT_PRIMARY if self.current_cause else self.COLOR_PRIMARY_BLUE,
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=self.FONT_SIZE_CAUSE_BODY),
            anchor="w",
            justify="left",
            wraplength=760,
        )
        self.cause_body.pack(fill="x", pady=(0, 16))

        # Execution Result Box (appears when Enter/run is clicked)
        self.exec_box = ctk.CTkFrame(content_scroll, fg_color=self.COLOR_BG_CARD, corner_radius=6)
        self.exec_label = ctk.CTkLabel(
            self.exec_box,
            text="",
            font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=self.FONT_SIZE_EXEC_OUTPUT),
            justify="left",
            anchor="w",
        )
        self.exec_label.pack(fill="both", expand=True, padx=10, pady=8)

        # 4. Bottom Controls: Divider + Input + Action Pills
        ctk.CTkFrame(self.body_container, fg_color=self.COLOR_BORDER, height=1).pack(fill="x", pady=(0, 10))

        # Bottom follow-up input
        self.input_entry = ctk.CTkEntry(
            self.body_container,
            placeholder_text=t("input_placeholder"),
            placeholder_text_color="#475569",
            fg_color=self.COLOR_BG_INPUT,
            border_color=self.COLOR_BORDER,
            border_width=1,
            text_color=self.COLOR_TEXT_PRIMARY,
            font=ctk.CTkFont(family=self.FONT_FAMILY_CODE, size=self.FONT_SIZE_INPUT_ENTRY),
            height=40,
            corner_radius=6,
        )
        self.input_entry.pack(fill="x", pady=(0, 10))
        self.input_entry.bind("<Return>", lambda e: self._on_submit_input())

        # Action Pills
        actions_row = ctk.CTkFrame(self.body_container, fg_color="transparent", height=32)
        actions_row.pack(fill="x")

        if self.current_cmd:
            self.btn_run = self._create_action_pill(
                actions_row,
                key_text="Enter",
                label_text=t("action_run"),
                command=self.run_current_command,
            )
            self.btn_run.pack(side="left", padx=(0, 8))

            self.btn_copy = self._create_action_pill(
                actions_row,
                key_text="c",
                label_text=t("action_copy"),
                command=self.copy_current_command,
            )
            self.btn_copy.pack(side="left", padx=(0, 8))

            self.btn_edit = self._create_action_pill(
                actions_row,
                key_text="e",
                label_text=t("action_edit"),
                command=self.edit_current_command,
            )
            self.btn_edit.pack(side="left", padx=(0, 8))

        self.btn_close = self._create_action_pill(
            actions_row,
            key_text="q",
            label_text=t("action_close"),
            command=self.destroy,
        )
        self.btn_close.pack(side="left")

    def _create_action_pill(
        self,
        parent: ctk.CTkFrame,
        key_text: str,
        label_text: str,
        command,
    ) -> ctk.CTkFrame:
        """Creates a sleek key action pill."""
        pill = ctk.CTkFrame(
            parent,
            fg_color=self.COLOR_BG_CARD,
            border_color=self.COLOR_BORDER,
            border_width=1,
            corner_radius=6,
            height=30,
        )
        pill.pack_propagate(False)

        key_lbl = ctk.CTkLabel(
            pill,
            text=key_text,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=self.FONT_SIZE_PILL_KEY, weight="bold"),
        )
        key_lbl.pack(side="left", padx=(10, 6), pady=4)

        lbl = ctk.CTkLabel(
            pill,
            text=label_text,
            text_color=self.COLOR_TEXT_SUBTLE,
            font=ctk.CTkFont(family=self.FONT_FAMILY_UI, size=self.FONT_SIZE_PILL_LABEL),
        )
        lbl.pack(side="left", padx=(0, 10), pady=4)

        def _on_enter(e):
            pill.configure(fg_color="#1E293B", border_color=self.COLOR_PRIMARY_BLUE)

        def _on_leave(e):
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

        if hasattr(self, "cmd_box"):
            self.cmd_box.configure(border_color=self.COLOR_PRIMARY_BLUE)
            self.after(500, lambda: self.cmd_box.configure(border_color=self.COLOR_BORDER))

    def edit_current_command(self) -> None:
        """Populates the input entry with the current command."""
        self.input_entry.delete(0, "end")
        self.input_entry.insert(0, self.current_cmd)
        self.input_entry.focus()

    def _on_submit_input(self) -> None:
        """Queries Groq AI with the text from input_entry."""
        query = self.input_entry.get().strip()
        if not query:
            return

        self.input_entry.delete(0, "end")
        self._query_groq(query)

    def _query_groq(self, query: str) -> None:
        """Sends query to Groq in a background thread and updates the UI."""
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
        """Parses and renders Groq's diagnosis and suggested command."""
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

        # Re-render the view with the fresh AI content
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
