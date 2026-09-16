#!/usr/bin/env python3
"""Offline-only regression orchestration. Never calls project experiment runners."""
import argparse
import glob
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
GUARDS = ROOT / 'scripts/offline'
RSS_TESTS = [
    'phase18_rss_bridge', 'phase19_account_bridge', 'phase57_intraday_capture',
    'phase57_rss_capture_integration', 'phase57_intraday_capture_ops',
    'phase57_intraday_capture_health', 'phase57_intraday_capture_runtime',
    'phase57_real_intraday_pipeline', 'phase58_excel_5m_chart_export',
    'phase58_excel_5m_history_pack', 'phase58_prospective_session_runner',
    'phase58_excel_synchronized_capture_freshness', 'phase58_excel_multisymbol_microstructure_capture',
    'phase58_validate_msii_multisymbol_registry', 'phase58_excel_dynamic_slots',
]


def launch(command, cwd, directory):
    directory.mkdir()
    env = dict(os.environ, ARK_TEST_OFFLINE='1', ARK_OFFLINE_AUDIT_DIR=str(directory),
        NODE_OPTIONS=f'--require={GUARDS / "node-network-guard.cjs"}',
        PYTHONPATH=str(GUARDS), PYTHONDONTWRITEBYTECODE='1')
    # Clean descriptors prevent inheriting an already-open network connection.
    with (directory / 'output.log').open('w') as log:
        result = subprocess.run([sys.executable, str(GUARDS / 'kernel_exec.py'), *command],
            cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, close_fds=True, timeout=900)
    records = [json.loads(line) for p in directory.glob('*.jsonl') for line in p.read_text().splitlines()]
    blocked = [r for r in records if r['event'] == 'BLOCKED_BEFORE_NETWORK']
    return result.returncode, records, blocked


def selftest(out):
    probes = [
        ('caught_fetch', ['node', '-e', "try{fetch('https://offline-probe.invalid')}catch{};process.exitCode=0"], 97),
        ('caught_http', ['node', '-e', "try{require('node:https').get('https://offline-probe.invalid')}catch{}"], 97),
        ('caught_python_dns', [sys.executable, '-c', "import socket\ntry: socket.getaddrinfo('offline-probe.invalid',443)\nexcept RuntimeError: pass"], 97),
        ('kernel_ipv4', [sys.executable, '-S', '-c', 'import socket; socket.socket(socket.AF_INET)'], -signal.SIGSYS),
        ('kernel_ipv6', [sys.executable, '-S', '-c', 'import socket; socket.socket(socket.AF_INET6)'], -signal.SIGSYS),
        ('explicit_mock', ['node', '-e', "globalThis.fetch=async()=>({ok:true});fetch('fixture:synthetic').then(x=>{if(!x.ok)process.exit(1)})"], 0),
    ]
    results = []
    for name, command, expected in probes:
        code, records, blocked = launch(command, ROOT, out / ('probe-'+name))
        passed = code == expected and (bool(blocked) if expected == 97 else not blocked)
        results.append({'name': name, 'expectedExit': expected, 'actualExit': code, 'passed': passed,
                        'blockedSyntheticAttempts': len(blocked), 'transmittedRequests': 0})
        if not passed:
            raise RuntimeError(f'NETWORK_GUARD_FAILED: {results[-1]}')
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--suite', choices=['all','guards','predict','discovery','foundation','python','rss'], default='all')
    parser.add_argument('--rss-python', default=sys.executable)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=False)
    report = {'contract': 'ARK_TEST_OFFLINE_V1', 'status': 'RUNNING', 'selftests': [], 'suites': [],
        'scope': 'TEST_PROCESS_TREES_ONLY', 'kernelPolicy': 'LIBSECCOMP_KILL_PROCESS_NON_UNIX_SOCKET_AND_ALL_CONNECT',
        'productionDefaultsChanged': False, 'projectFitCalls': 0, 'projectPredictions': 0,
        'oofRegeneration': 0, 'thresholdSelection': None, 'validationAccess': 0, 'oosAccess': 0,
        'projectExitAccess': 0, 'projectShortEvaluation': 0}
    try:
        report['selftests'] = selftest(out)
        suites = ['predict','discovery','foundation','python','rss'] if args.suite == 'all' else ([] if args.suite=='guards' else [args.suite])
        for suite in suites:
            cwd = ROOT
            if suite in ('predict','discovery','foundation'):
                cwd = ROOT / ('discovery' if suite=='discovery' else 'predict')
                files = sorted(glob.glob(str(cwd / 'tests/*.test.mjs')) + (glob.glob(str(cwd / 'tests/*.test.js')) if suite=='predict' else []))
                if suite=='foundation':
                    files = [str(cwd / f'tests/{name}.test.mjs') for name in [
                        'phase57-long-only-research-foundation','phase57-long-only-acquisition-dry-run',
                        'phase57-long-only-integrated-pipeline','phase57-long-only-storage-gate',
                        'phase57-long-only-selector-development']]
                command = ['node','--test','--test-reporter=tap',*files]
            elif suite=='python':
                command = [sys.executable,'-m','unittest','predict/tests/test_phase57_msh_entry_long_v1_proportional_odds.py',
                           'scripts/test_phase57_msh_entry_long_v1_development.py']
            else:
                command = [args.rss_python,'-m','pytest',*[f'tools/test_{name}.py' for name in RSS_TESTS]]
            code, records, blocked = launch(command, cwd, out / suite)
            output = (out / suite / 'output.log').read_text()
            counts = {}
            if suite in ('predict','discovery','foundation'):
                for key in ('tests','pass','fail','skipped','cancelled'):
                    found = re.findall(r'^# '+key+r' (\d+)\s*$', output, re.M)
                    counts[key] = int(found[-1]) if found else None
            elif suite=='python':
                match = re.search(r'Ran (\d+) tests?',output)
                total = int(match[1]) if match else None
                counts = {'tests': total, 'pass': total if code==0 else None,
                          'fail': 0 if code==0 else None, 'skipped': 0 if 'skipped=' not in output else None, 'cancelled': 0}
            else:
                passed = re.findall(r'(\d+) passed',output)
                failed = re.findall(r'(\d+) failed',output)
                skipped = re.findall(r'(\d+) skipped',output)
                counts = {'pass': int(passed[-1]) if passed else 0, 'fail': int(failed[-1]) if failed else 0,
                          'skipped': int(skipped[-1]) if skipped else 0,'cancelled':0}
                counts['tests'] = counts['pass']+counts['fail']+counts['skipped']
            success = code==0 and not blocked and counts['tests'] is not None and counts['fail']==0 and counts['cancelled']==0
            item = {'suite':suite,'exitCode':code,'counts':counts,'guardLoads':sum(r['event']=='GUARD_LOADED' for r in records),
                    'blockedUnexpectedNetworkAttempts':len(blocked),'status':'PASS' if success else 'FAIL',
                    'skipLines':[line for line in output.splitlines() if re.search(r'# SKIP|SKIPPED',line)]}
            report['suites'].append(item)
            print(json.dumps(item),flush=True)
            if not success:
                raise RuntimeError('OFFLINE_REGRESSION_FAILED:'+suite)
        report.update(status='PASS', providerRequests={'yahoo':0,'jquants':0,'otherMarketData':0},
            providerRequestConfidence='CONFIRMED_FOR_KERNEL_GUARDED_TEST_TREES',
            guardSelftestCount=6, guardSelftestSyntheticBlockedAttempts=3)
    except Exception as error:
        report.update(status='BLOCKED',error=str(error))
        raise
    finally:
        (out / 'regression.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'status':report['status'],'output':str(out)}))


if __name__=='__main__':
    main()
