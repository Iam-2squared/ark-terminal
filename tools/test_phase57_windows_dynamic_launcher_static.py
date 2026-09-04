from pathlib import Path


def test_start_logged_process_does_not_use_powershell_automatic_args_name():
    script = Path(__file__).with_name("phase57_msii_windows_dynamic_session.ps1").read_text(encoding="utf-8")
    assert "function StartLoggedProcess([string]$FilePath,[string[]]$ProcessArgs" in script
    assert "[string[]]$Args" not in script
    assert "$ProcessArgs.Count" in script
    assert "$ProcessArgs | ForEach-Object" in script
