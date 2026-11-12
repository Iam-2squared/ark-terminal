"""Read-only verification of the complete Display V2 -> Overlay source chain.

Keep both original journals unchanged. A valid overlay is not an unknown local
edit. Conversely ALREADY_APPLIED is never returned with absent/modified Python
presentation or contract sidecars. No installation, authorization, or Excel I/O.
"""
from __future__ import annotations

import base64
from pathlib import Path

import no11_nightly_resume as n
import no11_oneclick_display_transform as migration


def need(ok, code):
    if not ok:
        raise ValueError('NO11_DISPLAY_CHAIN_' + code)


def validate_v2_dependencies(store):
    # Import lazily: the older installer delegates to this module, but only
    # after its function definitions exist. Do not recurse into its verify().
    import install_no11_oneclick_display_v2 as original
    store = n.safe(store, True)
    home, launcher, legacy, engine, external = original.context(store)
    journal = n.safe(store / original.JOURNAL)
    record = n.checkpoint(journal)
    need(record.get('kind') == original.KIND and record.get('phase') == 'COMPLETE'
         and record.get('home') == str(home) and record.get('launcher') == str(launcher),
         'BASE_RECEIPT_INVALID')
    before = base64.b64decode(record['before'], validate=True)
    after = base64.b64decode(record['after'], validate=True)
    need(migration.transform(before) == after and migration.transform(after) == after,
         'BASE_DERIVATION_CHANGED')
    expected = original.payload(legacy)
    sidecars = record.get('sidecars')
    need(type(sidecars) is dict and set(sidecars) == set(expected), 'SIDECAR_SET')
    for name, data in expected.items():
        need(base64.b64decode(sidecars[name], validate=True) == data, 'SIDECAR_RECEIPT_CHANGED')
        path = n.safe(home / name)
        need(path.read_bytes() == data, 'SIDECAR_BYTES_CHANGED')
    return launcher, before, after, expected, record, journal


def verify_complete_chain(store, supplied_record=None):
    import install_no11_oneclick_display_overlay_compat as overlay
    launcher, before, after, extras, record, base_path = validate_v2_dependencies(store)
    if supplied_record is not None:
        need(supplied_record == record, 'BASE_RECORD_ARGUMENT_CHANGED')
    overlay_path = Path(store) / overlay.JOURNAL
    current = launcher.read_bytes()
    if not overlay_path.exists():
        need(current == after, 'LAUNCHER_CHANGED')
        return launcher, before, after, extras
    receipt = n.checkpoint(n.safe(overlay_path))
    derived = overlay.change(after)
    legacy = n.safe(launcher.parent / 'oneclick_status.py')
    need(receipt.get('kind') == overlay.KIND and receipt.get('phase') == 'COMPLETE'
         and receipt.get('tradeStarted') is False
         and receipt.get('launcher') == str(launcher)
         and receipt.get('home') == str(launcher.parent), 'OVERLAY_NOT_COMPLETE')
    checks = {
        'originalDisplayJournalSha256': n.digest(base_path.read_bytes()),
        'originalNativeStatusSha256': n.digest(legacy.read_bytes()),
        'originalLauncherSha256': n.digest(after),
        'updatedLauncherSha256': n.digest(derived),
    }
    for key, expected in checks.items():
        need(receipt.get(key) == expected, 'OVERLAY_IDENTITY_CHANGED')
    need(base64.b64decode(receipt['before'], validate=True) == after
         and base64.b64decode(receipt['after'], validate=True) == derived
         and current == derived, 'OVERLAY_DERIVATION_CHANGED')
    # Completed chain accepts unrelated legitimate daily updates. Dependency
    # sidecars, native status and every journal/launcher byte remain pinned.
    return launcher, before, derived, extras
