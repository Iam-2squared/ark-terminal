#!/usr/bin/env python3
"""Japanese C6 interpretation / proposed contract, with no decisions, fits or searches."""
import argparse,base64,csv,html,json,re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
P=Path(__file__).resolve().parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--basis',required=True);args=ap.parse_args()
def load(n):return json.loads((P/n).read_text())
S=load('GEOMETRY_SUMMARY.json');M=load('MISS_WINNER_ANALYSIS.json');T=load('TIME_GEOMETRY.json');A=load('INDEPENDENT_AUDIT.json');C=load('METRIC_CONTRACT.json');F=load('POPULATION_FREEZE.json')
assert A['status']=='ENTRY_GEOMETRY_BASELINE_AUDIT_PASS' and A['mismatch_count']==0
ARMS=['IMMEDIATE','R1'];JST=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat()
BUDGET=dict.fromkeys(['new_entry_model_fits','state_model_fits','exit_model_fits','threshold_searches','new_policy_replays','provider_requests','Protected_open','Holdout_open','Validation_new_open','OOS_open','Prospective_open','orders','paper_trades','live_trades','main_merges','bootstrap'],0)
SAFETY=dict.fromkeys(['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted'],False)
def num(x,d=3):return 'UNKNOWN' if x is None else f'{x:,.{d}f}'
def table(headers,rows):
 def cell(x):return str(x).replace('|','\\|').replace('\n',' ')
 return '\n'+'| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(cell(x) for x in r)+' |\n' for r in rows)+'\n'
def compare_metric(key):
 return [key]+[f"{num(S['continuous'][a][key]['mean'])} / {num(S['continuous'][a][key]['median'])} / {S['continuous'][a][key]['known_N']}" for a in ARMS]
def fig(name,alt):return '\n!['+alt+'](FIGURES/'+name+'.png)\n\n'
cp=[(f'C{i}',load('CHECKPOINTS/'+name+'.json')) for i,name in enumerate(['C1_SOURCE_FREEZE','C2_METRIC_FREEZE','C3_JOIN','C4_GEOMETRY_RESULTS','C5_INDEPENDENT_AUDIT'],1)]
heads={'C1':'08c914a65f5938bd87c407ecd431062ebcc43a78','C2':'08b99052f37db12a7ee0ac956967a5b3e5899a9e','C3':'987c0be273eb41a2a52b36d7ede627427921d2fd','C4':'895b7553fe24bb1e241ed217b78ba0c2439379ef','C5':args.basis}
header=f'''# 📐 Ark Terminal — Entry Geometry / Capture Baseline

- **現在status:** ENTRY_GEOMETRY_BASELINE_AUDIT_PASS + HYBRID_ENTRY_NEXT_SPEC_DRAFT_READY
- **latest HEAD（C6作業開始時のGitHub GET）:** `{args.basis}`
- **JST（この報告生成時の実時刻）:** {JST}
- **完了範囲:** C1 source freeze、C2 metric freeze、C3 saved join、C4 13表枠・7図、C5 独立監査、C6 解釈・次仕様草案。
- **次の方針:** 別の有限PrecommitでHybrid Entryのfit可否を判断する。草案statusは **PROPOSED_NOT_AUTHORIZED**。今回のfitは0。

Document ID: `WORK_ENTRY_GEOMETRY_CAPTURE_BASELINE_20261002_V1`

C6保存結果のHEADはGitHub commit自体が正本であり、本文で未来のSHAを予測しない。納品receiptと最終応答に保存後GETで確認したresult HEADを記録する。

## 🧭 結論と適用範囲

R1は中央値でSelector上昇余地の**88.316%**を残すが、IMMEDIATEの**95.760%**を下回る。残存upside中央値は**1.672%**、session-end MAE中央値は**−1.606%**である。同じOpportunityの共通known 1,868件では、R1は残存upside平均を**0.255 pp**失う一方、MAE平均は**0.223 pp**浅くなる。利益・実現P&L・exit性能・昇格の証拠ではない。

R1のRetention平均**102.176%**は、小さい正のSelector MFEを分母にした大きな比率に影響される。全体平均だけで改善とは判断しない。Winner ≥1%のRetention平均は**79.746%**、中央値は**86.337%**である。0〜100へのclip、UNKNOWNの0補完、標本の独立数への水増しは行っていない。

これは保存済み・既にoutcome-exposedなDevelopmentのdescriptive baselineである。各armの分母は同じ2,155 Opportunity、58 sessions、950 symbols。armごとのknown-only平均にはfill選択・missingness・残り観測時間が異なる。以下のfuture outcomeはすべて**evaluator-only / future-outcome-used**であり、decisionには使用しない。

## 🧊 C1/C2 — Sourceと意味の固定

Original Frozen Selectorの3,800 rows / 760 timestamps / 76 sessions / 934 symbolsと、今回のcanonical Entry 2,155 Opportunities / 58 sessions / 950 symbolsは別の保存lineageである。3,800を2,155へ切り詰めたり、元のTRAIN38 / VALIDATION19 / DEVELOPMENT_TEST19を現在母集団へ再適用したりしていない。38/19/19はCheckpoint 00の保存receiptを権威とする。現在の58 sessionsは2025-05-30〜2025-08-25の旧Entry研究で既にexposedであり、新しいValidation/OOS openではない。

`ENTRY_DUAL_FREEZE_R10.json`が正式に保持するIMMEDIATEとAll-Material R1だけを比較した。R1 frozen entry-records SHA-256は`15ddb5cfc5169024878ee72d9dbecc6e1d9dec24e78afa2dcdf8dea891117fa6`、saved raw-path SHA-256は`37853e73799544be6fd6eb955de514073dd13671692426291a9fdb6d80056c6b`。全sourceのGit blob・SHA-256・HEAD・exposureはSOURCE_MANIFEST.jsonにある。

保存済み`orderedOracle`は最大の**strict Low→High rebound**であり、global Low/Highとは異なる。従来のquality、Entry position、range retention、oracleはそのまま別欄に保持した。global extremaの時刻と厳密なEntry後最大Highは未保存のため、許可された保存raw pathから機械的に計算した。新Replay・fill生成・provider取得はない。

Selector→Highは権威ある保存済み`selectorOutcome.mfeEnd`を利用し、継承されたmax(0,...)を保つ。負のunclipped global-high returnは別診断欄に保存した。Entry→Later Highは**Entry minuteよりstrictに後のbar**の最大HIGHを使う。Entry barのHighを含むcanonical saved MFEによるCaptureとは分離する。両者を混ぜない。

Lowはpost-Selectorの観測global Lowである。Low minute≤Entry minuteだけをLow→Entryとし、LowがEntry後ならEntry→Future Lowのdownsideとして保存する。同一bar内のLow/Entryの実順序は不明である。global Lowであったと確定すること自体はfuture outcomeなので、過去running Lowのcausal featureとは区別する。

primary extremaはcanonical full-session admissionが通った行だけ評価する。このadmissionは保存sourceのslot/endpoint完全性であり、毎minuteの全取引を観測した保証ではない。30/60m MAEは保存ラベルと元のCOMPLETE/PARTIAL/CENSORED statusを保持する。

active minutesはAM09:00–11:30とPM12:30–15:30の区間長。昼休み60分を除外し、wall-clockを別欄に保存する。bucket境界はC2から固定のままである。

## 📋 TABLE 1 — 母集団・fill・unknown・oracle
'''
report=header
t1=S['tables']['01_population']
report+=table(['項目','IMMEDIATE','R1'],[[k,t1['IMMEDIATE'][k],t1['R1'][k]] for k in ['population_N','unique_opportunity_N','sessions','symbols','fill_N','no_entry_N','canonical_full_session_evaluable_N','selector_outcome_known_N','strict_later_high_known_N','saved_entry_outcome_known_N']])
report+=table(['remaining upsideのunknown理由','IMMEDIATE','R1'],[[k,t1['IMMEDIATE']['remaining_unknown_reason_counts'].get(k,0),t1['R1']['remaining_unknown_reason_counts'].get(k,0)] for k in ['NO_ENTRY','FULL_SESSION_NOT_EVALUABLE','NO_STRICTLY_LATER_HIGH','JOIN_MISMATCH']])
report+='Selector outcome UNKNOWN63件はWinnerに割り当てない。fillしてもfull-sessionが評価できない行はIMMEDIATE22件、R1 17件。join missing・重複・identity不一致はすべて0。NO_ENTRY理由は両armとも保存上RETRY_EXHAUSTEDである。\n\n'
report+='## 📈 TABLE 2 — Selector→High\n'
report+=table(['Selector upside bucket','N（各arm共通）'],[[b,S['tables']['02_selector_to_high']['IMMEDIATE']['bucket_counts'][b]] for b in C['buckets']['selector_to_high_pct']['labels']+['UNKNOWN']])
st=S['continuous']['IMMEDIATE']['selector_to_high_pct']
report+=f"known N={st['known_N']}、平均{num(st['mean'])}%、中央値{num(st['median'])}%。全quantileとmin/maxは付録にある。\n\n"
report+='## 🚀 TABLE 3 — Entry→Later High\n'
report+=table(['remaining upside bucket','IMMEDIATE N','R1 N'],[[b,S['tables']['03_entry_to_later_high']['IMMEDIATE']['bucket_counts'][b],S['tables']['03_entry_to_later_high']['R1']['bucket_counts'][b]] for b in C['buckets']['entry_to_later_high_pct']['labels']+['UNKNOWN']])
report+=table(['指標（%）','IMMEDIATE 平均 / 中央値 / known N','R1 平均 / 中央値 / known N'],[compare_metric('entry_to_later_high_pct'),compare_metric('entry_mae_end_pct'),compare_metric('entry_mae_30_pct'),compare_metric('entry_mae_60_pct')])
report+=fig('01_remaining_upside_distribution','IMMEDIATEとR1のstrictly later High return分布')
report+='## 📉 TABLE 4 — Upside Retention\n'
report+=table(['Retention（%）','IMMEDIATE','R1'],[[k,num(S['continuous']['IMMEDIATE']['upside_retention_pct'][k]) if k not in ['N','known_N','unknown_N'] else S['continuous']['IMMEDIATE']['upside_retention_pct'][k],num(S['continuous']['R1']['upside_retention_pct'][k]) if k not in ['N','known_N','unknown_N'] else S['continuous']['R1']['upside_retention_pct'][k]] for k in ['N','known_N','unknown_N','mean','median','p5','p25','p75','p90','p95','min','max']])
report+=table(['clipせず保持した行','IMMEDIATE','R1'],[[k,S['tables']['04_upside_retention']['IMMEDIATE'][k],S['tables']['04_upside_retention']['R1'][k]] for k in ['negative_N','greater_than_100_N']])
report+='100%超はEntry価格改善等によりEntry基準の上昇率がSelector基準を上回ることを含む。負値はstrictly later HighでもEntry価格に届かないことを示す。小さい分母のratioは不安定で、平均が中央値より高くても優位のGateにはならない。図は全データを表示し、軸だけをsymmetric logにしている。\n\n'
report+=fig('02_retention_distribution','clipしないRetentionの全観測範囲CDF')
report+='## 📏 TABLE 5 — Low→Entry（Low≤Entryのみ）\n'
report+=table(['Ordering','IMMEDIATE','R1'],[[k,S['tables']['05_low_to_entry']['IMMEDIATE']['ordering_counts'].get(k,0),S['tables']['05_low_to_entry']['R1']['ordering_counts'].get(k,0)] for k in ['LOW_AT_OR_BEFORE_ENTRY','LOW_AFTER_ENTRY','LOW_UNKNOWN','NO_ENTRY']]+[['same-bar真の順序不明',245,109]])
report+=table(['Low→Entry bucket','IMMEDIATE N','R1 N'],[[b,S['tables']['05_low_to_entry']['IMMEDIATE']['bucket_counts'][b],S['tables']['05_low_to_entry']['R1']['bucket_counts'][b]] for b in C['buckets']['low_to_entry_pct']['labels']])
report+=table(['指標（%）','IMMEDIATE 平均 / 中央値 / known N','R1 平均 / 中央値 / known N'],[compare_metric('low_to_entry_pct')])
report+='Low distanceとremaining upsideのSpearmanはIMMEDIATE +0.015（joint known309）、R1 +0.056（joint known624）。この限定母集団では「Lowから離れるほどremaining upsideが減る」という単調関係を確認できない。Opportunityの大きさ・価格基準・将来Low順序への条件付けが混在するため、causal効果ではない。\n\n'
report+=fig('03_low_distance_vs_remaining','LowがEntry以前の行だけのLow distanceとremaining upside')
report+='## 🔻 TABLE 6 — LOW_AFTER_ENTRYのdownside\n'
report+=table(['arm','cohort N / known N','Future Low 平均%','Future Low 中央値%','saved MAE 平均%','saved MAE 中央値%'],[[a,S['tables']['06_low_after_entry'][a]['total_N'],num(S['tables']['06_low_after_entry'][a]['geometry']['entry_to_future_low_pct']['mean']),num(S['tables']['06_low_after_entry'][a]['geometry']['entry_to_future_low_pct']['median']),num(S['tables']['06_low_after_entry'][a]['geometry']['entry_mae_end_pct']['mean']),num(S['tables']['06_low_after_entry'][a]['geometry']['entry_mae_end_pct']['median'])] for a in ARMS])
report+='このfuture-Low cohortではFuture Low returnとsaved MAEが一致する。R1全体のMAEは浅くても、このcohortのMAEはIMMEDIATEより深い。future Lowを「Lowから上でEntryした距離」に混ぜると、この差を見落とす。\n\n'
report+='## ⏱️ TABLE 7 — Selector→Entry delay\n'
report+=table(['active delay bucket','IMMEDIATE fills N','R1 fills N'],[[b,S['tables']['07_selector_to_entry_delay']['IMMEDIATE']['bucket_counts'][b],S['tables']['07_selector_to_entry_delay']['R1']['bucket_counts'][b]] for b in C['buckets']['selector_to_entry_active_minutes']['labels']+['UNKNOWN']])
report+=table(['時間指標（minutes）','IMMEDIATE 平均 / 中央値 / known N','R1 平均 / 中央値 / known N'],[compare_metric('selector_to_entry_active_minutes'),compare_metric('selector_to_entry_wall_minutes')])
rows=[]
for b in C['buckets']['selector_to_entry_active_minutes']['labels']:
 for a in ARMS:
  x=T['delay_buckets'][a][b];g=x['geometry'];rows.append([b,a,x['total_N'],g['entry_to_later_high_pct']['known_N'],num(g['entry_to_later_high_pct']['mean']),num(g['entry_to_later_high_pct']['median']),num(g['entry_mae_end_pct']['median']),num(x['remaining_at_least_pct_of_known']['2'],2),num(x['remaining_at_least_pct_of_known']['3'],2)])
report+=table(['delay','arm','N','known','remaining平均%','remaining中央値%','MAE中央値%','remaining≥2% share','remaining≥3% share'],rows)
report+='R1は0mと6–10mでremaining中央値が2%超だが、6–10mのknownは64件。11–20mは平均2.892%・中央値1.619%、≥2%が43.04%、≥3%が28.92%。21–30mにも≥2%が31.51%残る。ただしdelayの最適上限を探索した結果ではなく、10mまでなら安全というGateも作っていない。>30mは保存fill0件で推論不能。\n\n'
report+='delayとremainingのSpearmanはIMMEDIATE −0.118、R1 −0.131。delayとsigned MAEは+0.197、+0.076で、後者の正値は逆行が浅い方向である。待機によるprice改善・fill選択・time-of-day・終値までの露出時間が絡むので、待てば必ず改善するとは結論しない。\n\n'
report+=fig('05_delay_geometry','固定delay bucket別remaining upsideとMAE')
report+='## ⌛ TABLE 8 — Entry→Highの残り時間\n'
report+=table(['remaining active time bucket','IMMEDIATE N','R1 N'],[[b,S['tables']['08_entry_to_high_time']['IMMEDIATE']['bucket_counts'][b],S['tables']['08_entry_to_high_time']['R1']['bucket_counts'][b]] for b in C['buckets']['entry_to_high_active_minutes']['labels']+['UNKNOWN']])
report+=table(['時間指標（minutes）','IMMEDIATE 平均 / 中央値 / known N','R1 平均 / 中央値 / known N'],[compare_metric('entry_to_high_active_minutes'),compare_metric('entry_to_high_wall_minutes')])
report+='Entry後Highまでactive中央値は39m / 36m。昼休みを跨ぐEntry→Highは456 / 478件、Selector→Entryは167 / 154件で、独立監査はそれぞれwall-active=60mを確認した。残りHigh時刻もfuture outcomeであり、当時のdecision featureではない。\n\n'
report+='## 🎯 TABLE 9 — Winner Capture / Missed\n'
rows=[]
for t in ['1','2','3','5']:
 for a in ARMS:
  d=M['canonical_capture'][a][t];cc=d['counts'];rows.append(['+'+t+'%',a,d['selector_winner_N'],cc['CAPTURED'],cc['NO_ENTRY'],cc['ENTERED_BUT_BELOW_THRESHOLD'],cc['OUTCOME_UNKNOWN'],d['known_missed_N'],num(d['capture_pct_of_all_winners'],2)])
report+=table(['Selector Winner','arm','Winner N','CAPTURED','NO_ENTRY','entered below','UNKNOWN','known missed','Capture%'],rows)
report+='canonical Captureは保存MFEを権威としEntry barを含む。strict-later sensitivityのCapture率は以下。UNKNOWNをmissへ合算していない。ここではWinnerのentered outcome UNKNOWNは全thresholdで0だが、Selector UNKNOWN63件は別途残る。\n\n'
report+=table(['threshold','IMMEDIATE canonical% / strict%','R1 canonical% / strict%'],[['+'+t+'%']+[num(M['canonical_capture'][a][t]['capture_pct_of_all_winners'],2)+' / '+num(M['strict_later_sensitivity'][a][t]['capture_pct_of_all_winners'],2) for a in ARMS] for t in ['1','2','3','5']])
report+=fig('06_winner_capture','固定1,2,3,5% thresholdのCaptureとMissed、Unknown')
report+='### 🧩 Missedの内訳と遅延の関連\n'
rows=[]
for t in ['1','2','3','5']:
 for a in ARMS:
  ch=M['entered_below_threshold_chronology'][a][t];d=M['canonical_capture'][a][t];rows.append(['+'+t+'%',a,d['counts']['NO_ENTRY'],ch['global_high_at_or_before_entry_N'],ch['global_high_after_entry_N'],d['counts']['OUTCOME_UNKNOWN']])
report+=table(['threshold','arm','no entry','entered below: global High≤Entry minute','entered below: global High>Entry minute','outcome unknown'],rows)
report+='R1の+1% known missed439件はNO_ENTRY133、High≤Entry minute190、Highが後でもEntry基準upside不足116。+5% missed122件は18 / 23 / 81。+5%では、単にglobal Highを過ぎたことよりも、Highが後に存在してもEntry price基準で5%が残らない分類が多い。High≤Entryは同一barを含むchronology proxyであり、遅いEntryが原因と確定した件数ではない。NO_ENTRYは全件保存上RETRY_EXHAUSTEDであり、価格・流動性不足のcausal内訳は追加推測しない。\n\n'
report+='## 🪜 TABLE 10 — Selector upside bucket × Geometry\n'
rows=[]
for b in C['buckets']['selector_to_high_pct']['labels']:
 for a in ARMS:
  d=S['tables']['10_selector_upside_bucket'][a][b];g=d['geometry'];rows.append([b,a,d['total_N'],g['entry_to_later_high_pct']['known_N'],num(g['entry_to_later_high_pct']['median']),g['upside_retention_pct']['known_N'],num(g['upside_retention_pct']['mean']),num(g['upside_retention_pct']['median'])])
report+=table(['Selector bucket','arm','N','remaining known','remaining中央値%','retention known','retention平均%','retention中央値%'],rows)
report+=fig('04_selector_bucket_geometry','Selector上昇余地bucket別remaining upsideとRetention中央値')
rows=[]
for t in ['1','2','3','5']:
 for a in ARMS:
  d=M['winner_geometry'][a][t];g=d['geometry'];rows.append(['≥'+t+'%',a,d['total_N'],g['upside_retention_pct']['known_N'],num(g['upside_retention_pct']['mean']),num(g['upside_retention_pct']['median']),num(g['entry_to_later_high_pct']['median'])])
report+=table(['Winner帯','arm','Winner N','known','Retention平均%','Retention中央値%','remaining中央値%'],rows)
report+='R1でもSelector 3–5%帯のremaining中央値3.134%、5–10%帯5.576%、≥10%帯13.757%が残る。Lowぴったりを要求せず、当時のcausal情報からこうした機会を維持し、downsideを同時に見る余地がある。ただしSelector Winner帯はfuture outcomeによる評価用分類であり、当時のSelector scoreをそのままWinner確率とはみなさない。\n\n'
report+='## 🕘 TABLE 11 — Time-of-day × Geometry\n'
rows=[]
for b in C['time_of_day_bands']:
 for a in ARMS:
  d=T['selector_time_of_day'][a][b];g=d['geometry'];rows.append([b,a,d['total_N'],g['entry_to_later_high_pct']['known_N'],num(g['entry_to_later_high_pct']['median']),num(g['entry_mae_end_pct']['median']),num(g['entry_to_high_active_minutes']['median'])])
report+=table(['Selector時刻 JST','arm','N','known','remaining中央値%','MAE中央値%','Highまでactive中央値m'],rows)
report+=fig('07_time_of_day_geometry','Selector time-of-day別remaining upsideとMAE')
report+='R1の朝09–10時remaining中央値2.580%に対し15–15:30は0.317%。session-endまでの観測時間が異なるため、時間帯と残りactive時間を次研究の必須controlにする。Entry時刻別の同形式全統計もTIME_GEOMETRY.jsonに保存した。\n\n'
report+='## 🧬 TABLE 12 — State9 Geometryの可用性\n\n**NOT_AVAILABLE_EXACT_SOURCE_JOIN_NOT_CERTIFIED**。保存Entryのnine-pattern sourceは旧State-v3 contractであり、最終RC2 State9と同一ではない。RC2 V3/V6のsaved trace source identityと、このEntryのsymbol/session・raw price basisとの正確な同一性を認証できなかった。近時刻join・ラベル名置換・State再生成は行わず、旧StateをRC2の差として報告しない。State9別Geometry差は今回回答不能。これは許可されたNOT_AVAILABLE receiptであり、baselineの算術PASSを妨げない。\n\n'
report+='## 🧮 TABLE 13 — Session / symbol concentration\n'
report+=table(['単位','unique N','最大share%','top5 share%','top10 share%','HHI','機会数min / median / max'],[[k,d['unique_N'],num(d['top1_share_pct']),num(d['top5_share_pct']),num(d['top10_share_pct']),num(d['HHI'],6),num(d['population_counts']['min'],0)+' / '+num(d['population_counts']['median'],0)+' / '+num(d['population_counts']['max'],0)] for k,d in S['tables']['13_concentration'].items()])
for key in ['session','symbol']:
 d=S['tables']['13_concentration'][key]
 report+=table([key+' 上位5','Opportunity N','share%','IMMEDIATE fills / remaining known','R1 fills / remaining known'],[[r['value'],r['opportunity_N'],num(r['share_pct']),str(r['arms']['IMMEDIATE']['fill_N'])+' / '+str(r['arms']['IMMEDIATE']['remaining_known_N']),str(r['arms']['R1']['fill_N'])+' / '+str(r['arms']['R1']['remaining_known_N'])] for r in d['top20'][:5]])
report+='同じsymbolの複数sessionと同じsessionの複数symbolは独立標本とは宣言しない。全58 sessions・950 symbolsのfill / known / remaining統計・+5% Capture件数をCONCENTRATION.jsonに保持する。新しいconcentration Gateや有意性Gateは作らない。\n\n'
report+='## 🔍 C5 — 独立監査と共通known比較\n'
report+=table(['検証','結果'],[['status',A['status']],['機械的チェック数',A['total_checks']],['mismatch',A['mismatch_count']],['絶対許容差 pct',A['tolerance_pct']],['最大観測絶対誤差',max(A['max_absolute_errors'].values())],['原本hash / counts / identity / ordering / buckets / lunch / Capture','PASS'],['UNKNOWNの0補完 / future decision use','false / false']])
report+='主join・主aggregateをimportせず、保存原本からDecimal比率、streaming extrema、trading区間との交差時間、手動sorted quantileで再計算した。既存scorecardは再計算の入力ではなく、最後のCapture parity authorityとして使用した。+5と+3の分母区別、Entry前High不使用、Entry後Lowをdistanceに混ぜないことも確認した。\n\n'
rows=[]
for k,d in S['paired_common_known'].items():
 rows.append([k,d['common_known_N'],num(d['IMMEDIATE']['mean']),num(d['R1']['mean']),num(d['R1_minus_IMMEDIATE']['mean']),num(d['R1_minus_IMMEDIATE']['median'])])
report+=table(['指標（%またはminutes）','共通known N','IMMEDIATE平均','R1平均','paired差 R1−IM平均','paired差中央値'],rows)
report+='paired Retention差の平均は+16.437 ppでも中央値差は0。ratio tailを除去せず保持した結果であり、残存upsideのpaired平均差−0.255 ppと併せて読む。新bootstrap・CI・performance significance Gateはない。\n\n'
report+='## 🧭 C6 — 10の問いへの回答と次研究\n'
answers=[
 ('Selector Opportunityを何%残すか','全体Retention mean / medianはIMMEDIATE 85.385 / 95.760%、R1 102.176 / 88.316%。known Nは1,827 / 1,757で、ratio tailと選択差を伴う。'),
 ('Winner帯でも維持するか','R1の≥3% Winner Retention mean / medianは82.427 / 90.143%、≥5%は86.181 / 93.936%。上昇余地は残るがIMMEDIATEよりCaptureを失う。'),
 ('Lowからどれだけ上か','Low≤EntryのみR1 mean / median 1.650 / 1.084%、known624。その他を同じLow-distanceへ混ぜない。same-bar109件は真の順序不明。'),
 ('Lowから離れるとupsideが減るか','R1 Spearman+0.056で単調減少を確認できない。futureで条件付けた限定cohortであり、因果関係は判断できない。'),
 ('delayとremaining','弱い負の関連。R111–20mのknown1,020で中央値1.619%、21–30mのknown238で1.105%。'),
 ('delayとMAE','signed MAEと弱い正の関連。全体paired平均は0.223 pp浅いが、session-end露出時間とfill選択の違いを含む。'),
 ('どの程度のdelayで数%残るか','R1は0m・6–10mでmedian>2%。11–20mでも43.04%が≥2%、28.92%が≥3%。次specは時間帯・機会強度をcontrolし、任意のdelay閾値を今決めない。'),
 ('Missedの主因','既知分類ではR1はentered belowが多い。+5% missed122はno-entry18 / global High≤Entry23 / Highが後でもupside不足81。causal理由の確定ではない。'),
 ('State9差','正確な最終RC2 join未認証のため回答不能。State-v3は代用しない。'),
 ('次に見るcausal family','最低限は価格構造 + Selector時点の保存情報 + active delay/time-of-day。RC2 State9はidentity認証後の追加family候補。volume/liquidityはその次にsource可用性を固定して1familyずつ。relative strength・market/sector・volatilityは後続候補。')]
report+=table(['問い','Evidenceからの回答'],answers)
report+='対象は「底ぴったり」ではなく、**Entry後に数%のupsideが残り、downsideとのバランスが良いEntry**。まだ「良いdownside」の許容値をfitや探索で決めていない。NEXT_HYBRID_ENTRY_SPEC_DRAFT.mdへtarget / metric / minimum feature / missingness / audit / bounded research案を保存し、PROPOSED_NOT_AUTHORIZEDで停止する。\n\n'
report+='## 🛡️ V6結論・実行境界\n'
report+=table(['V6既存結論（再実行なし）','R1 dangerous UP→DOWN','R2 Full State9','improvement pp','95% CI pp'],[['V6-only','10.186757%','9.665227%','+0.521530','[−1.630718, +2.367065]'],['V5+V6 pooled','11.025943%','9.671848%','+1.354095','[−0.171312, +2.723970]']])
report+='STATE_R2_SIGNAL_NOT_REPLICATED、calibration FAIL、pooled dangerous PASS=falseを維持する。TRUE_NULL / sample / concentration / independent audit / core auditは既存PASS、mismatch=0、direct future leakageなし。R2 probabilityや未検証rankをEntry thresholdへ使わない。State / Path / 既存target定義を変更せず、自動Hybrid fit・promotionはしない。\n\n'
report+=table(['実績counter','値'],[[k,v] for k,v in BUDGET.items()])
report+=table(['Safety','値'],[[k,str(v).lower()] for k,v in SAFETY.items()]+[['方向 / 商品','LONG-only / cash-equity-only']])
report+='## 📚 付録 — 全主要連続指標の必須統計\n\nNは各armの全2,155行。knownのみから統計量を計算し、unknownは残す。Low→Entry / Future Lowは対象外のorderingもunknown側に含むため、対象cohort統計と併読する。quantileはlinear type7。単位は末尾pctが%、minutesが分。\n\n'
statkeys=['N','known_N','unknown_N','mean','median','p5','p25','p75','p90','p95','min','max']
for a in ARMS:
 report+='### 📊 '+a+'\n'
 report+=table(['metric']+statkeys,[[k]+[d[x] if x in ['N','known_N','unknown_N'] else num(d[x]) for x in statkeys] for k,d in S['continuous'][a].items()])
report+='全数値の精度を保つJSONはGEOMETRY_SUMMARY.json、CSVはCONTINUOUS_STATISTICS.csv。fillを分母としたknown / unknownもJSONに保存する。missingnessはMISSINGNESS.json、joinはJOIN_AUDIT.json、機械的raw計算receiptはC3_RECEIPT.json、State9不使用receiptはSTATE9_GEOMETRY_NOT_AVAILABLE.json。\n\n'
report+='## 💾 Checkpoint / 正本\n'
report+=table(['Checkpoint','saved_at_jst（実時刻）','basis HEAD','result HEAD（保存後GET確認）'],[[stage,obj['saved_at_jst'],obj['basis_head'],heads[stage]] for stage,obj in cp])
report+='C6はCHECKPOINTS/C6_INTERPRETATION.md/jsonへ実際の保存時刻と上記C5 result HEADをbasisとして保存する。result HEADはcommit自体を権威とする。force push / main mergeなし。\n'
(P/'REPORT-ja.md').write_text(report)
with (P/'CONTINUOUS_STATISTICS.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['arm','metric','unit']+statkeys)
 for a in ARMS:
  for key,d in S['continuous'][a].items():w.writerow([a,key,'pct' if key.endswith('_pct') else 'minutes']+[d[k] for k in statkeys])

draft=f'''# 🧩 NEXT HYBRID ENTRY SPEC — 草案

**status: PROPOSED_NOT_AUTHORIZED**  
Document ID: WORK_ENTRY_GEOMETRY_CAPTURE_BASELINE_20261002_V1  
generated_at_jst: {JST}  
basis_head: {args.basis}  
prerequisite: ENTRY_GEOMETRY_BASELINE_AUDIT_PASS（2,155 Opportunities / 58 sessions / 950 symbols / mismatch=0）

## 🎯 研究対象と根拠

目的はLowとの完全一致ではなく、causal情報から、Entry後のupsideを数%残しながらdownsideとのバランスを取ること。R1の残存upside中央値1.672%、MAE中央値−1.606%、+5% Capture70.098%。共通known1,868件ではIMMEDIATE比でremaining平均−0.255 pp、MAE平均+0.223 pp。時間を使ってdownsideだけ浅く見せる候補を自動採用しない。

global Low≤Entry cohortでLow距離とupsideの単調減少を確認できない。未来global Lowを待つ設計へ戻らない。future Winner帯ならR1の残存upsideは3–5%帯中央値3.134%、5–10%帯5.576%あるが、Winner membershipをdecision featureとして使えない。

## 🧊 引き継ぐ凍結境界

IMMEDIATE / R1、canonical Opportunity identity、Selector PIT price、saved next-open+5bps価格basis、session calendar、State9 RC2 / Path / 既存target定義を維持。V6は終了しSTATE_R2_SIGNAL_NOT_REPLICATED / calibration FAILのまま。R2 probabilityまたは未検証rankをEntry thresholdに利用しない。State9はcausal categorical feature family候補であり、今回State-only判断や新fitはない。

今回の2,155母集団はoutcome-exposed Development。ここを新OOSとして扱わない。元の76 session splitとは別lineageなので38/19/19を流用しない。新しいpartition・学習/選択/評価の境界は別Precommitで固定する。

## 📏 評価target / metric案

| 役割 | 草案 | 次Precommitで固定する条件 |
| --- | --- | --- |
| primary upside | Entryよりstrictに後のbarのsession-end maximum High return（clipなし） | 観測window・bar timestamp・full-session admissionをbaselineと照合 |
| primary downside | canonical saved session-end MAE（signed） | late Entryの短い露出時間をtime-of-day / remaining active timeで分離 |
| joint target候補 | remaining upside≥u かつ MAE≥−d | uは既存1/2/3/5%の有限候補。数%という目的には2%をprimary候補とするが**未承認**。dは未選択で、業務許容値を結果閲覧前に固定 |
| secondary upside | upside retention、Selector Winner 1/2/3/5%のcanonical Capture / strict-later sensitivity | 正のSelector MFEのみratio。小分母と100超/負値を保持 |
| secondary downside | 既存30/60m MAEとstatus / missingness | 元のhorizon clock・COMPLETE/PARTIAL/CENSORED semanticsを監査し、未認証なら使用しない |
| missed analysis | NO_ENTRY / entered below / OUTCOME_UNKNOWN、global High≤Entryのchronology proxy | UNKNOWNをmissにしない。時刻proxyを因果理由へ昇格しない |
| timing | active delay、Entry後Highまでのactive残り時間、JST time-of-day | 昼休みを除外。将来High時刻は評価専用 |
| descriptive controls | 共通Opportunity / 共通known比較、固定bucket、session/symbol concentration | fill率・unknown率・母集団の変化も評価 |

今のend-of-session Geometryと、将来の固定horizon比較は同一ではない。固定horizonが必要なら、別Precommitでclockとlabel sourceを定めてから実装可否を判断し、現在のState / Path / targetを上書きしない。許容downside d、fit数、モデルclass、選択回数、split、promotion Gateは本草案では未承認。

## 🧬 最低限のcausal featureと有限な追加順序

| 段階 | family | 必要性 / 可用性 |
| --- | --- | --- |
| A | price structure / turning point | decision cutoffまでの価格変化、当時までのrunning High/Lowからの距離、少数の固定recent return / higher-low確認。global future Low/Highはfeature禁止 |
| A | Selector information | exact PIT Selector price、当時保存のscore/rank等。未来Selector MFE / Winnerはfeature禁止。score/rankを確率扱いしない |
| A | active delay / time-of-day | upsideとdownsideに露出時間差があるため最低限のcontrol。時計由来で新provider不要 |
| B | State9 RC2 | 正確なsymbol/session/as-of/sourceHash/価格basisの認証後に1family追加。旧State-v3置換は禁止。未認証ならAだけを評価する契約を別途承認 |
| C | volume / liquidity | saved causal sourceのcoverage、staleness、spread/turnover proxy、fill retryの欠測を先に固定。その後1family追加で価値を比較 |
| 後続 | relative strength / market・sector context / volatility | sourceと時間契約を認証し、A/B/CのEvidenceから必要性を決める。一度に全部fitしない |

過去running Lowを使う場合も、それがsessionのglobal Lowになるかは不明。decision featureは当時の履歴だけ、teacher/evaluatorのfuture Geometryは別schemaとする。as-of以後のbar OHLC、global extrema時刻、Selector Winner、capture label、Entry MAE/MFE、現在報告のbucketはdecision inputへ流さない。

## 🧪 次の有限Precommitに必要な項目

1. source/identity/price/horizon/clockの契約と各feature cutoffをhash固定し、State9 RC2の正確なsaved joinを可用性監査する。
2. primary target、downside許容値、training/selection/evaluation split、finite fit budgetと候補順序を、次の結果閲覧前に固定する。
3. 既存armと同じ全Opportunity分母を保持し、fill / no-entry / unknown・時間帯・Winner帯・paired Geometryを併記する。
4. Aから開始し、追加familyは1つずつ。State9-only probability/rank thresholdや全family一括fitを行わない。
5. 新decision候補のcausal auditと独立算術監査、session/symbol依存、missingness、capture/downside tradeoffを確認する。新OOS/Protected openやprovider取得の必要性が出たら、そのPrecommitの範囲外へ進まない。

## 🛑 Authorization / 実績

**HYBRID_ENTRY_NEXT_SPEC_DRAFT_READY**。これはmodel完成・fit承認・自動promotionではない。今回の新fit / threshold search / Replay / provider / bootstrap / Protected・Holdout・Validation新open・OOS・Prospective open / orders / paper / live / main mergeはすべて0。全Safety flag=false、LONG-only / cash-equity-only。別の有限Precommitで初めてfit可否を判断する。
'''
(P/'NEXT_HYBRID_ENTRY_SPEC_DRAFT.md').write_text(draft)
handoff=header.split('## 🧭')[0]+'''## 📦 正本と再開地点

SOURCE_MANIFEST.json / POPULATION_FREEZE.json / JOIN_KEY_CONTRACT.json / METRIC_CONTRACT.jsonがC1/C2 authority。GEOMETRY_ROWS.jsonl.gzとJOINED_GEOMETRY_ROWS.jsonl.gzは同一内容のalias。JOIN_AUDIT.json / MISSINGNESS.json / C3_RECEIPT.jsonがjoin証拠。GEOMETRY_SUMMARY.json / MISS_WINNER_ANALYSIS.json / TIME_GEOMETRY.json / CONCENTRATION.json / FIGURE_INDEX.json / FIGURES/が集計証拠。STATE9_GEOMETRY_NOT_AVAILABLE.jsonがRC2不使用receipt。INDEPENDENT_AUDIT.jsonが原本別経路監査。

REPORT-ja.mdとREPORT-ja.html、CONTINUOUS_STATISTICS.csvで結果を確認できる。NEXT_HYBRID_ENTRY_SPEC_DRAFT.mdはPROPOSED_NOT_AUTHORIZED。MANIFEST.jsonは各成果物のSHA-256とGit blob identityを記録する。Git commit自身をresult HEAD正本とし、commit前にSHAを捏造しない。

## 🔄 再実行してよいもの

CODE/aggregate_geometry.pyは保存join rowsだけを読むdeterministic集計・plot。CODE/independent_audit.pyは保存原本から別経路で算術検証する。旧Entry/Selector/Stateのrunner・models.pkl・provider・Replayを実行しない。原本hash検証に必要な保存ZIP authorityのpathはSOURCE_MANIFEST.jsonにある。納品bundleのdocs/evidence/（PRIMARY_SOURCES_INDEX.jsonで列挙）にはcanonical Opportunity / IMMEDIATE / saved raw / legacy State / manifestsのexact bytesがあり、FROZEN_ARTIFACT_MEMBERS/にはR1 Entry原本とscorecard原本のlossless wrapperがある。artifact ZIP全体の再hashにはC1で認証した元の保存ZIPが必要。modelは納品bundleに含めない。保存sourceのabsolute pathは元work時点のreceiptであり、別workspaceで全監査を再実行する際は原本archiveの配置対応を確認する。

## 🧭 残る課題

State9最終RC2 exact join未認証、future-end exposure時間差のcontrol、downside許容値、次の有限fit budget/splitは別Precommit課題。現在のbaselineに未解決の算術・join blockerはない。State9欠測を旧State-v3で埋めない。V6を再開せず、R2 probability/rankをEntryに昇格しない。

## 🛡️ 実行境界

new_entry_model_fits=state_model_fits=exit_model_fits=threshold_searches=new_policy_replays=provider_requests=bootstrap=0。Protected/Holdout/Validation_new/OOS/Prospective open=0、orders/paper/live/main merge=0。全Safety flag=false。LONG-only / cash-equity-only。force pushなし。

## 💾 保存済みcheckpoint
'''+table(['checkpoint','saved_at_jst','basis HEAD','result HEAD'],[[stage,obj['saved_at_jst'],obj['basis_head'],heads[stage]] for stage,obj in cp])+'''C6 result HEADは保存後GitHub GETで確認する。FINAL_SAVED_RECEIPT.json（納品bundle）と最終応答がその実際のcommitを参照する。次の作業もbranch latestをread-only GETしてから始める。
'''
(P/'FINAL_HANDOFF.md').write_text(handoff)
(P/'EXECUTION_BUDGET.json').write_text(json.dumps(dict(actuals=BUDGET,safety=SAFETY,scope='SAVED_ALREADY_EXPOSED_DEVELOPMENT_READ_HASH_JOIN_ARITHMETIC_PLOT_AUDIT',direction='LONG-only / cash-equity-only',new_entry_decisions=0),indent=2)+'\n')

# Portable HTML export of the controlled Markdown subset; exact text/numbers come from REPORT-ja.md.
def inline(s):
 s=html.escape(s);s=re.sub(r'`([^`]+)`',r'<code>\1</code>',s);s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s);return s
blocks=[];lines=report.splitlines();i=0
while i<len(lines):
 line=lines[i]
 if not line.strip():i+=1;continue
 if line.startswith('#'):
  n=len(line)-len(line.lstrip('#'));blocks.append('<h'+str(n)+'>'+inline(line[n:].strip())+'</h'+str(n)+'>');i+=1;continue
 if line.startswith('|'):
  rows=[]
  while i<len(lines) and lines[i].startswith('|'):
   vals=[v.strip() for v in lines[i].strip().strip('|').split('|')]
   if not all(re.fullmatch(r':?-+:?',v) for v in vals):rows.append(vals)
   i+=1
  blocks.append('<div class="table-wrap"><table><thead><tr>'+''.join('<th>'+inline(v)+'</th>' for v in rows[0])+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+inline(v)+'</td>' for v in row)+'</tr>' for row in rows[1:])+'</tbody></table></div>');continue
 m=re.fullmatch(r'!\[([^\]]*)\]\(([^)]+)\)',line)
 if m:
  img=P/m[2];data=base64.b64encode(img.read_bytes()).decode();blocks.append('<figure><img alt="'+html.escape(m[1])+'" src="data:image/png;base64,'+data+'"><figcaption>'+inline(m[1])+'</figcaption></figure>');i+=1;continue
 if line.startswith('- '):
  vals=[]
  while i<len(lines) and lines[i].startswith('- '):vals.append(inline(lines[i][2:]));i+=1
  blocks.append('<ul>'+''.join('<li>'+v+'</li>' for v in vals)+'</ul>');continue
 para=[]
 while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','![','- ')):para.append(lines[i]);i+=1
 blocks.append('<p>'+inline(' '.join(para))+'</p>')
css='body{font-family:system-ui,"Noto Sans JP",sans-serif;max-width:1100px;margin:42px auto;padding:0 24px;color:#1e293b;line-height:1.75;background:#fafbfc}h1{font-size:28px}h2{font-size:23px;border-bottom:2px solid #dbe7ef;margin-top:42px}h3{font-size:18px}code{background:#eaf0f5;padding:2px 5px;overflow-wrap:anywhere}.table-wrap{overflow-x:auto;margin:20px 0}table{border-collapse:collapse;width:100%;background:white;font-size:13px}th,td{padding:9px 11px;border:1px solid #d9e3ea;text-align:left;white-space:nowrap}th{background:#e8f0f6}tr:nth-child(even){background:#f7fafc}figure{margin:28px 0}img{width:100%;height:auto}figcaption{font-size:13px;color:#526578}p,li{overflow-wrap:anywhere}@media print{body{max-width:none;margin:0;background:white}h2{break-after:avoid}figure,tr{break-inside:avoid}.table-wrap{overflow:visible}table{font-size:9px}th,td{white-space:normal;padding:4px}}'
(P/'REPORT-ja.html').write_text('<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Ark Terminal Entry Geometry Baseline</title><style>'+css+'</style><body>'+''.join(blocks)+'</body></html>')
print(json.dumps(dict(status='HYBRID_ENTRY_NEXT_SPEC_DRAFT_READY',audit_status=A['status'],generated_at_jst=JST,basis_head=args.basis,report_bytes=len(report.encode()),report_html_bytes=(P/'REPORT-ja.html').stat().st_size)))
