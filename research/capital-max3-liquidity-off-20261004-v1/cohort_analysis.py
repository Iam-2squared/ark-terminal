"""Read-only preservation/new-funding audits of the one fixed replay."""
from collections import Counter
from decimal import Decimal as D
from statistics import mean,median
import json,math
from checkpoint import OUT,PRIVATE,V2,save,now,git
from io_data import rows,stream,books,gzwrite
from execution import valid_market

def quantile(v,p):
 v=sorted(v)
 if not v:return None
 point=(len(v)-1)*p;lo=math.floor(point);hi=math.ceil(point)
 return v[lo]+(v[hi]-v[lo])*(point-lo)
def distribution(v):
 known=[float(x) for x in v if x is not None and math.isfinite(float(x))]
 return {'N':len(known),'missing_N':len(v)-len(known),'min':min(known) if known else None,
  'p05':quantile(known,.05),'p25':quantile(known,.25),'median':median(known) if known else None,
  'mean':mean(known) if known else None,'p75':quantile(known,.75),'max':max(known) if known else None}

def main():
 ss=stream();smap={r['entry_id']:r for r in ss};bb=books()
 teacher={r['entry_id']:r for r in rows(V2/'TEACHERS_EVALUATION.jsonl.gz')}
 ds=rows(PRIVATE/'LIQUIDITY_OFF_MAX3_DECISIONS.jsonl.gz');dmap={d['entry_id']:d for d in ds}
 ts=rows(PRIVATE/'LIQUIDITY_OFF_MAX3_TRADES.jsonl.gz');tmap={t['entry_id']:t for t in ts}
 curves=rows(PRIVATE/'LIQUIDITY_OFF_MAX3_CURVE.jsonl.gz');intents=rows(PRIVATE/'LIQUIDITY_OFF_MAX3_INTENTS.jsonl.gz')
 imap={i['entry_id']:i for i in intents}
 control_ds=rows(V2/'CORE_P5_MAX3_DECISIONS.jsonl.gz');control_funded={d['entry_id'] for d in control_ds if d['reason']=='FUNDED'}
 funded={d['entry_id'] for d in ds if d['reason']=='FUNDED'}
 new=funded-control_funded;shared=funded&control_funded;dropped=control_funded-funded
 winner5={r['entry_id'] for r in ss if teacher[r['entry_id']]['label_bigwinner5']==1}
 winner10={r['entry_id'] for r in ss if teacher[r['entry_id']]['label_bigwinner10']==1}
 assert len(winner5)==170
 old_reject={key for key in winner5 if not smap[key]['liquidity']['eligible']};assert len(old_reject)==52
 no_trade=Counter();stale_minutes=Counter()
 actual_minutes={key:{r['minute'] for r in bb[key]['market'] if r.get('session')==smap[key]['session'] and valid_market(r)} for key in funded}
 boundaries=set(range(545,691,5))|set(range(755,926,5))
 for f in curves:
  t=f['minute'];regular=540<=t<690 or 750<=t<930
  for key,known in f['known_marks'].items():
   if regular and known<t:stale_minutes[key]+=1
   if t in boundaries and smap[key]['entry_minute']<=t-5 and not any(m in actual_minutes[key] for m in range(t-5,t)):
    no_trade[key]+=1
 def cohort(keys):
  ordered=sorted(keys);closed=[tmap[k] for k in ordered if k in tmap]
  returns=[t['net_return'] for t in closed];hist=[smap[k]['liquidity'] for k in ordered]
  debit=sum((D(t['debit']) for t in closed),D(0));pnl=sum((D(t['pnl']) for t in closed),D(0))
  return {'N':len(keys),'primary_chain_funded_N':sum(dmap[k]['primary_chain'] for k in keys),
   'diagnostic_only_funded_N':sum(not dmap[k]['primary_chain'] for k in keys),
   'closed_valid_fill_N':len(closed),'unresolved_realized_return_N':len(keys)-len(closed),
   'realized_return_mean':mean(returns) if returns else None,'realized_return_median':median(returns) if returns else None,
   'positive_rate':mean(v>0 for v in returns) if returns else None,
   'BigWinner5_N':len(keys&winner5),'BigWinner10_N':len(keys&winner10),
   'worst_realized_return':min(returns) if returns else None,'maximum_realized_loss':max(0,-min(returns)) if returns else None,
   'p05_realized_return':quantile(returns,.05),'actual_realized_pnl_jpy':float(pnl),
   'debit_weighted_realized_return':float(pnl/debit) if debit else None,
   'Frozen_EXIT_N':sum(t['exit_kind']=='FROZEN_EXIT_V3' for t in closed),
   'EOD_regular_N':sum(t['exit_kind']=='EOD_REGULAR' for t in closed),
   'EOD_auction_N':sum(t['exit_kind']=='EOD_EXACT_1530_AUCTION' for t in closed),
   'EOD_unexecuted_N':sum(k in imap and k not in tmap for k in keys),
   'no_trade_MTM_event_N':sum(no_trade[k] for k in keys),'stale_mark_minute_snapshot_N':sum(stale_minutes[k] for k in keys),
   'historical_liquidity_status_N':dict(Counter(h['reason'] for h in hist)),
   'historical_active_coverage':distribution([h['median_coverage'] for h in hist]),
   'minimum_historical_active_coverage':min((float(h['median_coverage']) for h in hist if h['median_coverage'] is not None),default=None),
   'prior_daily_trading_value_jpy':distribution([h['median_value'] for h in hist])}
 statuses=('LIQUIDITY_ELIGIBLE','EXTREME_ILLIQUIDITY_REJECT','LIQUIDITY_UNKNOWN')
 new_groups={status:cohort({k for k in new if smap[k]['liquidity']['reason']==status}) for status in statuses}
 gate_recovered={k for k in new if not smap[k]['liquidity']['eligible']}
 report={'jst':now(),'basis_head':git('rev-parse','HEAD'),'definition':'OFF funded entry_ids minus Control funded entry_ids; not a post-hoc teacher filter',
  'LIQUIDITY_OFF_NEWLY_FUNDED':cohort(new),'newly_funded_status_cohorts':new_groups,
  'newly_funded_historical_liquidity_reject_or_unknown':cohort(gate_recovered),
  'shared_with_control':cohort(shared),'control_funded_dropped_N':len(dropped),
  'funded_entry_identity_counts':{'control':len(control_funded),'OFF':len(funded),'new':len(new),'shared':len(shared),'dropped':len(dropped)},
  'no_trade_definition':'Open-position closed regular5m full window after Entry with zero valid actual trades; stale-minute snapshots reported separately.',
  'realized_definition':'Actual closed fills only. Unexecuted returns stay null; mean/median/positive rate denominators are closed_valid_fill_N.',
  'attribution_limit':'New/dropped/shared cohorts separate outcomes, but concurrent selection, changed quantities and compounding interact; cohort PnL is not a causal decomposition of the paired portfolio delta.',
  'orders':0,'productionReady':False}
 save(OUT/'NEWLY_FUNDED_THIN_COHORT.json',report)
 missed=Counter(dmap[k]['reason'] for k in winner5-funded)
 preservation={'BigWinner5_total_N':170,'BigWinner5_funded_N':len(funded&winner5),
  'BigWinner5_capture_rate':len(funded&winner5)/170,'BigWinner10_funded_N':len(funded&winner10),
  'liquidity_reason_reject_N':sum(d['reason'] in ('EXTREME_ILLIQUIDITY_REJECT','LIQUIDITY_UNKNOWN','LIQUIDITY_LOT_CAP_REJECT') for d in ds),
  'Liquidity_Winner_reject_N':0,'Liquidity_Winner_reject_rate':0.0,
  'missed_score_lt1_N':missed['BELOW_CAPITAL_BASELINE'],'missed_MAX3_N':missed['MAX_POSITION_CAP']+missed['SYMBOL_ALREADY_OPEN'],
  'missed_cash_lot_N':missed['CASH_OR_LOT_CONSTRAINED'],'missed_Entry_cutoff_N':missed['CAPITAL_EOD_ENTRY_CUTOFF'],
  'all_missed_reasons':dict(missed),'control_funded_Winner5_N':42,'control_capture_rate':42/170,
  'capture_delta':(len(funded&winner5)-42)/170,
  'newly_funded_Winner5_N':len(new&winner5),'control_Winner5_dropped_N':len(dropped&winner5),
  'old_liquidity_rejected_Winner5_total_N':52,'old_reject52_score_eligible_N':sum(smap[k]['entry_minute']<920 and smap[k]['capital_score']>=1 for k in old_reject),
  'old_reject52_funded':cohort(old_reject&funded),
  'old_reject52_by_historical_status':{status:{'N':sum(smap[k]['liquidity']['reason']==status for k in old_reject),
    'score_eligible_N':sum(smap[k]['liquidity']['reason']==status and smap[k]['entry_minute']<920 and smap[k]['capital_score']>=1 for k in old_reject),
    'funded':cohort({k for k in old_reject&funded if smap[k]['liquidity']['reason']==status})} for status in statuses},
  'old_reject52_missed_reasons':dict(Counter(dmap[k]['reason'] for k in old_reject-funded)),
  'future_label_use':'Evaluation only; never candidate filter, score, allocation or size',
  'orders':0,'productionReady':False}
 assert preservation['liquidity_reason_reject_N']==0
 assert len(funded&winner5)+sum(missed.values())==170
 save(OUT/'BIGWINNER_PRESERVATION.json',preservation)
 gzwrite(PRIVATE/'FUNDED_COHORT_LEDGER.jsonl.gz',[
  {'entry_id':k,'session':smap[k]['session'],'symbol':smap[k]['symbol'],
   'cohort':'LIQUIDITY_OFF_NEWLY_FUNDED' if k in new else 'CONTROL_AND_OFF_FUNDED',
   'historical_liquidity':smap[k]['liquidity'],'decision':dmap[k],
   'BigWinner5':k in winner5,'BigWinner10':k in winner10,'old_reject52':k in old_reject,
   'actual_trade':tmap.get(k),'EOD_intent':imap.get(k),'no_trade_MTM_event_N':no_trade[k],
   'stale_mark_minute_snapshot_N':stale_minutes[k]} for k in sorted(funded)])
 gzwrite(PRIVATE/'OLD_REJECT52_LEDGER.jsonl.gz',[
  {'entry_id':k,'session':smap[k]['session'],'symbol':smap[k]['symbol'],'capital_score':smap[k]['capital_score'],
   'liquidity':smap[k]['liquidity'],'decision':dmap[k],'actual_trade':tmap.get(k),
   'BigWinner10':k in winner10} for k in sorted(old_reject)])
 print(json.dumps({'new_funded_N':len(new),'new_thin_or_unknown_N':len(gate_recovered),
  'funded_Winner5_N':len(funded&winner5),'capture_rate':len(funded&winner5)/170,
  'old_reject52_score_eligible_N':preservation['old_reject52_score_eligible_N'],
  'old_reject52_funded_Winner5_N':len(old_reject&funded),
  'new_mean_realized':report['LIQUIDITY_OFF_NEWLY_FUNDED']['realized_return_mean'],
  'new_EOD_unexecuted_N':report['LIQUIDITY_OFF_NEWLY_FUNDED']['EOD_unexecuted_N']}),flush=True)

if __name__=='__main__':main()
