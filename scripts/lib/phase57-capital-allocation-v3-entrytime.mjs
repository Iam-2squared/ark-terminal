import fs from 'node:fs';
import { createHash } from 'node:crypto';

const contractBytes = fs.readFileSync(new URL('../../predict/research/phase57-capital-allocation-v3-entrytime-contract.json', import.meta.url));
export const CONTRACT = Object.freeze(JSON.parse(contractBytes));
export const CONTRACT_SHA256 = createHash('sha256').update(contractBytes).digest('hex');
export const SAFETY = Object.freeze({...CONTRACT.safety});

const finite = v => typeof v === 'number' && Number.isFinite(v);
const hash = v => createHash('sha256').update(JSON.stringify(v)).digest('hex');
const forbidden = /^(labels?|targets?|outcomes?|future.*|mfe.*|mae.*|exit.*|realized.*|netReturn.*|grossReturn.*)$/i;

function assertNoOutcomeFields(value) {
  if (!value || typeof value !== 'object') return;
  for (const [k,v] of Object.entries(value)) {
    if ((k === 'outcomeUsed' || k === 'exitUsed') && v === false) continue;
    if (forbidden.test(k)) throw new Error(`OUTCOME_FIELD_FORBIDDEN:${k}`);
    assertNoOutcomeFields(v);
  }
}

function iso(v) {
  const t = Date.parse(String(v ?? ''));
  if (!Number.isFinite(t)) throw new Error('INVALID_TIMESTAMP');
  return new Date(t).toISOString();
}

function chosenFeatureRow(event) {
  const direction = Number(event?.decision?.direction);
  const pair = event?.directionFeatures;
  if (![-1,1].includes(direction) || !Array.isArray(pair)) throw new Error('MISSING_DIRECTION_FEATURES');
  const row = pair.find(x => Number(x?.direction) === direction);
  if (!row?.features) throw new Error('CHOSEN_DIRECTION_FEATURES_MISSING');
  return row;
}

export function recentRealizedVolatility(closes) {
  if (!Array.isArray(closes) || closes.length !== 7 || !closes.every(x => finite(x) && x > 0)) return null;
  const rets = [];
  for (let i=1;i<closes.length;i++) rets.push(Math.log(closes[i]/closes[i-1]));
  const mean = rets.reduce((a,b)=>a+b,0)/rets.length;
  const variance = rets.reduce((s,x)=>s+(x-mean)**2,0)/rets.length;
  return Math.sqrt(variance);
}

export function buildEntryTimeOpportunity(event, { recentCloses = null } = {}) {
  assertNoOutcomeFields(event);
  if (event?.decision?.action !== 'ENTER' || event?.stateAfter !== 'ENTERED' || Number(event?.entryCount) !== 1) {
    throw new Error('FIRST_ENTER_REQUIRED');
  }
  const mshScore = Number(event.decision.probability);
  if (!finite(mshScore) || !(mshScore > CONTRACT.upstream.entryThreshold)) throw new Error('ENTRY_THRESHOLD_MISMATCH');
  const featureRow = chosenFeatureRow(event);
  const features = {...featureRow.features};
  const required = [
    'directionalReturnFromOpenPct','directionalVwapDistancePct','directionalMomentum3Pct',
    'directionalMomentumAccelerationPct','directionalPullback6Pct','relativeVolume5',
    'minutesSinceFirstSelection','hybridReciprocalRank','priorSelectionCount','direction'
  ];
  if (!required.every(k => finite(features[k]))) throw new Error('MSH_FEATURE_SET_INCOMPLETE');
  const recentVol = recentRealizedVolatility(recentCloses);
  if (recentCloses !== null && !finite(recentVol)) throw new Error('RISK_FEATURE_WINDOW_INVALID');
  const opportunity = {
    contractSha256: CONTRACT_SHA256,
    eventId: String(event.eventId),
    symbolSessionId: String(event.symbolSessionId),
    sessionDate: String(event.sessionDate),
    decisionTimestamp: iso(event.decisionTimestamp),
    symbol: String(event.symbol),
    direction: Number(event.decision.direction),
    mshScore,
    hybridRank: Number(event.hybridRank),
    hybridScore: Number(event.hybridScore),
    features,
    recentRealizedVolatility: recentVol,
    sourceClass: event.sourceClass ?? 'UNKNOWN',
    selectionLineage: event.selectionLineage ?? null,
    outcomeUsed: false,
    exitUsed: false,
    safety: SAFETY,
  };
  return Object.freeze({...opportunity, opportunitySha256: hash(opportunity)});
}

export function groupOpportunitySets(opportunities) {
  if (!Array.isArray(opportunities)) throw new Error('OPPORTUNITIES_ARRAY_REQUIRED');
  const by = new Map();
  for (const x of opportunities) {
    assertNoOutcomeFields(x);
    if (x?.outcomeUsed !== false || x?.exitUsed !== false) throw new Error('NON_CAUSAL_OPPORTUNITY');
    const key = `${x.sessionDate}|${iso(x.decisionTimestamp)}`;
    if (!by.has(key)) by.set(key, []);
    by.get(key).push(x);
  }
  return [...by.entries()].sort(([a],[b])=>a.localeCompare(b)).map(([setId,rows])=>({setId,candidates:[...rows].sort((a,b)=>b.mshScore-a.mshScore||a.symbol.localeCompare(b.symbol))}));
}

function normalize(raw) {
  const total = raw.reduce((s,x)=>s+x,0);
  if (!(total > 0)) throw new Error('NONPOSITIVE_WEIGHT_SUM');
  return raw.map(x=>x/total);
}

export function allocateV3(set, policyId) {
  const candidates = set?.candidates ?? [];
  const n = candidates.length;
  if (!n) return [];
  if (policyId === 'V3_0_EQUAL') return candidates.map((c,i)=>({symbol:c.symbol,weight:1/n,rank:i+1}));
  if (policyId === 'V3_A_RANK') {
    const raw = candidates.map((_,i)=>n-i);
    const weights = normalize(raw);
    return candidates.map((c,i)=>({symbol:c.symbol,weight:weights[i],rank:i+1}));
  }
  if (policyId === 'V3_B_RISK') {
    const vols = candidates.map(c=>c.recentRealizedVolatility);
    if (!vols.every(v=>finite(v)&&v>0)) throw new Error('RISK_FEATURE_MISSING');
    const weights = normalize(vols.map(v=>1/v));
    return candidates.map((c,i)=>({symbol:c.symbol,weight:weights[i],rank:i+1}));
  }
  throw new Error('UNKNOWN_POLICY');
}

export function summarizePhaseA(sets, policyId) {
  const rows = [];
  for (const set of sets) {
    const alloc = allocateV3(set, policyId);
    const hhi = alloc.reduce((s,x)=>s+x.weight*x.weight,0);
    rows.push({setId:set.setId,candidateCount:alloc.length,hhi,top1:Math.max(...alloc.map(x=>x.weight)),weights:alloc});
  }
  return {policyId,opportunitySetCount:rows.length,meanHhi:rows.length?rows.reduce((s,x)=>s+x.hhi,0)/rows.length:null,rows,safety:SAFETY};
}
