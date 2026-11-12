"""Read-only verification of the complete Display V2 -> Overlay source chain.

Keep both original journals unchanged. A valid overlay is not an unknown local
edit. ALREADY_APPLIED requires the installed presentation and contract bytes.
No installation, authorization, or Excel I/O.
"""
from __future__ import annotations

import base64
from pathlib import Path

import no11_nightly_resume as n
import no11_oneclick_display_transform as migration

# Exact publicly released presentation payload from a9e0d8ad / 75f2c432.
# Do not infer authorization from a user's reported hash or an untrusted journal.
HISTORICAL_DISPLAY = '47e9161e40eaa81294eaa7faa437eeb6a26753ef3c703cebaa3bd0035694dd55'


def need(ok, code):
    if not ok:
        raise ValueError('NO11_DISPLAY_CHAIN_' + code)


def validate_v2_dependencies(store):
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
    sidecars = record.get('sidecars')
    need(type(sidecars) is dict and set(sidecars) == {original.DISPLAY, original.CONTRACT}, 'SIDECAR_SET')
    extras = {name: base64.b64decode(value, validate=True) for name, value in sidecars.items()}
    display_sha = n.digest(extras[original.DISPLAY])
    current_sha = n.digest(original.payload(legacy)[original.DISPLAY])
    need(display_sha in {HISTORICAL_DISPLAY, current_sha}, 'UNKNOWN_DISPLAY_RELEASE')
    contract = {'schemaId': 'ARK_NO11_ONECLICK_DISPLAY_INSTALL_V2',
                'displaySha256': display_sha, 'legacyStatusSha256': n.digest(legacy.read_bytes()),
                'orderTransmission': False, 'authorizationSourceChanged': False}
    need(extras[original.CONTRACT] == n.encode(contract), 'CONTRACT_BINDING_CHANGED')
    for name, data in extras.items():
        need(n.safe(home / name).read_bytes() == data, 'SIDECAR_BYTES_CHANGED')
    return launcher, before, after, extras, record, journal


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
    # Completed chains allow legitimate unrelated daily updates, but never
    # changed/missing presentation, native status, contract or launcher bytes.
    return launcher, before, derived, extras
