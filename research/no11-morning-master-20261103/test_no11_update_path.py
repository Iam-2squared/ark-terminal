"""Native weekend OneClick and maximum RSS capacity, all without Excel."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import importlib.util
import json
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
ENGINE = HERE.parent / 'no12-prebuy-causal-runtime-20261011' / 'windows'
sys.path.insert(0,str(HERE))
import nightly_workbook_compat as compat
import no11_update_path as patch
import no11_nightly_resume as n

class NativeUpdateTests(unittest.TestCase):
    def originals(self):
        sources={}
        for kind, relative in patch.FILES.items():
            if relative.startswith('engine/'):
                source = ENGINE / Path(relative).name
            else:
                source = HERE / 'oneclick_status.py'
            sources[kind]=source.read_bytes()
        native = compat.transform_launcher(sources['native'])
        native = native.replace(
            b"$weekly=Join-Path $PSScriptRoot 'Prepare-No11WeeklyAfterCloseReadOnly.ps1'",
            b"$weekly=Join-Path $PSScriptRoot 'Run-No11NightlyCycle.ps1'")
        sources['native']=native
        for k in ('daily','pool','minutes'):
            rel='windows/' + Path(patch.FILES[k]).name
            sources[k]=compat.transform_collector(rel,sources[k])
        sources['weekly']=compat.transform_first_week_carry(sources['weekly'])
        return sources

    def test_every_real_collector_accepts_max47(self):
        for kind, raw in self.originals().items():
            with self.subTest(kind=kind):
                updated=patch.transform(kind,raw)
                self.assertNotEqual(raw,updated)
                self.assertEqual(updated,patch.transform(kind,updated))
                self.assertEqual(updated.startswith(b'\xef\xbb\xbf'),raw.startswith(b'\xef\xbb\xbf'))
                after=updated.decode('utf-8-sig')
                if kind in ('daily','minutes'):
                    self.assertEqual(after.count('$physical=[Math]::Min($BatchSize,50-$existing-3)'),1)
                    self.assertNotIn('+$BatchSize -gt 50',after)
                    self.assertIn('RESERVED=3',after)
                if kind == 'weekly':
                    self.assertIn('$FullBatchSize=47',after)
                    self.assertIn('$RefreshBatchSize=47',after)
                    self.assertIn('$MinuteBatchSize=47',after)
                if kind == 'next':
                    self.assertIn('$DailyBatchSize=47',after)
                    self.assertIn('$MinuteBatchSize=47',after)
                if kind in ('previous','pool','minutes','daily'):
                    self.assertIn('$BatchSize=47',after)
                if kind in ('native','daily','minutes','pool'):
                    self.assertIn('ARK_NO11_AFTERCLOSE_CONFIGURED_THIRD_BOOK_V1',after)

    def test_friday_and_every_weekday_use_updated_native_pipeline(self):
        s=self.originals()
        weekly=patch.transform('weekly',s['weekly']).decode('utf-8-sig')
        next_stage=patch.transform('next',s['next']).decode('utf-8-sig')
        previous=patch.transform('previous',s['previous']).decode('utf-8-sig')
        self.assertIn("'-DailyBatchSize',[string]$FullBatchSize",weekly)
        self.assertIn("'-BatchSize',[string]$RefreshBatchSize",weekly)
        self.assertIn("'-MinuteBatchSize',[string]$MinuteBatchSize",weekly)
        self.assertIn('$dailyScript',next_stage)
        self.assertIn('Run-No11RssDailyTrendCensusReadOnly.ps1',next_stage)
        self.assertIn('Capture-No11RssTrainingBatchReadOnly.ps1',previous)
        self.assertEqual(next_stage.count('$DailyBatchSize=47'),1)

    def test_weekend_status_allows_data_only_and_never_trade(self):
        text=patch.transform('status',self.originals()['status']).decode()
        import types
        status=types.ModuleType('isolated_status')
        exec(compile(text,'isolated-status','exec'),status.__dict__)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            tool=root/'daily_cycle.py'
            tool.write_text('')  # local test presence only
            daily=root/'daily'
            daily.mkdir()
            cfg=root/'settings.json'
            binding=root/'binding.json'
            cfg.write_text(json.dumps({'normalMaxPositions':3,
                'sameDayApprovalRequired':True,'automaticOrderAuthorization':False,
                'orderTransmission':False}))
            binding.write_text(json.dumps({'schemaId':'ARK_NO11_AUTOMATIC_LAUNCHER_BINDING_V1',
                'orderTransmission':False,'dailyCycleTool':str(tool),'dailyCycleRoot':str(daily)}))
            sunday=datetime(2026,11,8,19,0,tzinfo=timezone(timedelta(hours=9)))
            result=status.inspect(cfg,binding,at=sunday)
            self.assertEqual(result['mode'],'WEEKEND_FRIDAY_DATA')
            self.assertTrue(result['canRunNightly'])
            self.assertFalse(result['canRequestTrade'])
            self.assertFalse(result['brokerOrderTransmission'])
            tool.unlink()
            self.assertFalse(status.inspect(cfg,binding,at=sunday)['canRunNightly'])

    def test_native_reentry_preserves_trade_once_and_weekly_marker(self):
        txt=patch.transform('native',self.originals()['native']).decode('utf-8-sig')
        self.assertIn("Need ($kind -ceq 'WEEKLY') ($kind+'_ALREADY_STARTED_NO_DUPLICATE')",txt)
        self.assertIn("prior.sourceSha256 -ceq $sourceDigest",txt)
        self.assertIn('WEEKLY_PREVIOUS_WORKER_STILL_RUNNING',txt)
        self.assertIn('ORIGINAL_MARKER_PRESERVED=True',txt)
        self.assertIn("if(-not $existingWeekly){",txt)
        self.assertEqual(txt.count("[IO.FileMode]::CreateNew"),2 if '[IO.FileMode]::CreateNew' in txt else 0)
        self.assertIn('NO11_UNIFIED_TRADEX=FROZEN_MAX3_ENGINE_REQUESTED',txt)

    def test_unknown_source_anchor_never_silent(self):
        full=self.originals()['weekly']
        changed=full.replace(b'$FullBatchSize=10',b'$FullBatchSize=11')
        with self.assertRaisesRegex(ValueError,'SOURCE_ANCHOR_CHANGED'):
            patch.transform('weekly',changed)

    def test_line_endings_and_backup_original_pinned_d100_preserved(self):
        raw=self.originals()['daily'].replace(b'\r\n',b'\n')
        raw=b'\xef\xbb\xbf'+raw.replace(b'\n',b'\r\n')
        out=patch.transform('daily',raw)
        self.assertTrue(out.startswith(b'\xef\xbb\xbf'))
        self.assertNotIn(b'\n',out.replace(b'\r\n',b''))
        self.assertEqual(raw,raw)  # originals are inputs, never overwritten

if __name__=='__main__':
    unittest.main(verbosity=2)
