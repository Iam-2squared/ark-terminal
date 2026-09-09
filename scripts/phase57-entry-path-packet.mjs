import fs from 'node:fs';
import {gzipSync} from 'node:zlib';
import {createHash} from 'node:crypto';
const p=process.argv[2],x=JSON.parse(fs.readFileSync(`${p}/path-diagnosis.json`));
x.analysisCodeCommit=process.env.ANALYSIS_CODE_COMMIT??'UNCOMMITTED';
x.verdict='TIMING_HYPOTHESIS_MIXED';
x.reason='Immediate adverse and subsequent observed recovery replicate; however this is not evidence of improved execution from waiting. Intrabar ordering, no-trade gaps, reference versus fills and selection-conditioned paths limit causal claims.';
const bytes=JSON.stringify(x,null,2)+'\n';fs.writeFileSync(`${p}/path-diagnosis.json`,bytes);fs.writeFileSync(`${p}/path-diagnosis.json.gz`,gzipSync(bytes));fs.writeFileSync(`${p}/path-diagnosis.json.sha256`,createHash('sha256').update(bytes).digest('hex')+'\n');
const a=x.groups.Development.ALL,b=x.groups.Holdout29.ALL,fmt=n=>n===null?'UNKNOWN':Number(n).toFixed(2);
let lines=['# Path diagnosis only','', 'Verdict: TIMING_HYPOTHESIS_MIXED. No candidate change; no Timing Challenger.','',`Candidate SHA: ${x.candidateSha256}. Threshold strictly >0.60 (not >=). Analysis code commit: ${x.analysisCodeCommit}.`,'','## Semantics',''];
for(const [k,v] of Object.entries(x.semantics))lines.push(`- ${k}: ${v}`);
lines.push('','All194 reference prices equal the last completed close; reference-age-at-availability0min. This is not an executable quote/fill. Any adverse excursion counts, with no depth cutoff. First adverse is localized to a bar, not a precise time. Same signal-bar adverse is not measured; BAR1 is the first future bar. Recovery is observed close recovery, not exact first touch. Neither guarantees net positive at horizon.','', '## Replication','', '| Metric | Development | Holdout29 | Difference H-D |','|---|---:|---:|---:|');
const row=(name,l,r)=>lines.push(`| ${name} | ${fmt(l)} | ${fmt(r)} | ${fmt(r-l)} |`);
row('ENTER',a.n,b.n);row('Immediate adverse %',a.immediate.rate*100,b.immediate.rate*100);
for(const k of ['BAR_1','BAR_2','BAR_3','BAR_4','BAR_5','BAR_6','NEVER_WITHIN6','UNKNOWN'])row('First adverse '+k,a.timeToAdverse[k]?.count??0,b.timeToAdverse[k]?.count??0);
for(const k of ['MAE_BEFORE_MFE','MFE_BEFORE_MAE','UNKNOWN_INTRABAR_ORDER','UNAVAILABLE_OR_NEITHER'])row(k,a.chronology[k]?.count??0,b.chronology[k]?.count??0);
for(const k of ['mae3','mfe3','mae6','mfe6','remainingFavorable'])for(const s of ['mean','median','p25','p75','p90'])row(k+' '+s+' bps',a[k][s],b[k][s]);
for(const h of [1,2,3,6])row('Observed recovery by'+h+' % of known immediate-adverse',a.recovery[h].rate*100,b.recovery[h].rate*100);
for(const h of [3,6])row('Immediate adverse -> net positive'+h+' %',a.adverseToPositive[h].rate*100,b.adverseToPositive[h].rate*100);
for(const k of ['A_NEG_POS','B_POS_POS','C_POS_NEG','D_NEG_NEG','MISSING'])row('Net3->net6 '+k,a.transition[k]?.count??0,b.transition[k]?.count??0);
row('Next Hybrid selected',a.hybridPersistence.PERSIST_DIRECTION_UNKNOWN.count,b.hybridPersistence.PERSIST_DIRECTION_UNKNOWN.count);
for(const k of ['TYPE_A','TYPE_B','TYPE_C','TYPE_D','TYPE_E','TYPE_UNKNOWN'])row(k,a.types[k]?.n??0,b.types[k]?.n??0);
lines.push('','Transition A:7/76=9.21% vs10/87=11.49% among paired labels (7/95 and10/99 among all entries). All counts and missing denominators are preserved in JSON. MFE6-MFE3 median0 in both groups: later favorable extension is not universal.','', '## Separate groups and sessions','');
for(const [name,g] of Object.entries(x.groups)){
 lines.push('### '+name,'','| Side | N | Immediate adverse | Adverse -> net6 positive |','|---|---:|---|---|');
 for(const side of ['ALL','SHORT','LONG']){const z=g[side],v=z.adverseToPositive[6];lines.push(`| ${side} | ${z.n} | ${z.immediate.count}/${z.immediate.valid} | ${v.positive}/${v.valid} |`);}
 lines.push('','LONG exploratory only:9 and14 entries; no reliable side-specific policy conclusion.','', '| Session | ENTER | Adverse/valid1 | Recovered by3 | Recovered by6 | Mean MAE6 | Mean MFE6 |','|---|---:|---|---|---|---:|---:|');
 for(const z of g.sessions)lines.push(`| ${z.sessionDate} | ${z.n} | ${z.immediate.count}/${z.immediate.valid} | ${z.recovery[3].recovered}/${z.recovery[3].valid} | ${z.recovery[6].recovered}/${z.recovery[6].valid} | ${fmt(z.mae6.mean)} | ${fmt(z.mfe6.mean)} |`);
}
lines.push('','## Interpretation and limits','', 'FOR: first-bar adverse concentration replicates; observed recovery by6 is51/60 and56/65; adverse-to-net6-positive32/53 and38/63; MAE-before-MFE34 and36 exceeds opposite20 and23; next selected72/95 and78/99.','', 'AGAINST/uncertainty: many reverse-order or unavailable paths; same-bar extrema order unknown3/5; recovery-to-reference is weaker than sustained net-positive; no executable price/spread/queue evidence or counterfactual wait comparison. Hybrid has no direction, so same/opposite directional persistence is not identifiable. Holdout is earlier historical diagnostic with prior Selector exposure, not prospective or formal OOS. Dev uses OOF fold models while Holdout uses the final58-session model. No pooled analysis, timing search, normalization revision or rule fitting.','', 'PIT: source feature/bar fingerprints verified; original runtime PIT/state0 inherited, not a fresh full-source independent audit.194 unique first entries and reference parity checked. Fresh Validation/OOS/Protected103 new access0; safety allfalse. Next: review diagnostic limitations and only with a separate instruction consider a hypothesis contract; no timing implementation in this task.');
fs.writeFileSync(`${p}/path-diagnosis-review.md`,lines.join('\n')+'\n');
