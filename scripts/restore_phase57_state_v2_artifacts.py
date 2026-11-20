"""Restore ONLY explicitly pinned Development ZIP members. No market provider API."""
from __future__ import annotations
import argparse,hashlib,json,shutil,urllib.request,urllib.error,zipfile
from pathlib import Path

ARTIFACTS=[
(10605887642,35510863265,'749caf82bbd9d39969f5712ef5a6f2705ac973a2f74483f03307c671586ae05a',{ 'substrate/'+n:n for n in ('opportunities.json.gz','raw-paths-evaluator-only.json.gz','source-ledger.json','inventory.json','manifest.json')}),
(10619378314,35553422490,'279388c00b6a97501a578d8ab1f2dd813ba5b56a8a1d91c7ee7afeea39b805e0',{'daily.json.gz':'daily.json.gz','receipt.json':'receipt.json'}),
(10621869067,35560748821,'cf4c8678fd41be570e3d262bfca29710400db8b2119aaf0b43be1de813d9f5a5',{'measurement/raw/audit-records.json.gz':'step1-audit-records.json.gz','measurement/raw/future-paths.json.gz':'step1-future-paths.json.gz','receipt.json':'step1-receipt.json'}),
(10630618102,35581246681,'cc921c476af1079344975daa78e89fe03ee0dfc20ee62333170199178ade795e',None)]
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def api_get(url,token):
    return urllib.request.Request(url,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
def restore(out,repo,token=None,archives=None):
    out=Path(out);out.mkdir(parents=True,exist_ok=False);inputs=out/'inputs';inputs.mkdir();v1=out/'v1';v1.mkdir();receipts=[]
    for aid,run,wanted,members in ARTIFACTS:
        p=Path(archives)/(str(aid)+'.zip') if archives else out/(str(aid)+'.zip')
        if not archives:
            if not token:raise ValueError('GITHUB_READ_TOKEN_REQUIRED')
            base='https://api.github.com/repos/Iam-2squared/ark-terminal/actions/artifacts/'+str(aid)
            with urllib.request.urlopen(api_get(base,token),timeout=60) as response:meta=json.load(response)
            if meta['id']!=aid or meta['workflow_run']['id']!=run or meta['digest']!='sha256:'+wanted:raise ValueError('PINNED_ARTIFACT_METADATA')
            try:
                urllib.request.build_opener(NoRedirect).open(api_get(base+'/zip',token),timeout=60)
                raise ValueError('EXPECTED_TEMPORARY_ARTIFACT_REDIRECT')
            except urllib.error.HTTPError as err:
                if err.code not in (301,302,303,307,308):raise
                url=err.headers['Location']
            if not url.startswith('https://'):raise ValueError('ARTIFACT_REDIRECT_MUST_BE_HTTPS')
            # No authorization header is forwarded to the storage host. Never log signed URLs.
            with urllib.request.urlopen(url,timeout=120) as response,p.open('xb') as file:shutil.copyfileobj(response,file)
        if sha(p)!=wanted:raise ValueError('ARTIFACT_ZIP_DIGEST:'+str(aid))
        with zipfile.ZipFile(p) as z:
            if len(z.namelist())!=len(set(z.namelist())):raise ValueError('DUPLICATE_ARCHIVE_MEMBERS')
            if members is not None:
                admitted=[]
                for src,dest in members.items():
                    data=z.read(src)
                    with (inputs/dest).open('xb') as f:f.write(data)
                    admitted.append({'member':src,'sha256':hashlib.sha256(data).hexdigest()})
            else:
                data=z.read('measurement/manifest.json')
                if hashlib.sha256(data).hexdigest()!='4e11b8eb576dcdd0552f2461c699f57bdabc1db37d8e4c2be9a389a80748d6d1':raise ValueError('V1_MEASUREMENT_MANIFEST')
                manifest=json.loads(data);admitted=[]
                for rel,want in manifest.items():
                    if not (rel in ('admission.json','inputs.jsonl.gz','checkpoints.csv.gz','summary.json') or rel.startswith(('raw/','contexts/'))):continue
                    if '..' in Path(rel).parts or Path(rel).is_absolute():raise ValueError('UNSAFE_MEMBER')
                    content=z.read('measurement/'+rel)
                    if hashlib.sha256(content).hexdigest()!=want:raise ValueError('V1_MEMBER_HASH')
                    dest=v1/rel;dest.parent.mkdir(exist_ok=True,parents=True)
                    with dest.open('xb') as f:f.write(content)
                    admitted.append({'member':'measurement/'+rel,'sha256':want})
                (v1/'manifest.json').write_bytes(data)
        receipts.append({'artifactId':aid,'runId':run,'archiveDigest':wanted,'members':admitted})
    shutil.copyfile(Path(repo)/'docs/evidence/phase57-entry-timing-signal-census-v1/protocol.json',inputs/'cohort-protocol.json')
    (out/'restoration-receipt.json').write_text(json.dumps({'artifacts':receipts,'providerRequests':0,'protectedDataOpened':0,'memberAdmission':'EXPLICIT_ALLOWLIST_ONLY'},sort_keys=True,indent=2)+'\n')

if __name__=='__main__':
    import os
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);p.add_argument('--repo',default='.');p.add_argument('--archives');a=p.parse_args()
    restore(a.output,a.repo,os.getenv('GH_READ_TOKEN'),a.archives)
