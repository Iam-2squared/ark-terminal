"""Runner-only exact input acquisition. Frozen State9 code is never changed here."""
from pathlib import Path
from datetime import datetime,timezone
from decimal import Decimal
import csv,hashlib,json,os,re,shutil,subprocess,sys,time,urllib.request,urllib.error

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
sys.path.insert(0,str(REPO))
from scripts import phase57_expansion_data as existing
CFG=json.loads((HERE/'config.json').read_text())
RAW=Path(os.environ['STATE9_AUDIT_RAW']);OUT=Path(os.environ['STATE9_AUDIT_OUT'])
RAW.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
PRIVATE=RAW/'private';PRIVATE.mkdir(exist_ok=True)
receipts=[];requests=0;tokens=0;minute_rows=0;master_rows=0;action_rows=0
class Token(str):pass
GRAM=re.compile(r'-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?',re.ASCII)
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,v):
 p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def parse(data):
 return json.loads(data,parse_int=Token,parse_float=Token,parse_constant=lambda _: (_ for _ in ()).throw(ValueError('NON_FINITE_JSON')))
def now():return datetime.now(timezone.utc).isoformat()
def authorize(day,kind):
 assert day in CFG['authorized_days'] and day not in CFG['blocked_days'],'PROTECTED_BOUNDARY'
 assert kind in ('master','daily','minute'),'ENDPOINT_BOUNDARY'
def fetch(day,kind,code=None):
 global requests,tokens,minute_rows,master_rows,action_rows
 authorize(day,kind)
 endpoint='equities/master' if kind=='master' else 'equities/bars/'+kind
 target=RAW/'pages'/day/(code or 'MASTER')/kind;target.mkdir(parents=True,exist_ok=True)
 cursor=None;seen=set();rows=[];scope={'date':day}
 if code is not None:scope['code']=code
 opener=urllib.request.build_opener(existing.NoRedirect())
 for page in range(1,31):
  query=dict(scope)
  if cursor:query['pagination_key']=cursor
  from urllib.parse import urlencode
  time.sleep(2.6);requests+=1
  req=urllib.request.Request('https://api.jquants.com/v2/'+endpoint+'?'+urlencode(query),headers={'x-api-key':os.environ['JQUANTS_API_KEY']})
  try:
   with opener.open(req,timeout=120) as response:data=response.read();status=response.status
  except urllib.error.HTTPError as e:
   receipts.append({'endpoint':'/v2/'+endpoint,'scope':scope,'page':page,'request_at':now(),'HTTP_status':e.code,'response_body_not_logged':True})
   raise RuntimeError('PROVIDER_HTTP_'+str(e.code)) from None
  data.decode('utf-8');doc=parse(data);original=doc['data']
  assert isinstance(original,list),'SCHEMA_DATA_NOT_LIST'
  name=target/f'page_{page:03d}.json';name.write_bytes(data)
  for n,row in enumerate(original):
   if kind!='master':assert row.get('Date')==day,'CROSS_DATE'
   if code is not None:assert row.get('Code')==code,'CROSS_CODE'
   row['_source']={'response_SHA256':sha(data),'page':page,'row_ordinal':n,'endpoint':'/v2/'+endpoint,'requested_date':day}
   if kind=='minute':
    for k in ('O','H','L','C'):
     assert isinstance(row.get(k),Token) and GRAM.fullmatch(row[k]),'EXACT_TOKEN_MISSING'
     assert Decimal(row[k]).is_finite(),'NONFINITE_PRICE'
     tokens+=1
    minute_rows+=1
   elif kind=='master':master_rows+=1
   else:action_rows+=1
  # Daily OHLC/AdjOHLC are not used as observations or classifier inputs.
  if kind=='daily':
   original=[{k:v for k,v in row.items() if k in ('Date','Code','AdjFactor','ExRT','_source')} for row in original]
  rows.extend(original)
  receipts.append({'endpoint':'/v2/'+endpoint,'scope':scope,'page':page,'received_at':now(),
   'HTTP_status':status,'raw_response_SHA256':sha(data),'raw_bytes':len(data),'row_N':len(original),
   'schema_fields':sorted(k for k in (doc['data'][0] if doc['data'] else {}) if k!='_source'),
   'numeric_mode':'original JSON number lexemes; no binary64','actual_historical_known_at':None})
  nxt=doc.get('pagination_key')
  if not nxt:return rows
  assert isinstance(nxt,str) and nxt not in seen,'PAGINATION_CYCLE'
  seen.add(nxt);cursor=nxt
 raise RuntimeError('PAGINATION_LIMIT_EXISTING_30')
def compatible(a,b):
 return all(a.get(k) is not None and a.get(k)==b.get(k) for k in ('Code','Mkt','CoName','ProdCat'))
def good(rows):
 if not rows:return False,'NO_MINUTE_ROWS'
 seen=set()
 for row in rows:
  if not re.fullmatch(r'\d\d:\d\d',row.get('Time','')):return False,'UNKNOWN_TIME'
  if row['Time'] in seen:return False,'DUPLICATE_SOURCE_TIME'
  seen.add(row['Time'])
  p={k:Decimal(row[k]) for k in ('O','H','L','C')}
  if min(p.values())<=0:return False,'NONPOSITIVE_PRICE'
  if not p['L']<=min(p['O'],p['C'])<=max(p['O'],p['C'])<=p['H']:return False,'INVALID_OHLC'
 return True,None
def adjacency(rows):
 t={int(r['Time'][:2])*60+int(r['Time'][3:]):r for r in rows}
 return sum(1 for m in t if m-1 in t and ((540<m<690) or (750<m<(925 if rows[0]['Date']>='2024-11-05' else 900))))

status='ACQUIRING_G1_INPUTS';reason=None;eligible=[];proposals=[];scopes=[];skip=[]
binding=bool(os.environ.get('JQUANTS_API_KEY'))
try:
 if not binding:raise RuntimeError('ACTIONS_JQUANTS_BINDING_UNAVAILABLE')
 exclusions={(x['date'],x['code']) for x in CFG['exclusion_pairs']}
 used=set();cache={}
 for link in CFG['acquisition_session_scope']:
  day,prev=link['date'],link['previous']
  for d in (day,prev):
   if d not in cache:cache[d]=fetch(d,'master')
  current={r['Code']:r for r in cache[day] if type(r.get('Code')) is str}
  previous={r['Code']:r for r in cache[prev] if type(r.get('Code')) is str}
  pool=[]
  for code,row in current.items():
   if code not in previous or not compatible(row,previous[code]):continue
   if (day,code) in exclusions or (prev,code) in exclusions:continue
   key=row['Mkt']+'|'+code
   if key in used:continue
   # Acquisition universe is pre-fixed metadata-only; this is not the case draw.
   metadata_hash=sha(json.dumps({k:v for k,v in row.items() if k!='_source'},sort_keys=True,separators=(',',':')).encode())
   pool.append((metadata_hash,code,row))
  n=0
  for mh,code,row in sorted(pool):
   if n>=3:break
   factors=[]
   for d in (day,prev):factors.extend(fetch(d,'daily',code))
   if len(factors)!=2 or any('ExRT' not in f or not isinstance(f.get('AdjFactor'),Token) or f['ExRT'] is not None or Decimal(f['AdjFactor'])!=1 for f in factors):
    skip.append({'date':day,'code':code,'reason':'ACTION_FACTOR_UNKNOWN_OR_DISCONTINUITY'});continue
   key=row['Mkt']+'|'+code;used.add(key);n+=1
   proposals.append({'date':day,'previous':prev,'code':code,'market':row['Mkt'],'acquisition_metadata_hash':mh,
    'master_current_source':row['_source'],'master_previous_source':previous[code]['_source'],'factor_sources':[f['_source'] for f in factors],
    'raw_basis':'UNADJUSTED','unit':'JPY','audit_key':day+'|'+key,'reuse_key':key})
  scopes.append({'date':day,'previous':prev,'proposed_security_N':n,'pool_metadata_N':len(pool)})
 assert len(proposals)<=36,'SYMBOL_SESSION_CAP'
 # Freeze requested identities before reading minute prices, without drawing cases.
 write(PRIVATE/'ACQUISITION_UNIVERSE_PRECOMMIT.json',{'created_at':now(),'proposals':proposals,'sample_draw':0,'State_results_used':False,'after_price_refill':False})
 for p in proposals:
  a=fetch(p['date'],'minute',p['code']);b=fetch(p['previous'],'minute',p['code'])
  ga,ra=good(a);gb,rb=good(b)
  if not ga or not gb or adjacency(b)==0:
   skip.append({'date':p['date'],'code':p['code'],'reason':ra or rb or 'NO_PREVIOUS_ADJACENT_RETURNS'});continue
  assert minute_rows+CFG['prior_price_rows']<=100000,'MARKET_PRICE_ROW_CAP'
  p['current_minute_rows']=a;p['previous_minute_rows']=b
  p['source_identity']=sha(json.dumps([r['_source'] for r in a+b],sort_keys=True).encode())
  p['source_vintage']=now()
  p['metadata_hash']=sha(json.dumps({k:v for k,v in p.items() if not k.endswith('minute_rows')},sort_keys=True).encode())
  p['authority_verified']=True;p['state_unexposed_verified']=True
  p['session_id']='JPX:'+p['date'];p['previous_session_id']='JPX:'+p['previous'];p['security_id']=p['reuse_key']
  p['verified_scheduled_cutoffs']=['10:00','11:15','14:00']
  eligible.append(p)
 write(PRIVATE/'ELIGIBLE_INPUTS.json',eligible)
 counts={}
 for p in eligible:counts[p['date']]=counts.get(p['date'],0)+1
 sufficient=sum(n>=3 for n in counts.values())>0
 status='G1_INPUTS_ACQUIRED_PENDING_FULL_GATE' if sufficient else 'BLOCKED_ELIGIBLE_POPULATION_UNAVAILABLE'
 if CFG.get('stage')=='FULL' and sufficient:
  from pipeline import complete
  complete(CFG,PRIVATE,OUT,eligible,receipts)
except Exception as e:
 status='BLOCKED_'+str(e) if str(e).startswith(('ACTIONS_','PROVIDER_')) else 'G1_INPUT_ACQUISITION_FAILED'
 reason={'type':type(e).__name__,'reason_code':str(e) if re.fullmatch('[A-Z0-9_]+',str(e) or '') else 'SANITIZED_EXCEPTION_NO_RAW_OR_SECRET_LOG'}
finally:
 # Private raw and mappings never appear in a plaintext artifact or log.
 write(PRIVATE/'SOURCE_RECEIPTS.json',receipts)
 write(PRIVATE/'SKIPS.json',skip)
 checkpoint=None
 if binding and any(RAW.iterdir()):
  try:
   encrypted=OUT/'runner-checkpoint.tar.gz.enc'
   existing.encrypt(RAW,encrypted)
   checkpoint={'encrypted_file':encrypted.name,'encrypted_bytes':encrypted.stat().st_size,'encrypted_SHA256':hashlib.sha256(encrypted.read_bytes()).hexdigest(),'existing_method':'OpenSSL aes-256-cbc pbkdf2 200000 env:JQUANTS_API_KEY','plaintext_publication':False}
  except Exception:checkpoint={'status':'ENCRYPT_FAILED_NO_SECRET_OR_RAW_LOG'}
 public_receipts=[{k:v for k,v in r.items() if k not in ('scope',)} for r in receipts]
 write(OUT/'ACQUISITION_RECEIPT.json',{'cycle':CFG['cycle'],'created_at':now(),'status':status,'error':reason,
  'stage':CFG.get('stage'),'sample_draw':0,'JQUANTS_API_KEY_binding_available_in_Actions':binding,
  'provider_requests':requests,'minute_rows':minute_rows,'master_rows':master_rows,'action_metadata_rows':action_rows,
  'exact_finite_decimal_tokens':tokens,'raw_response_hash_N':sum('raw_response_SHA256' in x for x in receipts),
  'raw_response_bytes':sum(x.get('raw_bytes',0) for x in receipts),'receipts':public_receipts,
  'acquisition_current_sessions_N':len(scopes),'acquisition_current_previous_days_N':len({d for x in scopes for d in (x['date'],x['previous'])}),
  'proposed_security_N':len(proposals),'eligible_raw_records_N':len(eligible),'G1_PASS_declared':False,
  'checkpoint':checkpoint,'old44_identity_count':CFG['old44_identity_count'],'State_exclusion_pairs':667,
  'RC2_M0_profile_changed':False,'classifier_steps':0,'Future_classifier_input':0,
  'protected_requests':0,'Entry_EXIT_profit_externalAI_orders':0})
 shutil.rmtree(RAW,ignore_errors=True)
 print(json.dumps({'status':status,'provider_requests':requests,'binding_available':binding,'sample_draw':0,'plaintext_raw_purged':not RAW.exists()}),flush=True)
 if reason:sys.exit(1)
