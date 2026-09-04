from __future__ import annotations

from pathlib import Path


SCRIPT = Path(__file__).with_name("phase57_msii_windows_dynamic_session.ps1").read_text(encoding="utf-8")


def test_windows_durable_sync_preserves_git_blob_bytes():
    assert "StandardOutput.BaseStream.CopyTo($stream)" in SCRIPT
    assert "Get-GitBlobId" in SCRIPT
    assert "Get-FileGitBlobId" in SCRIPT
    assert "byte-exact durable sync mismatch" in SCRIPT
    assert "$payload=git show" not in SCRIPT
    assert "WriteAllText($temp,($payload" not in SCRIPT


def test_windows_durable_sync_repairs_existing_mojibake_copy():
    assert "$localBlob=Get-FileGitBlobId $destination" in SCRIPT
    assert "if($localBlob -and $localBlob -eq $remoteBlob){ continue }" in SCRIPT
    assert "$verb=if($localBlob){'REPAIRED'}else{'SYNCED'}" in SCRIPT


def test_windows_durable_sync_validates_utf8_json_before_publish():
    assert "Assert-JsonUtf8 $temp" in SCRIPT
    assert "JSON.parse(require('fs').readFileSync(process.argv[1],'utf8'))" in SCRIPT
    assert "Move-Item -LiteralPath $temp -Destination $destination -Force" in SCRIPT
