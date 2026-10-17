import pytest

from src.core.sanitize import sanitize_command, strip_control
from src.core.schema import InvalidResponse, parse_response


def test_strip_ansi_and_controls():
    assert strip_control("\x1b[31mrouge\x1b[0m") == "rouge"
    assert strip_control("a\x07b\x00c") == "abc"
    assert strip_control("\x1b]0;titre\x07texte") == "texte"
    assert strip_control("l1\r\nl2") == "l1\nl2"


def test_multiline_command_is_flagged():
    s = sanitize_command("cd /tmp\nls")
    assert s.multiline is True
    assert sanitize_command("ls -la\x1b[2J").text == "ls -la"
    assert sanitize_command("ls -la").multiline is False


def test_parse_valid_json_and_fences():
    raw = '```json\n{"command":"ls","explanation":"x","risk":"low","confidence":"high"}\n```'
    r = parse_response(raw)
    assert r.command == "ls" and r.risk == "low"


def test_parse_with_surrounding_prose():
    r = parse_response('Voici : {"command":"pwd","risk":"low"} merci')
    assert r.command == "pwd"


@pytest.mark.parametrize(
    "raw", ["pas de json", '{"risk":"extreme"}', '{"confidence": 5}', "{broken"]
)
def test_invalid_responses_raise(raw):
    with pytest.raises(InvalidResponse):
        parse_response(raw)


def test_text_fields_are_cleaned():
    r = parse_response('{"command":"ls","explanation":"\\u001b[31mHack\\u001b[0m","risk":"low"}')
    assert r.explanation == "Hack"
