from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Optional

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Button,
    Input,
    Label,
    Markdown,
    Static,
)

from src.core.assistant import ChatMessageResult, ChatSession, extract_bash_commands
from src.core.config import EzShellConfig
from src.core.context import SystemContext
from src.core.pty_shell import PTYExecutor
from src.core.safety import RiskLevel, SafetyGuard, SafetyReport


CHAT_CSS = """
Screen {
    align: center middle;
    background: #060913 85%;
}

#dialog-container {
    width: 88%;
    max-width: 108;
    height: 86%;
    max-height: 38;
    background: #0B0F19;
    border: round #00E5FF;
    border-title-color: #00E5FF;
    border-title-style: bold;
    border-title-align: left;
    border-subtitle-color: #94A3B8;
    border-subtitle-align: right;
    padding: 0 1;
}

#context-bar {
    height: 1;
    margin: 0;
    padding: 0 1;
    color: #94A3B8;
    border-bottom: solid #1E293B;
}

#chat-scroll {
    height: 1fr;
    scrollbar-color: #00E5FF #0F172A;
    scrollbar-size: 1 1;
    padding: 1 0;
}

.welcome-card {
    background: #0D1527;
    border: round #00E5FF;
    border-title-color: #00E5FF;
    border-title-style: bold;
    padding: 1;
    margin-bottom: 1;
}

.welcome-desc {
    color: #FFFFFF;
}

.welcome-examples {
    color: #FACC15;
    margin-top: 1;
}

.user-bubble {
    background: #111A2E;
    border: round #00E5FF;
    border-title-color: #00E5FF;
    border-title-style: bold;
    padding: 0 1;
    margin-bottom: 1;
}

.user-text {
    color: #FFFFFF;
    padding: 0;
}

.ai-bubble {
    background: #0C1222;
    border: round #C084FC;
    border-title-color: #C084FC;
    border-title-style: bold;
    padding: 0 1;
    margin-bottom: 1;
}

.loading-tag {
    color: #C084FC;
    text-style: bold;
    margin: 0 1;
}

.cmd-container {
    background: #020617;
    border: round #00FF88;
    border-title-color: #00FF88;
    border-title-style: bold;
    padding: 0 1;
    margin-top: 1;
}

.cmd-container-danger {
    background: #020617;
    border: round #FF2A6D;
    border-title-color: #FF2A6D;
    border-title-style: bold;
    padding: 0 1;
    margin-top: 1;
}

.cmd-code {
    color: #00FF88;
    text-style: bold;
    background: #0F172A;
    padding: 0 1;
    margin: 1 0;
}

.cmd-btn-row {
    height: auto;
    margin-top: 1;
    margin-bottom: 0;
}

.run-btn {
    background: #00FF88;
    color: #0B0F19;
    text-style: bold;
    border: round #00FF88;
    margin-right: 1;
}

.run-btn-danger {
    background: #FF2A6D;
    color: #FFFFFF;
    text-style: bold;
    border: round #FF2A6D;
    margin-right: 1;
}

.copy-btn {
    background: #1E293B;
    color: #94A3B8;
    border: round #334155;
}

.exec-result {
    background: #050D1A;
    border: round #00FF88;
    border-title-color: #00FF88;
    border-title-style: bold;
    padding: 0 1;
    margin-top: 1;
}

.exec-result-err {
    background: #14070D;
    border: round #FF2A6D;
    border-title-color: #FF2A6D;
    border-title-style: bold;
    padding: 0 1;
    margin-top: 1;
}

.exec-output {
    color: #94A3B8;
    margin-top: 0;
}

#input-bar {
    height: 3;
    margin-top: 1;
    align-vertical: middle;
}

#chat-input {
    width: 1fr;
    background: #111A2E;
    color: #FFFFFF;
    border: round #00E5FF;
}

#chat-input:focus {
    border: round #C084FC;
}

#send-btn {
    width: 12;
    background: #00E5FF;
    color: #0B0F19;
    text-style: bold;
    border: round #00E5FF;
    margin-left: 1;
}

#shortcuts-bar {
    height: 1;
    color: #94A3B8;
    padding: 0 1;
    margin-top: 1;
}

.api-key-box {
    background: #111A2E;
    border: round #FFB800;
    border-title-color: #FFB800;
    border-title-style: bold;
    padding: 1;
    margin: 1 0;
}
"""


class CommandBox(Static):
    """Interactive command snippet box with rounded corners and Run & Copy actions."""

    def __init__(self, command: str, safety_report: Optional[SafetyReport] = None, **kwargs):
        super().__init__(**kwargs)
        self.command = command
        self.safety_report = safety_report

    def compose(self) -> ComposeResult:
        is_dangerous = (
            self.safety_report is not None
            and self.safety_report.risk_level == RiskLevel.DANGEROUS
        )
        box_class = "cmd-container-danger" if is_dangerous else "cmd-container"
        box_title = (
            f" [!] DANGEROUS: {self.safety_report.reason} "
            if is_dangerous
            else " Suggested Command "
        )

        with Container(classes=box_class) as c:
            c.border_title = box_title
            yield Static(f"  {self.command}", classes="cmd-code")

            with Horizontal(classes="cmd-btn-row"):
                btn_class = "run-btn-danger" if is_dangerous else "run-btn"
                btn_label = "Confirm & Run" if is_dangerous else "Run Command"
                yield Button(btn_label, classes=f"{btn_class} cmd-action-run")
                yield Button("Copy to Input", classes="copy-btn cmd-action-copy")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        app = self.app
        if event.button.has_class("cmd-action-run"):
            if isinstance(app, EzShellChatApp):
                app.run_suggested_command(self.command)
        elif event.button.has_class("cmd-action-copy"):
            if isinstance(app, EzShellChatApp):
                app.copy_command_to_input(self.command)


class UserBubble(Static):
    """User message bubble with rounded cyan border and embedded title."""

    def __init__(self, text: str, **kwargs):
        super().__init__(**kwargs)
        self.text = text

    def compose(self) -> ComposeResult:
        with Container(classes="user-bubble") as c:
            c.border_title = " › You "
            yield Static(self.text, classes="user-text")


class AssistantBubble(Static):
    """Assistant response bubble with rounded purple border, markdown explanation and commands."""

    def __init__(self, result: ChatMessageResult, **kwargs):
        super().__init__(**kwargs)
        self.result = result

    def compose(self) -> ComposeResult:
        with Container(classes="ai-bubble") as c:
            c.border_title = " › ezShell "
            yield Markdown(self.result.content)
            for cmd, safety in zip(self.result.suggested_commands, self.result.safety_reports):
                yield CommandBox(command=cmd, safety_report=safety)


class ExecutionResultBubble(Static):
    """Displays command execution output in a rounded container."""

    def __init__(self, command: str, exit_code: int, output: str, **kwargs):
        super().__init__(**kwargs)
        self.command = command
        self.exit_code = exit_code
        self.output = output

    def compose(self) -> ComposeResult:
        is_ok = self.exit_code == 0
        box_class = "exec-result" if is_ok else "exec-result-err"
        box_title = (
            f" Output (Exit: 0): `{self.command}` "
            if is_ok
            else f" Output (Failed: {self.exit_code}): `{self.command}` "
        )
        with Container(classes=box_class) as c:
            c.border_title = box_title
            yield Static(
                self.output.strip() or "(No output)",
                classes="exec-output",
            )


class ErrorBubble(Static):
    """Displays error notice in a rounded container."""

    def __init__(self, title: str, message: str, **kwargs):
        super().__init__(**kwargs)
        self.title = title
        self.message = message

    def compose(self) -> ComposeResult:
        with Container(classes="api-key-box") as c:
            c.border_title = f" {self.title} "
            yield Static(self.message, classes="user-text")


class EzShellChatApp(App):
    """Floating modal TUI chat popup with rounded borders powered by Groq LLM and Textual."""

    CSS = CHAT_CSS
    TITLE = "ezShell Popup"

    BINDINGS = [
        Binding("escape", "quit_app", "Close", show=True),
        Binding("ctrl+c", "quit_app", "Quit", show=False),
        Binding("ctrl+l", "clear_chat", "Clear", show=True),
        Binding("ctrl+r", "run_latest_command", "Run Latest", show=True),
    ]

    def __init__(self, config: Optional[EzShellConfig] = None):
        super().__init__()
        self.config = config or EzShellConfig.load()
        self.context = SystemContext.collect()
        self.chat_session: Optional[ChatSession] = None
        self.latest_command: Optional[str] = None

        if self.config.get_effective_api_key():
            self.chat_session = ChatSession(config=self.config, context=self.context)

    def compose(self) -> ComposeResult:
        with Container(id="dialog-container") as dlg:
            # 1. Embedded rounded border title and subtitle
            dlg.border_title = f" ezShell • {self.config.model} "
            dlg.border_subtitle = " [Esc] Close "

            # 2. Context line
            cwd = self.context.current_directory
            home = str(Path.home())
            if cwd.startswith(home):
                cwd = "~" + cwd[len(home):]
            branch_info = f" • ⎇ {self.context.git_branch}" if self.context.git_branch else ""
            yield Static(
                f"cwd: {cwd}{branch_info} • shell: {self.context.shell_name}",
                id="context-bar",
            )

            # 3. Chat scrollable area
            with VerticalScroll(id="chat-scroll"):
                if not self.config.get_effective_api_key():
                    with Container(classes="api-key-box") as box:
                        box.border_title = " GROQ_API_KEY Required "
                        yield Static(
                            "ezShell requires a Groq API key to activate instant AI diagnostics & chat.\n"
                            "Get a free key at https://console.groq.com and paste it below:",
                            classes="welcome-desc",
                        )
                        with Horizontal(classes="cmd-btn-row"):
                            yield Input(
                                placeholder="gsk_...",
                                password=True,
                                id="api-key-input",
                            )
                            yield Button("Save Key", id="save-key-btn", classes="run-btn")
                else:
                    with Container(classes="welcome-card") as wc:
                        wc.border_title = " ezShell AI Terminal Assistant "
                        yield Static(
                            "Ask questions, explain code or errors, or describe any task you need executed.",
                            classes="welcome-desc",
                        )
                        yield Static(
                            "Examples:\n"
                            " › \"How do I find all processes using port 8000?\"\n"
                            " › \"Show disk usage for current folder in human-readable format\"\n"
                            " › \"Revert last commit but keep modified files\"\n"
                            " › \"Clean up unused docker containers and dangling images\"",
                            classes="welcome-examples",
                        )

            # 4. Input bar
            with Horizontal(id="input-bar"):
                yield Input(
                    placeholder="Ask ezShell anything, or describe a command to run... (Enter to send)",
                    id="chat-input",
                )
                yield Button("Send ›", id="send-btn")

            # 5. Shortcuts footer
            with Horizontal(id="shortcuts-bar"):
                yield Static(
                    " [Enter] Send   [Ctrl+R] Run Latest   [Ctrl+L] Clear Chat   [Esc] Close ",
                )

    def on_mount(self) -> None:
        """Focus input on mount."""
        inp = self.query_one("#chat-input", Input)
        inp.focus()

    def action_quit_app(self) -> None:
        """Exit the popup modal."""
        self.exit()

    def action_clear_chat(self) -> None:
        """Clears the chat screen and resets conversation history."""
        if self.chat_session:
            self.chat_session.clear()
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        scroll.remove_children()

        scroll.mount(
            Static("Conversation history reset. You can ask a new question:", classes="welcome-desc")
        )

    def action_run_latest_command(self) -> None:
        """Runs the most recent command suggested by AI."""
        if self.latest_command:
            self.run_suggested_command(self.latest_command)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle send button or save key button."""
        if event.button.id == "send-btn":
            self.submit_message()
        elif event.button.id == "save-key-btn":
            self.save_api_key()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter in input."""
        if event.input.id == "chat-input":
            self.submit_message()
        elif event.input.id == "api-key-input":
            self.save_api_key()

    def save_api_key(self) -> None:
        """Saves Groq API key entered in popup UI."""
        key_input = self.query_one("#api-key-input", Input)
        val = key_input.value.strip()
        if not val:
            return

        self.config.groq_api_key = val
        self.config.save()
        self.chat_session = ChatSession(config=self.config, context=self.context)

        # Refresh scroll area
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        scroll.remove_children()
        scroll.mount(
            Static("✔ Groq API Key Activated! AI assistant is now ready.", classes="welcome-desc")
        )
        self.query_one("#chat-input", Input).focus()

    def submit_message(self) -> None:
        """Sends user message and requests AI response."""
        inp = self.query_one("#chat-input", Input)
        user_text = inp.value.strip()
        if not user_text:
            return

        # Check special exit commands
        if user_text.lower() in ("exit", "quit", ":q"):
            self.exit()
            return

        inp.value = ""

        # Check API key
        if not self.chat_session:
            self.post_system_notice("GROQ_API_KEY is not configured. Please configure it to chat.")
            return

        scroll = self.query_one("#chat-scroll", VerticalScroll)

        # Mount user bubble
        scroll.mount(UserBubble(user_text))
        scroll.scroll_end(animate=False)

        # Mount loading tag
        loading_label = Label("› ezShell thinking...", classes="loading-tag", id="loading-tag")
        scroll.mount(loading_label)
        scroll.scroll_end(animate=False)

        # Call AI in background worker
        self._async_fetch_ai_reply(user_text, loading_label)

    @work
    async def _async_fetch_ai_reply(self, user_text: str, loading_widget: Label) -> None:
        """Worker thread to fetch LLM response without blocking the UI."""
        try:
            result = await asyncio.to_thread(self.chat_session.send_message, user_text)
            self._render_ai_reply(result, loading_widget)
        except Exception as e:
            self._render_ai_error(str(e), loading_widget)

    def _render_ai_reply(self, result: ChatMessageResult, loading_widget: Label) -> None:
        """Renders AI message inside the chat scroll container."""
        loading_widget.remove()
        scroll = self.query_one("#chat-scroll", VerticalScroll)

        if result.suggested_commands:
            self.latest_command = result.suggested_commands[-1]

        scroll.mount(AssistantBubble(result))
        scroll.scroll_end(animate=False)

    def _render_ai_error(self, error_msg: str, loading_widget: Label) -> None:
        """Renders error if Groq call failed."""
        loading_widget.remove()
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        scroll.mount(ErrorBubble("Error consulting Groq API", error_msg))
        scroll.scroll_end(animate=False)

    def run_suggested_command(self, cmd: str) -> None:
        """Executes a suggested command directly from the popup and displays the output."""
        scroll = self.query_one("#chat-scroll", VerticalScroll)

        # Execute command via PTYExecutor
        result = PTYExecutor.execute(cmd, cwd=os.getcwd(), forward_output=False)
        scroll.mount(ExecutionResultBubble(cmd, result.exit_code, result.clean_output))
        scroll.scroll_end(animate=False)

    def copy_command_to_input(self, cmd: str) -> None:
        """Pastes the command into the chat input field."""
        inp = self.query_one("#chat-input", Input)
        inp.value = cmd
        inp.focus()

    def post_system_notice(self, msg: str) -> None:
        """Posts a system notice into chat."""
        scroll = self.query_one("#chat-scroll", VerticalScroll)
        scroll.mount(Static(f"[!] {msg}", classes="user-text"))
        scroll.scroll_end(animate=False)
