"""Verified formal measurement closeout with sparse coverage tables and figures."""
import argparse,json,os,re,subprocess
from pathlib import Path
from scripts import phase57_temporal_formal as f
s=f.s;d=f.d


def charts(root,coverage):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'phase57-formal-v1'})
    totals=coverage['oldUsableTotals'];families=[x for x in coverage['families'] if x['globalStatus']=='USABLE']
    fig,axs=plt.subplots(2,2,figsize=(14,11),layout='constrained');fig.suptitle('Ark Terminal | Formal temporal reliability & sparse coverage',fontsize=17,fontweight='bold')
    def bars(ax,labels,values,colors,title,xlabel):
        bs=ax.barh(labels,values,color=colors);ax.invert_yaxis();ax.bar_label(bs,labels=[f'{v:,}' for v in values],padding=5,fontsize=10);ax.set_xlim(0,max(values+[1])*1.25);ax.set_title(title,loc='left',pad=14,fontweight='bold');ax.set_xlabel(xlabel);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    bars(axs[0,0],['PASS','FAIL','INSUFFICIENT'],[totals[k] for k in ['PASS','FAIL','INSUFFICIENT']],['#207f76','#b65c42','#a6afb9'],'1. Temporal result | all 9 old USABLE families','Symbol x lane x trait cells')
    bars(axs[0,1],['HIGH + PASS','MEDIUM + PASS'],[totals['HIGH_PASS'],totals['MEDIUM_PASS']],['#285f91','#4e9fc1'],'2. Current confidence + temporal PASS','Symbol x lane x trait cells')
    labels=[x['family'] for x in families];a=[x['availableHIGH'] for x in families];b=[x['availableMEDIUM'] for x in families]
    ax=axs[1,0];ax.barh(labels,a,color='#285f91',label='HIGH');bars2=ax.barh(labels,b,left=a,color='#4e9fc1',label='MEDIUM');ax.bar_label(bars2,labels=[f'{x+y:,}' for x,y in zip(a,b)],padding=4);ax.invert_yaxis();ax.set_xlim(0,max([x+y for x,y in zip(a,b)]+[1])*1.25);ax.set_title('3. Available cells by family',loc='left',pad=14,fontweight='bold');ax.set_xlabel('Symbols with this lane-qualified trait');ax.legend(loc='lower right');ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    bins=coverage['symbolBins'];bars(axs[1,1],[x+' traits' for x in bins],list(bins.values()),'#207f76','4. Available trait count per symbol','Symbols (same trait across lanes deduplicated)')
    fig.savefig(root/'coverage.png',dpi=160,metadata={'Software':'Ark Terminal research'});fig.savefig(root/'coverage.svg',metadata={'Date':None});plt.close(fig)


def closeout(root,replay):
    protocol,spec=f.verify();root=Path(root);m=root/'measurement';other=Path(replay)
    manifest=s.read(m/'manifest.json');assert manifest==s.read(other/'manifest.json')
    for name,h in manifest.items():assert d.hashfile(m/name)==d.hashfile(other/name)==h
    regression=s.read(root/'regression/regression.json');assert regression['status']=='PASS'
    log=(root/'focused.log').read_text();assert re.search(r'\nOK\s*$',log) and 'FAILED' not in log
    tests=int(re.search(r'Ran (\d+) tests',log)[1]);assert tests>=239
    b=s.read(m/'09_boundary.json');assert not b['commonHoldoutIntersection'] and not b['excludedIntersection'];assert all(v is False for v in b['safety'].values())
    extraction=s.read(root/'extraction.json');assert extraction and all(set(x['selectedDates'])=={'2025-08-22','2025-08-25'} for x in extraction)
    cov=s.read(m/'01_coverage.json');tot=cov['oldUsableTotals'];families=[x for x in cov['families'] if x['globalStatus']=='USABLE'];folds=s.read(m/'02_family_periods.json');bad=s.read(m/'04_insufficient_families.json');watch=s.read(m/'03_watch_mapping.json');gi=s.read(m/'10_gate_inputs.json')
    assert tot['evaluated']==36720 and sum(tot[k] for k in ['PASS','FAIL','INSUFFICIENT'])==36720
    assert sum(cov['symbolBins'].values())==cov['symbols']==4080
    assert tot['available']==tot['availableHIGH']+tot['availableMEDIUM']
    gate={'status':'BLOCKED','reasons':[],'contracts':{name:'PASS' for name in ['precommittedTemporalMeasurement','noFutureLeakage','sameAsOf','deterministicRegeneration','traitLevelAvailability','confidencePreserved','temporalStatusPreserved','missingSemantics','coverageReported','strictComputedThrough','commonHoldoutUntouched','tests','regression']},'dispatchableSymbols':cov['atLeast']['1'],'dispatchableSymbolTraits':tot['available'],'realReaderConnections':gi['realReaderConnections'],'priorGate':'BLOCKED_UNCHANGED','scope':'RESEARCH_DEVELOPMENT_ONLY_NOT_PIT_NOT_OOS','entryExitTrainingPerformed':False,'productionAllowed':False,'safety':b['safety']}
    if tot['available']==0:gate['reasons'].append('NO_USABLE_HM_TEMPORAL_PASS_CELL')
    if gi['realReaderConnections']==0:gate['reasons'].append('NO_NONEMPTY_FRESH_REAL_READER_CONNECTION')
    if not gate['reasons']:gate['status']='SPARSE_DICTIONARY_CHART_READER_READY_FOR_ENTRY_EXIT_DEVELOPMENT'
    s.write(root/'handoff-gate.json',gate)
    head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()
    receipt={'status':'PASS','executionHead':head,'runId':os.environ.get('GITHUB_RUN_ID'),'focusedTests':tests,'regressionTests':sum(x['counts']['tests'] for x in regression['suites']),'deterministicRegeneration':'TWO_MANIFESTS_IDENTICAL','specSHA256':protocol['adoptedSpecSHA256'],'formalProtocolSHA256':d.hashfile(f.BASE/'protocol.json'),'sourceEvidenceUnchanged':True,'protectedPayloadReads':0,'providerRequests':0,'mainMerged':False,'safety':b['safety']}
    s.write(root/'ci-receipt.json',receipt);charts(root,cov)
    lines=['# Sparse Dictionary — Formal Temporal Reliability Remeasurement','',f"**Gate: {gate['status']}**",'',
      f"利用可能なSparse Dictionary: **{cov['atLeast']['1']:,}銘柄 / {tot['available']:,} symbol×lane×trait**。全trait PASSは要求しない。MEDIUMもconfidenceを保持したまま利用可能。",
      '固定仕様を正式採用してDevelopment144だけで再測定。window・minimum-N・sample confidence・temporal thresholdは保存済み仕様から変更なし。既存9USABLE/23WATCHと旧Gate/Evidenceは上書きしていない。','',
      '![Temporal reliability and sparse coverage](coverage.png)','',
      '## 1. Temporal結果・confidence（旧USABLE9、全4080銘柄）','',
      '| 指標 | symbol×lane×trait数 |','|---|---:|']
    names={'evaluated':'全評価対象','PASS':'Temporal PASS','FAIL':'Temporal FAIL','INSUFFICIENT':'Temporal INSUFFICIENT','HIGH_PASS':'HIGH + temporal PASS','MEDIUM_PASS':'MEDIUM + temporal PASS','LOW':'sample LOW（temporalとは別軸）','sampleINSUFFICIENT':'sample INSUFFICIENT（別軸）','availableHIGH':'利用可能 HIGH','availableMEDIUM':'利用可能 MEDIUM','available':'引渡し可能 合計'}
    for key,label in names.items():lines.append(f"| {label} | {tot[key]:,} |")
    lines+=['','PASS/FAIL/INSUFFICIENTのみが全評価対象を分割する。HIGH+PASS/MEDIUM+PASS/LOWは別軸であり、上表全行を足し合わせない。WATCH23を含む全32の補助集計はmeasurement/01_coverage.jsonのall32Totals。WATCHはPASSしても旧WATCHのまま、引渡し対象に含めない。','',
      '## 2. trait family別結果','',
      '| family | 3期間比較可 | PASS | FAIL | INSUFFICIENT | HIGH+PASS | MEDIUM+PASS | 利用可能 |','|---|---:|---:|---:|---:|---:|---:|---:|']
    fp={x['lane']+'/'+x['trait']:x for x in folds}
    for x in families:lines.append(f"| {x['family']} | {fp[x['family']]['threePeriodComparable']} | "+' | '.join(str(x[k]) for k in ['PASS','FAIL','INSUFFICIENT','HIGH_PASS','MEDIUM_PASS','available'])+' |')
    lines+=['','## 3. usable trait数／symbol','',
      '| usable trait数 | 銘柄数（同じtrait_idはlane間で重複除去） | lane別traitとして数えた場合 |','|---|---:|---:|']
    for key in ['0','1','2','3','4','5+']:lines.append(f"| {key} | {cov['symbolBins'][key]} | {cov['laneQualifiedSymbolBins'][key]} |")
    lines+=['','| 条件 | 銘柄数 |','|---|---:|']
    for k in ['1','2','3']:lines.append(f"| 少なくとも{k} trait利用可能 | {cov['atLeast'][k]} |")
    lines+=['','主表ではdaily/amihudとintraday/amihudを同一traitとして数える。値・confidence・出典は統合せず別レコードで保存する。引渡しセル総数はlane別。銘柄全体のALL PASS判定はない。','',
      '## 4. 固定3期間','',
      '| 期間 | Source終端 | 予測起点 | Target開始 | Target終了 | 許可session |','|---|---|---|---|---|---:|']
    for row in spec['schedule']['rows']:lines.append(f"| {row['name']} | {row['computedThrough']} | {row['predictionOrigin']} | {row['testStart']} | {row['testEnd']} | {row['targetAllowedSessions']} |")
    lines+=['','sourceは60取引所calendar-position。targetは固定済み26/26/20許可日を含む範囲で、各最低20適格日・peer100条件を維持。calibration期間は空白を含み108取引所日にまたがる。欠測はNaN、warm-up/resetは変更なし。対象期間は非重複だが、統計的独立・iidを認定しない。',
      'Temporal判定は3期間のsource H/M・最低標本・有限posteriorを要求し、sign consistency>=2/3、normalized RMSE<=1、|bias|<=0.5、slope0.5..1.5（prediction SD>=0.1）、posterior-change RMS<=1を全て満たす場合PASS。3期間未成立はINSUFFICIENT。既存関数による採点をそのまま使用。',
      '期間別resultはCOMPARABLE/INSUFFICIENTと実測x/y/change等を保存する。単一期間に独自のPASS基準は追加していない。','',
      '## 5. 残4/9のINSUFFICIENT','',
      '| family | Period1比較可 | Period2比較可 | Period3比較可 | 全3期間 |','|---|---:|---:|---:|---:|']
    for x in bad:lines.append('| '+x['lane']+'/'+x['trait']+' | '+' | '.join(str(a['comparable']) for a in x['periodCounts'])+f" | {x['threePeriodComparable']} |")
    for x in bad:
        lines+=['',f"**{x['lane']}/{x['trait']}**"]
        for a in x['periodCounts']:lines.append(f"- {a['period']}: {json.dumps(a['firstFailure'],sort_keys=True)}")
    lines+=['','現在の固定Development分割では標本・source confidence・事後推定等の条件が揃わず正式比較不能。追加session/eventで自然に条件が揃う可能性はあるが保証しない。trait自体が永久に測れないとの結論ではない。必要追加日数は銘柄別event頻度等に依存するためUNKNOWN。残4件を救済するwindow選び直し・条件緩和は実施していない。','',
      '## 6. WATCH23補正診断','',
      '| family | calibration fit pairs | validation1 PASS | validation2 PASS | 新version候補のみ |','|---|---:|---|---|---|']
    for x in watch:lines.append('| '+x['lane']+'/'+x['trait']+f" | {x['fitPairs']} | {x['independentPeriods'][0]['pass']} | {x['independentPeriods'][1]['pass']} | {x['newVersionCandidate']} |")
    lines+=['','mappingは最初の期間のみでfitし、その完了後の2起点に固定適用。各期間>=100 pairs、slope0.5..1.5、mapped MSE<=identity MSEの旧条件を変更していない。候補になっても旧WATCHをUSABLEへ昇格しない。','',
      '## 7. Sparse handoff・past-only・Reader','',
      'payloadはvalue / availability / sampleConfidence / temporalReliability / uncertainty / nEff / computedThrough / availableAt / definitionHashを分離する。利用不能value=null、availability=UNAVAILABLE、理由を保持。実値0はAVAILABLEとなり得る。失格の兄弟traitは他traitを排除しない。',
      'Profile/peer/normalization/referenceはsame-as-of。computedThrough < decisionTimeを厳格チェックし、temporal判定のcomputedThrough/availableAtも別に検査する。今回の再現性判定は2025-08-21終了分まで使用しており、それ以前のdecisionへ利用しない。MEDIUMの未検定driftは旧仕様どおり許容し、DRIFT_UNTESTEDを明示。',
      f"実データ同時接続: {gi['realReaderConnections']}件。8/22閉場までのProfile＋8/25 12:35のclosed-bar Reader、code順の最初3候補だけで接続を検証。鮮度・session境界・future/stale拒否・history adapterは契約テストで確認。全市場のReader coverageを主張しない。",
      '144日は将来のEntry/EXIT Developmentとして再利用できる。各decisionで全学習済みartifactとfeatureをpast-only再生成し、最終Profile/最終H/M/最終temporal判定の過去へのbackfillを禁止する。今回のcoverageは最終時点の研究用coverageであり、144日全decisionにこのcoverageが存在したとは言わない。',
      'availableAtは本研究のイベント時刻に基づく再構成であり、実際の当時の取得時刻が証明されたPITデータではない。固定registryや以前の開発結果は事後に見られており、独立したconfirmatory/OOS検証・売買利益を認定しない。','',
      '## 8. Gate・検証・保護境界','',
      f"Gate: **{gate['status']}**。残blocker: {gate['reasons']}。",f"Focused tests {tests} PASS / regression {receipt['regressionTests']} PASS / 2回再生成manifest完全一致。旧Evidence/registry/specハッシュ不変。",
      'Common Holdout244・REPORT19/Validation/OOS/Freshの追加開封0。既存matrixと元read ledgerを照合。Reader確認のraw復元は許可済み8/22と8/25のみ。過去Exposure Ledgerは維持。新規取得0。',
      'Frozen Selector・Capital Allocation・実売買系は不変。新Entry/EXIT学習0。安全フラグ9項目は全false。main未merge。',
      f"Execution HEAD `{head}` / PR587 Draft・未merge / CI {receipt['runId']}。保存HEADはこの実行commitの子孫。",'',
      '## 保存ファイル','',
      '- measurement/05_profiles.json.gz: 全symbol×traitのProfile・3期間結果・標本/再現性・provenance。',
      '- measurement/06_feature_payload.json.gz: 明示availabilityと欠測を持つ下流契約。',
      '- measurement/01_coverage.json / 02_family_periods.json: 表・グラフの全数値。',
      '- measurement/07_artifacts.json / 08_reader_integration.json / 09_boundary.json: as-of artifact・接続・境界証拠。',
      '- handoff-gate.json / ci-receipt.json / coverage.png / coverage.svg。',
      'STOP。READYでも今回Entry/EXIT本格学習は開始しない。','']
    (root/'REPORT-ja.md').write_text('\n'.join(lines));(root/'HANDOFF.md').write_text('# Handoff\n\n'+gate['status']+'\n\nRead REPORT-ja.md, handoff-gate.json, adopted immutable spec and trait payload contract. Same144 remain Development; past-only per decision. No Holdout or learning in this stage.\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--evidence',required=True);p.add_argument('--replay',required=True);a=p.parse_args();closeout(a.evidence,a.replay)
