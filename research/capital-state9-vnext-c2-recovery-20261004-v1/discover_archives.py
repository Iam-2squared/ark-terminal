"""Read existing archive directories and source metadata only; no strategy/model run.

Protected/holdout/fresh market or teacher bytes are never opened. Nested zip bytes
are container inventory, not interpreted market rows. Existing Development raw
members may be selected later by an explicit current-population identity list.
"""
import collections
import hashlib
import json
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

BASE = Path('/workspace/scratch/7d6b6257fecd')
OUT = BASE / 'capital_c2_recovery_private'
OUT.mkdir(exist_ok=True)
seen = set()
catalog = []
metadata = []
archive_receipts = []
META = re.compile(r'(source.*(?:receipt|proof|ledger|manifest)|(?:dataset|data_scope|input_location|inheritance|acquisition_import|delivery|split_package|source_code).*\.(json|csv)$|manifest.*\.json$|source_export_receipt)', re.I)
BLOCKED_PAYLOAD = re.compile(r'(protected|holdout|fresh|prospective|validation|oos).*(?:teacher|label|raw|bars|ohlc|feature|prediction)', re.I)

def sha_file(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''): h.update(chunk)
    return h.hexdigest()

def walk(path, lineage, depth=0):
    digest = sha_file(path)
    if digest in seen:
        archive_receipts.append({'lineage': lineage, 'sha256': digest, 'status': 'IDENTICAL_ARCHIVE_ALREADY_CATALOGED'})
        return
    seen.add(digest)
    with zipfile.ZipFile(path) as z:
        infos = z.infolist()
        archive_receipts.append({'lineage': lineage, 'sha256': digest, 'entries': len(infos), 'status': 'CENTRAL_DIRECTORY_READ'})
        for info in infos:
            if info.is_dir(): continue
            catalog.append({'archive_lineage': lineage, 'member': info.filename, 'bytes': info.file_size, 'crc32': info.CRC})
            if META.search(info.filename) and info.file_size <= 1000000 and not BLOCKED_PAYLOAD.search(info.filename):
                raw = z.read(info)
                try: obj = json.loads(raw)
                except (json.JSONDecodeError, UnicodeError): obj = None
                metadata.append({'archive_lineage': lineage, 'member': info.filename, 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'value': obj})
            if info.filename.lower().endswith('.zip') and depth < 5:
                with tempfile.TemporaryDirectory(dir=OUT) as tmp:
                    nested = Path(tmp)/'container.zip'
                    with z.open(info) as src, nested.open('wb') as dst: shutil.copyfileobj(src, dst)
                    walk(nested, lineage+'!'+info.filename, depth+1)

for path in sorted((BASE/'project_sources').glob('*.zip')):
    if path.name.startswith('12-'): continue  # Synthetic RC1 pack is not market-source recovery.
    walk(path, path.name)
for name, obj in [('NESTED_ARCHIVE_CATALOG.json', catalog), ('ARCHIVE_METADATA_PRIVATE.json', metadata), ('ARCHIVE_DISCOVERY_RECEIPTS.json', archive_receipts)]:
    with (OUT/name).open('x') as f: json.dump(obj, f, ensure_ascii=False, separators=(',',':'))
print(json.dumps({'unique_existing_archives': len(seen), 'archive_lineages': len(archive_receipts), 'catalog_entries': len(catalog), 'source_metadata_members': len(metadata), 'raw_market_or_teacher_members_opened': 0, 'new_data_or_provider': 0, 'raw_family_member_counts': dict(collections.Counter(r['member'].split('/')[0] for r in catalog if re.search(r'raw|minute|5m|1m|bars|ohlc',r['member'],re.I)).most_common(12))}))
