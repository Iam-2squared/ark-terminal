"""Development-only migration applied by isolated CI; never run on user's PC."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def edit(file, old, new):
    path = ROOT / file
    src = path.read_text(encoding='utf-8-sig')
    if new in src:
        return
    if src.count(old) != 1:
        raise RuntimeError('REVIEWED_CONTEXT_NOT_UNIQUE_' + file)
    path.write_text(src.replace(old, new, 1), encoding='utf-8', newline='\n')


COMPAT = r'''class SourceAnchorChanged(ValueError):
    def __init__(self, needle, matches=0):
        super().__init__('NO11_UPDATE_PATH_SOURCE_ANCHOR_CHANGED')
        self.anchor_id = hashlib.sha256(needle.encode('utf-8')).hexdigest()[:16]
        self.match_count = matches
        self.anchor = needle


# Formatting equivalence only. Strings and comments remain indivisible tokens;
# changed literals, statements or inserted comments do NOT disappear here.
_PS_TOKEN = re.compile(r"'(?:''|[^'])*'|\"(?:`[\s\S]|[^\"`])*\"|#[^\n]*|[^\s]")
_BATCH_NAMES = frozenset(('FullBatchSize', 'RefreshBatchSize',
                          'MinuteBatchSize', 'DailyBatchSize', 'BatchSize'))
_BATCH_VALUES = frozenset((5, 10, 20, 30, 40, 47, 50))
_BATCH_DECL = re.compile(
    r'(?m)^(?P<indent>[ \t]*)\[ValidateRange\([ \t]*1[ \t]*,[ \t]*(?P<upper>\d+)[ \t]*\)\]'
    r'[ \t]*\[int\][ \t]*\$(?P<name>FullBatchSize|RefreshBatchSize|MinuteBatchSize|DailyBatchSize|BatchSize)'
    r'[ \t]*=[ \t]*(?P<default>\d+)(?P<tail>[ \t]*,?[ \t]*)(?=\n|$)')


def _token_matches(text, needle):
    actual = list(_PS_TOKEN.finditer(text))
    wanted = [m.group() for m in _PS_TOKEN.finditer(needle)]
    if not wanted:
        return []
    tokens = [m.group() for m in actual]
    length = len(wanted)
    return [(actual[i].start(), actual[i + length - 1].end())
            for i in range(len(tokens) - length + 1)
            if tokens[i:i + length] == wanted]


def once(text, needle, value):
    count = text.count(needle)
    if count == 1:
        return text.replace(needle, value, 1)
    if count > 1:
        raise SourceAnchorChanged(needle, count)

    # Accept known, already-used batch defaults/ranges, not one historical
    # spelling such as FullBatchSize=10. Only this declaration is replaced.
    requested = _BATCH_DECL.fullmatch(needle.strip('\n'))
    if requested and requested['name'] in _BATCH_NAMES:
        name = requested['name']
        matches = [m for m in _BATCH_DECL.finditer(text) if m['name'] == name]
        if len(matches) != 1:
            raise SourceAnchorChanged(needle, len(matches))
        m = matches[0]
        if (int(m['upper']) not in _BATCH_VALUES or
                int(m['default']) not in _BATCH_VALUES or
                not 1 <= int(m['default']) <= int(m['upper'])):
            raise SourceAnchorChanged(needle)
        # Confirm the migration still sets the approved 47-function target.
        replacement = _BATCH_DECL.search(value)
        if replacement is None or replacement['name'] != name or replacement['default'] != '47':
            raise SourceAnchorChanged(needle)
        if m['tail'].strip() != replacement['tail'].strip():
            raise SourceAnchorChanged(needle)
        return text[:m.start()] + value + text[m.end():]

    # Existing Clean collectors can already have the intended startup logic.
    # An exact replacement present once is an applied operation, not a failure.
    if text.count(value) == 1:
        return text
    if '$' in needle or needle.lstrip().startswith('Write-Host'):
        matches = _token_matches(text, needle)
        if len(matches) == 1:
            start, end = matches[0]
            # Retain indentation from the existing source outside the span.
            return text[:start] + value.lstrip(' \t') + text[end:]
        # The AutoMax telemetry is OPTIONAL in deployed Clean variants.
        # Do not recreate its deleted feature flag or reject a valid collector
        # merely because a diagnostic Write-Host line does not exist.
        if (not matches and needle.lstrip().startswith('Write-Host')
                and 'NO11_DAILY_AUTOMAX=' in needle and '$AutoMaxThroughput' not in text):
            return text
        raise SourceAnchorChanged(needle, len(matches))
    raise SourceAnchorChanged(needle)
'''

edit('no11_update_path.py', 'from pathlib import Path\n',
     'from pathlib import Path\nimport hashlib\nimport re\n')
edit('no11_update_path.py',
     "def once(text, needle, value):\n    require(text.count(needle) == 1, 'SOURCE_ANCHOR_CHANGED')\n    return text.replace(needle, value, 1)\n",
     COMPAT)

# Validate every file before replacing any launcher/collector bytes. Report all
# incompatible kinds in one pass, not one opaque error on each user retry.
edit('install_no11_launcher_update.py',
     '    after = {k: patch.transform(k, before[k]) for k in KINDS}',
     '''    after = {}
    failed = []
    for kind in KINDS:
        try:
            after[kind] = patch.transform(kind, before[kind])
            print('NO11_UPDATE_SOURCE=' + kind.upper() + '|READY', flush=True)
        except ValueError as error:
            failed.append(kind)
            print('NO11_UPDATE_FAILED_FILE=' + paths[kind].name, flush=True)
            print('NO11_UPDATE_FAILED_KIND=' + kind.upper(), flush=True)
            print('NO11_UPDATE_SOURCE_SHA256=' + n.digest(before[kind]), flush=True)
            if isinstance(error, patch.SourceAnchorChanged):
                print('NO11_UPDATE_ANCHOR_ID=' + error.anchor_id, flush=True)
                print('NO11_UPDATE_ANCHOR_MATCHES=' + str(error.match_count), flush=True)
                # Public EXPECTED source fragment only: never print private
                # workbook paths, local source contents, keys or account data.
                label = error.anchor.strip().splitlines()[0][:180]
                print('NO11_UPDATE_EXPECTED_ANCHOR=' + label, flush=True)
            reason = str(error)
            if not reason.startswith('NO11_'):
                reason = 'NO11_UPDATE_SOURCE_UNRECOGNIZED'
            print('NO11_UPDATE_SOURCE_REASON=' + reason, flush=True)
    if failed:
        raise ValueError('NO11_UPDATE_PATH_' + '_'.join(k.upper() for k in failed) + '_SOURCE_ANCHOR_CHANGED')''')

edit('install_no11_unified_update.py',
     '        backend=core.install(store,source,True)\n',
     "        backend=core.install(store,source,True)\n        print('NO11_BASE_RESUME_INSTALL='+backend,flush=True)\n")
print('NO11_INSTALLER_COMPATIBILITY_REPAIR=APPLIED_TO_DEVELOPMENT_TREE')
