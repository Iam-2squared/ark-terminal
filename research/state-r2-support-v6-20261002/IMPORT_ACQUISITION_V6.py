"""Read-only import gate for the sole bounded V6 Actions acquisition artifact."""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone, timedelta
import hashlib, json, shutil, sys, zipfile

R = Path(__file__).resolve().parent

def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def main():
    src, digest, run_id, artifact_id = sys.argv[1:5]
    src = Path(src)
    digest = digest.removeprefix('sha256:')
    assert int(run_id) == 36995623338, 'UNREGISTERED_WORKFLOW_RUN'
    assert sha(src) == digest, 'ARTIFACT_DIGEST'
    assert not (R/'ACQUISITION').exists(), 'ALREADY_IMPORTED'
    assert not (R/'FRESH_LABELS').exists(), 'LABEL_BEFORE_IMPORT'
    archive = R/'ACQUISITION_ARTIFACT_V6.zip'
    assert not archive.exists(), 'ARCHIVE_ALREADY_PRESENT'
    with zipfile.ZipFile(src) as z:
        names = z.namelist()
        assert len(names) == len(set(names)), 'DUPLICATE_ARTIFACT_MEMBER'
        assert z.testzip() is None, 'ARTIFACT_CRC'
        assert all(not PurePosixPath(n).is_absolute() and '..' not in PurePosixPath(n).parts
                   and '\\' not in n for n in names), 'ARTIFACT_PATH'
        assert all((i.external_attr >> 16) & 0o170000 != 0o120000
                   for i in z.infolist()), 'ARTIFACT_SYMLINK'
        manifest = json.loads(z.read('MANIFEST.json'))
        listed = {p['path'] for p in manifest['files']}
        assert len(listed) == len(manifest['files']), 'MANIFEST_DUPLICATE'
        actual = {i.filename for i in z.infolist() if not i.is_dir()}
        assert actual == listed | {'MANIFEST.json','WORKFLOW_PURGE_RECEIPT.json'}, 'UNLISTED_EXPORT'
        for p in manifest['files']:
            data = z.read(p['path'])
            assert len(data) == p['bytes'] and hashlib.sha256(data).hexdigest() == p['SHA256'], 'ARTIFACT_MEMBER_HASH'
        runner = json.loads(z.read('RUNNER_FINAL_RECEIPT.json'))
        purge = json.loads(z.read('PURGE_RECEIPT.json'))
        wp = json.loads(z.read('WORKFLOW_PURGE_RECEIPT.json'))
        assert runner['status'] == 'FIXED_V6_DEVELOPMENT_PASS_COMPLETE' and runner['error'] is None, 'ACQUISITION_INTEGRITY'
        assert purge['verified'] and wp['verified'], 'RAW_PURGE'
        for k in ['raw_pages_exported','secret_values_exported','labels_created','model_fits','bootstrap_draws','replacement','protected_requests']:
            assert runner[k] == 0, 'EXPORT_BOUNDARY:'+k
        assert runner['actual_provider_HTTP'] <= 2000 and runner['new_steps'] <= 125000, 'ACQUISITION_CAP'
        assert runner['original_fixed_N'] <= 452 and runner['classified_N'] == runner['original_fixed_N'], 'FINITE_PASS_NOT_COMPLETE'
        out = R/'ACQUISITION'
        out.mkdir(exist_ok=False)
        z.extractall(out)
    shutil.copyfile(src, archive)
    receipt = {'status':'PASS','JST':datetime.now(timezone(timedelta(hours=9))).isoformat(),
               'mode':'ACQUISITION','workflow_run_id':int(run_id),'artifact_id':int(artifact_id),
               'artifact_SHA256':sha(archive),'artifact_bytes':archive.stat().st_size,
               'member_N':len(manifest['files']),'CRC_PASS':True,'member_SHA_PASS':True,
               'unlisted_export_N':0,'runner':runner,'all_raw_and_credentials_purged':True,
               'new_labels_fits_bootstrap_before_import':[0,0,0]}
    with (R/'ACQUISITION_IMPORT_RECEIPT_V6.json').open('x') as f:
        f.write(json.dumps(receipt,sort_keys=True,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__ == '__main__':
    main()
