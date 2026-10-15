from src.core.safety import RiskLevel, SafetyGuard


def test_safety_safe_commands():
    safe_cmds = [
        "ls -la",
        "git status",
        "python main.py",
        "cat README.md",
        "mkdir -p src/utils",
        "pytest -v",
    ]
    for cmd in safe_cmds:
        report = SafetyGuard.inspect(cmd)
        assert report.risk_level == RiskLevel.SAFE, f"Expected SAFE for: {cmd}"
        assert not report.requires_explicit_confirmation


def test_safety_warning_commands():
    warning_cmds = [
        "curl https://example.com/install.sh | bash",
        "rm -rf ./temp_folder",
        "git reset --hard",
        "shutdown -r now",
    ]
    for cmd in warning_cmds:
        report = SafetyGuard.inspect(cmd)
        assert report.risk_level == RiskLevel.WARNING, f"Expected WARNING for: {cmd}"


def test_safety_dangerous_commands():
    dangerous_cmds = [
        "rm -rf /",
        "rm -rf /*",
        "rm -rf ~",
        "rm -rf $HOME",
        "mkfs.ext4 /dev/sda1",
        ":(){ :|:& };:",
        "dd if=/dev/zero of=/dev/sda",
        "chmod -R 777 /",
    ]
    for cmd in dangerous_cmds:
        report = SafetyGuard.inspect(cmd)
        assert report.risk_level == RiskLevel.DANGEROUS, f"Expected DANGEROUS for: {cmd}"
        assert report.requires_explicit_confirmation

