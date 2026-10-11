# Private frozen native model bundle: optional one-time verified local import

The original 24 H2/H3/H5 saved model payloads were recovered from the user's provided 2026-10-05 private handoff nested zip archive, verified byte-for-byte against the public original FROZEN_NATIVE_INPUT_LINEAGE manifest. The model ZIP must remain private; GitHub only stores the pure source auditor and importer script.

Private ZIP SHA256: 990a0aaddddda36dec4c2e7d77bec291c306e57265b2d1879ac1447b1a0bdc80; package basename Ark_No11_Frozen_H2_H3_H5_Models_VERIFIED_PRIVATE.zip, 24 original JSON models plus untrusted README/pins list. The importer first verifies the exact ZIP hash, extracts only to a unique private staging directory under LOCALAPPDATA, verifies every model against pinned original manifest and its own byte SHA/size/Git blob, then moves the verified directory once. Existing installation is never overwritten; it must pass its own audit. An incomplete staged extraction is cleaned without touching a preexisting private model directory.

Optional future Windows step, after downloading the private ZIP to Downloads and updating the isolated integration worktree:
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "C:\ArkTerminal\no11-launcher\integration\no1-1-msii\windows\Install-No11PrivateNativeModels.ps1"

This is **dependency installation, not another user trading permission**. There is no need to do it to keep the existing READ ONLY UI running. The original 24 private model bytes, provenance, State9 traces, cash/account info and artifact ZIP must never be committed to the public repository. An installed 24/24 original model suite is not live native feature inference: receipt times, online feature construction, Selector/Entry/EXIT and broker execution are still absent. The only intended manual trade permission after the full implementation is Excel RSS order ON/OFF.
