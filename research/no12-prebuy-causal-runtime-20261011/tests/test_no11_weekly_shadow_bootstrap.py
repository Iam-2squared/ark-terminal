"""No11 existing received-data bootstrap accepts only verified weekly-source trio.
Synthetic private paths. Does not need real models, Excel, account or orders.
"""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import no11_received_session_bootstrap as bootstrap

class WeeklyScopeBootstrapTests(TestCase):
    def setUp(self):
        self.temp=TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.daily=self.root/'weekly-refresh'
        self.weekly=self.root/'verified-weekly'
        for p in (self.daily,self.weekly,self.root/'runtime',self.root/'private'):p.mkdir()
        self.plan=self.daily/'no11-chart50-private-test.json'
        self.mask=self.daily/'no11-observed-pass-watch-test.json'
        self.master=self.root/'master.json'
        self.previous=self.root/'previous.json'
        for p in (self.plan,self.mask,self.master,self.previous):p.write_text('{}',encoding='utf-8')
        self.config={
            'schemaId':bootstrap.CONFIG,
            'sessionDate':'2026-10-28',
            'dailyRun':str(self.daily),'datedMaster':str(self.master),
            'runtimeRoot':str(self.root/'runtime'),'privateRoot':str(self.root/'private'),
            'previousContext':str(self.previous),
            'precomputedChartReceipt':str(self.plan),
            'precomputedG1Mask':str(self.mask),
            'weeklySourceRun':str(self.weekly),
            'productionReady':False,'orderTransmission':False
        }

    def test_trio_is_recognized_only_as_readonly_inputs(self):
        cfg=bootstrap.validate_config(self.config)
        self.assertEqual(cfg['weeklySourceRun'],str(self.weekly))
        self.assertEqual(cfg['precomputedG1Mask'],str(self.mask))
        self.assertFalse(cfg['orderTransmission'])

    def test_partial_trio_and_extra_pins_rejected(self):
        for field in ('precomputedChartReceipt','precomputedG1Mask','weeklySourceRun'):
            bad=dict(self.config);del bad[field]
            with self.assertRaisesRegex(ValueError,'WEEKLY_SCOPE_ALL_THREE_REQUIRED'):
                bootstrap.validate_config(bad)
        bad=dict(self.config,pinsFile=str(self.mask))
        with self.assertRaisesRegex(ValueError,'WEEKLY_SCOPE_ALREADY_PINNED'):
            bootstrap.validate_config(bad)

    def test_foreign_chart_or_mask_receipt_rejected_before_node(self):
        outside=self.root/'outsider.json'
        outside.write_text('{}',encoding='utf-8')
        for field in ('precomputedChartReceipt','precomputedG1Mask'):
            bad=dict(self.config);bad[field]=str(outside)
            with self.assertRaisesRegex(ValueError,'WEEKLY_SCOPE_RECEIPTS_AND_DAILY_RUN'):
                bootstrap.validate_config(bad)
        bad=dict(self.config,weeklySourceRun=str(self.daily))
        with self.assertRaisesRegex(ValueError,'WEEKLY_SCOPE_RECEIPTS_AND_DAILY_RUN'):
            bootstrap.validate_config(bad)

    def test_actual_validator_must_return_exact_success_and_only_returns_pinned_files(self):
        cfg=bootstrap.validate_config(self.config)
        with mock.patch.object(bootstrap,'command_output',return_value=
                'NO11_WEEKLY_SHADOW_SCOPE=PASS_OBSERVED_NOT_EXTERNALLY_REVIEWED\n') as call:
            self.assertEqual(bootstrap.export_scope(cfg),(self.plan,self.mask))
            argv=call.call_args.args[0]
            self.assertIn('no11_verified_weekly_shadow_scope.mjs',argv[1])
            self.assertIn('--weekly-source-run',argv)
            self.assertIn('--session',argv)
            self.assertIn('2026-10-28',argv)
        with mock.patch.object(bootstrap,'command_output',return_value=
                'NO11_WEEKLY_SHADOW_SCOPE=BLOCKED'):
            with self.assertRaisesRegex(ValueError,'WEEKLY_SCOPE_G1_CHART_NOT_VERIFIED'):
                bootstrap.export_scope(cfg)

    def test_legacy_unmodified_bootstrap_does_not_promote_to_weekly_scope(self):
        old={k:v for k,v in self.config.items() if k not in
             ('precomputedChartReceipt','precomputedG1Mask','weeklySourceRun')}
        cfg=bootstrap.validate_config(old)
        self.assertNotIn('precomputedChartReceipt',cfg)
