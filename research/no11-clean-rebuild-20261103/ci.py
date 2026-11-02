"""GitHub-hosted offline validation, never a PC trading entry."""
from pathlib import Path
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import unittest

for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8', errors='backslashreplace')


def powershell_tests():
    output = Path(os.environ['NO11_CLEAN_PACKAGE'])
    wrapper = Path(os.environ['RUNNER_TEMP']) / 'no11-clean-diagnostic-wrapper.ps1'
    wrapper.write_text('''$ErrorActionPreference='Stop'
[Console]::OutputEncoding=[Text.UTF8Encoding]::new($false)
try {
 & $env:NO11_CLEAN_PS_TEST -EngineRoot $env:NO11_CLEAN_ENGINE -PackageRoot $env:NO11_CLEAN_PACKAGE -BaselineRoot $env:NO11_CLEAN_BASELINE
} catch {
 Write-Output ('NO11_CLEAN_TEST_ERROR='+$_.Exception.Message)
 Write-Output ('NO11_CLEAN_TEST_STACK='+$_.ScriptStackTrace)
 throw
}
''', encoding='utf-8-sig', newline='\n')
    shell = 'powershell.exe' if os.name == 'nt' else 'pwsh'
    result = subprocess.run([shell, '-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', str(wrapper)],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                            text=True, encoding='utf-8', errors='replace', timeout=120)
    (output / 'powershell-tests.log').write_text(result.stdout, encoding='utf-8', newline='\n')
    print(result.stdout)
    if result.returncode:
        raise SystemExit(result.returncode)


def build():
    root = Path.cwd()
    src, baseline = root / 'src', root / 'baseline'
    folder = src / 'research/no11-clean-rebuild-20261103'
    output = Path(os.environ['RUNNER_TEMP']) / 'Ark_No11_Clean_Rebuild_20261103'
    subprocess.run([sys.executable, '-B', str(folder / 'rebuild.py'), '--repo', str(src),
                    '--output', str(output), '--ci-stage', str(baseline)], check=True)
    # Canonical LF for ancillary release documents too, independently of host.
    for name in ('manifest.json', 'README.md', 'Stage-No11CleanRebuild.ps1'):
        path = output / name
        path.write_bytes(path.read_text(encoding='utf-8').encode('utf-8'))
    ps = Path(os.environ['RUNNER_TEMP']) / 'test-no11-clean.ps1'
    ps.write_text((folder / 'test_windows.ps1').read_text(encoding='utf-8-sig'), encoding='utf-8-sig', newline='\n')
    values = {'NO11_CLEAN_ENGINE': baseline / 'research/no12-prebuy-causal-runtime-20261011',
              'NO11_CLEAN_REPO': src, 'NO11_CLEAN_PACKAGE': output,
              'NO11_CLEAN_BASELINE': baseline, 'NO11_CLEAN_PS_TEST': ps}
    with open(os.environ['GITHUB_ENV'], 'a', encoding='utf-8') as env:
        for name, value in values.items():
            env.write(name + '=' + str(value) + '\n')
            os.environ[name] = str(value)
    powershell_tests()


def python_tests():
    engine = Path(os.environ['NO11_CLEAN_ENGINE'])
    folder = Path(os.environ['NO11_CLEAN_REPO']) / 'research/no11-clean-rebuild-20261103'
    output = Path(os.environ['NO11_CLEAN_PACKAGE'])
    sys.path.insert(0, str(engine / 'tools'))
    sys.path.insert(0, str(engine / 'tests'))
    sys.path.insert(0, str(folder))
    suites = {'new': unittest.TestLoader().discover(str(folder), pattern='test_*.py'),
              'existingFrozen': unittest.TestLoader().discover(str(engine / 'tests'),
                                      pattern='test_no11_frozen_p1_*.py')}
    results, logs = {}, ''
    for name, suite in suites.items():
        stream = io.StringIO()
        run = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
        log = stream.getvalue()
        logs += '\n=== ' + name + ' ===\n' + log
        print(log)
        results[name] = {'tests': run.testsRun, 'errors': len(run.errors),
                         'failures': len(run.failures), 'skipped': len(run.skipped),
                         'success': run.wasSuccessful()}
    (output / 'python-tests.log').write_text(logs, encoding='utf-8', newline='\n')
    (output / 'python-tests.json').write_text(json.dumps(results, indent=2), encoding='utf-8', newline='\n')
    if not all(r['success'] for r in results.values()):
        raise SystemExit(1)


def node_tests():
    engine = Path(os.environ['NO11_CLEAN_ENGINE'])
    tests = sorted(str(p) for p in (engine / 'tests').glob('*.test.mjs'))
    result = subprocess.run(['node', '--test'] + tests, cwd=engine.parents[1],
                            text=True, encoding='utf-8', stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    Path(os.environ['NO11_CLEAN_PACKAGE'], 'node-tests.log').write_text(result.stdout, encoding='utf-8', newline='\n')
    # Keep logs in the artifact; console includes failures and TAP summary only.
    lines = result.stdout.splitlines()
    for i, line in enumerate(lines):
        if line.startswith('not ok'):
            print('\n'.join(lines[max(0, i-1):i+40]))
    print('\n'.join(lines[-12:]))
    raise SystemExit(result.returncode)


def package():
    win, lin = Path('checked-windows'), Path('checked-linux')
    assert (win / 'manifest.json').read_bytes() == (lin / 'manifest.json').read_bytes()
    manifest = json.loads((win / 'manifest.json').read_text())
    for f in manifest['files']:
        a = (win / 'payload' / f['path']).read_bytes()
        b = (lin / 'payload' / f['path']).read_bytes()
        assert a == b and hashlib.sha256(a).hexdigest() == f['outputSha256']
    checks = {}
    for name, root in [('Windows', win), ('Linux', lin)]:
        report = json.loads((root / 'python-tests.json').read_text())
        assert all(v['success'] and v['errors'] == 0 and v['failures'] == 0 for v in report.values())
        data = (root / 'powershell-tests.log').read_bytes()
        text = data.decode('utf-16') if data.startswith(b'\xff\xfe') else data.decode('utf-8-sig')
        assert 'NO11_CLEAN_POWERSHELL=PASS_OFFLINE_ONLY' in text
        checks[name] = report
    shutil.copytree(win, 'release')
    shutil.copytree(lin, 'release/validation-linux',
                    ignore=shutil.ignore_patterns('payload', 'Stage-No11CleanRebuild.ps1', 'manifest.json', 'README.md'))
    report = {'status': 'PASS_OFFLINE_WINDOWS_LINUX', 'sourcePackagesUsed': False,
              'payloadFiles': len(manifest['files']), 'python': checks, 'realExcelTested': False,
              'realOrdersSent': False, 'installedOnUserPc': False, 'liveReady': False}
    Path('release/VALIDATION.json').write_text(json.dumps(report, indent=2), encoding='utf-8', newline='\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    if os.environ.get('GITHUB_ACTIONS') != 'true':
        raise SystemExit('NO11_CLEAN_CI_ONLY')
    {'build': build, 'python': python_tests, 'node': node_tests, 'package': package}[sys.argv[1]]()
