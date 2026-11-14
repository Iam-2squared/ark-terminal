from pathlib import Path
import base64
import hashlib
import json
import tarfile

root = Path('work/ad01/baseline')
archives = root / 'archives'
archives.mkdir(parents=True, exist_ok=True)
envelopes = Path('evidence/private')
listing = {r['name']: r for r in json.loads((envelopes/'e0-package-listing.json').read_text())}

def git_blob(data):
    return hashlib.sha1(f'blob {len(data)}\0'.encode() + data).hexdigest()

def decode(envelope, filename):
    value = json.loads(envelope.read_text())['structuredContent']
    if value['encoding'] == 'base64':
        data = base64.b64decode(value['content'])
    elif value['encoding'] == 'utf-8':
        data = value['content'].encode('utf-8')
    else:
        raise ValueError(value['encoding'])
    expected = listing[filename]
    assert len(data) == expected['size'], filename
    assert git_blob(data) == expected['sha'] == value['sha'], filename
    (archives/filename).write_bytes(data)
    return data

summary = []
for label in [f'W{i}' for i in range(13,22)] + ['CHAIN38']:
    manifest_name = label + '_PACKAGE_MANIFEST.json'
    manifest = json.loads(decode(envelopes/(manifest_name+'.envelope.json'), manifest_name))
    filename = manifest['archive']
    if label == 'W13':
        data = decode(envelopes/'w13-response.json', filename)
    elif label == 'CHAIN38':
        parts = [filename+f'.part-{i:03}.bin' for i in range(2)]
        data = b''.join(decode(envelopes/(name+'.envelope.json'),name) for name in parts)
        (archives/filename).write_bytes(data)
    else:
        data = decode(envelopes/(filename+'.envelope.json'), filename)
    assert len(data) == manifest['bytes'], label
    assert hashlib.sha256(data).hexdigest() == manifest['sha256'], label
    assert git_blob(data) == manifest['git_blob'], label
    expected_members = {m['path']:m for m in manifest['members']}
    with tarfile.open(archives/filename, 'r:xz') as archive:
        actual_members = archive.getmembers()
        assert {m.name for m in actual_members} == set(expected_members), label
        for member in actual_members:
            target = root / member.name
            assert target.resolve().is_relative_to(root.resolve()), member.name
            assert member.isfile(), member.name
            content = archive.extractfile(member).read()
            expected = expected_members[member.name]
            assert len(content) == expected['bytes'], member.name
            assert hashlib.sha256(content).hexdigest() == expected['sha256'], member.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    paths = list(expected_members)
    summary.append({'label':label,'archive_bytes':len(data),'members_verified':len(paths),
                    'manifest_keys':list(manifest),'member_paths':paths,
                    'E_aggregate_paths':[p for p in paths if f'/{label}/E/' in p and '/sessions/' not in p],
                    'all_git_blob_archive_and_member_hash_checks_passed':True})
(root/'CARRIER_VERIFICATION.json').write_text(json.dumps(summary,indent=2)+'\n')
for row in summary:
    print(row['label'], row['members_verified'], 'members verified;', row['E_aggregate_paths'])
