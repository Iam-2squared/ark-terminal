"""Model-free recovery/relay tests: real files and SQLite, mocked PC processes.

No broker, Excel, network, private weights or actual market observations.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import no11_received_run_recovery as r
import no11_received_session_controller as c

DAY = '2026-10-26'
NOW = DAY + 'T09:32:12+09:00'


def clock(minute, second=8):
    return DAY + f'T09:{minute:02d}:{second:02d}+09:00'


class Fixture(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.daily, self.private = self.root / 'daily', self.root / 'private'
        self.daily.mkdir(); self.private.mkdir()
        self.run = self.private / ('session-' + DAY + '-' + 'a' * 32)
        self.run.mkdir()
        self.config = {'sessionDate': DAY, 'dailyRun': str(self.daily), 'privateRoot': str(self.private),
                       'runtimeRoot': str(self.root), 'productionReady': False, 'orderTransmission': False}
        self.store = r.RunRecovery(self.config)
        self.prepared = self.prepare(self.run)

    def tearDown(self):
        self.temp.cleanup()

    def prepare(self, root):
        files = {}
        for key in ('plan', 'mask', 'master', 'previous'):
            p = root / (key + '.json')
            content = {'chartPlan': {'planSha256': 'b'*64, 'selectorInputSymbols': ['7203.T']}} if key == 'plan' else {'fixture': key}
            p.write_text(json.dumps(content))
            files[key] = str(p)
        prepared = {'schemaId': 'ARK_NO11_BOOTSTRAP_PREPARED_V1', 'sessionDate': DAY,
                    'files': files, 'productionReady': False, 'orderTransmission': False}
        (root / 'prepared-inputs.json').write_text(json.dumps(prepared))
        return prepared

    def register(self):
        self.store.register(self.run, self.prepared)

    def closed_attempt(self, pid=1234, capture=True):
        attempt = self.store.begin_attempt(self.run)
        attempt.requesting(); attempt.started(pid)
        folder = self.daily / f'chart50-shadow-{DAY}-093000-{pid}'
        if capture:
            folder.mkdir()
            ready = {'schemaId': 'ARK_NO11_C50_COLLECTOR_READY_V1', 'sessionDate': DAY,
                     'processId': pid, 'captureFolder': str(folder), 'orderTransmission': False}
            attempt.ready.write_text(json.dumps(ready))
            attempt.connected(folder)
        ack = {'schemaId': 'ARK_NO11_C50_COLLECTOR_CLOSED_V1', 'sessionDate': DAY,
               'processId': pid, 'temporaryWorkbookClosed': True, 'orderTransmission': False}
        Path(str(attempt.ready) + '.closed.json').write_text(json.dumps(ack))
        process = SimpleNamespace(pid=pid, poll=lambda: 0)
        attempt.close_confirmed(process)
        return attempt, folder

    def snapshot(self, folder, minute=31, **changes):
        payload = {'schemaId': 'ARK_NO11_RSS_CHART50_1M_CAPTURE_V1', 'sessionDate': DAY,
                   'chartPlanSha256': 'b'*64, 'selectedSymbols': ['7203.T'],
                   'source': 'RssChart_1M_AND_RssMarket_CUMULATIVE_READONLY',
                   'observedEndJst': clock(minute), 'marketObservedAtJst': clock(minute),
                   'chartRows': [], 'marketObservations': [], 'shadowOnly': True,
                   'productionReady': False, 'orderTransmission': False}
        payload.update(changes)
        data = json.dumps(payload, separators=(',', ':')).encode() + b'\n'
        sha = hashlib.sha256(data).hexdigest()
        path = folder / ('snapshot-' + sha + '.json')
        path.write_bytes(data)
        return path, data


class RecoveryTests(Fixture):
    def test_registered_run_reuses_exact_prepared_inputs(self):
        self.register()
        self.assertEqual(self.store.restore(self.run), self.prepared)
        with self.assertRaisesRegex(ValueError, 'EXISTING_SESSION_REQUIRES_RESUME'):
            self.store.check_new()

    def test_legacy_ledger_without_pointer_blocks_fresh_empty_run(self):
        infer = self.run / 'inference'; infer.mkdir()
        (infer / 'portfolio-shadow.sqlite').write_bytes(b'not-opened-by-recovery')
        with self.assertRaisesRegex(ValueError, 'UNREGISTERED_EXISTING_RUN'):
            self.store.check_new()

    def test_model_and_shadow_config_must_not_change_on_resume(self):
        shadow = self.root / 'shadow.json'; shadow.write_text('{"initialCashJpy":1000000}')
        cfg = dict(self.config, shadowAccountConfig=str(shadow))
        store = r.RunRecovery(cfg); store.register(self.run, self.prepared)
        shadow.write_text('{"initialCashJpy":2000000}')
        with self.assertRaisesRegex(ValueError, 'SHADOW_CONFIG_CHANGED'):
            store.restore(self.run)
        with self.assertRaisesRegex(ValueError, 'RUN_OR_CONFIG_CHANGED'):
            r.RunRecovery(dict(cfg, runtimeRoot=str(self.private))).restore(self.run)

    def test_broker_config_bytes_pinned_to_same_run(self):
        broker = self.root / 'broker.json'
        original = b'{"transport":{"mode":"OBSERVE_ONLY"},"orderTransmission":false}\n'
        broker.write_bytes(original)
        cfg = dict(self.config, brokerExecutionConfig=str(broker))
        store = r.RunRecovery(cfg)
        store.register(self.run, self.prepared)
        self.assertEqual(store.restore(self.run), self.prepared)
        contract = r.unseal(self.run / 'run-contract.json', r.CONTRACT)
        self.assertEqual(contract['extras']['brokerExecutionConfig'], {
            'path': str(broker), 'sha256': hashlib.sha256(original).hexdigest()})
        # Even identical JSON with changed bytes is a different source receipt.
        broker.write_bytes(original + b' ')
        with self.assertRaisesRegex(ValueError, 'BROKER_CONFIG_CHANGED'):
            store.restore(self.run)

    def test_broker_config_cannot_be_added_or_replaced_for_an_existing_run(self):
        self.register()
        broker = self.root / 'broker.json'
        broker.write_text('{"orderTransmission":false}')
        with self.assertRaisesRegex(ValueError, 'RUN_OR_CONFIG_CHANGED'):
            r.RunRecovery(dict(self.config, brokerExecutionConfig=str(broker))).restore(self.run)

    def test_broker_config_missing_does_not_register_a_run(self):
        store = r.RunRecovery(dict(self.config, brokerExecutionConfig=str(self.root / 'missing.json')))
        with self.assertRaisesRegex(ValueError, 'PRIVATE_SOURCE_MISSING'):
            store.register(self.run, self.prepared)
        self.assertFalse(store.pointer.exists())
        self.assertFalse((self.run / 'run-contract.json').exists())

    def test_supplemental_workbook_identity_is_pinned_without_freezing_observed_rows(self):
        book = self.root / 'ids.xlsx'; book.write_bytes(b'synthetic-saved-observations-v1')
        cfg = dict(self.config, orderIdWorkbookPath=str(book))
        store = r.RunRecovery(cfg); store.register(self.run, self.prepared)
        contract = r.unseal(self.run / 'run-contract.json', r.CONTRACT)
        self.assertEqual(contract['workbooks']['orderIdWorkbookPath'], r.workbook_pin(book))
        book.write_bytes(b'synthetic-saved-observations-v2')
        self.assertEqual(store.restore(self.run), self.prepared)
        other = self.root / 'other.xlsx'; other.write_bytes(book.read_bytes())
        with self.assertRaisesRegex(ValueError, 'RUN_OR_CONFIG_CHANGED'):
            r.RunRecovery(dict(cfg, orderIdWorkbookPath=str(other))).restore(self.run)
        book.unlink()
        with self.assertRaisesRegex(ValueError, 'PRIVATE_SOURCE_MISSING'):
            store.restore(self.run)

    def test_prepared_file_and_pointer_tamper_rejected(self):
        self.register()
        p = Path(self.prepared['files']['master']); p.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'PREPARED_INPUT_CHANGED'):
            self.store.restore(self.run)
        body = json.loads(self.store.pointer.read_text()); body['runRoot'] = str(self.root)
        self.store.pointer.write_text(json.dumps(body))
        with self.assertRaisesRegex(ValueError, 'CONTRACT_CHANGED'):
            self.store.restore(self.run)

    def test_attempt_crash_between_request_and_pid_stays_ambiguous(self):
        self.register(); a = self.store.begin_attempt(self.run); a.requesting()
        with self.assertRaisesRegex(ValueError, 'COLLECTOR_CLEANUP_UNCONFIRMED'):
            self.store.restore(self.run)

    def test_allocated_but_never_launched_attempt_can_resume(self):
        self.register(); self.store.begin_attempt(self.run)
        self.assertEqual(self.store.restore(self.run), self.prepared)

    def test_running_collector_without_close_ack_cannot_resume(self):
        self.register(); a = self.store.begin_attempt(self.run); a.requesting(); a.started(99)
        with self.assertRaisesRegex(ValueError, 'COLLECTOR_CLEANUP_UNCONFIRMED'):
            self.store.restore(self.run)

    def test_closed_process_and_workbook_are_both_required(self):
        self.register(); a = self.store.begin_attempt(self.run); a.requesting(); a.started(99)
        ack = {'schemaId': 'ARK_NO11_C50_COLLECTOR_CLOSED_V1', 'sessionDate': DAY,
               'processId': 99, 'temporaryWorkbookClosed': True, 'orderTransmission': False}
        Path(str(a.ready)+'.closed.json').write_text(json.dumps(ack))
        with self.assertRaisesRegex(ValueError, 'COLLECTOR_STILL_RUNNING'):
            a.close_confirmed(SimpleNamespace(pid=99, poll=lambda: None))
        ack['temporaryWorkbookClosed'] = False
        Path(str(a.ready)+'.closed.json').write_text(json.dumps(ack))
        with self.assertRaisesRegex(ValueError, 'COLLECTOR_CLEANUP_UNCONFIRMED'):
            a.close_confirmed(SimpleNamespace(pid=99, poll=lambda: 0))

    def test_closed_attempt_keeps_original_source_folder_and_ack(self):
        self.register(); attempt, folder = self.closed_attempt()
        self.assertEqual(self.store.history(self.run), [folder])
        self.assertEqual(self.store.restore(self.run), self.prepared)
        p = Path(str(attempt.ready)+'.closed.json'); p.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'COLLECTOR_CLEANUP_UNCONFIRMED'):
            self.store.restore(self.run)

    def test_relay_preserves_bytes_and_timestamps_across_two_collectors(self):
        self.register(); _, first = self.closed_attempt(1234); _, second = self.closed_attempt(1235)
        p1, b1 = self.snapshot(first, 30); p2, b2 = self.snapshot(second, 32)
        view = self.run/'capture-view'; view.mkdir()
        relay = r.CaptureRelay(view, self.store.history(self.run), session=DAY,
                               plan_sha256='b'*64, selected_symbols=['7203.T'])
        result = relay.refresh(NOW)
        self.assertEqual(result['newCopies'], 2)
        self.assertEqual((view/p1.name).read_bytes(), b1)
        self.assertEqual((view/p2.name).read_bytes(), b2)
        self.assertEqual(relay.refresh(NOW)['newCopies'], 0)
        # A fresh process rechecks existing source/view bytes, not receive times.
        other = r.CaptureRelay(view, [first, second], session=DAY,
                              plan_sha256='b'*64, selected_symbols=['7203.T'])
        self.assertEqual(other.refresh(NOW)['newCopies'], 0)
        self.assertEqual(json.loads((view/p1.name).read_bytes())['observedEndJst'], clock(30))

    def test_source_removal_or_edit_is_not_hidden_by_the_relay_copy(self):
        self.register(); _, folder = self.closed_attempt()
        p, _ = self.snapshot(folder)
        view = self.run/'capture-view'; view.mkdir()
        relay = r.CaptureRelay(view, [folder], session=DAY, plan_sha256='b'*64, selected_symbols=['7203.T'])
        relay.refresh(NOW)
        original = p.read_bytes(); p.write_bytes(original + b' ')
        with self.assertRaisesRegex(ValueError, 'CAPTURE_HASH_MISMATCH'):
            relay.refresh(NOW)
        p.unlink()
        with self.assertRaisesRegex(ValueError, 'SOURCE_REMOVED'):
            relay.refresh(NOW)

    def test_changed_view_is_not_repaired_using_the_source(self):
        self.register(); _, folder = self.closed_attempt(); p, data = self.snapshot(folder)
        view = self.run/'capture-view'; view.mkdir()
        relay = r.CaptureRelay(view, [folder], session=DAY, plan_sha256='b'*64, selected_symbols=['7203.T'])
        relay.refresh(NOW); (view/p.name).write_bytes(data+b' ')
        with self.assertRaisesRegex(ValueError, 'VIEW_CHANGED'):
            relay.refresh(NOW)

    def test_partial_new_snapshot_is_not_published_and_eventually_fails(self):
        self.register(); _, folder = self.closed_attempt(); p, data = self.snapshot(folder)
        p.write_bytes(data[:12]); now_epoch = datetime.fromisoformat(NOW).timestamp(); os.utime(p, (now_epoch, now_epoch))
        view=self.run/'capture-view'; view.mkdir()
        relay = r.CaptureRelay(view, [folder], session=DAY, plan_sha256='b'*64, selected_symbols=['7203.T'])
        self.assertEqual(relay.refresh(NOW)['newCopies'], 0)
        self.assertEqual(list(view.iterdir()), [])
        with self.assertRaisesRegex(ValueError, 'CAPTURE_HASH_MISMATCH'):
            relay.refresh(clock(33))

    def test_wrong_day_plan_symbols_future_and_live_flags_rejected(self):
        for change in ({'sessionDate': '2026-10-27'}, {'chartPlanSha256': 'c'*64},
                       {'selectedSymbols': ['6501.T']}, {'observedEndJst': clock(33)},
                       {'orderTransmission': True}):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as tmp:
                folder=Path(tmp); view=folder/'view'; view.mkdir()
                self.snapshot(folder, **change)
                relay = r.CaptureRelay(view, [folder], session=DAY, plan_sha256='b'*64, selected_symbols=['7203.T'])
                with self.assertRaisesRegex(ValueError, 'CAPTURE_SCOPE_OR_CLOCK_INVALID'):
                    relay.refresh(NOW)

    def test_original_data_is_not_modified_when_relaying(self):
        self.register(); _, folder = self.closed_attempt(); p, data = self.snapshot(folder)
        before=p.stat().st_mtime_ns
        view=self.run/'capture-view'; view.mkdir()
        r.CaptureRelay(view, [folder], session=DAY, plan_sha256='b'*64,
                       selected_symbols=['7203.T']).refresh(NOW)
        self.assertEqual(p.read_bytes(),data); self.assertEqual(p.stat().st_mtime_ns,before)

    def test_new_symlink_paths_and_other_repo_directory_rejected(self):
        if not hasattr(os, 'symlink'): self.skipTest('symlinks unavailable')
        link=self.root/'linked'
        try: link.symlink_to(self.daily, target_is_directory=True)
        except OSError: self.skipTest('symlink privilege unavailable')
        with self.assertRaisesRegex(ValueError, 'UNSAFE_PRIVATE_PATH'):
            r.private(link,directory=True)


class ControllerTests(Fixture):
    def fake_bootstrap(self):
        owner=self
        calls=[]
        processes=[]
        class Process:
            def __init__(self,pid,ready,folder):
                self.pid,self.ready,self.folder,self.code=pid,ready,folder,None
            def poll(self):return self.code
            def wait(self,timeout):
                self.code=0
                ack={'schemaId':'ARK_NO11_C50_COLLECTOR_CLOSED_V1','sessionDate':DAY,
                     'processId':self.pid,'temporaryWorkbookClosed':True,'orderTransmission':False}
                Path(str(self.ready)+'.closed.json').write_text(json.dumps(ack));return 0
        @contextmanager
        def lock(root):yield
        def prepare(config,run):calls.append('prepare');return owner.prepare(run)
        def args(config,prepared,infer,capture=None):
            out=['--private-root',str(infer)]
            if capture is not None:out+=['--capture-folder',str(capture)]
            return out
        def consume(argv,**kwargs):
            if '--preflight-only' in argv:calls.append('preflight');return
            calls.append('consume');kwargs['should_stop']()
            infer=Path(argv[argv.index('--private-root')+1]); db=sqlite3.connect(infer/'portfolio-shadow.sqlite')
            db.execute('CREATE TABLE IF NOT EXISTS test_partial(position_qty INT, reserved INT, sell_halt INT)')
            if not db.execute('SELECT * FROM test_partial').fetchone():
                db.execute('INSERT INTO test_partial VALUES (100,10125,1)')
            db.commit();db.close()
        def command(config,prepared,ready,stop):return [str(ready),str(stop)]
        def spawn(argv,**kwargs):
            self.assertNotIn('shell',kwargs)
            ready=Path(argv[0]);pid=1200+len(processes)
            folder=owner.daily/f'chart50-shadow-{DAY}-093000-{pid}';folder.mkdir()
            owner.snapshot(folder,30+len(processes))
            ready.write_text(json.dumps({'schemaId':'ARK_NO11_C50_COLLECTOR_READY_V1','sessionDate':DAY,
                'processId':pid,'captureFolder':str(folder),'orderTransmission':False}))
            p=Process(pid,ready,folder);processes.append(p);return p
        def ready_capture(ready,process,config,prepared):return process.folder
        def shutdown(process,ready,stop,marker):
            stop.write_text('STOP');process.wait(90)
        b=SimpleNamespace(ROOT=r.ROOT,os=SimpleNamespace(name='nt'),stamp=lambda:NOW,
             need=r.need,prepare=prepare,service_args=args,collector_command=command,
             ready_capture=ready_capture,shutdown_collector=shutdown,
             service=SimpleNamespace(main=consume,exclusive_service=lock))
        return b,spawn,calls,processes

    def test_same_root_resume_preserves_partial_state_and_buy_halt(self):
        b,spawn,calls,processes=self.fake_bootstrap()
        run=c.execute(self.config,b,popen=spawn,sleep=lambda _:None)
        self.assertEqual(calls,['prepare','preflight','consume'])
        path=run/'inference/portfolio-shadow.sqlite'
        before=path.read_bytes()
        self.assertEqual(len(list((run/'capture-view').glob('snapshot-*'))),1)
        resumed=c.execute(self.config,b,resume_run=run,popen=spawn,sleep=lambda _:None)
        self.assertEqual(resumed,run)
        self.assertEqual(calls.count('prepare'),1)
        db=sqlite3.connect(path);self.assertEqual(db.execute('SELECT * FROM test_partial').fetchall(),[(100,10125,1)]);db.close()
        self.assertEqual(path.read_bytes(),before)
        self.assertEqual(len(list((run/'capture-view').glob('snapshot-*'))),2)
        self.assertEqual(len(r.RunRecovery(self.config).history(run)),2)

    def test_second_fresh_launch_blocked_before_prepare_or_spawn(self):
        b,spawn,calls,processes=self.fake_bootstrap()
        c.execute(self.config,b,popen=spawn,sleep=lambda _:None)
        with self.assertRaisesRegex(ValueError,'EXISTING_SESSION_REQUIRES_RESUME'):
            c.execute(self.config,b,popen=spawn,sleep=lambda _:None)
        self.assertEqual(len(processes),1);self.assertEqual(calls.count('prepare'),1)

    def test_failure_of_original_asset_preflight_never_starts_collector(self):
        b,spawn,calls,processes=self.fake_bootstrap()
        b.service.main=mock.Mock(side_effect=ValueError('MODEL_MISSING'))
        with self.assertRaisesRegex(ValueError,'MODEL_MISSING'):
            c.execute(self.config,b,popen=spawn,sleep=lambda _:None)
        self.assertEqual(processes,[]);self.assertFalse(self.store.pointer.exists())

    def test_existing_cleanup_latch_is_not_cleared(self):
        marker=self.private/'bootstrap-recovery-required.json';marker.write_text('{}')
        b,spawn,calls,processes=self.fake_bootstrap()
        with self.assertRaisesRegex(ValueError,'PREVIOUS_CLEANUP_REQUIRES_REVIEW'):
            c.execute(self.config,b,popen=spawn,sleep=lambda _:None)
        self.assertEqual(marker.read_text(),'{}');self.assertEqual(calls,[])

    def test_preflight_only_cannot_claim_or_launch_a_session(self):
        b,spawn,calls,processes=self.fake_bootstrap()
        c.execute(self.config,b,preflight_only=True,popen=spawn,sleep=lambda _:None)
        self.assertEqual(calls,['prepare','preflight']);self.assertEqual(processes,[])
        self.assertFalse(self.store.pointer.exists())

    def test_consumer_exception_closes_only_owned_collector_and_retains_contract(self):
        b,spawn,calls,processes=self.fake_bootstrap()
        original=b.service.main
        def fail(argv,**kwargs):
            if '--preflight-only' in argv:return original(argv,**kwargs)
            raise ValueError('TEST_CONSUMER_FAILURE')
        b.service.main=fail
        with self.assertRaisesRegex(ValueError,'TEST_CONSUMER_FAILURE'):
            c.execute(self.config,b,popen=spawn,sleep=lambda _:None)
        self.assertEqual(processes[0].poll(),0)
        pointer=r.unseal(self.store.pointer,r.POINTER)
        self.assertEqual(len(self.store.history(pointer['runRoot'])),1)
        self.assertTrue((Path(pointer['runRoot'])/'controller-failure.json').is_file())


if __name__ == '__main__':unittest.main()
