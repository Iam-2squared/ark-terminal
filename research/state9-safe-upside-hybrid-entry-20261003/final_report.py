"""Final descriptive report and private derived-evidence package; never fits."""
import argparse
import datetime
import gzip
import hashlib
import json
from pathlib import Path
import zipfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

HERE=Path(__file__).resolve().parent;REPO=HERE.parents[1]
STATUS='SAFE_UPSIDE_ENTRY_NO_HIGH_PRECISION_CANDIDATE'
SECONDARY='STATE9_NO_INCREMENTAL_ENTRY_VALUE_ON_DEVELOPMENT'
BRANCH='state9-safe-upside-hybrid-entry-20261003-v1'
URL='https://github.com/Iam-2squared/ark-terminal/tree/'+BRANCH+'/research/state9-safe-upside-hybrid-entry-20261003'
SAFETY={k:False for k in ('executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed','paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted')}
def read(n):return json.loads((HERE/n).read_bytes())
def write(n,x):(HERE/n).write_text(json.dumps(x,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def now():return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()
def fmt(x,d=4):return 'UNKNOWN' if x is None else f'{x:.{d}f}'
def pct(x):return 'UNKNOWN' if x is None else f'{x*100:.2f}%'
def table(headers,rows):
 return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(map(str,r))+'|' for r in rows])

def figures(evaluation):
 fig,ax=plt.subplots(figsize=(9,4.5));distributions={}
 for family in ('H0','H1','H2'):
  values=np.sort([json.loads(s)['raw_score'] for s in gzip.open(HERE/f'OOF_{family}.jsonl.gz','rt')]);N=len(values)
  ax.plot(values,np.arange(1,N+1)/N*100,label=family)
  distributions[family]=dict(N=N,known_label_N=23457,unknown_label_N=41855,unit='raw logit not probability',mean=float(values.mean()),median=float(np.median(values)),
   min=float(values.min()),max=float(values.max()),**{f'p{q}':float(np.percentile(values,q)) for q in (5,25,75,90,95)})
 ax.set_xscale('symlog',linthresh=1);ax.set(xlabel='Raw logit (signed logarithmic axis; all scores retained)',ylabel='Candidate-row empirical cumulative share (%)',title='Outer-OOF raw-score distributions; no calibration claim');ax.legend()
 fig.text(.02,.01,'Each arm total N=65,312, known-label N=23,457; all points, no clipping/sampling; evaluator-only / future-outcome-used',fontsize=8);fig.tight_layout(rect=(0,.05,1,1));fig.savefig(HERE/'FIGURES/FINAL_RAW_SCORE_ECDF.png',dpi=180);plt.close(fig)
 write('RAW_SCORE_DISTRIBUTION.json',dict(status='DESCRIPTIVE_ONLY',families=distributions,score_is_probability=False,new_threshold_selection=0))
 fig,ax=plt.subplots(figsize=(9,4.5));t=list(range(1,6))
 for arm in ('IMMEDIATE','R1','H0','H1','H2'):
  rates=[evaluation['arms'][arm]['capture'][str(q)]['ratePct'] for q in t]
  ax.plot(t,rates,marker='o',label=arm)
 ax.set(xlabel='Frozen Selector Winner threshold (%)',ylabel='Captured / fixed Winner denominator (%)',title='Opportunity preservation: supported high-confidence Entry is absent',xticks=t,ylim=(0,100));ax.legend(ncol=3)
 fig.text(.02,.01,'Each arm total N=2,155; known Selector N=2,092; denominators1..5:1496/1054/761/544/408; evaluator-only / future-outcome-used',fontsize=8);fig.tight_layout(rect=(0,.06,1,1));fig.savefig(HERE/'FIGURES/FINAL_WINNER_CAPTURE.png',dpi=180);plt.close(fig)

def build_private(head):
 names=['FIRST_PASSAGE_LABELS.jsonl.gz','OOF_H0.jsonl.gz','OOF_H1.jsonl.gz','OOF_H2.jsonl.gz','INNER_OOF_H0.jsonl.gz','INNER_OOF_H1.jsonl.gz','INNER_OOF_H2.jsonl.gz','THRESHOLD_CURVES.jsonl.gz','ENTRY_CANDIDATE_RECORDS.jsonl.gz','C6_EVALUATED_ENTRY_RECORDS.jsonl.gz']
 names += [str(p.relative_to(HERE)) for p in sorted((HERE/'MODEL_ARITHMETIC').glob('*.npz'))]
 files=[]
 for name in names:
  p=HERE/name;files.append(dict(path=name,bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
 manifest=dict(status=STATUS,created_at_jst=now(),research_checkpoint_head=head,files=files,
  public_contract_receipt_source_location=URL,contains_row_level_derived_market_prices=True,public_GitHub_disclosure=False,
  raw_provider_payloads_included=False,original_model_pickle_included=False,private_H0_feature_matrix_included=False,
  source_dependencies='Use hash-pinned existing R1 archive, saved substrate and exact RC2 source/receipts. Do not re-fit or re-fetch provider data to reproduce these results.',safety=SAFETY,productionReady=False)
 outdir=REPO.parent/'deliverables';outdir.mkdir(exist_ok=True)
 archive=outdir/'Ark_State9_Safe_Upside_Private_Evidence_20261003.zip'
 note='''# 🔒 Ark State9 Safe-Upside — Private Derived Evidence

This package is for the requesting user only, not for public GitHub upload.
It contains exact fill-anchored first-passage labels, outer/inner OOF raw scores,
precommitted threshold-count curves, Entry/no-entry records, and exported model
coefficients with train-only preprocessing for independent arithmetic.

No raw provider OHLC payloads, private source-token wrappers, original pickle,
orders, protected partitions, or production deployment are included.

Status: SAFE_UPSIDE_ENTRY_NO_HIGH_PRECISION_CANDIDATE.
All three hybrid arms make NO_ENTRY on all2155 Opportunities under the frozen
90/85/80% precision/support/downside requirements. Zero fills do not imply a
measured 0% downside rate or 100% safety. No score is a calibrated probability.

Public Japanese report/contracts/source/hash/integrity receipts:
'''+URL+'\n\nSee PRIVATE_MANIFEST.json for exact bytes/hashes and source checkpoint HEAD.\n'
 with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_STORED) as z:
  for name in names:z.write(HERE/name,name)
  z.writestr('PRIVATE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');z.writestr('README.md',note)
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  for f in files:assert hashlib.sha256(z.read(f['path'])).hexdigest()==f['sha256']
 assert archive.stat().st_size<50*1024*1024
 receipt=dict(status='PRIVATE_PACKAGE_READY_NOT_PUBLIC_GITHUB',file_name=archive.name,bytes=archive.stat().st_size,sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
  files_with_row_model_evidence=len(files),public_disclosure=False,raw_provider_payloads_included=False,validation='ZIP CRC and each member SHA256 verified',private_delivery_status='PENDING')
 write('PRIVATE_EVIDENCE_PACKAGE_RECEIPT.json',receipt)
 return archive,receipt

def run(head):
 audit=read('INDEPENDENT_AUDIT.json');assert audit['gate']=='PASS' and audit['mismatch_count']==0
 evaluation=read('ENTRY_EVALUATION.json');assert evaluation['research_status']==STATUS
 inc=read('STATE_INCREMENTAL_VALUE.json');support=read('OPERATING_POINT_SUPPORT.json')['rows'];identity=read('STATE9_FINAL_IDENTITY.json');ledger=read('MODEL_FIT_LEDGER.json')
 assert ledger['completed_fits']==60 and not any(p['selected_operating_point'] for p in support)
 figures(evaluation);stamp=now();pooled=inc['pooled']
 output=['# 🚦 State9-Assisted Safe-Upside Hybrid Entry — 最終結果','',
  f'現在status: `{STATUS}`',f'補足status: `{SECONDARY}`',
  f'監査: `{audit["status"]}` / mismatch=0',f'latest HEAD（本文生成前のactual GitHub GET）: `{head}`',f'JST: `{stamp}`',
  '完了範囲: C0〜C7、固定60 fit、比較・図表・独立監査。FINAL保存後のresult HEADはGitHub commit自体を正本とする。未来のSHAは予測しない。',
  '次の方針: この有限仕様での追加fit・threshold緩和・Fresh Validationは開始しない。State9を正式Entryへ採用しない。`productionReady=false`。','',
  '## 🎯 結論','',
  '各candidate fill起点の「−1%を先に踏む前に+2%」を高precisionで識別できるEntryは得られなかった。H0、RC2 current追加H1、history追加H2の全15 family/foldで90/85/80% operating pointが不成立。新3armと選択armは全2,155 OpportunityでNO_HIGH_CONFIDENCE_ENTRY。',
  'H0のPR-AUC/AP、Brier、LogLossがState追加より良く、H1 ROCの差は+0.00000166にとどまる。H2もH0を上回らなかった。State追加の実用的incremental valueは、このDevelopment・固定LR・有限feature仕様では確認できない。State9の一般的無効や新しい統計的有意性を主張する結果ではない。','',
  '## 🧬 Exact RC2 / Saved Evidence / 新規性','',
  f'最終semantic freeze receiptのexact bytesを回収し、contract `{identity["contract_sha256"]}`、profile/M0/reference/Path/sourceを照合。29/29一致、観測Primary18/18、9/9 coverage、context-reset ACCEPTED_AS_DEFINEDを維持。Final Prefixだけをsemantic freezeの代用とはしていない。',
  '既存R1 original grid 149,900行 / 4,931 Opportunity / 133 sessionを再利用し、current canonical2,155 Opportunity / 65,312行 / 58 session / 950 symbolへ1:1 lineageを維持。新minute grid・provider取得・old State代用0。current214 Opportunity / 6,417行のState source不足を明示的MISSINGとして保持。formal null27,818行とsource不足は区別している。',
  'V6で宣言されたState-schema digestとcomplete FEATURE_SCHEMAのdigestはhash対象が異なるため同一digestと主張しない。最終freezeのexact current33 numeric/11 categoricalと有限過去historyを直接利用した。V6 R2 score/probability/rankは一切feature/thresholdへ接続しない。`STATE_R2_SIGNAL_NOT_REPLICATED`を維持。',
  '旧研究との違いは、old ad-hoc Stateではなく最終RC2、Selector+1/−0.5ではなく各Entry fill+2/−1、eventual Highではなく先着順、同条件nonstate controlとの比較、forced fallbackなしNO_ENTRY許可。near-low quartile teacherやPotential eventual+5/+10の再fitはしていない。',
  'H0は保存済み476 causal Pattern列＋凍結CONTEXT4列（480）。旧R1のSTATE/SIX86列は除外し、未保存の566列matrixを再生成しない。H1はH0+33numeric/11categorical、H2はH1+5numeric/3categoricalの有限履歴。','',
  '## 📐 Target / Fill / Split','',
  'Primary +2%/−1%は変更0。decision inputはintentまでにclosedな情報のみ。canonical fillは既存quote/retry grid上でraw open+5bps、fill価格はteacher/evaluator専用。openで順序確定できず同bar両touchならORDER_UNKNOWN。未説明のscheduled raw-minute欠落がfirst touch以前ならDATA_UNAVAILABLE。UNKNOWNをnegative/0へ補完していない。',
  '元R1は最初のregular opening slotを除外する。prefit全4,931 Opportunityの478で最初のeligible候補delay=1。Selector anchorは最初候補行ではなく保存origin.decisionTimestamp。Lunchはactive minutesへ加えない。baseline GeometryのPM endpoint930と今回R1 clock925は明示的に分離し、旧値を書き換えない。',
  '保存R1の5 chronological outer / 各3innerをexact再利用。train-only median/0+missing flags、train-only scaling/categories、Opportunity総eligible学習weight1。固定L2 LogisticRegression C=1/liblinear/max_iter1000/tol1e-4/class_weightNone、hyperparameter search0。60/72 fit、収束警告0。thresholdはinner OOFの初回strict >crossだけで選び、outer labelで選択0。','',
  '## 📊 OOF識別力 / State incremental value','',
  '各arm: total65,312候補行、known23,457、unknown41,855（64.08%）、knownを1行以上持つOpportunity1,337。表は各Opportunity総評価weight1。C4のrow-count UP率24.46%とこのweighted prevalence20.81%は別分母。候補行を独立取引として扱わない。','',
  table(['Arm','PR-AUC/AP ↑','PR-AUC台形 ↑','ROC-AUC ↑','Brier ↓','LogLoss ↓'],[[f]+[fmt(pooled[f][k],6) for k in ('PR_AUC_AP','PR_AUC_trapezoid','ROC_AUC','Brier','LogLoss')] for f in ('H0','H1','H2')]),'',
  'Brier/LogLossはuncalibrated sigmoid(logit)の評価用診断値。校正PASSではなく、raw scoreを絶対確率としてhandoffしない。','',
  table(['差分','ΔPR-AUC/AP','ΔROC-AUC','ΔBrier','ΔLogLoss'],[[name]+[fmt(d[k],8) for k in ('PR_AUC_AP','ROC_AUC','Brier','LogLoss')] for name,d in inc['differences'].items()]),'',
  '![同条件OOF](FIGURES/C6_OOF_DISCRIMINATION.png)','![Raw-score分布](FIGURES/FINAL_RAW_SCORE_ECDF.png)','',
  '## 🧪 90 / 85 / 80% operating-point support','',
  '固定条件はevaluable選択Opportunity≥100、evaluable session≥10、DOWN_FIRST≤10%。supportだけを満たす点のprecision上限も下表のとおり80%から遠く、supportとDOWN≤10%を同時に満たす点は全15組で0。診断上限を新Entry thresholdとして採用していない。','',
  table(['outer','H0 support時最大precision','H1','H2','90/85/80 feasible'],[[str(f)]+[pct(next(x for x in support if x['outer_fold']==f and x['family']==a)['maximum_precision_with_N_and_session_support']) for a in ('H0','H1','H2')]+['全arm 0 / 0 / 0'] for f in range(1,6)]),'',
  '![precision coverage](FIGURES/C6_PRECISION_COVERAGE.png)','',
  '## 📍 Entry起点 Safe-up / Baseline','',
  'IMMEDIATE/R1の3,848 saved fillをcandidate labelへexact joinして新Primaryだけ評価。追加baseline label生成0、旧Entry decision再生成0、旧Geometry・旧Capture本集計の再計算0。','',
  table(['Arm','母集団','selected','filled','evaluable','UP','DOWN','NEITHER','ORDER_UNKNOWN','DATA_UNAVAILABLE','UP/known','UP/all filled'],[[a]+[str(evaluation['arms'][a]['safe_up'][k]) for k in ('population_N','selected_N','filled_N','evaluable_N','UP_FIRST_N','DOWN_FIRST_N','NEITHER_N','ORDER_UNKNOWN_N','DATA_UNAVAILABLE_N')]+[pct(evaluation['arms'][a]['safe_up'][k]) for k in ('evaluable_precision','conservative_success')] for a in evaluation['arms']]),'',
  'Hybridのfilled=0は「DOWN率0%」「MAE0%」「安全性改善」を意味しない。precision/MAE/Entry→Highは測定不能UNKNOWN。各arm2,155件全体のNO_ENTRY率は100%。NO_ENTRYを不利なprice/labelで埋めていない。baselineのknown-only率にも大きなmissingness/selection制約があり、全母集団の安全確率ではない。','',
  '![fill first passage](FIGURES/C6_SAFE_UP_ENTRY_COUNTS.png)','',
  '## 🏆 Winner保持 / 既存Geometry引用','',
  table(['Selector Winner','固定分母','IMMEDIATE captured / rate','R1 captured / rate','H0/H1/H2各arm captured','各新armNO_ENTRY'],[[f'+{t}%',evaluation['arms']['IMMEDIATE']['capture'][str(t)]['selectorWinnerDenominator'],f"{evaluation['arms']['IMMEDIATE']['capture'][str(t)]['captured']} / {evaluation['arms']['IMMEDIATE']['capture'][str(t)]['ratePct']:.2f}%",f"{evaluation['arms']['R1']['capture'][str(t)]['captured']} / {evaluation['arms']['R1']['capture'][str(t)]['ratePct']:.2f}%",'0',evaluation['arms']['H0']['capture'][str(t)]['noEntry']] for t in range(1,6)]),'',
  'Selector outcome unknown63件はWinner分母やmissへ強制投入していない。+4を省略せず、+5と+3を混同していない。','',
  '![Capture](FIGURES/FINAL_WINNER_CAPTURE.png)','',
  table(['既存Geometry引用','IMMEDIATE','R1','Hybrid'],[['strictly later High median','1.872141%','1.672065%','UNKNOWN（fill0）'],['session-end MAE median','−1.763404%','−1.605520%','UNKNOWN（fill0）'],['delay median（旧clock）','0 active min','20 active min','UNKNOWN（fill0）']]),'',
  'paired IMMEDIATE/R1は共通fill1,885、Primary共通known673。R1−IMMEDIATEの共通known strictly-later-upside平均差−0.254720pp、MAE平均差+0.223043pp。これらは新matched比較であって独立取引数の加算ではない。Hybridとの共通fillは0で、MAEを抑えつつ数%残したという主張はできない。','',
  '## 🕒 State Census / 安定性','',
  'current candidate census: UP5,738 / DOWN16,212 / NEITHER1,507 / ORDER_UNKNOWN73 / DATA_UNAVAILABLE41,782。全9formal Stateを保持し、semantic nullとsource不足を別集計。State/pathの小標本高率から手作業BUY/除外ruleは作っていない。secondary15組は記述保存のみで、最良組合せ選択0。','',
  '![State first passage](FIGURES/C4_STATE_FIRST_PASSAGE.png)','![Delay first passage](FIGURES/C4_DELAY_FIRST_PASSAGE.png)','',
  table(['outer','Known rows','H0 PR-AUC/AP','H1','H2'],[[f,inc['by_outer_fold']['H0'][str(f)]['evaluable_rows']]+[fmt(inc['by_outer_fold'][a][str(f)]['PR_AUC_AP'],6) for a in ('H0','H1','H2')] for f in range(1,6)]),'',
  'State追加の識別力差はfoldで符号が揺れる。全58session別評価・symbol/session concentrationはSTATE_INCREMENTAL_VALUE.json / SESSION_SYMBOL_CONCENTRATION.jsonに保存。Hybridにfillがないため選択symbol集中や安定した安全Entryの実証はない。','',
  '## 🔍 独立監査 / Integrity','',
  table(['確認','実績'],[[k,str(v)] for k,v in audit['checks'].items()]),'',
  f'独立dense score最大絶対差: {audit["max_independent_dense_score_absolute_error"]:.12g}。主model/helperと主label/helper import0、audit fit0、tuning0、bootstrap0、future feature input0、mismatch0。candidate PrimaryはC4別Decimal経路で全149,900行も照合済み。',
  '監査scopeを過大表示しない: all-row cutoffとmodel/threshold算術は全数、独立RC2 full-prefix/H1/H2は事前選定12 Opportunity / 358snapshot。actual received_atはUNKNOWN。bar-end availability仮定と有限Decimal確認をlive PIT/exact-log保証に読み替えない。','',
  '## ❓ 指示書の12問への回答','',
  table(['問','回答'],[
   ['1 exact接続','exact contract/source/grid identityとclosed-input lineageはPASS。全2,155保持。ただし214 OpportunityはState source不足として明示UNKNOWN/MISSING、全値observedという意味ではない。'],
   ['2 新規性','最終RC2、fill起点+2/−1先着順、同条件H0比較、NO_ENTRY許可。旧State/DIRECT/near-low/Potentialの再fitではない。'],
   ['3 H0','PR-AUC/AP0.259632、ROC0.580380。90/85/80% operating pointは全fold不成立。'],
   ['4 H1改善','PR-AUC/AP−0.001004、Brier/LL悪化。ROC差+0.00000166だけでは採用根拠にならず、operating pointなし。'],
   ['5 H2改善','H0比PR-AUC/AP−0.000499、ROC−0.000631、Brier/LL悪化。operating pointなし。'],
   ['6 precisionかcoverageか','実用operating pointがなく、3armともcoverage0。同条件でprecision向上やcoverage改善を確認していない。'],
   ['7 DOWNを減らせたか','Hybridはfill0。DOWN件数0を安全性改善と呼べない。率はUNKNOWN。baseline known DOWN率IM71.61%、R165.23%。'],
   ['8 MAE/upside','共通Hybrid fill0で比較不能。IM/R1既存Geometryは引用済み。MAE削減＋数%upside保持の候補なし。'],
   ['9 Winner保持','新arm+1/+2/+3/+4/+5全てCapture0、Winner各固定分母が全てNO_ENTRY。UNKNOWNはmissへ補完しない。'],
   ['10 high-precision support','45 target check全て不成立。N≥100/session≥10でのprecision診断上限は最大38.14%、DOWN≤10%併用point0。'],
   ['11 増分なし結論','今回DevelopmentではState9追加Entry価値未確認を維持し、Stateを優遇/採用しない。一般無効証明ではない。'],
   ['12 次の方針','Fresh Validationを今は開かない。この有限Hybrid仕様を閉じる。Entry研究全体の打切りは一般化せず、別Precommitの前に保存source coverageの意味を整理する。']]),'',
  '## 🛡️ Budget / Safety / 次工程','',
  'fits60/72（Entryのみ）、state/exit fit0、hyperparameter search0、threshold selection15（固定target check45）、新candidate label pass1、追加provider0、protected/holdout/新Validation/OOS/prospective open0、bootstrap0、orders0、paper/live0、main merge0。既存R1等のpolicy再Replay0。新hybrid policyは保存OOFのfirst-cross算術のみ。EXIT/Capital/Portfolio変更0。',
  '全execution/broker/excel/rss/live/paper/automaticPromotion/productionUpdate/transmitted flagsはfalse。LONG-only / cash-equity-only。`productionReady=false`。',
  '次は候補不成立を理由に80%を緩和したりDown10%を緩めたりせず、保存sourceでどの欠落が未分類・no-trade・censorかを整理する。provider取得が必要なら別承認。新familyやmodel変更が必要なら別有限Precommit。H0には既に価格構造・volume関連proxyがあるため、同じ列を新familyとして再fitしない。','',
  '## 🔒 保存範囲 / Publication','',
  '公開GitHubへの全directory pushは安全審査で拒否され、再試行しなかった。価格を含む行単位label/OOF/Entry/model算術は非公開成果物として保持。GitHubには集計・contract・source・hash manifest・receipt・各checkpointを明示allowlistで保存し、各commit後actual HEAD GET確認。raw/private provider payloadや元model pickleを公開しない。',
  '公開範囲を広げて行単位fill価格をGitHubへ出すには明示的な追加承認が必要。非公開研究成果物のhashはPRIVATE_EVIDENCE_PACKAGE_RECEIPT.json、完全row/modelデータはユーザー専用Evidence ZIP。','']
 (HERE/'REPORT-ja.md').write_text('\n'.join(map(str,output)))
 final=dict(status=STATUS,secondary_status=SECONDARY,independent_audit='PASS',mismatch_count=0,completed_checkpoints=['C0','C1','C2','C3','C4','C5','C6','C7'],
  basis_head=head,saved_at_jst=stamp,model_fits=60,fit_cap=72,feasible_operating_points=0,threshold_selection_passes=15,all_new_arms_no_entry_N=2155,
  State9_adopted=False,Fresh_Validation_opened=False,Fresh_Validation_recommended_now=False,productionReady=False,calibrated_probability_handoff=False,
  maintained_V6_status='STATE_R2_SIGNAL_NOT_REPLICATED',safety=SAFETY,new_provider_requests=0,protected_opens=0,orders=0,main_merge=0,
  current_direction='Close this finite specification without promotion. Preserve evidence and source-missingness. Any new experiment/provider authority needs separate finite precommit.',
  pending_publication_authority='Full row-level price-containing evidence remains private, not sent to public GitHub.',result_head='The FINAL GitHub commit is authoritative; no future SHA is predicted.')
 write('FINAL_STATUS.json',final)
 (HERE/'FINAL_HANDOFF.md').write_text('# 🧭 Final Handoff\n\n'+json.dumps(final,ensure_ascii=False,indent=2)+'\n\n## 📎 Evidence\n\n[Japanese report](REPORT-ja.md) / [Audit](INDEPENDENT_AUDIT.json) / [Entry evaluation](ENTRY_EVALUATION.json) / [Incremental value](STATE_INCREMENTAL_VALUE.json).\n\nDo not run the finite model script again: its 60-fit ledger is closed. Never force push/main merge/open Fresh Validation/promote a score.\n')
 archive,receipt=build_private(head)
 print(json.dumps(dict(status=STATUS,secondary_status=SECONDARY,report_bytes=(HERE/'REPORT-ja.md').stat().st_size,private_archive=str(archive),private_archive_receipt=receipt,model_fits=60,audit='PASS'),ensure_ascii=False))

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--basis-head',required=True);a=ap.parse_args();run(a.basis_head)
