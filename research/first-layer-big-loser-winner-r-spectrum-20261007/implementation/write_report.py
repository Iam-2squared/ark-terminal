"""Format already validated saved-outcome tables. No new statistical or model calculation."""
import csv
import json
from decimal import Decimal
from pathlib import Path
import argparse

def main():
    a=argparse.ArgumentParser();a.add_argument('--public',required=True);args=a.parse_args();p=Path(args.public)
    def rows(name):return list(csv.DictReader((p/name).open(encoding='utf-8',newline='')))
    def fmt(v,n=2):return 'N/A' if str(v)=='N/A' else f'{Decimal(v):,.{n}f}'
    def pc(v):return 'N/A' if str(v)=='N/A' else fmt(v)+'%'
    def table(headers,data):
        return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                         ['| '+' | '.join(str(v) for v in r)+' |' for r in data])+'\n'
    A=rows('ENTRY_EXIT_R_DISTRIBUTION.csv');B=rows('LEGACY_R_BAND_KEEP_DROP.csv');C=rows('CUMULATIVE_LOSER_WINNER_KEEP_DROP.csv')
    DC=rows('DROP_COMPOSITION.csv');M=rows('RETURN_MASS_DECOMPOSITION.csv')
    summary=json.loads((p/'CENSUS_SUMMARY.json').read_text());audit=json.loads((p/'INDEPENDENT_AUDIT.json').read_text())
    bmap={(r['cohort'],r['point'],r['bucket']):r for r in B}
    cmap={(r['cohort'],r['point'],r['group']):r for r in C}
    mm={(r['cohort'],r['point'],r['group'],r['decision_partition']):r for r in M}
    points=['CAL95','M80','M60','M40','M20','M10']
    labels='LEGACY_DIAGNOSTIC_ONLY / NEGATIVE_EVIDENCE / NOT_A_NEW_PARENT'
    out=['# 📊 Frozen Entry→Frozen EXIT/EOD 全R帯・保存済み旧C11診断',
         '文書ID: ARK_FIRST_LAYER_BIG_LOSER_WINNER_R_SPECTRUM_WORK_20261007。Primaryは旧C11のS1/S2 DEV_COMPARE、KEEP/DROP前のFrozen Entry union。',
         '期間は2025-07-09～2025-07-29、対象12 sessions・223銘柄・322 Entry。正式R既知316件、不明6件。S1は164件（既知159・不明5）、S2は158件（既知157・不明1）、Entry ID重複0件。']
    for cohort in ['UNION','S1','S2']:
        out+=['## 📋 表A — '+cohort+' 全EntryのR分布',
              '構成比の分母は各cohortのR既知全件。UNKNOWNはその分母へ入れず、全Entry比を併記する。TOTALの既知構成比は既知行だけで100%。中央値・合計は正式R既知行のみ。pp-sumは各EntryのR百分率を等重みで足した値。']
        data=[]
        for r in A:
            if r['cohort']!=cohort:continue
            data.append([r['bucket'],r['range'],r['N'],pc(r['share_R_known_pct']),pc(r['share_all_entries_pct']),
                r['distinct_sessions'],r['distinct_symbols'],fmt(r['R_median_pct'],4),fmt(r['R_sum_pp'],6)])
        out.append(table(['bucket','範囲','元N','R既知比','全件比','sessions','銘柄','R中央値 %','R合計 pp-sum'],data))
    out+=['## 🎯 大Loser・中大Winnerの規模',
          '以下は重なる累積群。合算してEntry数を増やさない。負R絶対和の分母はMINUS全体314.234103pp、正R合計の分母はPLUS全体388.127604pp。符号混在のnet Rを分母に使っていない。']
    data=[]
    for group in ['R_LE_NEG5','R_LE_NEG4','R_LE_NEG3','R_GE_POS2','R_GE_POS3','R_GE_POS4','R_GE_POS5']:
        r=mm['UNION','M20',group,'ALL']
        denominator=mm['UNION','M20','ALL_MINUS' if group.startswith('R_LE') else 'ALL_PLUS','ALL']
        field='negative_mass_abs_pp' if group.startswith('R_LE') else 'positive_mass_pp'
        share=Decimal(r[field])/Decimal(denominator[field])*100
        data.append([r['range'],r['group_N'],fmt(r['negative_mass_abs_pp'],6),fmt(r['positive_mass_pp'],6),pc(str(share))])
    out.append(table(['累積群','元N','負R絶対和 pp','正R合計 pp','該当符号全体のmass比'],data))
    out+=['−3%以下28件はMINUS172件の16.28%だが、負R絶対和の55.18%を占める。＋2%以上56件はPLUS144件の38.89%で、正R合計の80.18%を占める。＋5%以上20件だけで正R合計の54.88%。小標本の割合を性能Gateへ変えていない。',
          '## 🔎 保存済み旧C11の6点比較 — UNION',labels,
          '全点のfinal decisionをそのまま読む。M80等は旧保存point名の表示変換であり、thresholdを再適用していない。セルは件数/元Nと率。decision coverageは全6点で322/322＝100%（空のZERO帯はN/A）。']
    def kd(r,field):return f"{r[field]}/{r['N']} ({pc(r[field+'_rate_pct'])})"
    data=[]
    for point in points:
        data.append([point,kd(cmap['UNION',point,'R_LE_NEG5'],'DROP'),kd(cmap['UNION',point,'R_LE_NEG3'],'DROP'),
            kd(cmap['UNION',point,'R_GE_POS2'],'KEEP'),kd(cmap['UNION',point,'R_GE_POS3'],'KEEP'),
            kd(cmap['UNION',point,'R_GE_POS4'],'KEEP'),kd(cmap['UNION',point,'R_GE_POS5'],'KEEP')])
    out.append(table(['保存point','≤−5% DROP','≤−3% DROP','≥＋2% KEEP','≥＋3% KEEP','≥＋4% KEEP','≥＋5% KEEP'],data))
    out+=['CAL95は≥＋3% Winnerを30/30件KEEPする一方、≤−3% LoserのDROPは0/28件。M20では≤−3%の24/28件をDROPするが、≥＋2%も40/56件、≥＋3%も20/30件、≥＋5%も12/20件DROPする。M10は≤−3%を26/28件DROPする一方、≥＋5% KEEPは1/20件。この旧系譜の交換関係をnegative evidenceとして保持する。新しいChampion・Pareto・推奨threshold・数値Gateは選ばない。',
          '## ⚖️ 件数とreturn massの両面 — UNION、全6点',labels]
    data=[]
    for point in points:
        lo=mm['UNION',point,'R_LE_NEG3','DROP'];wi=mm['UNION',point,'R_GE_POS2','DROP']
        pk=mm['UNION',point,'ALL_PLUS','KEEP'];ld=mm['UNION',point,'ALL_MINUS','DROP']
        data.append([point,fmt(lo['negative_mass_abs_pp'],6),fmt(wi['positive_mass_pp'],6),
            pc(pk['positive_mass_share_of_group_pct']),pc(ld['negative_mass_share_of_group_pct'])])
    out.append(table(['保存point','≤−3% DROP負R絶対和 pp','≥＋2% DROP正R合計 pp','PLUS正R合計のKEEP比','MINUS負R絶対和のDROP比'],data))
    out+=['M20の≤−3% DROP負R絶対和は135.749979pp、≥＋2% DROP正R合計は184.903783pp。PLUS全体で残った正R合計は39.06%。負R件数・massの除去だけを成功扱いしない。これは等重みの保存R会計で、口座の円利益・複利収益・Final Equity・Capital改善を表さない。',
          '## 🧾 表B — 保存decisionのR帯別分解（S1 / S2 / UNION、全6点）',
          '各表にALL MINUS、ALL PLUS、R既知、TOTALを含める。R UNKNOWNのdecisionは示すが、Winner/Loserの成功・失敗へ分類しない。各帯でN＝KEEP＋DROP＋decision UNKNOWN。KEEP率・DROP率・coverageの分母は元N、元N=0はN/A。']
    for cohort in ['UNION','S1','S2']:
        for point in points:
            out+=['### '+cohort+' / '+point,labels]
            data=[[r['bucket'],r['N'],r['KEEP'],r['DROP'],r['decision_UNKNOWN'],pc(r['KEEP_rate_pct']),pc(r['DROP_rate_pct']),pc(r['decision_coverage_pct'])]
                for r in B if r['cohort']==cohort and r['point']==point]
            out.append(table(['R帯','元N','KEEP','DROP','decision不明','KEEP率','DROP率','coverage'],data))
    out+=['## 📐 表C — 累積Loser / Winner（S1 / S2 / UNION、全6点）',
          'ZEROとR UNKNOWNを含めない。各累積群は排他的bucketの該当合計と照合済み。累積群同士を合算しない。']
    for cohort in ['UNION','S1','S2']:
        for point in points:
            out+=['### '+cohort+' / '+point,labels]
            data=[[r['range'],r['N'],r['KEEP'],r['DROP'],r['decision_UNKNOWN'],pc(r['KEEP_rate_pct']),pc(r['DROP_rate_pct']),pc(r['decision_coverage_pct'])]
                for r in C if r['cohort']==cohort and r['point']==point]
            out.append(table(['累積群','元N','KEEP','DROP','decision不明','KEEP率','DROP率','coverage'],data))
    out+=['## 🧩 DROP composition — UNION、全6点',
          '以下の分母は各pointでDROPした全件（R UNKNOWNも含む）。各帯の元Nを分母とするDROP率と区別する。S1/S2の全内訳もDROP_COMPOSITION.csvへ保存。']
    for point in points:
        out+=['### UNION / '+point,labels]
        data=[[r['bucket'],r['DROP_N'],r['all_DROP_N'],pc(r['share_of_all_DROP_pct'])]
            for r in DC if r['cohort']=='UNION' and r['point']==point]
        out.append(table(['R帯または重なる要約群','DROP件数','全DROP','全DROPに占める割合'],data))
    out+=['## 💠 全R帯のreturn mass分解 — UNION / M20の表示例',labels,
          'RETURN_MASS_DECOMPOSITION.csvにはS1/S2/UNION × 全6点 × 全R帯・累積群 × ALL/KEEP/DROP/decision UNKNOWNを保存。負R絶対和と正R合計は別々に計算し、分母0はN/A。以下はM20の全R帯であり、他5点を省略・採用選別したものではない。']
    data=[]
    for r in A:
        if r['cohort']!='UNION':continue
        g=r['bucket'];total=mm['UNION','M20',g,'ALL'];keep=mm['UNION','M20',g,'KEEP'];drop=mm['UNION','M20',g,'DROP'];un=mm['UNION','M20',g,'DECISION_UNKNOWN']
        data.append([g,fmt(total['negative_mass_abs_pp'],6),fmt(drop['negative_mass_abs_pp'],6),pc(drop['negative_mass_share_of_group_pct']),
            fmt(total['positive_mass_pp'],6),fmt(keep['positive_mass_pp'],6),fmt(drop['positive_mass_pp'],6),pc(keep['positive_mass_share_of_group_pct']),
            fmt(un['negative_mass_abs_pp'],6)+' / '+fmt(un['positive_mass_pp'],6)])
    out.append(table(['群','全負R絶対和','DROP負R絶対和','負mass DROP比','全正R合計','KEEP正R合計','DROP正R合計','正mass KEEP比','decision不明の負/正mass'],data))
    out+=['正式R不明6件のmassは算定不能。CSVのknown-only集計0はR=0への補完を意味しない。表AのR UNKNOWNのR合計はN/A。会計恒等式はR・decisionがともに既知の同一maskでのみ、KEEP合計−全件合計＝−DROP合計として照合し、全18比較で残差0。',
          '## 🗂️ 原本・欠損・用途',
          '公開原本ref: 8c9988157680aa4dec40bf984b789a5309a4904c、private原本ref: b7fb211ba62e966a4f9dc4d37567851c238cc63c。source branchのcurrent HEADもこの2値とactual GETで一致した。過去pointerだけでcurrentを認定していない。',
          'C11 final archiveは5,942,456 bytes、SHA256 10ac0ff4a3148df636a2cf0ddab81e74476adfcf52d75416151c3f051e9ff69d。保存10partと選択読取りmemberのbytes/hash/blobは照合済み。必要原本はWORK_SCOPE_AND_SOURCE_MANIFEST.jsonへexact member/path/hashで固定。モデル・全1600特徴量・CAL/TEST outcomeは開かない。',
          '322件のCANONICAL_RETURN_ROWS、同じ322件のtargeted正式teacher、S1/S2 DEV_COMPARE ID台帳、Exposure台帳、C11 union/S1/S2保存decision、prediction sealを読む。明示symbol列は保存済みidentity metadataから同じ322 IDへ機械的に対応付け、IDを日付・銘柄へ縮約しない。S1/S2重複0なので帰属競合なし。代替Entry世界・別armを新たに合算していない。',
          '保存R_pct_numerator/R_pct_denominatorを百分率の正確なFractionとして主集計。別実装はR_native_fraction_decimal（fraction単位）×100をDecimalで再計算。両者は原値で一致し、表示前の正式値でbucketを決める。Entry価格・EXIT/EOD・fill・buy debit/sell credit・100株basisは保存teacherのまま。teacher再生成なし。',
          '必要入力ファイルと保存decision6点に不足はない。正式R不明6件は原本でreturn_available=false、R native/分子/分母がnullであり、より詳細なreasonは保存されていない。FORMAL_R_UNAVAILABLE_SOURCE_REASON_UNSPECIFIEDとして保持する。0%、MINUS、DROPへ補完しない。6点ともdecision UNKNOWNは0件。',
          '旧C11 decision sealはWinner join前に保存され、現在の各split decision bytesとunion bytesがsealに一致する。今回はscoreの再計算・threshold再適用・判定値変更をしていない。R帯・EXIT結果は評価専用で、BUY_INTENT featureへコピーしない。',
          'ALL_KEEPは1種類だけの定義上の非学習参照（cohort別表示はALL_KEEP_REFERENCE.csv）。新FIRST LAYERはNEW_FIRST_LAYER_NOT_RUNでKEEP/DROP=N/A。旧C11やALL_KEEPの数字を代入していない。',
          '## ✅ 検算・再現・Development Exposure',
          f"別実装検算は{audit['checks']:,}項目、不一致{audit['mismatch_N']}件。主集計はFraction＋if-chain、別実装はDecimal＋排他的interval表。原本ID・R・decisionから再計算し、主表を計算入力として使っていない。同一作者の別実装検算であり、第三者盲検監査とは呼ばない。",
          '人工境界は−5/−4/−3/−2/−1/0/＋1/＋2/＋3/＋4/＋5%の直前・同値・直後、計33値（差1e−9 percentage points）。欠損・NaN・不正値等6caseと合わせ両実装78確認、不一致0。人工差は正式Rのepsilonへ持ち込んでいない。',
          '同一入力の再現確認は1回のみ。主10成果物とprivate row join、計11ファイルがbyte/hash一致。入力10ファイルのhash変更0、単一specは集計前に固定済み。集計の技術修復cycleは0/5。取得時の個別blob 404はarchive memberの所在を解決して回復し、集計仕様・母集団・R・decisionへ変更なし。',
          '対象は全て繰り返し露出したADAPTIVE_DEVELOPMENT。今回outcomeを読んだのはDEV_COMPARE 322 IDのみ。R既知316/不明6、12既存session、新規日付0。TRAIN/CAL outcome追加閲覧0、TEST/Protected/Fresh/OOS/Prospective/保護REPORT開封0。1600 identity metadataにはoutcomeがなく、旧1600 QA記録から閲覧許可を推定していない。',
          '## 🛡️ 実行receiptと停止状態']
    operations=['new model fits','preprocessing/calibration fits','model inference/score replay','new feature/representation build',
        'threshold search/recomputation/reapplication','new KEEP/DROP policies','Entry/EXIT policy Replay','Capital/Portfolio Replay',
        'new teacher generation','RAW scan/recovery','provider requests','TEST/protected partition opens','orders/production updates','main merges/force pushes']
    out.append(table(['禁止操作','今回実行量'],[[x,0] for x in operations]))
    safety=['executionAllowed','brokerWriteAllowed','excelOrderWriteAllowed','rssOrderFunctionAllowed','liveTradingAllowed',
        'paperTradingAllowed','automaticPromotionAllowed','productionUpdateAllowed','transmitted']
    out.append(table(['Safety9','値'],[[x,'false'] for x in safety]))
    out+=['保存は診断専用branch/directoryへappend-only。原本・旧closure・Champion/Pareto・mainを上書きしない。公開側は契約・集計・報告・hashのみ。個別ID・R原値・decision・source packageはprivate側。実際のcommit/bytes/hash/readbackは保存後のREADBACK_RECEIPT_PUBLICATION.jsonへ記録する。',
          '終了status: **R_SPECTRUM_CENSUS_COMPLETE_DEVELOPMENT**。newFirstLayerSelected=null、productionReady=false、capitalImprovement=NOT_EVALUATED。新FIRST LAYERは未設計確定・未実装・未学習。1か月100万円→200万円への資産効果は今回測定していない。',
          '## ⏹️ 次の問い（1つだけ）',
          '「＋2%以上のWinner（56件、正R合計311.19pp）を残しながら、−3%以下のLoser（28件、負R絶対和173.39pp）を購入前情報で分離できるか。」',
          'これは今回の分布から出した次の研究質問であり、学習target・採用thresholdの決定ではない。設計・fit・TEST・Capitalへの自動進行は行わず、ここでSTOPする。']
    (p/'REPORT-ja.md').write_text('\n\n'.join(out)+'\n',encoding='utf-8')
    (p/'NEXT_QUESTION.txt').write_text('「＋2%以上のWinner（56件、正R合計311.19pp）を残しながら、−3%以下のLoser（28件、負R絶対和173.39pp）を購入前情報で分離できるか。」\n研究質問のみ。学習target・threshold採用・モデル設計・fit・TEST・Capitalへの進行は未許可。STOP。\n',encoding='utf-8')
    print(json.dumps({'report_bytes':(p/'REPORT-ja.md').stat().st_size,'report_tables':sum(s.startswith('|') for s in out)},ensure_ascii=False))

if __name__=='__main__':main()
