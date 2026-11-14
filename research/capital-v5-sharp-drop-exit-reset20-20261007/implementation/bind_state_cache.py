"""Project verified saved causal State prefixes; no State kernel run or RAW scan."""
from io_utils import *
import zipfile,collections

STATES=('RISE_STOP','RISE','SHARP_RISE','PULLBACK','RANGE','REBOUND','SHARP_DROP','DROP','DROP_STOP')
def project(key,day,buy,control,body,member,member_hash):
 frames=[];last=None;prefix=hashlib.sha256();count=0;gaps=[]
 for line in gzip.decompress(body).splitlines(keepends=True):
  raw=json.loads(line);t=raw['bar_end_minute']
  if t>control:break
  prefix.update(line);count+=1
  if t<=buy:continue
  gap=False
  if last is not None and t<=last:gap=True;gaps.append('NONMONOTONIC_CHECKPOINT')
  last=t;s=raw['state'];p=raw['path'];a=s['as_of'];token=raw['input']
  valid_order=(raw['watch_key']==s['case_id']==p['case_id']==key and a==t-540 and p['scheduled_t']==a and raw['assumed_available_at']==stamp(day,t) and p['bar_end']==raw['assumed_available_at'] and (token is None or token['known_at']<=a and token['t']<=a))
  if not valid_order:gap=True;gaps.append('IDENTITY_OR_TIMESTAMP_CONTRADICTION')
  primary=p['Primary_or_null'];observed=s['current_semantics_observed'] is True and p['current_semantics_observed'] is True
  usable=bool(valid_order and observed and s['observed_at']==s['as_of'] and p['quality']['numeric_status']=='ACCEPTED' and primary in STATES and raw['source_status']=='RAW_CLOSED_AT_ASSUMED_BAR_END' and s['activity']!='CARRIED_GAP' and s['basis']!='CARRIED_GAP')
  if primary is not None and primary not in STATES:gap=True;gaps.append('ENUM_NOT_FROZEN_STATE9')
  frames.append({'entry_id':key,'session':day,'checkpoint_minute':t,'Primary':primary if usable else None,'usable':usable,'evidence_gap':gap,'source_line_sha256':hashlib.sha256(line).hexdigest(),'source_member':member,'source_hash':member_hash,'source_available_at':raw['assumed_available_at'],'quality_reason':'OBSERVED_VALID' if usable else 'SOURCE_UNAVAILABLE:'+str(raw['source_unavailable_reason']) if raw['source_unavailable_reason'] else s['activity'] if s['activity'] in ['INITIALIZING','CARRIED_GAP'] else 'NO_VALID_OBSERVED_STATE:'+str(p['quality']['reason'] or p['quality']['numeric_status']),'historical_actual_known_at':raw['historical_actual_known_at']})
 return frames,{'entry_id':key,'member':member,'member_sha256':member_hash,'buy_fill_minute':buy,'control_intent_minute':control,'prefix_row_N':count,'prefix_sha256':prefix.hexdigest(),'holding_checkpoint_N':len(frames),'gaps':gaps}

def run():
 target=PRI/'immutable/STATE_PREFIX_CACHE.jsonl.gz'
 if target.exists():
  print('State cache already materialized; reuse only');return
 stream=rows(ROOT/'inputs/v5/candidate_stream');books={r['entry_id']:r for r in rows(ROOT/'inputs/v5/books')}
 fixtures={r['entry_id']:r for r in json.loads((SHARP/'parent/private/ENTRY_CONTROL_SOURCE_ROWS.json').read_bytes())}
 identities={r['entry_id']:{'entry_id':r['entry_id'],'session':r['session'],'buy':r['entry_minute'],'control':min(books[r['entry_id']]['frozen_exit']['exit_intent']['minute'],920) if books[r['entry_id']]['frozen_exit']['exit_intent'] else 920} for r in stream}
 for key,r in fixtures.items():
  if key in identities:assert identities[key]['buy']==r['buy_fill_minute'] and identities[key]['control']==r['control_intent_minute']
  else:identities[key]={'entry_id':key,'session':r['session'],'buy':r['buy_fill_minute'],'control':r['control_intent_minute']}
 archive=ROOT/'inputs/STATE9_V2_FROZEN_TRACE_ARCHIVE.zip';bind=json.loads((ROOT/'inputs/STATE9_TRACE_ARCHIVE_BINDING.json').read_text())
 cache=[];lineages=[]
 with zipfile.ZipFile(archive) as z:
  components=bind['manifest']['components']
  for key,r in sorted(identities.items()):
   member=bind['trace_members'].get(key)
   if member is None:
    frames=[{'entry_id':key,'session':r['session'],'checkpoint_minute':r['buy']+1,'Primary':None,'usable':False,'evidence_gap':True,'reason':'SAVED_TRACE_MEMBER_MISSING'}]
    lineage={'entry_id':key,'gaps':['SAVED_TRACE_MEMBER_MISSING']}
   else:
    cp=components[member];body=z.read(member)
    assert len(body)==cp['bytes'] and hashlib.sha256(body).hexdigest()==cp['sha256'],key
    frames,lineage=project(key,r['session'],r['buy'],r['control'],body,member,cp['sha256'])
   cache.append({'entry_id':key,'session':r['session'],'buy_fill_minute':r['buy'],'control_intent_minute':r['control'],'frames':frames});lineages.append(lineage)
 gzsave(target,cache);save(PRI/'immutable/STATE_PREFIX_LINEAGE.json',lineages)
 save(PUB/'STATE_CACHE_BINDING.json',{'status':'VERIFIED_SAVED_TRACE_CACHE','candidate_stream_N':len(stream),'candidate_sessions_N':len({r['session'] for r in stream}),'cached_unique_ID_N':len(cache),'prior_fixture_population_N':len(fixtures),'State_kernel_run_N':0,'source_archive_pin':pin(archive),'cache_pin':pin(target),'prefix_lineage_pin':pin(PRI/'immutable/STATE_PREFIX_LINEAGE.json'),'EVIDENCE_GAP_ID_N':sum(bool(r['gaps']) for r in lineages),'input_prefix_only_before_Control_intent':True,'portfolio_state_shared':False,'actual_receive_time':'UNKNOWN','authority':'S4 exact saved extraction semantics; native Capital first-fill/control clock under S2/S5'})
 print(json.dumps({'State_cache_ID_N':len(cache),'candidate_N':len(stream),'evidence_gaps':sum(bool(r['gaps']) for r in lineages)}))
if __name__=='__main__':run()
