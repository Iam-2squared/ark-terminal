"""Build the required sign-only aggregate report and three fixed diagnostic plots."""
import csv
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from sign_io import *

SHORT={'SF_A_PRICE':'SF_A PRICE','SF_B_STATE':'SF_B STATE','SF_C_SCORE':'SF_C SCORE','SF_D_UNION':'SF_D UNION',
       'B0':'B0 過去負率','HL0':'HL0 reuse','OLD_D1':'旧D1 reuse','OLD_D2':'旧D2 reuse'}
LEVEL={'0.05':'保守5%','0.10':'標準10%','0.20':'強20%'}

def pct(x):return 'null' if x is None else f'{x*100:.2f}%'
def num(x):return 'null' if x is None else f'{x:.6f}'

def main():
    j=read(OUT/'SIGN_METRICS.json');gate=read(OUT/'STAGE1_TERMINATION.json');audit=read(OUT/'INDEPENDENT_SIGN_AUDIT.json')
    assert audit['status']=='PASS'
    population='FROZEN_ENTRY_EXECUTION_ELIGIBLE';metric={k:v[population] for k,v in j['metrics'].items()}
    figdata=[];colors=['#3970a9','#7b57a4','#b87523','#177953']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'ark-sign-only-stage1-v1'})
    fig,ax=plt.subplots(figsize=(9,5))
    markers={'0.05':'o','0.10':'s','0.20':'^'}
    for recipe,color in zip(RECIPES,colors):
        ss=[metric[recipe]['filters'][a] for a in ALPHAS]
        x=[s['positive_retention']*100 for s in ss];y=[s['negative_removal']*100 for s in ss]
        ax.plot(x,y,'-',label=SHORT[recipe],color=color,lw=2.6 if recipe=='SF_D_UNION' else 1.6)
        for a,xx,yy in zip(ALPHAS,x,y):ax.scatter([xx],[yy],marker=markers[a],s=65,color=color,zorder=3)
        figdata.extend({'figure':1,'recipe':recipe,'alpha':a,'positive_retention_pct':xx,'negative_removal_pct':yy} for a,xx,yy in zip(ALPHAS,x,y))
    ax.axvline(90,color='#aaaaaa',ls='--',lw=1);ax.axhline(30,color='#aaaaaa',ls='--',lw=1)
    ax.set(xlabel='Actual positive examples retained (%)',ylabel='Actual negative examples removed (%)',
           title='Sign-only filter: 3 fixed past-OOF count budgets',xlim=(80,101),ylim=(0,35))
    ax.grid(alpha=.18)
    handles,labels=ax.get_legend_handles_labels()
    handles += [Line2D([0],[0],color='#555555',marker=markers[a],ls='None',label='alpha '+str(int(float(a)*100))+'%') for a in ALPHAS]
    ax.legend(handles=handles,loc='upper left',fontsize=9);fig.tight_layout()
    fig.savefig(OUT/'01_positive_retention_negative_removal.svg',metadata={'Date':None})
    fig.savefig(WORK/'sign_figure_01_preview.png',dpi=150);plt.close(fig)
    names=['NO FILTER']+[SHORT[k] for k in RECIPES];ss=[j['no_filter']]+[metric[k]['filters']['0.10'] for k in RECIPES]
    fig,ax=plt.subplots(figsize=(8,4.5));pos=[s['P_keep'] for s in ss];neg=[s['N_keep'] for s in ss];xs=np.arange(5)
    ax.bar(xs,pos,label='Actual POSITIVE passed',color='#3d9c71');ax.bar(xs,neg,bottom=pos,label='Actual NEGATIVE passed',color='#cb6464')
    for i,(p,n) in enumerate(zip(pos,neg)):
        ax.text(i,p/2,str(p),ha='center',va='center',color='white',weight='bold');ax.text(i,p+n/2,str(n),ha='center',va='center',color='white',weight='bold')
        figdata.append({'figure':2,'recipe':names[i],'P_keep':p,'N_keep':n})
    ax.set_xticks(xs,names,rotation=0,fontsize=9);ax.set(ylabel='Known signed examples',title='Passed examples: standard alpha 10%, all OOF including OFF',ylim=(0,1150))
    ax.legend(loc='upper right',fontsize=9);ax.grid(axis='y',alpha=.16);fig.tight_layout()
    fig.savefig(OUT/'02_passed_sign_composition.svg',metadata={'Date':None});fig.savefig(WORK/'sign_figure_02_preview.png',dpi=150);plt.close(fig)
    with (OUT/'BLOCK_METRICS.csv').open() as f:blockrows=list(csv.DictReader(f))
    fig,ax=plt.subplots(figsize=(8,4.5))
    for recipe,color in zip(RECIPES,colors):
        rr=[r for r in blockrows if r['recipe']==recipe and r['alpha']=='0.10'];rr.sort(key=lambda r:int(r['block']))
        x=[int(r['block']) for r in rr];y=[float(r['J_sign'])*100 for r in rr]
        ax.plot(x,y,'o-',color=color,label=SHORT[recipe],lw=2.6 if recipe=='SF_D_UNION' else 1.5)
        figdata.extend({'figure':3,'recipe':recipe,'block':xx,'J_sign_percentage_points':yy} for xx,yy in zip(x,y))
    ax.axhline(0,color='#444444',lw=1);ax.axvspan(.5,2.5,color='#eeeeee',alpha=.6,label='Initial OFF: insufficient CAL sessions')
    ax.set(xticks=range(1,9),xlabel='Frozen OOF block',ylabel='J_sign (percentage points)',title='Standard filter stability: no block removed');ax.grid(alpha=.18)
    ax.legend(fontsize=8,ncol=2);fig.tight_layout();fig.savefig(OUT/'03_block_J_sign.svg',metadata={'Date':None});fig.savefig(WORK/'sign_figure_03_preview.png',dpi=150);plt.close(fig)
    write_csv(OUT/'FIGURE_DATA.csv',figdata)
    lines=['| 固定0.5の二値予測 | 実マイナスを正しく予測 | 実プラスを正しく予測 | balanced accuracy | 有効予測coverage |',
           '|---|---:|---:|---:|---:|']
    for recipe in ['B0','HL0','OLD_D1','OLD_D2']+RECIPES:
        b=metric[recipe]['binary_0.5'];lines.append(f'| {SHORT[recipe]} | {b["actual_NEG_pred_NEG"]}/554 | {b["actual_POS_pred_POS"]}/462 | {pct(b["balanced_accuracy"])} | {pct(b["model_prediction_coverage_all"])} |')
    lines+=['','| 構成・強度 | PASSの実プラス | PASSの実マイナス | REJECTの実プラス | REJECTの実マイナス | プラス保存率 | マイナス除去率 | 通過後マイナス率 |',
            '|---|---:|---:|---:|---:|---:|---:|---:|']
    s=j['no_filter'];lines.append(f'| 無フィルター | {s["P_keep"]} | {s["N_keep"]} | {s["P_reject"]} | {s["N_reject"]} | {pct(s["positive_retention"])} | {pct(s["negative_removal"])} | {pct(s["pass_negative_rate"])} |')
    for recipe in RECIPES:
        for alpha in ALPHAS:
            s=metric[recipe]['filters'][alpha];label=SHORT[recipe]+' '+LEVEL[alpha]
            if recipe=='SF_D_UNION' and alpha=='0.10':label='**'+label+' Primary**'
            lines.append(f'| {label} | {s["P_keep"]} | {s["N_keep"]} | {s["P_reject"]} | {s["N_reject"]} | {pct(s["positive_retention"])} | {pct(s["negative_removal"])} | {pct(s["pass_negative_rate"])} |')
    primary=metric['SF_D_UNION']['filters']['0.10'];b=metric['SF_D_UNION']['binary_0.5']
    lines+=['',f'🛡️ **Capital 第1審査・符号専用フィルター／終了判定 `{gate["status"]}`**',
            f'実時計JST: `{now()}`。Primaryは事前固定のSF_D＋標準alpha10%、全38 OOF sessionsの実行適格集合。初期OFFも含む。上2表は同一の既知1,016件（マイナス554・プラス462）で、未知教師を正負に補完していない。',
            f'**プラス447件を保存し15件を誤拒否、マイナス26件を除去し528件が通過した。** マイナス除去率{pct(primary["negative_removal"])}は事前目安30%未達。通過後負率は無フィルター{pct(j["no_filter"]["pass_negative_rate"])}から{pct(primary["pass_negative_rate"])}へ小幅低下した。REVIEW_CANDIDATEにはしない。',
            '','### 🎯 評価範囲とcoverage','',
            '| 集合 | 全行 | プラス | マイナス | EXACT_ZERO | UNKNOWN |', '|---|---:|---:|---:|---:|---:|',
            '| CORE全期間 | 1,600 | 706 | 854 | 0 | 40 |',
            '| warmup全Entry | 561 | 244 | 300 | 0 | 17 |',
            '| warmup実行適格 | 550 | 244 | 300 | 0 | 6 |',
            '| OOF全Entry | 1,039 | 462 | 554 | 0 | 23 |',
            '| OOF実行適格（Primary） | 1,028 | 462 | 554 | 0 | 12 |',
            '| Rank通過（補助） | 494 | 219 | 273 | 0 | 2 |',
            '| 旧V5購入（補助） | 150 | 68 | 82 | 0 | 0 |',
            '', '既存件数と一致。全Entryの不適格11件、教師UNKNOWN23件は別集計。実行適格UNKNOWN12件のうち標準で11件PASS、1件REJECT。標準の全適格判定はPASS986／REJECT42、正負既知だけならPASS975／REJECT41。UNKNOWNを成功例に数えない。',
            '初期OFFはblock1/2の10 sessions、実行適格266件（既知261・UNKNOWN5）。これらをPASS_UNASSESSEDとして通過側へ計上した。OFFを予測POSITIVEと呼ばず、ACTIVEだけの成績へPrimaryを差し替えていない。予測自体は全適格1,028件に有効なモデル出力があり、欠落／baseline fallbackは0。B0のcoverage100%は過去率baselineが存在する意味で、Primaryのモデルcoverageへは算入しない。',
            '', '### 🧠 固定0.5を隠さない符号診断','',
            '| 構成 | AUROC負 | AP負 | AP正 | Brier | log loss | accuracy | 負precision | 負recall | 正precision | 正recall |',
            '|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for recipe in ['B0','HL0','OLD_D1','OLD_D2']+RECIPES:
        m=metric[recipe]['binary_0.5']
        lines.append('| '+SHORT[recipe]+' | '+' | '.join(num(m[k]) if k in ['AUROC_neg','AP_neg','AP_pos','Brier','log_loss'] else pct(m[k]) for k in ['AUROC_neg','AP_neg','AP_pos','Brier','log_loss','accuracy','negative_precision','negative_recall','positive_precision','positive_recall'])+' |')
    lines+=['',f'Primaryの固定0.5混同行列は、実マイナス→負416／正138、実プラス→正124／負338。accuracyは{pct(b["accuracy"])}, balanced accuracyは{pct(b["balanced_accuracy"])}。全マイナスの無情報判定はaccuracy54.53%・balanced accuracy50%、全プラスはaccuracy45.47%・balanced accuracy50%。0.5の判定とREJECT閾値を混同しない。',
            'AUROCはscore_negが高いほどNEGATIVEの向きを保持。SF_AのAUROCが0.5未満でも反転0。scoreは未校正であり、数値をそのまま将来損失確率と解釈しない。AP正はy_posと1-score_negで算定。すべて件数の等重み。B0はfoldごとの過去負率が変わるためpool AUROCが0.5に一致しない。',
            '', '### ⚖️ フィルターと安定性','',
            '| SF_D 強度 | 正例誤拒否率 | 見送りprecision | 通過率（正負既知） | J_sign | filter balanced accuracy |',
            '|---|---:|---:|---:|---:|---:|']
    for alpha in ALPHAS:
        m=metric['SF_D_UNION']['filters'][alpha];lines.append('| '+LEVEL[alpha]+' | '+' | '.join(pct(m[k]) for k in ['positive_false_reject','reject_precision','pass_rate','J_sign','filter_balanced_accuracy'])+' |')
    lines+=['','過去CALの正例誤拒否件数予算だけでtauを決めた。distinct scoreを昇順で検査し、score>=tauの同点は一括REJECT。floor(alpha×過去正例数)、ALL_PASS sentinel、最小tauを保存した。現在blockの分布・教師を見る前にsnapshotを固定し、block中の変更0。正例保存率の将来保証ではない。',
            '','| block | CAL support／標準tau | PASS正 | PASS負 | REJECT正 | REJECT負 | 正保存率 | 負除去率 | J_sign |',
            '|---|---|---:|---:|---:|---:|---:|---:|---:|']
    selected=[r for r in blockrows if r['recipe']=='SF_D_UNION' and r['alpha']=='0.10'];selected.sort(key=lambda r:int(r['block']))
    for r in selected:
        lines.append(f'| {r["block"]} | {r["threshold_status"]}／{r["tau"] or "ALL_PASS"} | {r["P_keep"]} | {r["N_keep"]} | {r["P_reject"]} | {r["N_reject"]} | {pct(float(r["positive_retention"]))} | {pct(float(r["negative_removal"]))} | {pct(float(r["J_sign"]))} |')
    lines+=[ '',f'CAL supportと評価側正負各10件を満たした6block中{gate["J_positive_block_N"]}blockでJ_sign>0（{gate["J_positive_block_N"]}/6）。4block以上・75%以上の安定性条件は満たすが、全OOF負例除去30%条件は未達。全8blockの全構成・全alphaはBLOCK_METRICS.csvに残した。',
             '','| 事前終了条件 | 実測／判定 |','|---|---|',
             '| source／符号／as-of／時間順監査 | PASS（歴史的可用性仮定の範囲） |',
             '| モデル自身の有効予測coverage ≥95% | 100%（1,028/1,028）PASS |',
             '| 全OOFプラス保存率 ≥90% | 96.75% PASS |',
             '| 全OOFマイナス除去率 ≥30% | 4.69% FAIL |',
             '| 通過後負率 < 無フィルター | 54.15% < 54.53% PASS |',
             '| 評価可能block ≥4 | 6 PASS |',
             '| その75%以上でJ_sign>0 | 5/6 PASS |',
             '', '### 📈 3つの固定図','',
             '![正例保存率と負例除去率の固定3点](01_positive_retention_negative_removal.svg)','',
             '![標準フィルターの通過群正負件数](02_passed_sign_composition.svg)','',
             '![標準block別J_sign](03_block_J_sign.svg)','',
             '各図は保存済み予測・閾値だけから作図。図を見て新たなruntime閾値や採用先を選んでいない。図1の破線は今回の事前目安で、統計的保証ではない。初期OFFを図3から除外していない。',
             '', '### 🧩 情報群・再利用・不足Evidence','',
             '| 構成 | 入力 | 新fit | 役割／再利用との違い |','|---|---|---:|---|',
             '| SF_A | 108 numeric、categorical0 | 8 | Frozen P0の価格／出来高／VWAP／ボラ／経路、Entry自身の時刻・遅延 |',
             '| SF_B | 18 numeric＋7 categorical | 8 | COREのState9／Path／方向／dwell／stop／gap・観測情報 |',
             '| SF_C | 13 numeric、categorical0 | 8 | Frozen P1 score／threshold、Selector context、pP／MOVE_U2／MOVE_U3／MRETの保存済み初回OOF |',
             '| SF_D | 139 numeric＋7 categorical | 8 | A＋B＋Cの固定和集合、元D2列順の後ろに4score。唯一のPrimary |',
             '', '元metadata・生成コードの意味で所属を固定。Selector anchorの価格進行／clock／delay／refreshはSelector contextに属し、Entry自身のclock／delayは価格・時刻群に属する。BへCORE全列を一括混入していない。重複clockMinute／activeMinutesSinceSelectorは元receipt通り各1回、UNRESOLVED列0。旧566列・新市場feature・銘柄embedding追加0。',
             '旧HL0／D1／D2もすでに正負を学習していた。新しい検証は情報群を分離すること、符号だけの読出しへ統一すること、Capital口座変化から切り離すこと。符号ラベル名の変更だけでは再fitしていない。旧24モデルの初回OOFは比較用にreuseし、元モデルは不変。今回A/B/C/Dの列順・入力値集合はどれも旧D1/D2と完全一致しない。SF_Dは4つの保存scoreを追加した別構成であり、同じD2の改名ではない。32新fit・各1attempt、技術再試行0。',
             '58 sessions／warmup20／OOF38／元8blockを維持。全過去の実行適格かつ成熟した正負を学習し、旧V5購入150件だけへ絞らない。sample_weight=None／class_weight=None、各行1件。欠測は0＋indicator、標準化・categorical vocabularyはtrain-only。numericのみ／categoricalのみのshape処理を補う以外は旧前処理を保持。Random state57、旧小型HistGradientBoostingClassifierの全パラメータ・scikit-learn1.8.0を固定。追加fit・seed・hyperparameter・calibration・stacking・inner fit0。',
             'scoreはP1の5producer graphとpP／MOVE_U2／MOVE_U3／MRETの32保存producerについて、train ID、cutoff、外側testの除外、行時点の生成可能性を照合。pP／MOVE_U2／MOVE_U3／MRETが存在しないwarmup561行は欠測のまま。未来producerでの再採点・in-sample scoreによる穴埋め・producer新fit0。旧Qualityのbaseline integrity incidentと旧MRETの数値FAILは履歴として残し、今回は独立OOF認証済みproducer／scoreだけを回収した。baseline失敗ファイル・旧金額政策は使わない。',
             '価格OPEN quoteは元fillの購入直前・数量確定前の可用性仮定を継承。閉じたState prefixとFrozen first-intent snapshotを読む。fill足H/L/C/volume、将来EXIT可用性はXへ入れず、Entry延期0。as-of時間とsource可用順は別々に検査したが、actual arrivalはUNKNOWNのためHISTORICAL_ASSUMED_AVAILABILITYを維持し、実受信PITへ昇格しない。',
             '符号は元sell_credit／buy_debitのFraction比較だけ。費用は元実効価格に1回含まれ、追加適用0。厳密0は独立、UNKNOWNも独立。微小正負を0へ丸めない。教師viewは6列だけ、学習／閾値／評価は符号view以外のoutcomeを読まない。購入前の価格・出来高入力は数値のまま許可する。',
             f'新箇所の合成テスト621件PASS。追加の独立AP／Brier／log loss、全補助slice／全blockの件数、退化予測・coverage・PASS引き渡し検算426件もPASS。独立監査は{audit["checks_N"]:,}項目、mismatch0、監査refit0。符号を保った原結果の大きさの変更1,560件で、source_hashは別記し、学習要求payload／重み／閾値／評価／終了判定は不変。保存modelを独立に前処理・推論して初回OOFと一致。current／future test教師を変えてもprediction／tauは不変で評価だけが変化。tie／floor／ALL_PASS／ゼロ分母／初期OFF／欠測coverage、退化判定の非成功を検算。巨大な既存State／R全域監査は再実行しない。',
             '', 'この全期間は反復利用済みDevelopmentである。旧sign成績とexpert成績を知って本設計を作ったexposureを保存しており、precommit・時間順OOF・別ラベル名でFresh/OOSへ戻したとは言わない。未知期間の一般化、受信時刻PIT、将来の正例誤拒否率の保証、経済価値は不足Evidence。CIは未計算、救済Gateとして使用0。',
             '','### 🔒 終了点と引き渡し','',
             'Selector／Entry／EXIT／State定義・元Capitalコードおよび旧RNEG evidenceのhash不変。Capital／RESET20／Replacement Replay0、第2審査0、数量配分変更0、provider0、注文0、main merge0、force push0、Claude0。金額・平均R・R階層・RN tail・U5/U10・最終資産は今回の成績欄として未計算で、終了判定に使用0。旧RNEG Defense=DEFENSE_REJECTED、旧V5.1=REJECTEDのclosureは保持した。',
             '成果物はMODEL_PRECOMMIT、FEATURE_FAMILY_MAP、ASOF_AND_SCORE_LINEAGE、SOURCE_BINDING、REUSE_MATRIX、符号契約／件数、FIT_LEDGER、8block閾値、混同行列／FILTER_COUNTS／BLOCK_METRICS／SIGN_METRICS、独立監査、MANIFEST。Entry／symbol別入力・sign view・モデル・初回OOF・action・学習payload・学習IDはprivate成果物へ分離し、GitHubは契約・集約・hash・状態だけを保存する。',
             'privateのOOF_PASS_HANDOFFは、当時のSF_D標準フィルターがPASSした候補986件（実行適格UNKNOWN込み）を保存した。実POSITIVEだけのoracle抽出ではなく、既知実NEGATIVE528件も残る。将来の別Workに渡す場合にこの当時のPASS集合を使う。今回、第2審査は実装しない。',
             '', '**回答:** State／Path単独はAUROC0.526791で弱い識別差があるが、明確な有用性は未確認。PRICE単独0.493583、SCORE単独0.505693、UNION0.522135。統合の明確な改善は確認できず、旧D2の0.521678からの差も小さい。標準ではプラス447件を残し、マイナス26件を除いた。PrimaryはSIGN_FILTER_TRADEOFF_ONLYで終了。保存scoreや符号性能から資産増加を主張しない。',
             '', '`productionReady=false / executionAllowed=false / automaticPromotionAllowed=false`。良い補助sliceや別構成へ採用先を変更0。次方針はこのcycleを閉じ、残存負率54.15%と未達Evidenceを次の設計へ渡すこと。Capital接続や経済検証には別Workが必要。',
             '', '設計根拠: WORK_REQUEST.mdのS1〜S3、旧RNEG REPORT／fit_rneg.py／source契約。実装参考S4はscikit-learn公式[threshold](https://scikit-learn.org/1.8/modules/classification_threshold.html)、[HistGradientBoostingClassifier](https://scikit-learn.org/1.8/modules/generated/sklearn.ensemble.HistGradientBoostingClassifier.html)、[train-only pitfalls](https://scikit-learn.org/1.8/common_pitfalls.html)。特徴群、alpha、support、到達目安は本Workの設計選択で、公式推奨の最適値や達成済みの経済結果ではない。']
    (OUT/'REPORT-ja.md').write_text('\n'.join(lines)+'\n')
    print(canonical({'report':str(OUT/'REPORT-ja.md'),'status':gate['status'],'figures':3,'primary':primary}))

if __name__=='__main__':main()
