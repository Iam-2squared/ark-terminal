"""Source-only audit before any revised outcome measurement. No price interpolation."""
import argparse,collections,json
from pathlib import Path
from scripts import phase57_behavior_intelligence as b
from scripts import phase57_expansion_data as a

def audit(cache,output):
 p=a.plan();days=p['intradayDevelopment'];assert len(days)==144
 old={x['sessionDate'] for x in b.read(b.ROOT/b.LEDGER)['new']};inventory=[]
 for day in days:
  row={'session':day,'lineage':'REUSE' if day in p['reuseMinuteDates'] else 'EXPANSION','savedFrozenCandidates':day in old,'sources':{},'minuteTimeCounts':{},'validMinuteTimeCounts':{},'sourceRequests':[]}
  for kind in ['daily','master','minute']:
   a.authorize(day,kind,p);f=Path(cache)/day/(kind+'-pages.json')
   if not f.exists():row['sources'][kind]={'status':'MISSING'};continue
   rows,receipt=a.base.pages(f);assert all(x['Date']==day for x in rows)
   row['sources'][kind]={'status':'AVAILABLE','rows':len(rows),'sha256':b.sha(f)}
   if kind=='minute':
    keys=[(x['Code'],x['Time']) for x in rows];assert len(keys)==len(set(keys)),'DUPLICATE_MINUTES'
    times=collections.Counter(x['Time'] for x in rows);valid=collections.Counter(x['Time'] for x in rows if b.v.valid(x))
    row['minuteTimeCounts']=dict(sorted(times.items()));row['validMinuteTimeCounts']=dict(sorted(valid.items()))
    row['lateSource']={t:{'rows':times[t],'validOHLCV':valid[t]} for t in ['15:24:00','15:25:00','15:26:00','15:27:00','15:28:00','15:29:00','15:30:00']}
    # Keep request/response provenance only, never credentials or raw market rows.
    for page in b.read(f):row['sourceRequests'].append({'request':page.get('request'),'responseSha256':page.get('responseSha256'),'acquiredAt':page.get('acquiredAt')})
  inventory.append(row);print(json.dumps({'audit':day,'lateSource':row.get('lateSource'),'sourceStatus':{k:v['status'] for k,v in row['sources'].items()}}),flush=True)
 out=Path(output);out.mkdir(parents=True,exist_ok=True)
 summary={'inputSessions':len(days),'savedCandidateSessions':len(set(days)&old),'requireFrozenInference':len(set(days)-old),'allMinuteAvailable':all(x['sources']['minute']['status']=='AVAILABLE' for x in inventory),'commonHoldoutOpened':0,'sealedOpened':0,'newProviderRequests':0,'safety':b.SAFETY,'splitSHA256':b.sha(a.B/'04_session_split_manifest.json'),'inputHead':__import__('subprocess').check_output(['git','rev-parse','HEAD'],text=True).strip()}
 b.write(out/'session-inventory.json',inventory);b.write(out/'source-audit-summary.json',summary)
 b.write(out/'REPORT-ja.md','# Full 144 source audit\n\n'+json.dumps(summary,ensure_ascii=False,indent=2)+'\n\n価格結果を測定する前のsource-only監査。15:25〜15:29の存在判定はsession-inventory.jsonの元response内Time分布で行う。\n')
 b.write(out/'manifest.json',{x.name:b.sha(x) for x in sorted(out.iterdir()) if x.name!='manifest.json'})
if __name__=='__main__':
 q=argparse.ArgumentParser();q.add_argument('--cache',required=True);q.add_argument('--output',required=True);x=q.parse_args();audit(x.cache,x.output)
