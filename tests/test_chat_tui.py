import asyncio
from unittest.mock import MagicMock
import pytest
from textual import events

from src.core.assistant import ChatMessageResult
from src.core.config import EzShellConfig
from src.core.safety import RiskLevel, SafetyReport
from src.ui.chat_tui import DraggableDialog, EzShellChatApp


@pytest.mark.anyio
async def test_chat_tui_lifecycle():
    config = EzShellConfig(groq_api_key="gsk_mock")
    app = EzShellChatApp(config=config)
    async with app.run_test() as pilot:
        assert pilot.app.is_running
        inp = pilot.app.query_one("#chat-input")
        assert inp is not None
        await pilot.press("escape")


@pytest.mark.anyio
async def test_chat_tui_send_and_run_command():
    config = EzShellConfig(groq_api_key="gsk_mock")
    app = EzShellChatApp(config=config)

    cmd_sample = "echo ezShell rocks"
    mock_session = MagicMock()
    mock_session.send_message.return_value = ChatMessageResult(
        content="You can test with:\n```bash\n" + cmd_sample + "\n```",
        suggested_commands=[cmd_sample],
        safety_reports=[
            SafetyReport(
                risk_level=RiskLevel.SAFE,
                command=cmd_sample,
                reason="",
            )
        ],
    )
    app.chat_session = mock_session

    async with app.run_test() as pilot:
        inp = pilot.app.query_one("#chat-input")
        inp.value = "How do I test this?"
        await pilot.press("enter")
        await pilot.pause()

        assert pilot.app.latest_command == cmd_sample
        pilot.app.run_suggested_command(pilot.app.latest_command)
        await pilot.pause()

        await pilot.press("escape")


@pytest.mark.anyio
async def test_chat_tui_draggable_and_movable():
    config = EzShellConfig(groq_api_key="gsk_mock")
    app = EzShellChatApp(config=config)

    async with app.run_test() as pilot:
        dlg = pilot.app.query_one(DraggableDialog)
        assert dlg._offset_x == 0
        assert dlg._offset_y == 0

        # 1. Test keyboard nudging
        await pilot.press("alt+right")
        assert dlg._offset_x == 3
        await pilot.press("alt+down")
        assert dlg._offset_y == 2

        # Reset position
        await pilot.press("alt+home")
        assert dlg._offset_x == 0
        assert dlg._offset_y == 0

        # 2. Test mouse drag simulation
        dlg.on_mouse_down(
            events.MouseDown(
                dlg,
                x=10,
                y=1,
                delta_x=0,
                delta_y=0,
                button=1,
                shift=False,
                meta=False,
                ctrl=False,
                screen_x=10,
                screen_y=1,
            )
        )
        assert dlg._dragging is True
        dlg.on_mouse_move(
            events.MouseMove(
                dlg,
                x=25,
                y=6,
                delta_x=15,
                delta_y=5,
                button=1,
                shift=False,
                meta=False,
                ctrl=False,
                screen_x=25,
                screen_y=6,
            )
        )
        dlg.on_mouse_up(
            events.MouseUp(
                dlg,
                x=25,
                y=6,
                delta_x=0,
                delta_y=0,
                button=1,
                shift=False,
                meta=False,
                ctrl=False,
                screen_x=25,
                screen_y=6,
            )
        )
        assert dlg._dragging is False
        assert dlg._offset_x == 15
        assert dlg._offset_y == 5

        await pilot.press("escape")
