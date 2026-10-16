from __future__ import annotations

import os
from pathlib import Path
import threading
from typing import List, Optional

import customtkinter as ctk
from PIL import Image

from src.core.assistant import ChatMessageResult, ChatSession, extract_bash_commands
from src.core.config import EzShellConfig
from src.core.context import SystemContext
from src.core.pty_shell import PTYExecutor
from src.core.safety import RiskLevel, SafetyGuard, SafetyReport


class EzShellDesktopApp(ctk.CTk):
    """Pixel-perfect modern desktop GUI popup window for ezShell AI Assistant.

    Follows the exact visual reference:
    - Top bar: Logo [>_] + ezShell (left), [Esc] to close pill (right)
    - Prompt: > explain this error (or user query)
    - CAUSE: Root cause diagnosis
    - FIX: Monospace command block
    - RISK: Neon badge (● LOW RISK / HIGH RISK) + safety rationale
    - Divider line
    - ASK ANOTHER QUESTION: Interactive input bar
    - Action pills: [Enter  run]  [c  copy]  [e  edit]  [q  close]
    """

    # Premium developer typography constants
    FONT_UI = "Inter"
    FONT_UI_DISPLAY = "Inter Display"
    FONT_CODE = "JetBrains Mono"

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
        self.configure(fg_color="#0B121B")

        # Compact popup dimensions (matching the mockup)
        win_w, win_h = 760, 560
        try:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            x = max(0, (sw - win_w) // 2)
            y = max(0, (sh - win_h) // 2)
            self.geometry(f"{win_w}x{win_h}+{x}+{y}")
        except Exception:
            self.geometry(f"{win_w}x{win_h}")

        self.minsize(640, 480)

        # Keyboard shortcuts
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<KeyPress>", self._handle_global_key)

        # Drag tracking
        self._drag_x = 0
        self._drag_y = 0

        # State
        self.current_query = initial_query or "explain this error"
        self.current_cause = (
            "Your local branch is behind origin/main, so Git rejected the push."
        )
        self.current_cmd = "git pull --rebase origin main"
        self.current_risk_level = RiskLevel.SAFE
        self.current_risk_reason = "Only changes your local branch."
        self.error_context = error_context

        # Load logo image
        self.logo_path = Path(__file__).resolve().parent.parent.parent / "assets" / "logo.png"
        self.logo_image: Optional[ctk.CTkImage] = None
        if self.logo_path.exists():
            try:
                pil_img = Image.open(self.logo_path).resize((26, 26), Image.Resampling.LANCZOS)
                self.logo_image = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(26, 26))
            except Exception:
                pass

        self._build_ui()

        # If a real query or error was provided, analyze it
        if initial_query or error_context:
            self._query_groq(initial_query or "explain this error")

    def _build_ui(self) -> None:
        """Constructs the exact layout matching the visual reference."""
        # Main outer padding frame
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=24, pady=20)

        # 1. Header Bar: [Icon] ezShell ............ [Esc] to close
        self.header_frame = ctk.CTkFrame(self.main_container, fg_color="transparent", height=36)
        self.header_frame.pack(fill="x", pady=(0, 16))

        # Drag support on header
        self.header_frame.bind("<ButtonPress-1>", self._start_drag)
        self.header_frame.bind("<B1-Motion>", self._on_drag)

        # Left: Logo icon + ezShell label
        header_left = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_left.pack(side="left")
        header_left.bind("<ButtonPress-1>", self._start_drag)
        header_left.bind("<B1-Motion>", self._on_drag)

        if self.logo_image:
            logo_lbl = ctk.CTkLabel(header_left, text="", image=self.logo_image)
            logo_lbl.pack(side="left", padx=(0, 10))
            logo_lbl.bind("<ButtonPress-1>", self._start_drag)
            logo_lbl.bind("<B1-Motion>", self._on_drag)
        else:
            prompt_mark = ctk.CTkLabel(
                header_left,
                text=">_",
                text_color="#00E5FF",
                font=ctk.CTkFont(family="JetBrains Mono", size=16, weight="bold"),
            )
            prompt_mark.pack(side="left", padx=(0, 8))

        app_title = ctk.CTkLabel(
            header_left,
            text="ezShell",
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Inter Display", size=18, weight="bold"),
        )
        app_title.pack(side="left")
        app_title.bind("<ButtonPress-1>", self._start_drag)
        app_title.bind("<B1-Motion>", self._on_drag)

        # Right: [Esc] to close pill
        close_pill = ctk.CTkFrame(
            self.header_frame,
            fg_color="#101926",
            border_color="#1B2B3F",
            border_width=1,
            corner_radius=6,
            height=28,
        )
        close_pill.pack(side="right")

        esc_badge = ctk.CTkLabel(
            close_pill,
            text="Esc",
            text_color="#CBD5E1",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            fg_color="#1E2C40",
            corner_radius=4,
            width=32,
            height=20,
        )
        esc_badge.pack(side="left", padx=(4, 6), pady=4)

        close_text = ctk.CTkLabel(
            close_pill,
            text="to close",
            text_color="#64748B",
            font=ctk.CTkFont(family="Inter", size=11),
        )
        close_text.pack(side="left", padx=(0, 8), pady=4)

        # Click on close pill closes app
        close_pill.bind("<Button-1>", lambda e: self.destroy())
        esc_badge.bind("<Button-1>", lambda e: self.destroy())
        close_text.bind("<Button-1>", lambda e: self.destroy())

        # Top divider line
        ctk.CTkFrame(self.main_container, fg_color="#152232", height=1).pack(fill="x", pady=(0, 16))

        # 2. Content Area (Scrollable if content is long, but transparent & compact)
        self.content_frame = ctk.CTkFrame(self.main_container, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True)

        # User Query: > explain this error
        self.query_row = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.query_row.pack(fill="x", pady=(0, 14))

        self.query_chevron = ctk.CTkLabel(
            self.query_row,
            text=">",
            text_color="#00E5FF",
            font=ctk.CTkFont(family="JetBrains Mono", size=15, weight="bold"),
        )
        self.query_chevron.pack(side="left", padx=(0, 8))

        self.query_label = ctk.CTkLabel(
            self.query_row,
            text=self.current_query,
            text_color="#F1F5F9",
            font=ctk.CTkFont(family="JetBrains Mono", size=14),
            anchor="w",
        )
        self.query_label.pack(side="left", fill="x", expand=True)

        # Section: CAUSE
        self.cause_header = ctk.CTkLabel(
            self.content_frame,
            text="CAUSE",
            text_color="#64748B",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            anchor="w",
        )
        self.cause_header.pack(fill="x", pady=(0, 4))

        self.cause_body = ctk.CTkLabel(
            self.content_frame,
            text=self.current_cause,
            text_color="#E2E8F0",
            font=ctk.CTkFont(family="Inter", size=13),
            anchor="w",
            justify="left",
            wraplength=710,
        )
        self.cause_body.pack(fill="x", pady=(0, 16))

        # Section: FIX
        self.fix_header = ctk.CTkLabel(
            self.content_frame,
            text="FIX",
            text_color="#64748B",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            anchor="w",
        )
        self.fix_header.pack(fill="x", pady=(0, 6))

        # Code block: $ git pull --rebase origin main
        self.cmd_box = ctk.CTkFrame(
            self.content_frame,
            fg_color="#070D16",
            border_color="#182739",
            border_width=1,
            corner_radius=8,
            height=44,
        )
        self.cmd_box.pack(fill="x", pady=(0, 14))
        self.cmd_box.pack_propagate(False)

        cmd_inner = ctk.CTkFrame(self.cmd_box, fg_color="transparent")
        cmd_inner.pack(fill="both", expand=True, padx=14, pady=8)

        self.prompt_dollar = ctk.CTkLabel(
            cmd_inner,
            text="$",
            text_color="#64748B",
            font=ctk.CTkFont(family="JetBrains Mono", size=13),
        )
        self.prompt_dollar.pack(side="left", padx=(0, 10))

        self.cmd_text_lbl = ctk.CTkLabel(
            cmd_inner,
            text=self.current_cmd,
            text_color="#00E5FF",
            font=ctk.CTkFont(family="JetBrains Mono", size=13, weight="bold"),
            anchor="w",
        )
        self.cmd_text_lbl.pack(side="left", fill="x", expand=True)

        # Section: RISK BADGE
        self.risk_row = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        self.risk_row.pack(fill="x", pady=(0, 16))

        self.risk_dot = ctk.CTkLabel(
            self.risk_row,
            text="●",
            text_color="#00FF88",
            font=ctk.CTkFont(family="Inter", size=12),
        )
        self.risk_dot.pack(side="left", padx=(0, 6))

        self.risk_title = ctk.CTkLabel(
            self.risk_row,
            text="LOW RISK",
            text_color="#00FF88",
            font=ctk.CTkFont(family="Inter", size=12, weight="bold"),
        )
        self.risk_title.pack(side="left", padx=(0, 12))

        self.risk_reason_lbl = ctk.CTkLabel(
            self.risk_row,
            text=self.current_risk_reason,
            text_color="#7B8C9F",
            font=ctk.CTkFont(family="Inter", size=12),
            anchor="w",
        )
        self.risk_reason_lbl.pack(side="left", fill="x", expand=True)

        # Optional execution result box (appears when Enter/run is clicked)
        self.exec_box = ctk.CTkFrame(self.content_frame, fg_color="#060C14", corner_radius=6)
        self.exec_label = ctk.CTkLabel(
            self.exec_box,
            text="",
            font=ctk.CTkFont(family="JetBrains Mono", size=11),
            justify="left",
            anchor="w",
        )
        self.exec_label.pack(fill="both", expand=True, padx=10, pady=8)

        # 3. Bottom Section: Separator + ASK ANOTHER QUESTION + Action pills
        ctk.CTkFrame(self.main_container, fg_color="#152232", height=1).pack(fill="x", pady=(0, 14))

        self.ask_header = ctk.CTkLabel(
            self.main_container,
            text="ASK ANOTHER QUESTION",
            text_color="#64748B",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
            anchor="w",
        )
        self.ask_header.pack(fill="x", pady=(0, 8))

        # Input field
        self.input_entry = ctk.CTkEntry(
            self.main_container,
            placeholder_text="Type a question or error to diagnose... (Enter to ask)",
            placeholder_text_color="#475569",
            fg_color="#070D16",
            border_color="#1B2B3F",
            border_width=1,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="JetBrains Mono", size=12),
            height=38,
            corner_radius=6,
        )
        self.input_entry.pack(fill="x", pady=(0, 12))
        self.input_entry.bind("<Return>", lambda e: self._on_submit_input())

        # 4. Action Pills Row: [Enter  run]  [c  copy]  [e  edit]  [q  close]
        self.actions_row = ctk.CTkFrame(self.main_container, fg_color="transparent", height=32)
        self.actions_row.pack(fill="x")

        self.btn_run = self._create_action_pill(
            self.actions_row,
            key_text="Enter",
            label_text="run",
            command=self.run_current_command,
        )
        self.btn_run.pack(side="left", padx=(0, 8))

        self.btn_copy = self._create_action_pill(
            self.actions_row,
            key_text="c",
            label_text="copy",
            command=self.copy_current_command,
        )
        self.btn_copy.pack(side="left", padx=(0, 8))

        self.btn_edit = self._create_action_pill(
            self.actions_row,
            key_text="e",
            label_text="edit",
            command=self.edit_current_command,
        )
        self.btn_edit.pack(side="left", padx=(0, 8))

        self.btn_close = self._create_action_pill(
            self.actions_row,
            key_text="q",
            label_text="close",
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
        """Creates a sleek key action pill matching the visual reference."""
        pill = ctk.CTkFrame(
            parent,
            fg_color="#0E1724",
            border_color="#1C2B3E",
            border_width=1,
            corner_radius=6,
            height=28,
        )
        pill.pack_propagate(False)

        key_lbl = ctk.CTkLabel(
            pill,
            text=key_text,
            text_color="#FFFFFF",
            font=ctk.CTkFont(family="Inter", size=11, weight="bold"),
        )
        key_lbl.pack(side="left", padx=(10, 6), pady=4)

        lbl = ctk.CTkLabel(
            pill,
            text=label_text,
            text_color="#64748B",
            font=ctk.CTkFont(family="Inter", size=11),
        )
        lbl.pack(side="left", padx=(0, 10), pady=4)

        # Hover effects & click handler
        def _on_enter(e):
            pill.configure(fg_color="#162337", border_color="#00E5FF")

        def _on_leave(e):
            pill.configure(fg_color="#0E1724", border_color="#1C2B3E")

        for w in (pill, key_lbl, lbl):
            w.bind("<Button-1>", lambda e: command())
            w.bind("<Enter>", _on_enter)
            w.bind("<Leave>", _on_leave)

        return pill

    def _handle_global_key(self, event) -> None:
        """Handles single-key shortcuts when the text entry is not focused."""
        # If user is typing in input_entry, let normal typing happen
        if self.focus_get() == self.input_entry._entry:
            return

        k = event.keysym.lower()
        if k == "q":
            self.destroy()
        elif k == "c":
            self.copy_current_command()
        elif k == "e":
            self.edit_current_command()
        elif k == "return":
            self.run_current_command()

    def run_current_command(self) -> None:
        """Executes the fix command via PTYExecutor and displays terminal output."""
        cmd = self.current_cmd.strip()
        if not cmd:
            return

        self.cmd_box.configure(border_color="#00FF88")
        result = PTYExecutor.execute(cmd, cwd=os.getcwd(), forward_output=False)

        is_ok = result.exit_code == 0
        status_col = "#00FF88" if is_ok else "#FF2A6D"
        status_text = (
            f"› Command finished (exit 0)\n{result.clean_output.strip() or '(No output)'}"
            if is_ok
            else f"✘ Command exited with code {result.exit_code}\n{result.clean_output.strip() or '(No output)'}"
        )

        self.exec_label.configure(text=status_text, text_color=status_col)
        self.exec_box.pack(fill="x", pady=(0, 10))

    def copy_current_command(self) -> None:
        """Copies the fix command to clipboard with temporary button feedback."""
        try:
            self.clipboard_clear()
            self.clipboard_append(self.current_cmd)
        except Exception:
            pass

        # Visual feedback: flash border
        self.cmd_box.configure(border_color="#00E5FF")
        self.after(600, lambda: self.cmd_box.configure(border_color="#182739"))

    def edit_current_command(self) -> None:
        """Populates the input entry with the current command and focuses it."""
        self.input_entry.delete(0, "end")
        self.input_entry.insert(0, self.current_cmd)
        self.input_entry.focus()

    def _on_submit_input(self) -> None:
        """Queries Groq AI with the question from the input entry."""
        query = self.input_entry.get().strip()
        if not query:
            return

        self.input_entry.delete(0, "end")
        self._query_groq(query)

    def _query_groq(self, query: str) -> None:
        """Sends query to Groq in a background thread and updates the UI."""
        self.current_query = query
        self.query_label.configure(text=query)
        self.cause_body.configure(text="Analyzing with Groq AI...", text_color="#00E5FF")
        self.cmd_text_lbl.configure(text="thinking...", text_color="#64748B")
        self.exec_box.pack_forget()

        def _worker():
            try:
                if not self.chat_session:
                    self.after(
                        0,
                        lambda: self._apply_error(
                            "GROQ_API_KEY is missing. Run 'ezsh --set-key <key>'."
                        ),
                    )
                    return

                result: ChatMessageResult = self.chat_session.send_message(query)
                self.after(0, lambda: self._apply_result(result))
            except Exception as e:
                self.after(0, lambda: self._apply_error(str(e)))

        threading.Thread(target=_worker, daemon=True).start()

    def _apply_result(self, result: ChatMessageResult) -> None:
        """Parses and renders Groq's diagnosis and suggested command."""
        # Cause explanation
        content = result.content.strip()
        self.current_cause = content
        self.cause_body.configure(text=content, text_color="#E2E8F0")

        # Suggested command
        if result.suggested_commands:
            self.current_cmd = result.suggested_commands[0]
            self.cmd_text_lbl.configure(text=self.current_cmd, text_color="#00E5FF")

            # Risk report
            if result.safety_reports:
                report = result.safety_reports[0]
                self.current_risk_level = report.risk_level
                self.current_risk_reason = report.reason or "Standard terminal command."

                if report.risk_level == RiskLevel.DANGEROUS:
                    color = "#FF2A6D"
                    title = "HIGH RISK"
                elif report.risk_level == RiskLevel.WARNING:
                    color = "#FFB800"
                    title = "MEDIUM RISK"
                else:
                    color = "#00FF88"
                    title = "LOW RISK"

                self.risk_dot.configure(text_color=color)
                self.risk_title.configure(text=title, text_color=color)
                self.risk_reason_lbl.configure(text=self.current_risk_reason)
        else:
            self.current_cmd = ""
            self.cmd_text_lbl.configure(text="(No command required)", text_color="#64748B")

    def _apply_error(self, err_msg: str) -> None:
        """Renders API error message."""
        self.cause_body.configure(text=f"Error: {err_msg}", text_color="#FF2A6D")
        self.cmd_text_lbl.configure(text="", text_color="#64748B")

    def _start_drag(self, event) -> None:
        """Records mouse offset for window dragging."""
        self._drag_x = event.x
        self._drag_y = event.y

    def _on_drag(self, event) -> None:
        """Updates window position as mouse is dragged."""
        x = self.winfo_x() + (event.x - self._drag_x)
        y = self.winfo_y() + (event.y - self._drag_y)
        self.geometry(f"+{x}+{y}")
