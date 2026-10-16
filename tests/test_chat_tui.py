import asyncio
from unittest.mock import MagicMock
import pytest

from src.core.assistant import ChatMessageResult
from src.core.config import EzShellConfig
from src.core.safety import RiskLevel, SafetyReport
from src.ui.chat_tui import EzShellChatApp


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

