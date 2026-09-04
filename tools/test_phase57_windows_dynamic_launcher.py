from pathlib import Path


def test_dynamic_windows_launcher_avoids_start_job_filepath_argumentlist_bug():
    script = Path(__file__).with_name("phase57_msii_windows_dynamic_session.ps1").read_text(encoding="utf-8")
    assert "Start-Job -FilePath" not in script
    assert "$syncProcess=StartLoggedProcess 'powershell.exe'" in script
    assert "'durable-sync.stdout.log'" in script
    assert "'durable-sync.stderr.log'" in script
    assert "Stop-Process -Id $process.Id" in script
