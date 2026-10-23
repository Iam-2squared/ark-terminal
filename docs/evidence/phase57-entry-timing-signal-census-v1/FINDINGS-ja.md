# Entry Timing Signal Census v1 — 結論と次段階への引継ぎ

**Censusは完了。今回の固定Timing候補によるImmediate超えは確認できなかった。Entry vNextの学習・採用・Freezeは行わない。**

同じ2,155 Opportunityを全方式に残し、Signalなし・失敗・観測不足も保存した。
SignalなしでOpportunityを拒否する経路はなく、10 active minutesでFallback
BUY attemptへ移り、共通30 active minutesまでretryする。

| 比較方式 | fill proxy | +3 Capture | +5 Capture | paired買値改善 平均 |
|---|---:|---:|---:|---:|
| A Immediate + retry | 1,963 | 85.28% | 87.50% | 0.000% |
| B Continuation | 1,857 | 67.67% | 70.59% | -0.017% |
| C Breakout / Expansion | 1,857 | 69.25% | 71.57% | -0.021% |
| D Pullback / Recovery | 1,857 | 70.43% | 72.55% | -0.025% |
| E Combination | 1,857 | 70.96% | 73.28% | -0.026% |
| F 10m Fallback | 1,857 | 67.54% | 70.59% | -0.015% |

買値改善は正が安い価格。B-Fのpaired中央値はいずれも0%。約定・価格・returnは
歴史的next observed Open+5bpsのproxyであり、発注や実現利益ではない。
全2,155件にBUY意図を維持しても、取引時間境界や待機後の価格観測不足により
fillは減少する。この106件減をモデルによるNO BUYと混同しない。

## 3つのEvidenceを分ける

1. **値幅の存在**: Selector→High +3%=761件、+5%=408件。
   Oracle Low→strictly later High +3%=1,143件、+5%=666件。
   全日評価不能63件は、Selector→High +1%未満596件と分離。
2. **因果的認識**: 比較window内のtrigger発生はContinuation31、Breakout598、
   Compression/Expansion95、Higher Low478、Lower Wick336、Reclaim237件。
   すべてclosed 1mで認識可能になった時刻を保存。State/Event/Contextを分離。
3. **その時点でのEntry改善**: どの固定候補もImmediateよりCaptureが低い。
   一部の条件付きMAE改善は、同一母数での機会保持・買値改善を証明しない。

## BUY NOWに関して得られた情報

- Continuation Stateは反転Eventなしでも検出できた。しかし比較windowで31件
  （1.44%）しか発生せず、広いDirect Continuationを守る状態表現として不十分。
- 31件のうち元のSelector +3% winnerは29件。ただし、すでに価格が上がった後の
  Signalを含むDevelopment内の条件付き関連であり、残存上昇余地の予測精度や
  BUY NOWの優位性とは言えない。
- C/D/Eは固定10分待機よりCaptureを一部回復した。Eの+3 CaptureはFより
  3.42ポイント高いが、Immediateより14.32ポイント低い。早期Eventには
  timingを動かす観測がある一方、現定義の十分性は示せていない。

## WAITに関して得られた情報

- 今回の6系統・比較候補から、平均買値改善を伴うWAIT判断の有効性は示せなかった。
- EのWAIT中の観測最大上昇は中央値約0.429%。paired買値改善中央値は0%、
  平均は-0.026%。押しを待つ間に上昇を消費する側面が残る。
- 30m MAEのpaired平均差はEで約+0.122ポイントだが、30mの終了時刻も後ろへ
  ずれ、Captureとfillが悪化する。これだけを成功根拠にはしない。

## 情報量が弱い／未確立の候補

- ContinuationとCompression/Expansionは発生数が少ない。とくにContinuationは
  欠測・strict window条件の影響も大きく、「情報がない」と断言する前に
  状態表現と観測可用性を分ける必要がある。
- Lower Wickは336件認識できたが、独立したWAIT優位性は今回確立していない。
- Volume/Trading Valueは全系統に1/3/5/10mの変化・前日同時刻比・欠測maskを
  保存した。増加＝BUYというgateは設けていない。各層の結果は補助診断であり、
  Volume単独の増分予測能力を学習・検証したものではない。
- 観測不足をSignal不発や失敗へ置き換えない。全件のunknown内訳を読む。

## 重複とDirect Continuationの取り逃し

- 比較windowのOpportunity単位JaccardはBreakoutとHigher Lowで約0.522。
  この2つを独立な証拠として二重に数える設計は避けるべき。
- 将来anatomy上のDirect Continuationは354件。+3 CaptureはImmediate74.86%、
  Combination50.28%、固定10分47.74%。Continuationを候補に加えるだけでは
  取り逃しを防げなかった。将来path classは意思決定には使用していない。

## Entry vNextに渡すcausal feature候補

今回は候補の引継ぎだけとし、モデル学習や新しい閾値探索は行わない。

- EventとStateの別列、Eventからの経過active minutes、Signal同士のco-occurrence。
- 1/3/5/10m return、VWAP位置とslope、直近highからの押し幅、higher-high/low構造。
- 確認済みpivotの価格・確認時刻、breakout levelまでの距離、wick/close location。
- 実観測Volume/Trading Value、同長window acceleration、前日同時刻比。
- 各windowの観測数・coverage、staleness、前営業日availability、時間帯・残り時間。
- 使用禁止: oracle Low/High、future MFE/MAE、future path class、Dictionary、
  将来OutcomeによるOpportunity除外。raw symbol IDでの記憶も今回の入力にない。

**次段階の問いは「このSignalが出た銘柄を買うか」ではなく、同じOpportunityで
これらの観測からBUY NOWとWAITの差を予測できるか。今回の結果でその差を
学習できると保証したわけではない。**

## 検証と停止位置

- 新規41テスト、既存Entry関連込み108テストPASS。
- offline regression合計2,949 PASS。初回RSS起動のpytest未導入を解消し、
  RSS89件のみ再実行。プロジェクトソースの変更による救済なし。
- 全Census2回一致、時刻境界修正後の評価2回一致、REPORT/plots2回一致。
- 修正は11:30 endpointを選択後Lowへ含めない評価上の訂正のみ。
  修正前Evidence・理由・manifestを保持。Signal、閾値、WAIT、trade streamは不変。
- Frozen Selector・既存Evidenceは保持。Common Holdout244未開封。
- Dictionary追加、モデル学習、NEW EXIT、Freeze、merge、売買なし。9 safetyはfalse。

[全表・グラフ付きREPORT](report/REPORT-ja.md) /
[機械可読集計](measurement/metrics.json) /
[検証receipt](validation/completion.json) /
[事前固定protocol](PROTOCOL.md)
