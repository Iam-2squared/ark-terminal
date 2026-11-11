"""Development migration for the user-observed non-AutoMax collector.

Edits the official update-path transformer, not the Windows user's files.
The fixture represents the supplied snippets; it is not the complete user's
private source and must never be labeled an exact SHA256 reproduction.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATH = ROOT / 'no11_update_path.py'
source = PATH.read_text(encoding='utf-8-sig')


def edit(old, new):
    global source
    if new in source:
        return
    if source.count(old) != 1:
        raise RuntimeError('PLAIN_POOL_REVIEWED_SOURCE_CONTEXT_CHANGED')
    source = source.replace(old, new, 1)


edit("""        text = once(text,
            '  $physical=if($AutoMaxThroughput){[Math]::Min(5,$ceiling)}else{$ceiling}',
            '  $physical=$ceiling')""", """        # ARK_NO11_USER_OBSERVED_PLAIN_POOL_START_V1
        # Local lines 347-348 calculate SafePhysicalBatch directly and have
        # no AutoMax switch/helper. Recognize that complete paired statement;
        # do not invent a removed feature or overwrite the rest of the file.
        plain_start = ('  $physical=SafePhysicalBatch $existing $BatchSize\\n'
                       '  $ceiling=$physical;$fullWaves=0')
        if _token_matches(text, plain_start):
            text = once(text, plain_start,
                '  $ceiling=SafePhysicalBatch $existing $BatchSize\\n'
                '  $physical=$ceiling;$fullWaves=0')
        else:
            text = once(text,
                '  $physical=if($AutoMaxThroughput){[Math]::Min(5,$ceiling)}else{$ceiling}',
                '  $physical=$ceiling')""")

old = '''        text = once(text, old, new)
        # Group-complete telemetry may no longer land on a perfect hundred.'''
new = '''        # User-observed lines 426-433 use a two-clean-wave +5 ramp,
        # not the AutoMax branch above. Replace either reviewed variant with
        # the SAME immediate restoration of the current available ceiling.
        plain_ramp = """   }elseif($physical -lt $ceiling){
    $fullWaves++
    if($fullWaves -ge 2){
     $physical=[Math]::Min($ceiling,$physical+5)
     $fullWaves=0
     Write-Host ('NO11_DAILY_BATCH_TUNE=FULL_WAVES_RAISED_TO_{0}' -f $physical)
    }
   }"""
        if _token_matches(text, plain_ramp):
            text = once(text, plain_ramp, new)
        else:
            text = once(text, old, new)
        # Group-complete telemetry may no longer land on a perfect hundred.'''
edit(old, new)

# A selftest-only diagnostic line is not a prerequisite for migrating the
# live collector. Some local Clean sources predate that embedded selftest.
# We still execute the migrated startup, wave end and recovery via AST in CI.
start = source.index('        # The legacy grouping/ramp helpers stay available')
end = source.index("    elif kind == 'daily':", start)
old = source[start:end]
if 'ARK_NO11_POOL_SELFTEST_OPTIONAL_V1' not in old:
    needle = "        text = once(text,\n            \" Write-Host 'NO11_DAILY_AUTO_100_GROUP_OFFLINE_SELFTEST=PASS'\","
    if old.count(needle) != 1:
        raise RuntimeError('PLAIN_POOL_SELFTEST_CONTEXT_CHANGED')
    comments, statement = old.split('        text = once(text,', 1)
    statement = '        text = once(text,' + statement
    # Indent all Python statement lines AND PowerShell triple-string body
    # consistently. PowerShell's syntax is whitespace-independent here.
    indented = ''.join('    ' + line if line.strip() else line
                       for line in statement.splitlines(keepends=True))
    guard = '''        # ARK_NO11_POOL_SELFTEST_OPTIONAL_V1
        selftest_line = " Write-Host 'NO11_DAILY_AUTO_100_GROUP_OFFLINE_SELFTEST=PASS'"
        selftest_matches = _token_matches(text, selftest_line)
        if len(selftest_matches) > 1:
            raise SourceAnchorChanged(selftest_line, len(selftest_matches))
        if selftest_matches:
'''
    source = source[:start] + comments + guard + indented + source[end:]

compile(source, str(PATH), 'exec')
PATH.write_text(source, encoding='utf-8', newline='\n')
print('NO11_PLAIN_POOL_COMPATIBILITY_MIGRATION=PASS')
print('USER_PC_CHANGED=False\nORDER_TRANSMISSION=False')
