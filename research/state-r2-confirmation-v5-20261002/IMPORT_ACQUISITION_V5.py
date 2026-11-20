"""Import an authorized Actions export only after its immutable digest is GET."""
from pathlib import Path
import json,hashlib,zipfile,shutil,sys
R=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 mode,src,digest,run_id,artifact_id=sys.argv[1:6];assert mode in ['RECOVERY','EXTENSION']
 src=Path(src);assert sha(src)==digest,'ARTIFACT_DIGEST';out=R/mode;out.mkdir(exist_ok=False);archive=R/(mode+'_ARTIFACT_V5.zip');shutil.copyfile(src,archive)
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None and all(not n.startswith('/') and '..' not in Path(n).parts for n in z.namelist()),'ARTIFACT_CRC_OR_PATH'
  z.extractall(out)
 manifest=json.loads((out/'MANIFEST.json').read_text())
 for x in manifest['files']:assert sha(out/x['path'])==x['SHA256'] and (out/x['path']).stat().st_size==x['bytes'],'ARTIFACT_MEMBER_HASH'
 runner=json.loads((out/'RUNNER_FINAL_RECEIPT.json').read_text());purge=json.loads((out/'PURGE_RECEIPT.json').read_text());wp=json.loads((out/'WORKFLOW_PURGE_RECEIPT.json').read_text())
 assert purge['verified'] and wp['verified'] and runner['raw_pages_exported']==runner['secret_values_exported']==runner['labels_created']==runner['model_fits']==runner['bootstrap_draws']==runner['replacement']==runner['protected_requests']==0,'EXPORT_BOUNDARY'
 record={'status':'PASS','mode':mode,'workflow_run_id':int(run_id),'artifact_id':int(artifact_id),'artifact_SHA256':sha(archive),'artifact_bytes':archive.stat().st_size,'member_N':len(manifest['files']),'CRC_PASS':True,'member_SHA_PASS':True,'runner':runner,'all_raw_and_credentials_purged':True,'new_labels_fits_bootstrap_before_import':[0,0,0]}
 (R/(mode+'_IMPORT_RECEIPT_V5.json')).write_text(json.dumps(record,sort_keys=True,indent=2)+'\n');print(json.dumps(record))
if __name__=='__main__':main()
