"""V2's unchanged metadata-first selector, with explicit per-link failures."""
import json,hashlib,os
import acquisition_base as a
def safe(ex):
 s=str(ex)
 return s if s and all(c.isupper() or c.isdigit() or c=='_' for c in s) else 'SANITIZED_TECHNICAL_EXCEPTION'
def build(H,save):
 cfg=a.CFG;pre=json.loads((H/'ACQUISITION_EXPANSION_PRECOMMIT.json').read_text())
 assert cfg['acquisition_session_scope']==pre['date_links'],'SCOPE_OR_EXPOSURE_BOUNDARY'
 v4=json.loads((H/'PREDICTIVENESS_V4_PRECOMMIT.json').read_text())
 for n,h in v4['hashes'].items():
  assert hashlib.sha256((H/n).read_bytes()).hexdigest()==h,'PRECOMMIT_CHANGED'
 assert bool(os.environ.get('JQUANTS_API_KEY')),'BINDING_UNAVAILABLE'
 exc={(r['date'],r['code']) for r in cfg['exclusion_pairs']};cache={};failed={};proposals=[];failures=[];links=[];stopped=None
 for ordinal,link in enumerate(pre['date_links'],1):
  d,p=link['date'],link['previous'];record={'link_ordinal':ordinal,'date':d,'previous':p,'selected_proposal_N':0,'replacement_after_raw':0}
  links.append(record)
  if stopped:
   record.update(status='PROVIDER_FAILURE',reason=stopped,request_attempted=False);continue
  try:
   for day in [d,p]:
    if day in failed:raise RuntimeError('DATE_MASTER_UNAVAILABLE')
    if day not in cache:
     try:cache[day]=a.fetch(day,'master')
     except Exception as ex:failed[day]=safe(ex);raise
   if not cache[d] or not cache[p]:raise RuntimeError('DATE_MASTER_UNAVAILABLE')
   cur={r['Code']:r for r in cache[d] if isinstance(r.get('Code'),str)};old={r['Code']:r for r in cache[p] if isinstance(r.get('Code'),str)};pool=[]
   for c,r in cur.items():
    if c not in old or not a.compatible(r,old[c]) or (d,c) in exc or (p,c) in exc:continue
    mh=hashlib.sha256(json.dumps({k:v for k,v in r.items() if k!='_source'},sort_keys=True,separators=(',',':')).encode()).hexdigest();pool.append((mh,c,r))
   record['compatible_metadata_N']=len(pool)
   for mh,c,r in sorted(pool):
    if record['selected_proposal_N']==3:break
    try:fac=a.fetch(d,'daily',c)+a.fetch(p,'daily',c)
    except Exception as ex:
     code=safe(ex);failures.append({'date':d,'previous':p,'code':c,'security_id':r['Mkt']+'|'+c,'status':'PROVIDER_FAILURE','reason':code,'stage':'FACTOR_METADATA','replacement_after_raw':0})
     if code in ['PROVIDER_HTTP_401','PROVIDER_HTTP_403','PROVIDER_HTTP_429','PROVIDER_REQUEST_CAP']:stopped=code;break
     continue
    if len(fac)!=2 or any('ExRT' not in f or not isinstance(f.get('AdjFactor'),a.Token) or f['ExRT'] is not None or a.Decimal(f['AdjFactor'])!=1 for f in fac):
     failures.append({'date':d,'previous':p,'code':c,'security_id':r['Mkt']+'|'+c,'status':'FACTOR_UNAVAILABLE','reason':'ACTION_UNAVAILABLE','stage':'FACTOR_METADATA','replacement_after_raw':0});continue
    proposals.append({'date':d,'previous':p,'code':c,'market':r['Mkt'],'security_id':r['Mkt']+'|'+c,'session_id':'JPX:'+d,'previous_session_id':'JPX:'+p,'audit_key':d+'|'+r['Mkt']+'|'+c,'master_current_source':r['_source'],'master_previous_source':old[c]['_source'],'factor_sources':[f['_source'] for f in fac],'acquisition_metadata_hash':mh,'raw_basis':'UNADJUSTED','unit':'JPY','link_ordinal':ordinal});record['selected_proposal_N']+=1
   record.update(status='METADATA_SELECTION_COMPLETE' if not stopped else 'PROVIDER_FAILURE',reason=stopped if stopped else 'LESS_THAN_THREE_FACTOR_COMPATIBLE' if record['selected_proposal_N']<3 else None)
  except Exception as ex:
   code=safe(ex)
   if code in ['SCOPE_OR_EXPOSURE_BOUNDARY','PROTECTED_BOUNDARY','CROSS_DATE','CROSS_CODE','PRECOMMIT_CHANGED']:raise
   record.update(status='PROVIDER_FAILURE' if code.startswith('PROVIDER_') else 'DATE_MASTER_UNAVAILABLE',reason=code,request_attempted=True)
   if code in ['PROVIDER_HTTP_401','PROVIDER_HTTP_403','PROVIDER_HTTP_429','PROVIDER_REQUEST_CAP']:stopped=code
  save('METADATA_DATE_LEDGER.json',links);save('METADATA_UNAVAILABLE.json',failures)
  print(json.dumps({'metadata_link':ordinal,'fixed_links':len(pre['date_links']),'selected':len(proposals),'requests':a.requests,'minute_requests':0,'labels_created':0}),flush=True)
 assert len(proposals)<=pre['proposal_cap'],'PROPOSAL_CAP'
 universe={'at':a.now(),'proposals':proposals,'fixed_date_links':pre['date_links'],'metadata_date_ledger':links,'factor_unavailable':failures,'minute_price_rows_read':0,'State_results_used':False,'after_price_refill':False,'provider_stopped':stopped,'provider_requests_before_minute':a.requests,'V4_precommit_SHA256':pre['V4_precommit_SHA256']}
 save('METADATA_DATE_LEDGER.json',links);save('METADATA_UNAVAILABLE.json',failures);save('ACQUISITION_UNIVERSE_PRECOMMIT.json',universe)
 return universe
