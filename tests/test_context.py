from src.core.context import CommandHistoryEntry, SystemContext


def test_system_context_collect():
    context = SystemContext.collect()
    assert context.os_name
    assert context.current_directory
    assert context.current_user
    assert context.architecture


def test_system_context_to_prompt():
    entry = CommandHistoryEntry(command="git status", exit_code=0, timestamp=123.4)
    context = SystemContext(
        os_name="Fedora Linux",
        os_version="40",
        architecture="x86_64",
        current_user="testuser",
        current_directory="/home/testuser/project",
        shell_name="bash",
        git_branch="main",
        git_is_dirty=False,
        recent_history=[entry],
    )
    prompt_str = context.to_prompt_context()
    assert "Fedora Linux" in prompt_str
    assert "main (clean)" in prompt_str
    assert "`git status` (exit: 0)" in prompt_str

