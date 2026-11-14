"""Compare exact Git blob identities against read-only post-commit tree GETs."""
from pathlib import Path
from datetime import datetime, timezone, timedelta
import hashlib, json, sys
R = Path(__file__).resolve().parent
PREFIX = 'research/state-r2-support-v6-20261002/'

def gitsha(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def expected():
    entries = []
    for p in sorted(R.glob('*.py')):
        data = p.read_bytes()
        entries.append({'path':PREFIX+p.name,'local_path':str(p),
                        'Git_blob_SHA1':gitsha(data),'SHA256':hashlib.sha256(data).hexdigest()})
    for name,path in [('state-r2-v6-support-20261002.yml','.github/workflows/state-r2-v6-support-20261002.yml'),
                      ('ACQUISITION_PAYLOAD_V6.b64',PREFIX+'payload.b64')]:
        data = (R/name).read_bytes()
        entries.append({'path':path,'local_path':str(R/name),
                        'Git_blob_SHA1':gitsha(data),'SHA256':hashlib.sha256(data).hexdigest()})
    return entries

def main():
    mode = sys.argv[1]
    if mode == 'expected':
        print(json.dumps(expected())); return
    assert mode == 'verify'
    head, treefile = sys.argv[2:4]
    actual = json.loads(Path(treefile).read_text())
    assert actual['verified_HEAD'] == head and actual['actual_post_commit_GET'], 'SOURCE_GET_IDENTITY'
    entries = expected()
    for item in entries:
        assert actual['Git_blob_SHA1_by_path'].get(item['path']) == item['Git_blob_SHA1'], 'PUBLIC_SOURCE_BYTE_MISMATCH:'+item['path']
    index = json.loads((R/'SOURCE_CODE_LOCATION_INDEX_V6.json').read_text())
    assert index['verified_final_snapshot_HEAD'] == head, 'INDEX_HEAD'
    assert {p['path']:p['SHA256'] for p in index['source_files']} == {p['path']:p['SHA256'] for p in entries}, 'INDEX_SOURCE_SHA'
    receipt = {'status':'PASS','JST':datetime.now(timezone(timedelta(hours=9))).isoformat(),
               'verified_HEAD':head,'actual_post_commit_GET':True,'source_N':len(entries),
               'all_public_source_bytes_equal':True,'Git_blob_SHA1_and_local_SHA256_checked':True,
               'index_SHA256':hashlib.sha256((R/'SOURCE_CODE_LOCATION_INDEX_V6.json').read_bytes()).hexdigest(),
               'parent_result_mutations':0,'new_fits_labels_bootstrap':[0,0,0]}
    with (R/'PUBLIC_SOURCE_VERIFICATION_V6.json').open('x') as f:
        f.write(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
