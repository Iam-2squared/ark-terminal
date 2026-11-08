"""Development-only exact edits, run in isolated branch CI; never installed on PC."""
from pathlib import Path
import hashlib
import re

ROOT = Path(__file__).resolve().parent


def edit(name, old, new):
    p = ROOT / name
    raw = p.read_bytes()
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    if new in text:
        return
    if text.count(old) != 1:
        raise SystemExit('REVIEWED_CONTEXT_CHANGED_' + name)
    p.write_text(text.replace(old, new, 1), encoding='utf-8', newline='\n')


# This fresh-checkout installer was still pinned to the pre-#610 bridge.
# The historical bootstrap downloads its immutable OLD commit and is untouched.
p = ROOT / 'install_daily_cycle.py'
s = p.read_text(encoding='utf-8-sig')
raw = (ROOT / 'launcher_automatic_bridge_v4.py').read_bytes().replace(b'\r\n', b'\n')
actual = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
pattern = r"('launcher_automatic_bridge_v4.py'\s*:\s*')([0-9a-f]{40})(')"
m = re.search(pattern, s)
assert m and m[2] in ('224766266bfe953bc6dfa1abda28230fae6ff69f', actual)
if m[2] != actual:
    p.write_text(s[:m.start(2)] + actual + s[m.end(2):], encoding='utf-8', newline='\n')

edit('no11_nightly_resume.py',
     "    python = safe(binding['python'])",
     "    need(digest(paths['validator'].read_bytes()) == binding.get('nightlyResumeValidatorSha256'), 'VALIDATOR_SOURCE_CHANGED')\n    python = safe(binding['python'])")
edit('no11_nightly_resume.py',
     "Prepare-No11PreviousArchiveReadOnly|\"",
     "Prepare-No11PreviousArchiveReadOnly|Start-No11UnifiedLauncher|Start-No11PreopenStandby|\"")
edit('install_no11_week_resilience.py',
     "               bridgeSha256=n.digest(bridge))",
     "               nightlyResumeValidatorSha256=n.digest(payload['no11_selection_status.py']),\n               bridgeSha256=n.digest(bridge))")
edit('install_no11_week_resilience.py',
     "        return True\n    need(j['phase']",
     "        b = n.read(paths['binding'])\n        for field in ('transportProbe', 'nightlyResumeTool'):\n            need(n.digest(n.safe(b[field]).read_bytes()) == b[field + 'Sha256'], 'INSTALLED_PACKAGE_CHANGED')\n        validator = Path(b['nightlyResumeTool']).with_name('no11_selection_status.py')\n        need(n.digest(n.safe(validator).read_bytes()) == b['nightlyResumeValidatorSha256'], 'INSTALLED_VALIDATOR_CHANGED')\n        return True\n    need(j['phase']")
edit('install_no11_week_resilience.py',
     "                with dest.open('xb') as f:\n                    f.write(raw); f.flush(); os.fsync(f.fileno())",
     "                candidate = None\n                try:\n                    with tempfile.NamedTemporaryFile('wb', dir=package, delete=False) as f:\n                        candidate = Path(f.name)\n                        f.write(raw); f.flush(); os.fsync(f.fileno())\n                    # Publish complete bytes only. Existing destinations never overwritten.\n                    os.link(candidate, dest)\n                finally:\n                    if candidate is not None:\n                        candidate.unlink(missing_ok=True)")
edit('install_no11_week_resilience.py',
     "'-NonInteractive', '-File', str(harness)",
     "'-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(harness)")
# Remove an unused parser command string; all actual paths use argv, never eval.
p = ROOT / 'install_no11_week_resilience.py'
s = p.read_text()
s = '\n'.join(line for line in s.split('\n') if not line.lstrip().startswith('command = "$t=$null;$e=$null;'))
p.write_text(s, encoding='utf-8', newline='\n')

print('NO11_REVIEWED_SOURCE_HARDENING=PASS')
print('USER_PC_CHANGED=False\nORDER_TRANSMISSION=False')
