"""Build a fresh repair from Git objects, never from previous patch archives.

The only writable source tree is an explicit CI checkout under --ci-stage.
Ordinary invocation creates a new output directory and package, not a live install.
"""
from __future__ import annotations
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import zipfile

BASE = '24b906e19a2623e45701311ca3fbb20dafe11c80'
ENGINE = 'research/no12-prebuy-causal-runtime-20261011'
HERE = Path(__file__).resolve().parent
TARGETS = (
    'tools/no11_broker_execution_service.py',
    'tools/no11_prepare_received_inputs.py',
    'tools/no11_input_prerequisites.py',
    'windows/Read-No11BrokerSnapshot.ps1',
    'windows/Invoke-No11MsiiOrder.ps1',
    'windows/Capture-No11SessionReferenceReadOnly.ps1',
    'windows/Observe-No11AccountReadOnly.ps1',
)
ADDITIONS = {
    'runtime_guards.py': 'tools/no11_clean_runtime_guards.py',
    'weekly.py': 'tools/no11_clean_weekly.py',
    'compatibility.ps1': 'windows/No11CleanCompatibility.ps1',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def normalized(data):
    return data.decode('utf-8').replace('\r\n', '\n').encode('utf-8')


def blob(data):
    data = normalized(data)
    return hashlib.sha1(b'blob ' + str(len(data)).encode('ascii') + b'\0' + data).hexdigest()


def git(root, *args):
    return subprocess.run(['git', '-C', str(root), *args], check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout


def replace(text, old, new, count=1):
    if text.count(old) != count:
        raise ValueError('NO11_CLEAN_BUILD_CONTEXT_CHANGED: ' + repr(old[:90]))
    return text.replace(old, new)


def transform(name, source):
    text = source.decode('utf-8').replace('\r\n', '\n')
    helper = ". (Join-Path $PSScriptRoot 'No11CleanCompatibility.ps1')\n"
    if name.endswith('no11_broker_execution_service.py'):
        text = replace(text, "CONFIG = 'ARK_NO11_BROKER_EXECUTION_CONFIG_V1'",
                       "from no11_clean_runtime_guards import validate_fee_course, recheck_exit\n\n"
                       "CONFIG = 'ARK_NO11_BROKER_EXECUTION_CONFIG_V1'")
        text = replace(text, "    ledger.money(config.get('reserveChargesJpy', '0'))",
                       "    validate_fee_course(config)\n    ledger.money(config.get('reserveChargesJpy', '0'))")
        text = replace(text, '    def _dispatch(self, command, at):\n',
                       '    def _dispatch(self, command, at):\n'
                       '        at = recheck_exit(self, command, at)\n')
    elif name.endswith('no11_prepare_received_inputs.py'):
        text = replace(text, 'import no11_previous_archive_context as archive\n',
                       'import no11_previous_archive_context as archive\nimport no11_clean_weekly as weekly\n')
        anchor = '    evidence, evidence_sha = bootstrap.load_json(evidence_file, 5000000)\n'
        extra = '''    if evidence.get('schemaId') == weekly.SCHEMA:
        verify_documents(evidence, evidence_documents)
        evidence = weekly.assemble(info, reference, evidence, prepared_at,
                                   weekly_sha=evidence_sha, reference_sha=reference_sha)
        verify_documents(evidence, evidence_documents)
        assembled = bootstrap.immutable(root, 'weekly-session-security-evidence', evidence)
        evidence, evidence_sha = bootstrap.load_json(assembled, 5000000)
'''
        text = replace(text, anchor, anchor + extra)
    elif name.endswith('no11_input_prerequisites.py'):
        text = replace(text, 'import no11_prepare_received_inputs as prep\n',
                       'import no11_prepare_received_inputs as prep\nimport no11_clean_weekly as weekly\n')
        anchor = 'def validate_review(info, evidence, known_at):\n'
        text = replace(text, anchor, anchor +
                       "    if evidence.get('schemaId') == weekly.SCHEMA:\n"
                       "        return weekly.validate_static(info, evidence, known_at)\n")
    elif name.endswith('Read-No11BrokerSnapshot.ps1'):
        anchor = 'param([Alias(\'OfflineSelfTest\')][switch]$BrokerOfflineSelfTest)\n'
        text = replace(text, anchor, anchor + helper)
        anchor = '    $fn=Get-No11BrokerText (Get-No11BrokerCell $Data $r 1)'
        text = replace(text, anchor, '    $fn=Convert-No11CleanFunctionName (Get-No11BrokerText (Get-No11BrokerCell $Data $r 1))')
    elif name.endswith('Invoke-No11MsiiOrder.ps1'):
        text = replace(text, "$ErrorActionPreference='Stop'\n", "$ErrorActionPreference='Stop'\n" + helper)
        text = replace(text, "  Need-No11Transport ((& $Sink.PreparedStatus $Packet $Sink.State) -ceq '待機中')",
                       "  Need-No11Transport ((Get-No11CleanVendorStatus ([string](& $Sink.PreparedStatus $Packet $Sink.State)) $Packet) -ceq '待機中')")
        text = replace(text, '  $statusText=[string](& $Sink.Response $Packet $Sink.State)',
                       '  $statusText=Get-No11CleanVendorStatus ([string](& $Sink.Response $Packet $Sink.State)) $Packet')
        text = replace(text, '発注済み[（(]発注ID=', '発注済み[（(](?:発注|注文)ID=', 2)
        text = replace(text, ' $formula=[string]$State.formula.Formula',
                       ' $formula=Convert-No11CleanFormula ([string]$State.formula.Formula)')
        text = replace(text, "([string]$state.formula.Formula -match '^=Rss(?:StockOrder|CancelOrder)\\(')",
                       "((Convert-No11CleanFormula ([string]$state.formula.Formula)) -match '^=Rss(?:StockOrder|CancelOrder)\\(')")
        text = replace(text, '$value=[string]$state.formula.Value2',
                       '$value=Get-No11CleanVendorStatus ([string]$state.formula.Value2) $p', 2)
    elif name.endswith('Capture-No11SessionReferenceReadOnly.ps1'):
        anchor = "$ErrorActionPreference='Stop';Set-StrictMode -Version Latest\n"
        text = replace(text, anchor, anchor + helper)
        text = replace(text, '$start=Stamp;$values=$sheet.Range($range).Value2;$end=Stamp',
                       '$start=Stamp;$values=Read-No11CleanReferenceRows $sheet $symbols.Count;$end=Stamp')
        text = replace(text, '(ConvertTo-Json -InputObject $obj -Depth 10 -Compress)',
                       '(ConvertTo-No11CleanJson $obj)')
    elif name.endswith('Observe-No11AccountReadOnly.ps1'):
        text = replace(text, '(ConvertTo-Json -InputObject $value -Depth 20 -Compress)',
                       '(ConvertTo-No11CleanJson $value)')
    else:
        raise ValueError('NO11_CLEAN_BUILD_UNKNOWN_TARGET')
    if name.endswith('.py'):
        ast.parse(text, filename=name)
    return text.encode('utf-8')


def build(repo: Path, out: Path, ci_stage: Path | None = None):
    if out.exists() or out.is_symlink() or not out.parent.is_dir():
        raise ValueError('NO11_CLEAN_BUILD_NEW_OUTPUT_REQUIRED')
    originals, changed = {}, {}
    for name in TARGETS:
        raw = git(repo, 'show', BASE + ':' + ENGINE + '/' + name)
        original_blob = git(repo, 'rev-parse', BASE + ':' + ENGINE + '/' + name).decode().strip()
        if blob(raw) != original_blob:
            raise ValueError('NO11_CLEAN_BUILD_GIT_SOURCE_MISMATCH')
        originals[name] = raw
        changed[name] = transform(name, raw)
    for src, name in ADDITIONS.items():
        text = (HERE / src).read_text(encoding='utf-8-sig').replace('\r\n', '\n')
        if name.endswith('.py'):
            ast.parse(text, filename=name)
        else:
            text = '\ufeff' + text  # Windows PowerShell 5.1 Japanese literals.
        changed[name] = text.encode('utf-8')
    if ci_stage is not None:
        if os.environ.get('GITHUB_ACTIONS') != 'true':
            raise ValueError('NO11_CLEAN_BUILD_STAGE_ONLY_ON_CI')
        head = git(ci_stage, 'rev-parse', 'HEAD').decode().strip()
        if head != BASE or ci_stage.resolve() == repo.resolve():
            raise ValueError('NO11_CLEAN_BUILD_ISOLATED_BASELINE_REQUIRED')
        for name, raw in originals.items():
            if blob((ci_stage / ENGINE / name).read_bytes()) != blob(raw):
                raise ValueError('NO11_CLEAN_BUILD_STAGE_SOURCE_CHANGED')
        for name in ADDITIONS.values():
            if (ci_stage / ENGINE / name).exists():
                raise ValueError('NO11_CLEAN_BUILD_STAGE_ADDITION_EXISTS')
    out.mkdir()
    entries = []
    for name, data in changed.items():
        destination = out / 'payload' / ENGINE / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(data)
        entries.append({'path': ENGINE + '/' + name,
                        'sourceGitBlob': blob(originals[name]) if name in originals else None,
                        'outputSha256': sha(data), 'outputGitBlob': blob(data)})
    manifest = {'schemaId': 'ARK_NO11_CLEAN_REBUILD_PACKAGE_V1', 'baseCommit': BASE,
                'sourceOfRebuild': 'PINNED_GIT_OBJECTS_AND_NEW_SOURCE_ONLY',
                'oldPackagesUsed': False, 'files': entries,
                'modelsChanged': False, 'orderTransmission': False,
                'liveInstallationModified': False, 'productionReady': False}
    (out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    for name in ('Stage-No11CleanRebuild.ps1', 'README.md'):
        source = HERE / name
        if source.exists():
            text = source.read_text(encoding='utf-8-sig')
            (out / name).write_text(('\ufeff' if name.endswith('.ps1') else '') + text, encoding='utf-8')
    if ci_stage is not None:
        for name, data in changed.items():
            (ci_stage / ENGINE / name).write_bytes(data)
    archive = out.parent / (out.name + '.zip')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for file in sorted(out.rglob('*')):
            if file.is_file():
                info = zipfile.ZipInfo(file.relative_to(out).as_posix(), (2026, 11, 3, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, file.read_bytes())
    print('NO11_CLEAN_REBUILD_FILES=' + str(len(entries)))
    print('NO11_CLEAN_REBUILD_ZIP_SHA256=' + sha(archive.read_bytes()))
    print('OLD_PACKAGES_USED=False')
    print('ORDER_TRANSMISSION=False')
    return manifest


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--repo', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--ci-stage', type=Path)
    a = p.parse_args()
    build(a.repo.resolve(), a.output.resolve(), a.ci_stage.resolve() if a.ci_stage else None)
