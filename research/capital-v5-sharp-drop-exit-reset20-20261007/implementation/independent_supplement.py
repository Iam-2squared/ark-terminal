"""Source-reconstructed independent ledgers -> summary/cohort/accounting audit. No primary imports."""
from pathlib import Path
from decimal import Decimal,localcontext
from fractions import Fraction
from statistics import median
import json,csv,gzip,hashlib,collections
R=Path(__file__).resolve().parent;D=Decimal
def read(p):return json.loads(Path(p).read_bytes())
def rows(p):return [json.loads(x) for x in gzip.decompress(Path(p).read_bytes()).splitlines() if x]
def save(p,x):Path(p).write_text(json.dumps(x,sort_keys=True,indent=2,ensure_ascii=False)+'\n')
def rp(t):
 with localcontext() as c:c.prec=60;x=D(t['pnl'])/D(t['debit'])
 return Fraction(str(x))*100
checks=[]
def check(name,a,b):
 equal=D(str(a))==D(str(b)) if a is not None and b is not None else a==b;checks.append({'name':name,'exact_match':equal});assert equal,(name,a,b)
def main():
 s=read(R/'public/RESET20_SUMMARY.json');paths={};dt=[];winner=collections.Counter();firsts=[]
 for w in s['mask']:
  paths[w]={a:read(R/'private/independent'/w/a/'RESULT.json') for a in ['C','E']}
  t={a:{v['entry_id']:v for v in rows(R/'private/independent'/w/a/'TRADES.jsonl.gz')} for a in ['C','E']}
  c,e=t['C'],t['E'];direct=qty=onlyE=onlyC=D(0)
  for key in c.keys()|e.keys():
   if key in c and key in e:
    uc=D(c[key]['sell_effective'])-D(c[key]['buy_effective']);ue=D(e[key]['sell_effective'])-D(e[key]['buy_effective']);direct+=c[key]['quantity']*(ue-uc);qty+=(e[key]['quantity']-c[key]['quantity'])*ue
   elif key in e:onlyE+=D(e[key]['pnl'])
   else:onlyC+=D(c[key]['pnl'])
  target=next(x for x in csv.DictReader((R/'public/FUNDING_AND_PNL_DECOMPOSITION.csv').open()) if x['window_id']==w)
  for k,v in [('COMMON_direct_EXIT_jpy',direct),('COMMON_quantity_jpy',qty),('E_ONLY_PnL_jpy',onlyE),('C_ONLY_PnL_jpy',onlyC)]:check('DECOMPOSITION:'+w+':'+k,v,target[k])
  delta=D(paths[w]['E']['final_equity'])-D(paths[w]['C']['final_equity']);dt.append(delta);check('ACCOUNTING_IDENTITY:'+w,direct+qty+onlyE-onlyC,delta)
  for key,x in c.items():
   if rp(x)<=0:continue
   winner['C_N']+=1
   if key not in e:winner['E_not_purchased_N']+=1;continue
   winner['E_purchased_N']+=1;y=e[key];diff=rp(y)-rp(x);money=D(y['pnl'])-D(x['pnl']);winner['per_unit_EXIT_'+('improved' if diff>0 else 'equal' if diff==0 else 'worsened')+'_N']+=1;winner['actual_PnL_'+('improved' if money>0 else 'equal' if money==0 else 'worsened')+'_N']+=1;winner['positive_to_negative_N']+=rp(y)<0
  intents=[x for x in rows(R/'private/independent'/w/'E/INTENTS.jsonl.gz') if x.get('reason')=='SHARP_DROP_FIRST_OBSERVED']
  if intents:firsts.append(min(intents,key=lambda x:(x['session'],x['minute'],x['entry_id']))|{'window_id':w})
 for a in ['C','E']:
  money=[D(paths[w][a]['final_equity']) for w in s['mask']];ss={'min':min(money),'mean':sum(money,D(0))/len(money),'median':median(money),'max':max(money)}
  for k,v in ss.items():check(a+':FINAL_STATS:'+k,v,s[a+'_final_equity_stats'][k])
  for k,field in [('gross_loss_jpy','_gross_loss_jpy_overlapping_accounts'),('gross_positive_jpy','_gross_positive_jpy_overlapping_accounts')]:check(a+':AGGREGATE:'+k,sum((D(paths[w][a][k]) for w in s['mask']),D(0)),s[a+field])
 for k,v in {'min':min(dt),'mean':sum(dt,D(0))/len(dt),'median':median(dt),'max':max(dt)}.items():check('PAIRED_DELTA_STATS:'+k,v,s['paired_delta_stats'][k])
 check('DIFFERENCE_OF_MEDIANS',median([D(paths[w]['E']['final_equity']) for w in s['mask']])-median([D(paths[w]['C']['final_equity']) for w in s['mask']]),s['difference_of_medians_jpy'])
 target=read(R/'public/WINNER_LOSER_AND_FUNDING_DIAGNOSTICS.json')['fixed_C_winners']
 for k,v in target.items():check('FIXED_C_WINNER:'+k,winner[k],v)
 first=min(firsts,key=lambda x:(x['session'],x['minute'],x['window_id'],x['entry_id']));target=read(R/'public/FIRST_DIVERGENCE.json')
 assert first['window_id']==target['global_window'] and first['session']==target['global_session']
 receipt={'status':'PASS','separate_implementation_primary_imports':0,'input':'Independent source-reconstructed20paths, not primary final tables','check_N':len(checks),'checks':checks,'cohorts_accounting_summary_first_divergence_verified':True,'portfolio_replay_N':0}
 save(R/'public/INDEPENDENT_SUPPLEMENT.json',receipt);print(json.dumps({'status':'PASS','check_N':len(checks)}))
if __name__=='__main__':main()
