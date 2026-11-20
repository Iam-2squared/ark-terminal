// Presentation-only: reads the completed experiment; never fits or predicts.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import {fileURLToPath} from 'node:url';
const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const dir=path.join(root,'docs/evidence/phase57-msh-entry-long-v1-first-development');
const r=JSON.parse(fs.readFileSync(path.join(dir,'development-report.json')));
const verdict=JSON.parse(fs.readFileSync(path.join(dir,'development-verdict.json')));
const lines=[];
const add=s=>lines.push(s,'');
const fmt=x=>x===null||x===undefined?'N/A':typeof x==='number'?Number.isInteger(x)?String(x):x.toFixed(4):String(x);
function table(headers,rows){add('| '+headers.join(' | ')+' |\n| '+headers.map(()=> '---').join(' | ')+' |\n'+rows.map(row=>'| '+row.map(fmt).join(' | ')+' |').join('\n'));}
const levels=['1','2','3','5'];
const candidates=Object.entries(r.thresholds);
const vals=(metrics,key)=>levels.map(k=>metrics[k][key]);
add('# Phase57 MSH-Entry LONG v1 — First Development evaluation');
add('Date: 2026-09-16 JST. Verdict: **'+verdict.verdict+'**. Selected threshold: **none**. Development only; STOP.');
add('## Repository / reproducibility');
table(['Item','Value'],[
 ['Repository','Iam-2squared/ark-terminal'],['Branch','research/phase57-long-only-cash-equity'],['PR','#587'],
 ['Verified remote source head',r.sourceHead],['Latest main at audit',verdict.latestMainAtAudit],
 ['Local pre-fit protocol commit',verdict.localPrefitCommit],['Remote update','NOT performed; new CI not triggered'],
 ['Fit Contract SHA-256',r.contractSha256],['Model implementation SHA-256',r.implementationSha256],
 ['Frozen Selector payload SHA-256','3dc6d222d4039737c0dcfdcfa4a83372202152e29b582225419ab97c00610d59'],
 ['Ridge artifact SHA-256','994f1dbaba1d32e97458d5dd9d4c646ef443fbb37128650e8166001d8deabefb'],
 ['Selector / CURRENT Entry / Fit Contract','UNCHANGED; integrity checks PASS'],
 ['Scope','JPX CASH EQUITY LONG-only; project SHORT evaluation = 0']]);
add('The protocol was committed locally before the four fits. GitHub blob/tree/commit objects for that protocol were prepared, but no branch ref was updated. Publication is deferred because the existing full test workflow may contact Yahoo Finance.');
add('Verified source-head CI: Predict Tests run35053207614 SUCCESS; Phase52 Daily Dry-Run Persistence run35053207633 SUCCESS; LONG-only Research Foundation run35053207611 SUCCESS. These are PRIOR source-head checks, not CI of the new results.');
add('## Execution / data integrity');
table(['Metric','Count'],Object.entries(r.dataAudit).filter(([k,v])=>typeof v==='number'));
table(['Unlabelable reason','Rows'],Object.entries(r.dataAudit.unlabelableReasons));
add('Labelable coverage: 1,828 / 3,800 = 48.1053%. Initial 16-session prefix has 377 labelable training rows and NO OOF. Evaluation sessions 17–76 contain 3,000 events / 2,170 symbol-sessions; the labelable OOF subset contains 1,451 events / 1,099 symbol-sessions. Excluded rows are retained in row-ledger.ndjson.gz and never assigned Class 0.');
add('**Denominator limitation:** the 1,099-group evaluation pool is conditioned on future label availability. It is not a causal live availability gate, full-universe coverage, or 1,451 independent trades. Frozen Selector used already exposed Development data, so chronological Entry OOF is not end-to-end OOS.');
add('**Schedule:** saved Frozen Selector evidence has ten decisions/session at 09:30, 10:00, 10:30, 11:00, 11:30, 13:00, 13:30, 14:00, 14:30, 15:00 JST. No five-minute reselections were manufactured.');
add('## Frozen fit / all-fold convergence');
add('Exactly four fits, no retries and no full-76-session refit. Core = Ridge Score + Ridge Rank, optional = none, price = REFERENCE_ONLY. Five-class proportional odds/logit, SUM NLL + 1/2 ||beta||², cutpoints unpenalized, unweighted. L-BFGS-B maxiter=2000, ftol=1e-12, gtol=1e-8. Each training prefix independently supplies population mean/std; no eval data enter scaler estimation.');
table(['Fold','Train sessions','Eval sessions','Train rows','Eval rows','Train classes 0/1/2/3/4','Eval classes 0/1/2/3/4','success/status','nit/nfev/njev','Objective'],r.folds.map(f=>[f.fold,f.trainSessions.length,f.evalSessions.length,f.trainRows,f.evalRows,f.trainClassCounts.join('/'),f.evalClassCounts.join('/'),`${f.convergence.success}/${f.convergence.status}`,`${f.convergence.nit}/${f.convergence.nfev}/${f.convergence.njev}`,f.convergence.objective]));
add('All ten pre-fit checks passed for every fold. Every optimizer message: CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH. Finite parameters, ordered cutpoints, finite nonnegative probabilities summing to one and exact artifact save/reload checks all passed.');
table(['Fold','Train dates','Eval dates','Mean [score,rank]','Std [score,rank]'],r.folds.map(f=>[f.fold,`${f.trainSessions[0]} – ${f.trainSessions.at(-1)}`,`${f.evalSessions[0]} – ${f.evalSessions.at(-1)}`,f.scaler.mean.join(', '),f.scaler.std.join(', ')]));
table(['Fold','Scaler SHA-256','Model artifact SHA-256'],r.folds.map(f=>[f.fold,f.scalerSha256,f.artifactFileSha256]));
add('## First-entry primary results — strict 30m HIGH');
add('ENTER means the first eligible event with E[L] ≥ threshold in each symbol-session. Repeated entries are suppressed. Precision uses that ENTER event’s own Decision Price / next complete 30m window. Admission preservation uses first-eligible baseline winners eventually admitted. These are distinct measures. Percentages below are %, throughput is per session (60-session denominator).');
table(['Threshold','ENTER','Coverage %','ENTER/session','+1 precision','+2 precision','+3 precision','+5 precision','Frozen balance'],[['Selector',r.selectorPaired],...candidates.map(([t,v])=>[t,v.firstEntry])].map(([t,v])=>[t,v.enterCount,v.firstEntryCoveragePct,v.entriesPerSession,...vals(v.high30,'precisionPct'),v.frozenBalanceMetric]));
table(['Threshold','+1 preservation','+2 preservation','+3 preservation','+5 preservation','Preserved +1/day','+2/day','+3/day','+5/day'],candidates.map(([t,v])=>[t,...vals(v.firstEntry.high30,'admissionPreservationPct'),...vals(v.firstEntry.high30,'preservedPerSession')]));
table(['Threshold','+1 timely','+2 timely','+3 timely','+5 timely','+1 remaining','+2 remaining','+3 remaining','+5 remaining'],candidates.map(([t,v])=>[t,...vals(v.firstEntry.high30,'timelyAdmissionPreservationPct'),...vals(v.firstEntry.high30,'remainingPreservationPct')]));
add('Timely = admitted strictly before the first baseline 30m window ends. Remaining = first-baseline winner AND ENTER-time threshold hit; this uses a new Entry window, not proof of an executable realized return or proof that the first window’s hit happened after ENTER. Admission alone must not be called economically retained opportunity.');
add('## HIGH vs completed CLOSE supporting diagnostic');
table(['Cohort','HIGH +1','+2','+3','+5','CLOSE +1','+2','+3','+5'],[['Selector',r.selectorPaired],...candidates.map(([t,v])=>[t,v.firstEntry])].map(([t,v])=>[t,...vals(v.high30,'precisionPct'),...vals(v.close30,'precisionPct')]));
table(['Threshold','CLOSE preservation +1','+2','+3','+5'],candidates.map(([t,v])=>[t,...vals(v.firstEntry.close30,'admissionPreservationPct')]));
add('CLOSE is supporting only, never mixed into the HIGH training target. Threshold 2 has HIGH +3 53.15% versus CLOSE +3 39.16%; the touch/confirmation distinction remains material.');
add('## Event-level qualification — not independent trades');
table(['Threshold','OOF events','Qualified events','Qualification %','HIGH +1 precision','+2','+3','+5','HIGH +1 preservation','+2','+3','+5'],candidates.map(([t,{eventLevel:v}])=>[t,v.eventN,v.qualifiedEventN,v.qualificationRatePct,...vals(v.high30,'precisionPct'),...vals(v.high30,'preservationPct')]));
add('## Fold stability — first-entry strict 30m HIGH');
table(['Threshold','Fold','OOF rows','Eligible groups','ENTER','Coverage %','ENTER/day','+1 precision','+2','+3','+5','+1 preservation','+2','+3','+5'],candidates.flatMap(([t,v])=>v.folds.map(f=>[t,f.fold,f.oofRows,f.candidateSymbolSessions,f.enterCount,f.firstEntryCoveragePct,f.entriesPerSession,...vals(f.high30,'precisionPct'),...vals(f.high30,'admissionPreservationPct')])));
table(['Threshold','Fold','+1 enrichment pp','+2','+3','+5'],candidates.flatMap(([t,v])=>v.folds.map(f=>[t,f.fold,...vals(f.high30,'enrichmentPp')])));
add('Threshold 2 has positive HIGH enrichment at all four opportunity levels in all four folds. Threshold 1 is near an identity gate, with small +1/+2 reversals in some folds. Threshold 3 admits only 3/8/3/9 groups per fold and fold 3 has zero +5 hits; aggregate precision is insufficient.');
add('## MFE / true MAE / latency / consumed return');
const diagnostics=[['strict30mMfePct','30m MFE %'],['sessionMfePct','Session MFE % (different horizon)'],['sessionTrueMaePct','Session true MAE % (different horizon)'],['firstEligibleLatencyMinutes','First-eligible to ENTER minutes'],['firstEligibleConsumedReturnBps','First-eligible to ENTER consumed bps'],['firstOriginalLatencyMinutes','First-original to ENTER minutes'],['firstOriginalConsumedReturnBps','First-original to ENTER consumed bps']];
table(['Threshold','Diagnostic','N','Mean','Median','P25','P75','P90','Min','Max'],candidates.flatMap(([t,v])=>diagnostics.map(([k,label])=>[t,label,...['n','mean','median','p25','p75','p90','min','max'].map(x=>v.firstEntry[k][x])])));
add('**Strict 30m true MAE: UNAVAILABLE for every candidate.** Future lows are not saved in the reused feasibility ledger. Session true MAE is reported separately and is NOT a replacement. The reused session series includes extreme drawdowns (minimum −60% in thresholds 1/2 and −50% in threshold 3); no cost/risk/profitability claim is made and these extrema were not filtered away.');
add('Same-event Selector→Entry reference latency and consumed return are exactly zero by definition, not measured execution quality. First-original latency additionally includes earlier selections omitted for labelability. Negative consumed return means a lower reference price, not proven beneficial waiting. No fill/slippage, portfolio or EXIT simulation was run.');
add('## Paired CURRENT Entry / Selector comparison');
const c=r.currentPaired;
table(['Metric','Value'],[['Common eligible symbol-session pool',c.poolSymbolSessions],['CURRENT actual first PASS',c.actualFirstPassCount],['CURRENT coverage %',c.actualFirstPassCoveragePct],['CURRENT PASS/session',c.actualPassPerSession],['CURRENT exact 30m matched PASS',c.strict30mExactEventMatchedPassCount],['CURRENT 30m unmatched PASS',c.strict30mUnmatchedPassCount],['CURRENT PASS before first eligible event',c.passBeforeFirstEligible],['All60session CURRENT context groups',r.currentAllEvaluationSessions.candidateSymbolSessions],['All60session CURRENT context PASS',r.currentAllEvaluationSessions.actualFirstPassN]]);
add('Only 24 of the 66 actual CURRENT passes have an exact saved OOF event timestamp AND reference-price match. Other PASS timings are unavailable at strict30m, not Class 0. Therefore the following full-pool comparison uses **session-remaining horizon**, not the primary30m target. CURRENT state/model is unchanged; ALREADY_ENTERED is not counted as a new PASS.');
table(['Cohort','Session +1 precision','+2','+3','+5','Session +1 admission preservation','+2','+3','+5'],[
 ['Selector',...vals(r.selectorPaired.session,'precisionPct'),100,100,100,100],
 ['CURRENT',...vals(c.actualPassSessionQuality,'precisionPct'),...vals(c.sessionAdmissionPreservation,'preservationPct')],
 ...candidates.map(([t,v])=>[t,...vals(v.firstEntry.session,'precisionPct'),...vals(v.firstEntry.session,'admissionPreservationPct')])]);
table(['Cohort','Session preserved +1/day','+2/day','+3/day','+5/day'],[['CURRENT',...vals(c.sessionAdmissionPreservation,'preservedPerSession')],...candidates.map(([t,v])=>[t,...vals(v.firstEntry.session,'preservedPerSession')])] );
table(['CURRENT exact matched subset ONLY','+1','+2','+3','+5'],[['HIGH30 precision',...vals(c.strict30mExactEventSubsetOnly.high30,'precisionPct')],['CLOSE30 precision',...vals(c.strict30mExactEventSubsetOnly.close30,'precisionPct')]]);
add('Do not compare formal Selector Development percentages 76.39/61.29/47.26/24.99 directly against the restricted 30m OOF pool. Do not compare historical96/2743 CURRENT coverage directly against1099 groups. Those formal artifacts remain unchanged.');
add('## Verdict / threshold selection');
add(verdict.reasons.map(s=>'- '+s).join('\n'));
add('No threshold is promoted. The scalar leader is1.0 (0.724053); Selector-only is0.726408. Threshold2 is promising descriptive evidence, but changing the selection rule to prefer it after seeing its precision is not permitted. This is BORDERLINE, not a finding that the mathematical model failed and not a Validation pass.');
add('## Tests / access / STOP');
table(['Check','Result'],[['Frozen model synthetic','18 PASS'],['Evaluation synthetic','12 PASS'],['Discovery','26 PASS'],['RSS bridge','89 PASS'],['Read-only evidence audit','PASS;1451 OOF rows,4353 decisions; max probability error2.220446049250313e-16'],['Full prediction suite','BLOCKED by safety review; no complete PASS claim'],['New remote CI','NOT run; remote ref unchanged']]);
add('The full prediction suite continuation was rejected because it can issue an unapproved Yahoo Finance request. It was not retried or bypassed. Development runner provider requests=0 (saved ledgers only), but the attempted regression suite’s provider-request count is UNVERIFIED, not asserted zero. No newly fetched data were used for model fitting/evaluation.');
table(['Control','Value'],Object.entries(r.methodology).filter(([k])=>k!=='thresholdCandidatesEvaluated'));
add('The providerRequests=0 entry above is scoped to the Development experiment, not the blocked general regression suite. Validation new access=0, OOS new access=0, Project EXIT access=0, Project SHORT evaluation=0. Synthetic regression fixture names are not Project Validation/OOS access.');
table(['Safety flag','Value'],Object.entries(r.safety));
add('**Exact next action: STOP.** Independent review of the Development evidence. Separate permission is needed to make the full regression suite offline-only and publish/run CI safely. Do not retrain, add features/thresholds, alter the contract, or open Validation/OOS.');
add('## Files / hashes');
table(['Ledger','Compressed SHA-256','Payload SHA-256'],Object.entries(r.inputHashes).map(([k,v])=>[k,v.gzipSha256,v.payloadSha256]));
table(['Output','Rows','File SHA-256','Payload SHA-256'],Object.entries(r.files).map(([k,v])=>[k,v.rows,v.fileSha256,v.payloadSha256]));
add('Full-precision metrics and all distributions are in development-report.json; separate final disposition is development-verdict.json. Results were generated once; report generation performs no fit.');
fs.writeFileSync(path.join(dir,'REPORT.md'),lines.join('\n'));
const manifest={algorithm:'SHA-256',excludesSelf:true,files:{}};
for(const name of fs.readdirSync(dir).sort())if(name!=='manifest.json'&&fs.statSync(path.join(dir,name)).isFile())manifest.files[name]=crypto.createHash('sha256').update(fs.readFileSync(path.join(dir,name))).digest('hex');
fs.writeFileSync(path.join(dir,'manifest.json'),JSON.stringify(manifest,null,2)+'\n');
console.log(JSON.stringify({report:'REPORT.md',verdict:verdict.verdict,files:Object.keys(manifest.files).length}));
