from io_utils import *
import sys,tarfile,io,lzma,shutil

def pack(stage):
 window=stage if stage.startswith('W') or stage=='CHAIN38' else None
 if window:
  from analyze import analyze_primary
  if window!='CHAIN38':analyze_primary()
  members=[]
  for p in sorted((PRI/'runs'/window).rglob('*')):
   if p.is_file():members.append((p.relative_to(ROOT).as_posix(),p.read_bytes()))
  payload=io.BytesIO()
  with tarfile.open(fileobj=payload,mode='w',format=tarfile.PAX_FORMAT) as t:
   for name,b in members:
    info=tarfile.TarInfo(name);info.size=len(b);info.mtime=0;info.uid=info.gid=0;info.mode=0o644;t.addfile(info,io.BytesIO(b))
  p=PRI/(window+'_PORTFOLIO_CHECKPOINT.tar.xz');atomic(p,lzma.compress(payload.getvalue(),preset=6))
  save(PRI/(window+'_PACKAGE_MANIFEST.json'),{'window_id':window,'archive':p.name,**pin(p),'members':[{'path':n,'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest()} for n,b in members],'input_reference_manifest':'INITIAL_INPUT_MANIFEST.json','shared_State_cache':'STATE_CACHE_BINDING.json','row_level_visibility':'PRIVATE_ONLY'})
 for p in ROOT.glob('*.py'):
  if p.name not in ['initialize.py','materialize.py']:
   dest=PUB/'implementation'/p.name;dest.parent.mkdir(exist_ok=True);shutil.copyfile(p,dest)
 save(PRI/'TECHNICAL_AND_EXECUTION_COUNTERS.json',{'formal_C_paths_started':sum(p.name=='STARTED.json' and p.parent.name=='C' for p in (PRI/'runs').glob('*/*/STARTED.json')),'formal_E_paths_started':sum(p.name=='STARTED.json' and p.parent.name=='E' for p in (PRI/'runs').glob('*/*/STARTED.json')),'technical_repair_cycles':sum(json.loads(l).get('cycle',0)>0 for l in (PRI/'TECHNICAL_REPAIR_LEDGER.jsonl').read_text().splitlines()),'new_fit':0,'new_inference':0,'new_State_kernel':0,'threshold_search':0,'provider_requests':0,'protected_opens':0,'orders':0,'previous_72_repair_history_preserved':'Pinned S4 carrier, parent5cycles and subsequent72 repair ledger; separate budget.'})
 meta={}
 large=[]
 for p in sorted(PRI.glob('*.json')):
  if p.stat().st_size>600000:
   b=p.read_bytes();dest=p.with_suffix(p.suffix+'.gz');atomic(dest,gzip.compress(b,mtime=0))
   large.append({'original_local':p.name,'exact_uncompressed':pin(p),'published_carrier':dest.name,'carrier_pin':pin(dest),'original_large_GET':'UNVERIFIED_EXTRA_DEBUG_COPY; use exact gzip carrier'})
 if large:save(PRI/'LARGE_LOG_CARRIER_MANIFEST.json',{'files':large})
 segments=[]
 for p in sorted(PRI.iterdir()):
  if p.is_file() and p.stat().st_size>900000 and p.suffix!='.json':
   b=p.read_bytes();parts=[]
   for i,start in enumerate(range(0,len(b),600000)):
    dest=PRI/(p.name+'.part-%03d.bin'%i);atomic(dest,b[start:start+600000]);parts.append({'index':i,'file':dest.name,**pin(dest)})
   segments.append({'archive':p.name,**pin(p),'parts':parts,'serialization':'concatenate numbered raw binary parts in index order'})
 if segments:save(PRI/'SEGMENTED_CARRIER_MANIFEST.json',{'carriers':segments})
 for side,root in [('public',PUB),('private',PRI)]:
  files=[]
  for p in sorted(root.rglob('*')):
   if p.is_file() and (side=='public' or len(p.relative_to(root).parts)==1) and not (side=='private' and (p.suffix=='.json' and p.stat().st_size>600000 or p.stat().st_size>900000)):files.append({'relative':p.relative_to(root).as_posix(),'local':str(p),'bytes':p.stat().st_size,**pin(p)})
  meta[side]=files
 save(ROOT/'PUBLICATION_PAYLOAD_METADATA.json',{'stage':stage,'files':meta})
 print(json.dumps({'stage':stage,'files':meta}))
if __name__=='__main__':pack(sys.argv[1])
