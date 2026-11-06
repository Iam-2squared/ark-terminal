from pathlib import Path
import json,hashlib,zipfile,base64,sys,ast
R=Path(__file__).resolve().parent;T=R/'runner';first=R/'FIRST_EXPANSION'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
receipt=json.loads((first/'RUNNER_FINAL_RECEIPT.json').read_text());assert receipt['error']['code']=='RAW_DECIMAL_LEXEME_REQUIRED' and receipt['new_steps']==0
artifact_id=int(sys.argv[1]);artifact_SHA=sys.argv[2]
source=(T/'export_expansion.py').read_text()
source=source.replace("status='NOT_STARTED';error=None;proposals=[];skips=[];datasets=[]", "status='NOT_STARTED';error=None;proposals=[];skips=[];datasets=[];priorrequests=0")
start=source.index(" exc={(r['date'],r['code'])")
end=source.index(" assert len(proposals)<=72,'PROPOSAL_CAP'")
replacement=f''' import urllib.request,urllib.error,io,zipfile
 class RedirectOff(urllib.request.HTTPRedirectHandler):
  def redirect_request(self,*args,**kwargs):return None
 request=urllib.request.Request('https://api.github.com/repos/Iam-2squared/ark-terminal/actions/artifacts/{artifact_id}/zip',headers={{'Authorization':'Bearer '+os.environ['GH_TOKEN'],'Accept':'application/vnd.github+json'}})
 try:response=urllib.request.build_opener(RedirectOff()).open(request,timeout=120)
 except urllib.error.HTTPError as e:
  if e.code not in (301,302,303,307,308):raise RuntimeError('REPAIR_ARTIFACT_READ_FAILED') from None
  location=e.headers['Location'];assert location.startswith('https:')
  response=urllib.request.urlopen(location,timeout=120)
 with response:b=response.read()
 assert hashlib.sha256(b).hexdigest()=='{artifact_SHA}','REPAIR_ARTIFACT_HASH'
 with zipfile.ZipFile(io.BytesIO(b)) as z:
  assert z.testzip() is None
  previous=json.loads(z.read('ACQUISITION_UNIVERSE_PRECOMMIT.json'));oldreceipt=json.loads(z.read('RUNNER_FINAL_RECEIPT.json'));oldsource=json.loads(z.read('SOURCE_RECEIPTS.json'))
 assert oldreceipt['error']['code']=='RAW_DECIMAL_LEXEME_REQUIRED' and oldreceipt['new_steps']==0,'REPAIR_BOUNDARY'
 proposals=previous['proposals'];allowed={{(x['date'],x['previous']) for x in cfg['acquisition_session_scope']}};exc={{(r['date'],r['code']) for r in cfg['exclusion_pairs']}}
 assert all((p['date'],p['previous']) in allowed and (p['date'],p['code']) not in exc and (p['previous'],p['code']) not in exc for p in proposals),'REPAIR_SCOPE'
 a.receipts.extend(oldsource);priorrequests=oldreceipt['provider_requests'];cfg['maxrequests']-=priorrequests
 save('REPAIR_METADATA_REUSE_RECEIPT.json',{{'artifact_id':{artifact_id},'artifact_SHA256':'{artifact_SHA}','original_run':36950498344,'prior_provider_requests':priorrequests,'metadata_reused':True,'proposal_identity_hash':hashlib.sha256(json.dumps(proposals,sort_keys=True).encode()).hexdigest(),'new_selection':0,'prior_frozen_steps':0,'source_receipts_carry_forward':len(oldsource)}})
'''
source=source[:start]+replacement+source[end:]
source=source.replace("mapped=map_rows(cur);norm=normalize80.generate(prev,mapped)","cur=[{**r,**{f:str(r[f]) for f in ['O','H','L','C']}} for r in cur];prev=[{**r,**{f:str(r[f]) for f in ['O','H','L','C']}} for r in prev]\n  mapped=map_rows(cur);norm=normalize80.generate(prev,mapped)")
source=source.replace("save('ACQUISITION_UNIVERSE_PRECOMMIT.json',{'at':a.now(),'proposals':proposals,'price_rows_read':0,'State_results_used':False,'after_price_refill':False})","save('ACQUISITION_UNIVERSE_PRECOMMIT.json',previous)")
source=source.replace("'provider_requests':a.requests,'new_steps':steps,'completed_pairs'","'provider_requests':a.requests,'provider_requests_cumulative':priorrequests+a.requests,'new_steps':steps,'completed_pairs'")
ast.parse(source);(T/'export_expansion.py').write_text(source)
archive=R/'EXPANSION_REPAIR_PAYLOAD.zip'
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(T.rglob('*')):
  if p.is_file() and '__pycache__' not in str(p):z.write(p,str(p.relative_to(T)))
(R/'EXPANSION_REPAIR_PAYLOAD.b64').write_text(base64.b64encode(archive.read_bytes()).decode()+'\n')
wf=(R/'state-nextstate-v2-20261002.yml').read_text();oldsha=sha(R/'EXPANSION_PAYLOAD.zip');wf=wf.replace(oldsha,sha(archive)).replace('JQUANTS_API_KEY: ${{ secrets.JQUANTS_API_KEY }}','JQUANTS_API_KEY: ${{ secrets.JQUANTS_API_KEY }}\n          GH_TOKEN: ${{ github.token }}').replace('  contents: read\n','  contents: read\n  actions: read\n')
(R/'state-nextstate-v2-repair.yml').write_text(wf)
(R/'TECHNICAL_REPAIR_RECEIPT.json').write_text(json.dumps({'issue':'In-memoryToken(str subclass) rejected by unchanged M0 positive exact type check; original serialized checkpoint used plainstr','repair':'Convert onlyO/H/L/C Token tostr without changing exact lexicalbytes before M0; Frozen kernel/profile/M0 source unchanged','prior_run_receipt':receipt,'metadata_restore_no_repeat_selection':True,'first_artifact_id':artifact_id,'first_artifact_SHA256':artifact_SHA,'semantics_changes':0,'precommit_changes':0,'max_Actions_runs_remains2':True,'provider_cumulative_cap_remains900':True,'payload_SHA256':sha(archive)},indent=2)+'\n')
print(json.dumps({'payload_bytes':archive.stat().st_size,'payload_SHA':sha(archive),'prior_requests':receipt['provider_requests']}))
