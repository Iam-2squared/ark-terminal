"""G1 limited to the existing checkpoint, no provider/network calls."""
from pathlib import Path
from decimal import Decimal
import hashlib,json,re
class Lex(str):pass
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parsed(p):return json.loads(p.read_bytes(),parse_int=Lex,parse_float=Lex,parse_constant=lambda _:(_ for _ in ()).throw(ValueError('NONFINITE_JSON')))
def minute_number(s):
 if type(s) is not str or re.fullmatch(r'[0-2][0-9]:[0-5][0-9]',s) is None:raise ValueError('CLOCK_UNKNOWN')
 return int(s[:2])*60+int(s[3:])
def scheduled_minutes(day):
 last=925 if day>='2024-11-05' else 900
 # Source Time is the start of the source one-minute aggregation, including
 # terminal-auction buckets. Keep them separate, do not merge their OHLC.
 return list(range(541,691))+[691]+list(range(751,last+1))+[931 if last==925 else 901]
def map_rows(rows):
 ordered=sorted(rows,key=lambda r:r['Time']);first_am=next((r['Time'] for r in ordered if minute_number(r['Time'])<690),None)
 first_pm=next((r['Time'] for r in ordered if 750<=minute_number(r['Time'])<(925 if r['Date']>='2024-11-05' else 900)),None)
 out=[]
 for r in ordered:
  m=minute_number(r['Time']);last=930 if r['Date']>='2024-11-05' else 900
  terminal=m in (690,last)
  if not terminal and not (540<=m<690 or 750<=m<(925 if last==930 else 900)):raise ValueError('UNKNOWN_DATED_SOURCE_INTERVAL')
  mixed=r['Time'] in (first_am,first_pm)
  auction='TERMINAL_AUCTION_MINUTE' if terminal else 'OPENING_MIXED_MINUTE' if mixed else 'CONTINUOUS'
  end=m+1
  if end not in scheduled_minutes(r['Date']):raise ValueError('UNSCHEDULED_BAR_END')
  out.append({**r,'bar_end_minute':end,'bar_end':f'{end//60:02d}:{end%60:02d}','t':end-540,
   'source':'JQUANTS_V2_EQUITIES_BARS_MINUTE','auction':auction,'raw_known_at':'UNKNOWN','assumed_available_at':f'{end//60:02d}:{end%60:02d}'})
 return out
def verify(raw,cfg):
 private=raw/'private';receipts=json.loads((private/'SOURCE_RECEIPTS.json').read_text());universe=json.loads((private/'ACQUISITION_UNIVERSE_PRECOMMIT.json').read_text())
 candidates=json.loads((private/'ELIGIBLE_INPUTS.json').read_text());exclusions={(x['date'],x['code']) for x in cfg['exclusion_pairs']}
 pages={};hash_records=[]
 for r in receipts:
  assert r['HTTP_status']==200 and r['scope']['date'] in cfg['authorized_days'] and r['scope']['date'] not in cfg['blocked_days'],'AUTH_SCOPE'
  day=r['scope']['date'];code=r['scope'].get('code','MASTER');kind=r['endpoint'].rsplit('/',1)[1]
  path=raw/'pages'/day/code/kind/f"page_{r['page']:03d}.json"
  assert digest(path)==r['raw_response_SHA256'],'RAW_PAGE_HASH'
  assert path.stat().st_size==r['raw_bytes'],'RAW_PAGE_BYTES'
  pages[r['raw_response_SHA256']]=path;hash_records.append({'SHA256':digest(path),'bytes':path.stat().st_size,'endpoint':r['endpoint'],'rows':r['row_N']})
  if kind=='minute':assert universe['created_at']<=r['received_at'],'PRICE_BEFORE_PRECOMMIT'
 assert len(receipts)==168 and len(candidates)==25 and len(universe['proposals'])==36,'ACQUIRED_DENOMINATOR'
 assert universe['sample_draw']==0 and universe['State_results_used'] is False and universe['after_price_refill'] is False
 source_cache={};eligible=[];rejects=[]
 def original(s):
  key=s['response_SHA256']
  if key not in source_cache:source_cache[key]=parsed(pages[key])['data']
  return source_cache[key][s['row_ordinal']]
 def price_row(row,day,code):
  original_row=original(row['_source'])
  assert original_row['Date']==day and original_row['Code']==code and original_row['Time']==row['Time'],'RAW_IDENTITY'
  for field in ['O','H','L','C']:
   v=original_row[field]
   assert isinstance(v,Lex) and re.fullmatch(r'-?(0|[1-9][0-9]*)(\.[0-9]+)?([eE][+-]?[0-9]+)?',v),'EXACT_NUMBER_TOKEN'
   assert str(v)==row[field] and Decimal(v).is_finite() and Decimal(v)>0,'RAW_LEXEME_OR_POSITIVITY'
  o,h,l,c=[Decimal(row[k]) for k in ['O','H','L','C']]
  assert l<=min(o,c)<=max(o,c)<=h,'RAW_OHLC'
 for p in candidates:
  try:
   day,prev,code=p['date'],p['previous'],p['code'];assert (day,code) not in exclusions and (prev,code) not in exclusions,'STATE_EXPOSURE'
   assert day in cfg['authorized_days'] and prev in cfg['authorized_days'] and prev<day,'DEVELOPMENT_LINK'
   assert any(x['date']==day and x['previous']==prev for x in cfg['acquisition_session_scope']),'PRECOMMITTED_SESSION'
   assert any(x['audit_key']==p['audit_key'] for x in universe['proposals']),'PRECOMMITTED_SECURITY'
   cur=original(p['master_current_source']);old=original(p['master_previous_source'])
   assert all(cur.get(k) is not None and cur.get(k)==old.get(k) for k in ['Code','Mkt','CoName','ProdCat']),'DATED_MASTER_CONTINUITY'
   assert cur['Code']==code and cur['Mkt']==p['market'] and isinstance(cur['Mkt'],str) and cur['Mkt'],'DATED_MARKET'
   assert p['audit_key']==day+'|'+p['market']+'|'+code and p['reuse_key']==p['market']+'|'+code,'AUDIT_IDENTITY'
   assert p['raw_basis']=='UNADJUSTED' and p['unit']=='JPY','PRICE_BASIS'
   assert len(p['factor_sources'])==2,'FACTOR_PAIR'
   for source in p['factor_sources']:
    factor=original(source);assert factor['Code']==code and factor['Date'] in [day,prev],'FACTOR_IDENTITY'
    assert isinstance(factor.get('AdjFactor'),Lex) and Decimal(factor['AdjFactor'])==1 and 'ExRT' in factor and factor['ExRT'] is None,'ACTION_CONTINUITY'
   for name,d in [('current_minute_rows',day),('previous_minute_rows',prev)]:
    rows=p[name];assert rows,'NO_RAW_ROWS'
    for r in rows:price_row(r,d,code)
    mapped=map_rows(rows);assert len({x['t'] for x in mapped})==len(mapped),'DUPLICATE_CANONICAL_CLOCK'
    assert len(mapped)<=512,'SLOTS_CAP'
   # Existence only, no U/State result or scale-dependent admission.
   previous=map_rows(p['previous_minute_rows']);pairs=sum(1 for a,b in zip(previous,previous[1:]) if b['t']==a['t']+1 and a['auction']==b['auction']=='CONTINUOUS')
   assert pairs>0,'U_UNAVAILABLE'
   assert p['authority_verified'] is True and p['state_unexposed_verified'] is True
   assert set(p['verified_scheduled_cutoffs'])=={'10:00','11:15','14:00'}
   assert all(minute_number(cutoff) in scheduled_minutes(day) for cutoff in p['verified_scheduled_cutoffs']),'DATED_CALENDAR_CUTOFF'
   eligible.append(p)
  except (AssertionError,ValueError,KeyError) as e:
   rejects.append({'audit_key':p.get('audit_key'),'reason':str(e) if re.fullmatch('[A-Z0-9_]+',str(e)) else type(e).__name__})
 assert len({p['reuse_key'] for p in eligible})==len(eligible),'SECURITY_REUSE_IN_POOL'
 counts={}
 for p in eligible:counts[p['session_id']]=counts.get(p['session_id'],0)+1
 return eligible,{'pass':any(n>=3 for n in counts.values()),'eligible_population_N':len(eligible),'eligible_session_counts':counts,
  'excluded_after_quality_gate':rejects,'acquisition_proposals_N':36,'acquisition_eligible_raw_N':25,'raw_hashes':hash_records,
  'raw_hashes_verified_N':len(hash_records),'exact_raw_verified':True,'G1_scope':'Available precommitted Development eligible population; not all-market certification.',
  'old44_pairs_in_667':cfg['old44_pairs_in_667_N'],'State_exclusion_pairs':667,'sample_draws':0,'provider_additional_requests':0,
  'calendar_basis':'Inherited exact Development previous-session ledger plus dated source intervals; no extra calendar requests.',
  'AUDIT_identity_not_production_stable_identity':True,'actual_historical_known_at':'UNKNOWN'}
