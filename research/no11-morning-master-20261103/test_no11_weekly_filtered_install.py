"""Offline-only installer tests, NO Excel, NO RSS, NO LIVE approval or orders."""
from __future__ import annotations
import ast
import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE=Path(__file__).resolve().parent
ENGINE=HERE.parent/'no12-prebuy-causal-runtime-20261011'
sys.path.insert(0,str(HERE))
import no11_nightly_resume as n
import no11_weekly_filtered_lineage as fix
import install_no11_weekly_filtered_lineage as installer


def rss_funding_source():
    """Reproduce the approved source from its actual historical transform."""
    path=HERE.parent/'no11-rss-funding-live-20261103/patches.py'
    spec=importlib.util.spec_from_file_location('no11_known_rss_funding_patches',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original=(ENGINE/'tools/no11_received_session_bootstrap.py').read_bytes()
    _, text, _=fix.norm(original)
    return module.change_bootstrap(text).encode('utf-8')


def fixture(root):
    store=root/'store'
    store.mkdir()
    engine=root/'engine'
    (engine/'windows').mkdir(parents=True)
    (engine/'tools').mkdir()
    (store/'oneclick').mkdir()
    source=engine/'tools/no11_received_session_bootstrap.py'
    source.write_bytes((ENGINE/'tools/no11_received_session_bootstrap.py').read_bytes())
    verifier=engine/'tools/no11_verified_weekly_shadow_scope.mjs'
    verifier.write_bytes((ENGINE/'tools/no11_verified_weekly_shadow_scope.mjs').read_bytes())
    sender=engine/'windows/Invoke-No11MsiiOrder.ps1'
    sender.write_bytes(b'ORIGINAL_FROZEN_BROKER_SENDER')
    js=engine/'tools/no11_msii_transport.mjs'
    js.write_bytes(b'ORIGINAL_NATIVE_TRANSPORT_VALIDATOR')
    ui=store/'oneclick/Start-No11OneClick.ps1'
    ui.write_bytes(b'ORIGINAL_WHITE_UI')
    settings=store/'settings.json'
    settings.write_bytes(n.encode(
        {'schemaId':'ARK_NO11_UNIFIED_LAUNCHER_SETTINGS_V1',
         'normalMaxPositions':3,'sameDayApprovalRequired':True,
         'automaticOrderAuthorization':False,'orderTransmission':False}))
    binding=store/'automatic-inputs.json'
    binding.write_bytes(n.encode(
        {'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
         'engine':str(engine),'orderTransmission':False}))
    frozen={p:p.read_bytes() for p in (verifier,sender,js,ui,settings,binding)}
    return store, source, frozen


class Installer(unittest.TestCase):
    def test_only_registered_original_native_source_is_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            store, source, frozen = fixture(Path(d))
            original=source.read_bytes()
            self.assertEqual(installer.git_blob(original),installer.KNOWN_ORIGINAL_BLOB)
            original_native=(Path(d)/'engine/tools/no11_verified_weekly_shadow_scope.mjs').read_bytes()
            self.assertEqual(installer.git_blob(original_native),installer.KNOWN_NATIVE_BLOB)
            self.assertEqual(installer.install(store), 'READY')
            self.assertFalse((store/installer.JOURNAL).exists())
            self.assertFalse((store/'unified-refresh-install.lock').exists())
            self.assertEqual(source.read_bytes(),original)
            for p,content in frozen.items():
                self.assertEqual(p.read_bytes(),content)

    def test_known_rss_funding_source_and_windows_encodings_preserve_contract(self):
        funding=rss_funding_source()
        raw_blob=hashlib.sha1(b'blob '+str(len(funding)).encode()+b'\0'+funding).hexdigest()
        self.assertEqual(raw_blob, '011171c82c960e3b2a8f520439e3e609b2578607')
        self.assertEqual(raw_blob, installer.KNOWN_RSS_FUNDING_BLOB)
        contract=next(node for node in ast.parse(funding).body
                      if isinstance(node, ast.FunctionDef) and
                      node.name=='validate_readonly_broker_config')
        for newline in (b'\n',b'\r\n'):
            for bom in (b'',b'\xef\xbb\xbf'):
                with self.subTest(newline=newline,bom=bool(bom)), tempfile.TemporaryDirectory() as d:
                    store, source, frozen=fixture(Path(d))
                    before=bom+funding.replace(b'\n',newline)
                    source.write_bytes(before)
                    self.assertEqual(installer.git_blob(before),raw_blob)
                    self.assertEqual(installer.install(store),'READY')
                    self.assertEqual(source.read_bytes(),before)
                    self.assertFalse((store/installer.JOURNAL).exists())
                    self.assertEqual(installer.install(store,apply=True,test=True),'PASS')
                    after=source.read_bytes()
                    actual_bom, text, actual_newline=fix.norm(after)
                    self.assertEqual(actual_bom,bom)
                    self.assertEqual(actual_newline.encode(),newline)
                    self.assertIn('import no11_rss_buying_power as rss_funding\n',text)
                    updated=next(node for node in ast.parse(text).body
                                 if isinstance(node, ast.FunctionDef) and
                                 node.name=='validate_readonly_broker_config')
                    self.assertEqual(ast.dump(updated),ast.dump(contract))
                    journal=n.checkpoint(store/installer.JOURNAL)
                    self.assertEqual(installer.raw(journal['before']),before)
                    self.assertEqual(installer.raw(journal['after']),after)
                    self.assertEqual(installer.install(store,apply=True,test=True),'ALREADY_APPLIED')
                    self.assertEqual(installer.install(store),'ALREADY_APPLIED')
                    self.assertEqual(source.read_bytes(),after)
                    for p,content in frozen.items():
                        self.assertEqual(p.read_bytes(),content)

    def test_rss_funding_validation_changes_are_not_new_supported_sources(self):
        with tempfile.TemporaryDirectory() as d:
            store, source, _=fixture(Path(d))
            unknown=rss_funding_source().replace(b'rss_funding.validate(obj)',b'pass')
            source.write_bytes(unknown)
            with self.assertRaisesRegex(ValueError,'UNKNOWN_INSTALLED_BOOTSTRAP'):
                installer.install(store)
            with self.assertRaisesRegex(ValueError,'UNKNOWN_INSTALLED_BOOTSTRAP'):
                installer.install(store,apply=True,test=True)
            self.assertEqual(source.read_bytes(),unknown)
            self.assertFalse((store/installer.JOURNAL).exists())

    def test_apply_is_idempotent_and_preserves_workbooks_markers_ui_and_broker(self):
        with tempfile.TemporaryDirectory() as d:
            store, source, frozen = fixture(Path(d))
            trade_marker=store/'TRADE-2026-11-11.launch.json'
            trade_marker.write_bytes(b'IMMUTABLE_ALREADY_CLAIMED')
            preopen_marker=store/'PREOPEN-2026-11-11.execution-claimed'
            preopen_marker.write_bytes(b'DO_NOT_REARM')
            original=source.read_bytes()
            self.assertEqual(installer.install(store, apply=True, test=True),'PASS')
            self.assertNotEqual(source.read_bytes(), original)
            self.assertIn(fix.MARK.encode(), source.read_bytes())
            self.assertEqual(installer.install(store, apply=True, test=True),'ALREADY_APPLIED')
            self.assertEqual(installer.install(store),'ALREADY_APPLIED')
            self.assertEqual(trade_marker.read_bytes(), b'IMMUTABLE_ALREADY_CLAIMED')
            self.assertEqual(preopen_marker.read_bytes(), b'DO_NOT_REARM')
            for p,content in frozen.items():
                self.assertEqual(p.read_bytes(),content)
            self.assertEqual(n.checkpoint(store/installer.JOURNAL)['phase'],'COMPLETE')

    def test_interrupted_replace_resumes_only_known_before_or_after(self):
        with tempfile.TemporaryDirectory() as d:
            store, source, frozen = fixture(Path(d))
            original=installer._replace_exact
            def interrupted(*args):
                original(*args)
                raise KeyboardInterrupt('AFTER_REPLACEMENT_SYNTHETIC_CRASH')
            with patch.object(installer,'_replace_exact',side_effect=interrupted):
                with self.assertRaises(KeyboardInterrupt):
                    installer.install(store,apply=True,test=True)
            self.assertEqual(n.checkpoint(store/installer.JOURNAL)['phase'],'PREPARED')
            self.assertIn(fix.MARK.encode(),source.read_bytes())
            self.assertEqual(installer.install(store,apply=True,test=True),'PASS')
            for p,content in frozen.items():
                self.assertEqual(p.read_bytes(),content)

    def test_unknown_local_bootstrap_source_blocks_audit_and_install(self):
        with tempfile.TemporaryDirectory() as d:
            store, source, _ = fixture(Path(d))
            source.write_bytes(source.read_bytes()+b'\n# UNKNOWN_LOCAL_SOURCE\n')
            with self.assertRaisesRegex(ValueError,'UNKNOWN_INSTALLED_BOOTSTRAP'):
                installer.install(store)
            with self.assertRaisesRegex(ValueError,'UNKNOWN_INSTALLED_BOOTSTRAP'):
                installer.install(store,apply=True,test=True)

    def test_native_weekly_verifier_must_not_be_changed(self):
        with tempfile.TemporaryDirectory() as d:
            store, source, _ = fixture(Path(d))
            file=Path(d)/'engine/tools/no11_verified_weekly_shadow_scope.mjs'
            file.write_bytes(file.read_bytes()+b'\n//UNKNOWN\n')
            with self.assertRaisesRegex(ValueError,'NATIVE_WEEKLY_SOURCE_CHANGED'):
                installer.install(store)

    def test_frozen_white_ui_tampering_detected_after_install(self):
        with tempfile.TemporaryDirectory() as d:
            store, source, frozen = fixture(Path(d))
            self.assertEqual(installer.install(store,apply=True,test=True),'PASS')
            ui=store/'oneclick/Start-No11OneClick.ps1'
            ui.write_bytes(b'UNRECOGNIZED_WHITE_UI')
            with self.assertRaisesRegex(ValueError,'FROZEN_FILE_CHANGED'):
                installer.install(store)

    def test_invalid_settings_cannot_initiate_patch(self):
        with tempfile.TemporaryDirectory() as d:
            store, _, _ = fixture(Path(d))
            cfg=store/'settings.json'
            obj=n.read(cfg)
            obj['automaticOrderAuthorization']=True
            cfg.write_bytes(n.encode(obj))
            with self.assertRaisesRegex(ValueError,'SETTINGS_SAFETY'):
                installer.install(store)

    def test_no_trading_or_order_writes_present_in_installer(self):
        content=(HERE/'install_no11_weekly_filtered_lineage.py').read_text()
        for token in ('RssStockOrder(', 'RssCancelOrder(', 'START TRADING',
                      'Start-No11UnifiedLauncher.ps1', 'TRADE_LAUNCHED=True',
                      'ORDER_SENT=True','.Value2=1', 'Remove-Item', 'TRADE-2026-11-11.launch.json'):
            self.assertNotIn(token,content,token)


if __name__=='__main__':
    unittest.main(verbosity=2)
