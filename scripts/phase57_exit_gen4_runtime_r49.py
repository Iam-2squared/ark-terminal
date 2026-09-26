"""R49 historical-replay winner-capture policy boundary."""
from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
import hashlib, json, math
from pathlib import Path
from scripts.phase57_exit_execution_contract_v1 import continuous_minutes

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / 'docs/evidence/phase57-comprehensive-exit-v1/GEN4_PRECOMMIT_R49.json'
PROTOCOL_SHA256 = '5d10e3fe1a927923ff1a32e56adf40e952b298ac6a11a14786a444560bdd4354'
FACTS = ('certifiedMfePct','certifiedGivebackPp','timeSincePeak','barsHeld','currentReturnPct',
         'momentum5Pct','weakRun','stateRecovery','failedRecovery','signalTrueN','signalFalseN',
         'signalLossN','signalRecoveryN','newPeak','STRUCT/Lrising')

def require(ok, reason):
    if not ok: raise ValueError(reason)

def finite(v): return type(v) in (int,float) and math.isfinite(v)

@lru_cache(maxsize=1)
def _protocol():
    raw=PROTOCOL_PATH.read_bytes()
    require(hashlib.sha256(raw).hexdigest()==PROTOCOL_SHA256,'R49_PROTOCOL_HASH')
    p=json.loads(raw)
    require(p['status']=='FROZEN_BEFORE_REPLAY' and p['candidateCount']==3,'R49_PROTOCOL_STATUS')
    require(p['modelFits']==0 and p['predictionRefits']==0 and not p['futureOutcomeInputsAllowed'],'R49_CONTROLLED_DESIGN')
    require([x['id'] for x in p['candidates']]==['R49_A','R49_B','R49_C'],'R49_CANDIDATES')
    return p

def load_protocol(): return deepcopy(_protocol())

@lru_cache(maxsize=128)
def endpoints(day): return tuple(s+1 for s in continuous_minutes(day))

@lru_cache(maxsize=128)
def endpoint_index(day): return {t:i for i,t in enumerate(endpoints(day))}

def adjacent(day,a,b):
    ix=endpoint_index(day); return a in ix and b in ix and ix[b]==ix[a]+1

def initial_state(): return {'lastNow':None,'harvestCount':0,'tailCount':0}

def validate_facts(envelope):
    require(type(envelope) is dict and set(envelope)=={'now','maxKnownAt','maxBarEnd','fresh','values'},'R49_FACT_ENVELOPE')
    now=envelope['now']; require(type(now) is int and type(envelope['fresh']) is bool,'R49_FACT_TYPES')
    require(all(type(envelope[k]) is int and 0<=envelope[k]<=now for k in ('maxKnownAt','maxBarEnd')),'R49_FUTURE_FACT')
    v=envelope['values']; require(type(v) is dict and set(v)==set(FACTS),'R49_FACT_ALLOWLIST')
    require(all(x is None or finite(x) for x in v.values()),'R49_NONFINITE_FACT')
    return v

def intent(day,envelope,scores,previous_state,candidate):
    p=_protocol(); v=validate_facts(envelope); now=envelope['now']
    require(now in endpoint_index(day),'R49_NOT_ENDPOINT')
    require(candidate in p['candidates'],'R49_UNKNOWN_CANDIDATE')
    require(type(previous_state) is dict and set(previous_state)==set(initial_state()),'R49_STATE_KEYS')
    s=deepcopy(previous_state); last=s['lastNow']
    require(last is None or (type(last) is int and last<now),'R49_NONMONOTONE')
    if last is not None and not adjacent(day,last,now): s.update(harvestCount=0,tailCount=0)
    s['lastNow']=now
    if now==925: return {'action':'FORCE_TERMINAL','authority':'FORCE_TERMINAL','state':s}
    valid=type(scores) in (list,tuple) and len(scores)==3 and all(finite(x) and 0<=x<=1 for x in scores)
    if not envelope['fresh'] or not valid:
        s.update(harvestCount=0,tailCount=0)
        return {'action':'HOLD','authority':'MISSING_HOLD','state':s}
    c,_,d=scores
    def ge(k,b): return finite(v[k]) and v[k]>=b
    def le(k,b): return finite(v[k]) and v[k]<=b
    q=p['common']; tail=q['tail']
    tail_ok=(le('currentReturnPct',tail['currentReturnPctMax']) and d>=tail['dScoreMin'] and
             ge('weakRun',tail['weakRunMin']) and ge('signalFalseN',tail['signalFalseNMin']))
    s['tailCount']=s['tailCount']+1 if tail_ok else 0
    if s['tailCount']>=tail['confirm']:
        s['harvestCount']=0
        return {'action':'EXIT_INTENT','authority':'EXTREME_TAIL_GUARD','state':s}
    recovery=((v['stateRecovery']==1 or ge('signalRecoveryN',1)) and ge('momentum5Pct',0) and ge('signalTrueN',1))
    structural=(v['STRUCT/Lrising']==1 and ge('momentum5Pct',-0.5))
    model_cont=(c>=q['continuationScoreMin'] and ge('momentum5Pct',0) and ge('signalTrueN',2))
    veto=(v['newPeak']==1 or recovery or structural or model_cont)
    h=candidate
    common=(ge('certifiedMfePct',h['mfeMin']) and ge('timeSincePeak',h['peakAgeMin']) and
            ge('barsHeld',h['barsHeldMin']) and le('momentum5Pct',h['momentumMax']) and
            ge('signalFalseN',h['signalFalseMin']))
    if h['id']=='R49_A':
        harvest=common and ge('certifiedGivebackPp',h['givebackMin']) and d>=h['dScoreMin']
    elif h['id']=='R49_B':
        threshold=None if not finite(v['certifiedMfePct']) else max(h['givebackFloor'],h['givebackFraction']*v['certifiedMfePct'])
        harvest=common and threshold is not None and ge('certifiedGivebackPp',threshold) and c<=h['cScoreMax']
    else:
        harvest=common and ge('certifiedGivebackPp',h['givebackMin']) and c<=h['cScoreMax'] and ge('weakRun',h['weakRunMin'])
    if veto:
        s['harvestCount']=0
        return {'action':'HOLD','authority':'CONTINUATION_VETO','state':s}
    s['harvestCount']=s['harvestCount']+1 if harvest else 0
    if s['harvestCount']>=h['confirm']:
        return {'action':'EXIT_INTENT','authority':'WINNER_HARVEST','state':s}
    return {'action':'HOLD','authority':'OBSERVE','state':s}
