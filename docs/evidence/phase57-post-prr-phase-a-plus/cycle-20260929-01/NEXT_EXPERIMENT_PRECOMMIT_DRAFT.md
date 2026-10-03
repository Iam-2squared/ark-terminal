# 🧪 案B 次有限実験Precommit草案 — DRAFT_ONLY_NO_LAUNCH

**研究質問:** 凍結CCMGが初回SELL_INTENTを出した時刻τに、当時観測可能なState／Signal等が `ΔNetPP = Net_CCMG − Net_R50` を区別できるか。ΔJPYは副指標。残上昇幅は評価専用。

**入口と三つのmask:** 全初回intent Iから始める。R50がactiveで先行pendingがなく、時点情報が証明されたEを結果で選ばず定義する。両枝が保存会計できるKは事後の教師可用性mask。I／EのUNKNOWNを結果0にせず、K上の測定を条件付き記述とする。今回のE 370/339は暫定。DEFENSIVE限定 72/86と全Eのどちらを本対象にするか未決定であり、成績を見て選ばない。

**一回限りの行動:** ALLOWは既存CCMG first-sale契約の価格参照と打切り処理へ委ねる。ABSTAINはその後CCMGを再質問せず、凍結R50へ完全委譲する。長期HOLDや次足再試行ではない。同時刻10行のevent order、R50先行／pending、既存R50の内部状態独立性、ALLOW価格なしの扱いを原本で固定するまで枝の同一性は未認証。欠けた参照価格を新policyで救済しない。

**入力候補の固定候補表:** CCMG guard traceのmilestone／floorMargin／confirmation／freshness、既存causal State、六つの既存signal family、Entry時刻とτ時刻、保存Potential順位。正確なversion／definition hash／barEnd／knownAt／欠測区別は現在未確認。StateやEntry buy signalをそのままsell判断に転用しない。新RSI期間、手描きpattern、学習済みStateの追加はこの草案の外。

**因果性検査:** τで入力を切断し、future suffix置換でもτまでの値が不変。unfinished bar、後で確定したswing、当日終値、後日調整、後日fitしたnormalizerを拒否。historical 1m `m+1` はpublication proxyである限界を明記。値がない場合はUNKNOWNを保持する。

**学習・評価設計の条件:** 今回はfamily／thresholdを選ばない。将来のsplitはsession-forward、label成熟とpurge／embargoを示す。Potentialを二段目入力に使うなら、各stage-2 evaluation sessionがstage-1 train／transformer／label依存に混入しないnested証明を要する。今回の24 sessionを再分割しても新しいFreshにはならない。独立した将来評価partitionを使う許可は別途必要。

**比較とGate案:** 同じEntry、quantity、会計、paired maskでR50、凍結PRR route、新候補を比較する。円合計／平均円と平均Net%を別Gate、Winner 5–10と≥10の保持、実介入support、欠測率、正負tail、session／symbol頑健性、コストstress、反復閲覧を明記。統合Capital cash競合・MAX3・後続Entryは別Replay Gateであり今回は未算定。新候補の収益は未測定。

**未決定（数値null）:** 最小support、未知outcome許容度、tail許容度、介入threshold、モデルfamily、fit数、calibration数、stage-1再生成数、policy Replay数、Capital Replay数、採否Gate値。予算式は `B_total=B_stage1_if_required+B_stage2+B_calibration+B_policy_replay+B_capital_replay`、各項はnull。結果を見た閾値救済やfamily選び直しは別のExposureとして扱う。

**開始条件:** ①初回intent全行の欠測機序と教師定義、②Eと枝の同一性／tie、③τのas-of State／Signal行、④nested score系譜、⑤将来の独立検証とGate／予算の事前承認。いずれも現時点で満たしたとはしない。

**status:** `PROPOSED_NOT_AUTHORIZED / DRAFT_ONLY_NO_LAUNCH`。`selectedDevelopment=null`、`adaptiveDevelopmentOnly=true`、`productionReady=false`。
