"""Render descriptive saved tables/figures and one unapproved design hypothesis."""
from pathlib import Path
from decimal import Decimal
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo
import csv, gzip, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

REPO=Path(__file__).resolve().parents[2];ROOT=REPO.parent
OUT=REPO/'docs/evidence/capital-full-r-spectrum-20261006-v1';PRIVATE=ROOT/'capital_r_spectrum_private'
def read(p):return json.loads(Path(p).read_text())
def rows(p):return [json.loads(s) for s in gzip.open(p,'rt') if s.strip()]
def save(name,obj):(OUT/name).write_text(json.dumps(obj,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def table(headers,data):
    return '\n'.join(['|'+'|'.join(headers)+'|','|'+'|'.join(['---']*len(headers))+'|']+['|'+'|'.join(map(str,row))+'|' for row in data])
def yen(x):return f"{Decimal(x):,.2f}"
def pct(x):return f"{Decimal(x):.4f}%"
def image(fig,name):
    fig.savefig(OUT/name,dpi=160,bbox_inches='tight',facecolor='white');plt.close(fig)
def plots(census,cross,flow,miss,score):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    bb=census['populations']['ALL_FROZEN_ENTRY']['buckets'];x=np.array([b['bucket_pp_lower']+.5 for b in bb]);n=np.array([b['candidate_N'] for b in bb]);colors=['#cf5b61' if v<0 else '#238d9d' for v in x]
    ticks=list(range(-15,40,5))
    def axis(a):
        a.set_xlim(x.min()-.5,x.max()+.5);a.set_xticks(ticks);a.axvline(0,color='#374151',lw=1);a.grid(axis='y',alpha=.2);a.set_xlabel('Realized net return (%) - exclusive 1pp buckets')
    fig,ax=plt.subplots(2,1,figsize=(13,7),sharex=True,gridspec_kw={'height_ratios':[1.2,1]})
    for a in ax:a.bar(x,n,width=.9,color=colors);axis(a);a.set_ylabel('Unique Entry N')
    ax[1].set_yscale('symlog',linthresh=1);ax[1].set_ylabel('N (symlog detail, includes zero bins)')
    ax[0].set_title('Full R spectrum | known 1,016 / unknown 23 | min -17.565% / max +37.252%')
    fig.tight_layout();image(fig,'01_full_r_histogram.png')
    fig,ax=plt.subplots(2,1,figsize=(13,7),sharex=True)
    for a,key,title in zip(ax,['ALL_KNOWN_U5','U10'],['U5 opportunity -> realized R (N=170, includes U10)','U10 opportunity -> realized R (N=67)']):
        y=[b['candidate_N'] for b in cross['groups'][key]['buckets']];a.bar(x,y,width=.9,color=colors);a.set_ylabel('Unique Entry N');a.set_title(title);axis(a)
    fig.tight_layout();image(fig,'02_u_to_r_distribution.png')
    funded=np.array([b['funded_N'] for b in bb]);missed=n-funded
    fig,ax=plt.subplots(2,1,figsize=(13,7),sharex=True,gridspec_kw={'height_ratios':[1.4,1]})
    ax[0].bar(x,funded,width=.9,color='#238d9d',label='V5 funded');ax[0].bar(x,missed,bottom=funded,width=.9,color='#c8d0d8',label='V5 not funded (known)')
    ax[0].set_title('Original V5 account | funded vs missed by realized R | unique Entry');ax[0].legend();ax[0].set_ylabel('N')
    rate=np.array([b['funded_rate_all'] if b['funded_rate_all'] is not None else np.nan for b in bb]);ax[1].plot(x,rate*100,'o-',color='#238d9d',ms=3);ax[1].set_ylabel('Funded rate (%)');ax[1].set_ylim(-2,102)
    for a in ax:axis(a)
    fig.tight_layout();image(fig,'03_v5_funded_missed.png')
    fig,ax=plt.subplots(2,1,figsize=(13,7),sharex=True)
    debit=[float(b['buy_debit_jpy'])/1e6 for b in flow['buckets']];pnl=[float(b['realized_pnl_jpy'])/1e6 for b in flow['buckets']]
    ax[0].bar(x,debit,width=.9,color=colors);ax[0].set_ylabel('BUY debit (JPY million)');ax[0].set_title('Original V5 chain150 trades | actual BUY turnover and realized PnL')
    ax[1].bar(x,pnl,width=.9,color=colors);ax[1].axhline(0,color='#374151',lw=1);ax[1].set_ylabel('Realized PnL (JPY million)')
    for a in ax:axis(a)
    fig.tight_layout();image(fig,'04_v5_debit_pnl.png')
    fig,ax=plt.subplots(2,2,figsize=(14,8),sharex='col',gridspec_kw={'height_ratios':[2,1]})
    palette=['#2563eb','#0d9488','#c26b21','#8b5cf6'];head_order=['pP/MOVE_P5','MOVE_U2','MOVE_U3','MRET']
    for j,prefix in enumerate(['R','RN']):
        num=37 if prefix=='R' else 17;ks=list(range(1,num+1));curve=[r for r in score['pooled'] if r['population']=='EXECUTION_ELIGIBLE']
        for head,color in zip(head_order,palette):
            lookup={r['label']:r for r in curve if r['head']==head};a=[lookup[f'{prefix}{k}']['raw_direction_AUROC'] for k in ks];ax[0,j].plot(ks,a,'o-',ms=3,color=color,label=head)
        support=[next(r['positive_N'] for r in curve if r['label']==f'{prefix}{k}') for k in ks]
        ax[1,j].bar(ks,support,color='#c8d0d8');ax[1,j].set_ylabel('Event support N');ax[1,j].set_xlabel('Threshold magnitude (percentage points)')
        ax[0,j].axhline(.5,color='#64748b',ls='--');ax[0,j].set_ylim(0,1);ax[0,j].set_ylabel('Raw HIGH-score event AUROC');ax[0,j].set_title('Positive R >= +k%' if prefix=='R' else 'Negative RN <= -k% (direction NOT inverted)')
        ax[0,j].legend(fontsize=8);ax[1,j].set_xlim(.4,num+.6)
        for i in [0,1]:ax[i,j].grid(axis='y',alpha=.2)
    fig.suptitle('Existing causal scores across ALL observed thresholds | known eligible N=1,016 | no new fit',y=1.01)
    fig.tight_layout();image(fig,'05_score_r_threshold_curves.png')
    fig,ax=plt.subplots(figsize=(13,5));labels=[f'R{k}' for k in range(1,11)];xs=np.arange(10);bottom=np.zeros(10)
    palette={'rank/admission':'#64748b','Reserve':'#d79435','MAX3':'#8356ac','cash/lot':'#0d9488','cutoff':'#ef4444','same-symbol':'#1d4ed8','other':'#cbd5e1'}
    for reason,color in palette.items():
        values=np.array([next(r['grouped_reasons'][reason] for r in miss['cumulative'] if r['label']==label) for label in labels]);ax.bar(xs,values,bottom=bottom,color=color,label=reason);bottom+=values
    ax.set_xticks(xs,labels);ax.set_ylabel('Known positive-R misses (cumulative, overlapping)');ax.set_title('Original V5 missed standalone opportunities | native reasons | NOT recoverable portfolio profit');ax.legend(ncol=4,loc='upper right',fontsize=9);ax.grid(axis='y',alpha=.2)
    fig.tight_layout();image(fig,'06_positive_r_miss_reasons.png')
def main():
    census=read(OUT/'R_FULL_CENSUS.json');allc=census['populations']['ALL_FROZEN_ENTRY'];cum={x['label']:x for x in allc['cumulative']}
    cross=read(OUT/'U_R_CROSS.json');flow=read(OUT/'V5_R_CAPITAL_FLOW.json');fc={x['label']:x for x in flow['cumulative']};miss=read(OUT/'V5_R_MISS_REASONS.json');mc={x['label']:x for x in miss['cumulative']};score=read(OUT/'SCORE_R_SPECTRUM.json');audit=read(OUT/'INDEPENDENT_R_AUDIT.json')
    assert audit['pass'];now=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat();joined=rows(PRIVATE/'evaluation-only/ENTRY_JOINED_ANATOMY.jsonl.gz')
    tranches=[]
    for label in census['grid']['labels']:
        rr=[r for r in joined if r['actual_funded_trade'] is not None and r['events'][label]]
        base_debit=Decimal(0);extra_debit=Decimal(0);base_pnl=Decimal(0);extra_pnl=Decimal(0);water_debit=Decimal(0);water_shares=0;extra_shares=0
        for r in rr:
            t=r['actual_funded_trade'];d=r['native_decision'];b=100*Decimal(t['buy_effective']);p=100*(Decimal(t['sell_effective'])-Decimal(t['buy_effective']))
            base_debit+=b;base_pnl+=p;extra_debit+=Decimal(t['debit'])-b;extra_pnl+=Decimal(t['pnl'])-p
            extra_shares+=t['quantity']-100;water_shares+=d['water_fill_lots']*100;water_debit+=d['water_fill_lots']*b
            assert t['quantity']==d['first_pass_quantity']+d['water_fill_lots']*100
        tranches.append({'label':label,'funded_N':len(rr),'actual_first100_shares':100*len(rr),'actual_beyond100_shares':extra_shares,
            'actual_first100_debit_jpy':str(base_debit),'actual_beyond100_debit_jpy':str(extra_debit),
            'actual_first100_pnl_jpy':str(base_pnl),'actual_beyond100_pnl_jpy':str(extra_pnl),
            'native_water_fill_shares':water_shares,'native_water_fill_debit_jpy':str(water_debit)})
    save('ACTUAL_LOT_TRANCHE_FLOW.json',{'schema':'ARK_ACTUAL_FILLED_LOT_TRANCHE_V1','exact_jst':now,'rows':tranches,
        'meaning':'Decompose already-filled quantities under inherited proportional costs. All tranches belonged to the original single BUY. Not a cap-policy replay or recovery estimate.'})
    flat=sum(r['realized_net_return_exact']==[-2,2001] for r in joined if r['known'])
    save('ZERO_NEAR_ANATOMY.json',{'exact_jst':now,'exact_zero_N':cum['ZERO']['event_N'],'known_negative_N':cum['RNEG']['event_N'],
        'flat_gross_cost_return_exact':[-2,2001],'flat_gross_cost_pointmass_N':flat,'interpretation':'Unchanged raw BUY/SELL price gives net -2/2001 from existing 1.0005/0.9995 factors; no new label column or runtime threshold',
        'minus1_to_zero':next(x for x in allc['buckets'] if x['bucket_pp_lower']==-1),
        'zero_to_plus1':next(x for x in allc['buckets'] if x['bucket_pp_lower']==0)})
    plots(census,cross,flow,miss,score)
    positives=table(['累積条件','全known N','rank-pass N','V5 funded N','実購入株数','miss N'],
        [[f'R{k}',cum[f'R{k}']['event_N'],next(x['event_N'] for x in census['populations']['RANK_PASS_EXECUTION_ELIGIBLE']['cumulative'] if x['label']==f'R{k}'),fc[f'R{k}']['trade_N'],fc[f'R{k}']['shares'],mc[f'R{k}']['missed_N']] for k in range(1,11)])
    negatives=table(['累積条件','全known N','V5 funded N','BUY debit円','実現PnL円'],
        [[f'RN{k}',cum[f'RN{k}']['event_N'],fc[f'RN{k}']['trade_N'],yen(fc[f'RN{k}']['buy_debit_jpy']),yen(fc[f'RN{k}']['realized_pnl_jpy'])] for k in range(1,11)])
    stats=allc['continuous_return'];statstable=table(['指標','Entry実現net return'],[['平均',pct(stats['mean'])],['中央値',pct(stats['median'])],['最悪',pct(stats['min'])],['最高',pct(stats['max'])]]+[[f'Q{k}',pct(stats['quantiles'][str(k)])] for k in [1,5,10,25,75,90,95,99]])
    utable=[]
    for group in ['ALL_KNOWN_U5','U5_NOT_U10','U10','NON_U5','U_UNKNOWN']:
        z=cross['groups'][group];cc={x['label']:x for x in z['cumulative']}
        utable.append([group,z['N'],z['known_N'],z['unknown_N']]+[cc[k]['event_N'] for k in ['R1','R2','R3','R4','R5','R10','RNEG','RN1','RN2','RN3','RN5','RN10']]+[next(b['candidate_N'] for b in z['buckets'] if b['bucket_pp_lower']==0)])
    utable=table(['U群','N','R known','unknown','R1','R2','R3','R4','R5','R10','RNEG','RN1','RN2','RN3','RN5','RN10','0〜<1%'],utable)
    ft=table(['実funded帯','N','株数','BUY debit円','PnL円','拘束分合計','資金×拘束時間 円分'],
        [[label,fc[label]['trade_N'],fc[label]['shares'],yen(fc[label]['buy_debit_jpy']),yen(fc[label]['realized_pnl_jpy']),fc[label]['holding_minutes_total'],yen(fc[label]['capital_minutes_jpy'])] for label in ['RPOS','RNEG','RN1','RN2','RN3','RN5','RN10','R1','R3','R5','R10']]+[
        ['0〜<1%',flow['near_zero_0_to_1']['trade_N'],flow['near_zero_0_to_1']['shares'],yen(flow['near_zero_0_to_1']['buy_debit_jpy']),yen(flow['near_zero_0_to_1']['realized_pnl_jpy']),flow['near_zero_0_to_1']['holding_minutes_total'],yen(flow['near_zero_0_to_1']['capital_minutes_jpy'])]])
    reasons=table(['条件','miss N','rank/admission','Reserve','MAX3','cash/lot','cutoff','same-symbol','その他'],
        [[label,mc[label]['missed_N']]+[mc[label]['grouped_reasons'][k] for k in ['rank/admission','Reserve','MAX3','cash/lot','cutoff','same-symbol','other']] for label in [f'R{k}' for k in range(1,11)]])
    auroc=[]
    for label in [f'R{k}' for k in range(1,11)]+[f'RN{k}' for k in range(1,11)]:
        rr=[x for x in score['pooled'] if x['population']=='EXECUTION_ELIGIBLE' and x['label']==label]
        auroc.append([label,rr[0]['positive_N']]+[f"{next(x['raw_direction_AUROC'] for x in rr if x['head']==h):.6f}" for h in ['pP/MOVE_P5','MOVE_U2','MOVE_U3','MRET']])
    auroc=table(['event','N','pP','MOVE_U2','MOVE_U3','MRET'],auroc)
    reset=read(OUT/'RESET20_R_FLOW.json');resetrows=list(csv.DictReader((OUT/'RESET20_R_FLOW.csv').open()))
    resettable=table(['window','final cash円','RNEG debit比率','R3+比率','R5+比率','R10+比率'],
        [[x['window_id'],yen(x['final_cash_jpy'])]+[f"{float(x[k])*100:.2f}%" for k in ['RNEG_debit_share','R3_debit_share','R5_debit_share','R10_debit_share']] for x in resetrows])
    candidates='''# 🧭 次のCapital判断 — 1個の草案、実装未承認

判定: **R_SPECTRUM_INCONCLUSIVE**。Economic relevanceとsupportは確認できたが、悪いR帯と良いR帯を既存causal情報で安全に選び分ける根拠が不足している。今回のAUROCを新Gate承認へ変換しない。

検討する草案は **初回BUY内の100株を超える追加lotへの集中上限** の1個だけ。変更箇所はCapitalの整数数量・配分cap。全Entryに共通の上限候補を別Workで事前に固定し、V5の同じ購入ゲート、同じtarget、MAX3、最低lot、cash・約定制約の下で適用する案。現時点では上限値・式・trade-off受容条件は未決であり、policyとして固定済みとは扱わない。

観測上のdonor課題はRNEG、特にRN1〜RN3と深い負tailへの多lot投入。receiver課題はR1〜R10以上を含む既存購入適格Entryへの配分。R3/R5など単一thresholdを新Gateにはしない。小幅利益も一律悪い候補としない。これらのR帯は将来outcomeによる診断名であり、runtimeの対象選定条件ではない。

元の100株を超える実funded部分とnative water-fill部分の金額・損益をACTUAL_LOT_TRANCHE_FLOW.jsonへ分離した。損失だけでなく大きな利益も追加lotから出ており、上限を置けばmedian wealthが上がるとは示せていない。縮小で解放できるのはcashで、保有slotではない。残したcashは、その時点の同batchまたは後続の新しいFrozen Entryが既存ゲートを通過した場合にだけ使える。過去rejectの復活、早売り、置換、買い増し、Reserve/Rank/Quality Pareto/MRET throttleの再開は行わない。

この草案は、reject済みV5.1のpP順lot優先を再試行する案ではない。高pP/高Qualityは正tailと負tailの両方に順位情報があるため、scoreだけで増額する仮説を支持しない。MRET反転・新weight・新thresholdで救済しない。MRET absolute-loss defenseはINCONCLUSIVEを維持する。

**V5.2を直ちに実装・Replayする根拠は不足。** 別Workでこの追加lot集中機構のcash→受け手・利益減少リスクを固定仕様へ具体化できたときに、初めて評価を検討する。今回は設計仮説1個、実装candidate0、Replay0で閉じる。100万円→200万円の改善・回収利益は未証明。
'''
    (OUT/'NEXT_CAPITAL_DECISION.md').write_text(candidates)
    report=f'''# 📊 Capital Full R-Spectrum Anatomy — 最終報告

実時計JST: {now}  
判定: **R_SPECTRUM_INCONCLUSIVE / DIAGNOSTIC_COMPLETE / V5.2未実行**

## 🎯 冒頭回答

R1〜R10、RN1〜RN10の全件数は下表。全Frozen Entry 1,039件のうちknown1,016・unknown23。実観測は−17.565%〜＋37.252%までで、**−18〜＋37の56個の1pp bucketとR37/RN17までの累積grid**を機械生成した。positive462、negative554、exact0は0。平均＋0.1434%だが中央値−0.09995%。これはEntry単体returnであり、portfolio wealthではない。

U5 170件の43件、U10 67件の15件がnegativeへ着地。U5のRN5は8件・RN10は2件、U10のRN5は2件・RN10は1件。U5とU10の最悪はそれぞれ−16.9990%・−13.9279%。Opportunityは実現利益の保証ではない。

V5はnegativeへBUY debit23,691,039.60円、損益−564,508.65円を投じた。全positiveへ20,733,961.80円、利益＋1,041,944.80円。R1/R2/R3/R4/R5/R10の実購入件数・株数・missを全表へ保存。R+ missの最大理由は全帯でrank/admission。rank-pass内ではReserve/MAX3が主要で、closed routeを再開する根拠にはしない。

既存pP/U2/U3はR4〜R10へ順位情報が強まる一方、RN1〜RN10も高score側へ寄る。全曲線から見えるのは正負tail双方の大きさへの情報であり、Win/Lossを安全に分ける証明ではない。MRET原向きは実行適格母集団のR1〜R10とRN1〜RN10でAUROCが0.5未満。さらに遠いtailでは0.5を超える箇所もあるがsupportが小さい。向き反転を行わずrelative diagnosticに留める。V5 funded内では向き・強さが変わり、選択条件による偏りもある。

次の課題はnegativeへの追加lot集中を抑え、既存ゲートを通るpositive全帯への配分を維持できるか。草案は追加lot集中上限1個のみ。ただし良いtailも削るため、V5.2を今すぐ作る価値はまだ立証されていない。新fit、新Capital/EXIT Replay、provider、protected、order、merge、Claudeはすべて0。

## 🧮 全域censusとcontinuous統計

{positives}

{negatives}

{statstable}

累積R/RNは重複する。R10はR5の内数、RN10はRN1の内数で、列を足して機会数や資金を求めない。全tailと空bucketをR_FULL_CENSUS.json/CSVへ保存し、tailを一括化していない。unknownをevent/non-event/Loserへ入れていない。

![full R histogram](01_full_r_histogram.png)

0付近は−1〜<0%が{next(b['candidate_N'] for b in allc['buckets'] if b['bucket_pp_lower']==-1)}件、0〜<1%が{next(b['candidate_N'] for b in allc['buckets'] if b['bucket_pp_lower']==0)}件。raw価格が同じ場合の費用だけによるnet −2/2001（約−0.09995%）と一致するpoint massは{flat}件。exact0がないのは観測結果であり、Loser<=0とRNEG<0の定義は別のまま。

## 🔥 U Opportunity → R Realization

{utable}

ALL_KNOWN_U5はU10を含む。U5非U10/U10/non-U5/U unknownがUの排他的分割。U5/U10は全件R knownで、R unknown23件はnon-U5に属する。U unknownは0件であり、0補完したものではない。U unknown群の全bucketも保存した。U5/U10をR予測精度と呼ばない。

![U to R](02_u_to_r_distribution.png)

## 💴 V5資金・数量・拘束時間

{ft}

元V5旧chainの一意Entry150件・157,300株をreuse。BUY debit総額44,425,001.40円は38 selected sessionsにわたる繰返し売買のturnoverであり、同時保有資金でも20連続営業日の月次値でもない。実現PnLは＋477,436.15円、recycle cash使用6,728,380.05円。資金×拘束時間の単位は円分。funded slotは1/2/3が41/59/50件で、各BUY直後のconcurrent occupancy。時刻は固定の時刻帯で集計した。

0〜<1%帯へのdebit6,406,201.50円から利益29,079.25円。小幅利益は一律悪い候補ではない。どの帯も実quantityのcredit/debitで分類し、100株referenceと実funded returnの一致を確認した。slot、時刻、native allocation band、recycle、拘束の全facetはV5_R_CAPITAL_FLOW.jsonに保存した。

![funded missed](03_v5_funded_missed.png)
![debit pnl](04_v5_debit_pnl.png)

未funded候補には実購入quantityがないため、回収可能株数はnull。reference100株はlabel単位であり、全missを同時に購入できた量や回収可能利益ではない。

## 🚧 Positive R miss reason

{reasons}

各known R+は現在実行適格。cutoff0件という表示は、cutoff以降11件のRがunknownであることと分離する。unknown by reasonはrank/admission19、Reserve2、cutoff11などを便宜的に数え直さず、V5_R_MISS_REASONS.jsonの原本を参照する。nativeの最初の阻害reasonを保存し、二次的な原因や全回収可能性を推定していない。

![miss reasons](06_positive_r_miss_reasons.png)

## 🧠 既存causal scoreの全曲線

{auroc}

分母はknown実行適格1,016。rank-pass内492・funded150の全曲線も保存。原score高方向でRN event AUROCを計算し、逆数や-scoreへ切り替えていない。特にRNの高AUROCは「高scoreほど損失eventへ順位が寄る」という意味。

既存pP training-rank HIGH/LOWでは、R3率13.04%/8.37%、RN3率15.37%/4.98%。低score側に深いRNが増えるという仮説は支持されない。pPのRN3とRN5は8/8 blockで原向きAUROC>0.5、RN10は定義可能5/5 block。R5も8/8で>0.5。両側の順位情報を同時に保持して読む。

R1〜R3は全母集団のAUROCが概ね0.55〜0.60、R4〜R10では概ね0.65〜0.72へ強まるが、positive supportは271→25へ減る。極端なtailはR37=1件、RN17=3件で新Gateの根拠にできない。MRET fixed-rM HIGH側はRN率が低いがpositiveも低く、funded subsetでは逆にR1の原向きAUROC0.5555となる。選択・support・方向の変化をabsolute-loss defense成立へ読み替えない。

SCORE_R_STRATA.csvに原8block/session別のknown/unknown・event率・全4頭AUROC、SCORE_R_FIXED_BUCKETS.csvにnative S/A/B/C・既存pP band・training由来r/rM halfの全event率を保存。q2/q3には正式固定rank bucketがないため、新quantileを作らなかった。既存R5/R10の744個のAUROCセルをreuseし、新fit/再認証/bootstrapは0。

![score curves](05_score_r_threshold_curves.png)

## 🔁 保存RESET20との接続

{resettable}

予定21窓を保持し、12coverage-blockedはR_flow/final cash=null。7月11日・14日の調査は反復していない。新reset Replayは0。9口座は重複する市場期間なので独立標本ではない。記述Pearson相関はRNEG debit比率対cash−0.6285、R3+＋0.5263、R5+＋0.2023、R10+＋0.9425。R10を新Gateとして選んだり、因果効果・有意差・将来性能を主張しない。

## 🔍 独立監査・実施量

独立経路はsaved debit/creditを整数の比へ直し、cross multiplicationで全境界と負のfloorを再判定。known partition、累積単調性、U row totals、quantity/debit/PnL、holding、slot、全reset終点、unknown mask、既存R5/R10一致を確認した。main analytical関数・EXIT/Capital engine・allocatorをimportしていない。全4raw scoreのR1/RN1はpairwise AUROCで照合。

{table(['確認','結果'],[['独立チェック',f"{audit['check_N']:,}項目・不一致0"],['known/unknown','1,016/23'],['V5 trade','150件'],['reset complete/blocked','9/12'],['mechanical derived labels','1 logical batch・1 completed output'],['技術修復','unknown metadata読取り1回、旧public session summary→既存private full support読取り1回'],['新fit/refit/calibration','0'],['新Capital candidate/Replay・EXIT rematerialization','0/0/0'],['provider/protected/order/main merge/force push/Claude','すべて0']])}

技術修復はTECHNICAL_RECEIPT.jsonに保存。成功済みderived1039行を再生成せず、strategy・mask・固定grid・原本Rを変えなかった。修復後は既存完成Rを読み、表作成を続けた。元providerのhistorical arrivalはUNKNOWNのままで、verifiedへ昇格していない。

## 🧭 次の1機構と終了判定

**R_SPECTRUM_INCONCLUSIVE**。Economic relevanceとsupportは十分あるが、既存scoreで悪いR帯を選んで資金を抜き、良いR帯へ増額する因果的な分離が弱い。拒否済みV5.1・closed Reserve・Rank cutoff・Quality Pareto・MRET throttleは保持。

草案は初回BUY内の100株を超える追加lot集中上限のみ。ACTUAL_LOT_TRANCHE_FLOW.jsonは実約定済みtrancheを分離した記述表で、新上限のwealthではない。上限値・式は未固定。NEXT_CAPITAL_DECISION.mdにdonor/receiver、cashのみ解放する制約、利益tailを削る副作用、次Workの未決事項を記載した。今回はV5.2を実装・Replayしない。V5 baseline維持、productionReady=false、改善・200万円到達の新claimなし。

実購入の100株超部分は、RNEGではdebit18,089,040.00円・PnL−441,768.05円、RPOSではdebit13,917,655.35円・PnL＋721,721.30円。native water-fillそのものは全150件で700株・debit269,134.50円に留まる。従って問題をwater-fillだけと決め打ちしない。これらは既存約定を部分へ分解した値であり、数量変更後の新しいcash/購入集合/最終資産ではない。

## 💾 保存

JSON/CSVを数値正本、上図を補助とする。private identity/symbol別のjoinはprivate ZIPへ隔離し、公開GitHubはaggregateのみ。開始・contract、census、score/capital、finalを実時計JST付きcheckpointへ保存し、actual GETのcommit/tree/blob/本文検証をGITHUB_READBACKS.jsonと最終receiptへ記録する。旧V5/V5.1 Evidenceはread-only。
'''
    # Obtain exact unknown-reason counts from the authoritative saved miss table.
    report=report.replace('unknown by reasonはrank/admission19、Reserve2、cutoff11などを便宜的に数え直さず、V5_R_MISS_REASONS.jsonの原本を参照する。',
                          'unknown by native reasonは'+json.dumps(miss['unknown_by_native_reason'],ensure_ascii=False)+'。')
    (OUT/'REPORT-ja.md').write_text(report)
    state=read(OUT/'CURRENT_STATE.json');state.update(exact_jst=now,status='R_SPECTRUM_INCONCLUSIVE',work_status='DIAGNOSTIC_COMPLETE',
        completed=['All56 exclusive buckets and full positive/negative thresholds','U cross/native150 funded flows/miss reasons','All4 causal score curves, inherited strata and fixed buckets','Saved9 complete reset flows and12 null blocked windows','Independent audit passed','Six real-data plots','One unapproved extra-lot concentration-cap design hypothesis'],
        blockers=['Existing causal scores do not safely isolate harmful returns from profitable tails; no V5.2 promotion','Jul11/14 coverage remains unknown, retained from prior work; not re-investigated'],
        next='Keep V5 baseline. Before any new cycle, decide whether a fixed extra-lot concentration cap can be specified and preserve positive-tail gains; this Work does not authorize implementation/replay',
        next_design_hypothesis_N=1,new_policy_candidate_N=0,improvement_claim=False,fresh_validation_claim=False,productionReady=False)
    state['counts'].update(new_descriptive_AUROC_cells=score['new_descriptive_AUROC_cells'],prior_AUROC_cells_reused=score['prior_R5_R10_AUROC_cells_reused'],independent_check_N=audit['check_N'],independent_audit_invocations=1,score_aggregation_failed_incomplete_attempts=1)
    save('CURRENT_STATE.json',state);event={**state,'event':'FINAL_R_SPECTRUM_COMPLETE'}
    save('checkpoints/FINAL_R_SPECTRUM_COMPLETE.json',event)
    with (OUT/'WORK_STATUS_LOG.jsonl').open('a') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
    print(json.dumps({'status':state['status'],'exact_jst':now,'plots':6,'design_hypotheses':1,'policy_candidates':0,'replays':0}))
if __name__=='__main__':main()
