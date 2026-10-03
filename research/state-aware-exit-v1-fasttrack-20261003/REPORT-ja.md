# State-aware EXIT v1 FastTrack — 2-arm OOF Evidence

saved_at_jst: 2026-10-03T17:05:35.246196+09:00  
basis_head: `b4b0c0317b9df5ce7faaea05bd46e24d270db91d`  
Document ID: `WORK_STATE_AWARE_EXIT_V1_FASTTRACK_20261003`

**新EXITの2-arm Evidenceを生成してSTOP。どちらのarmも正式採用・Freeze・production promotionしていない。**

Frozen FIRST ENTRY v2 — P1_Q70 / HEAD `4a2d6f35946b16820a13449a9288a6685a5c283c` / 1,600 filled Entries / 58 Development sessionsをREAD ONLYで使用。Entry再fit・Q再選択・Selector変更は0。最新RC2 State9 current、同じRC2 past-only State Path/Transition history、price/volume/Selector contextを使った新モデル1 head ×5 chronological foldsを実際に学習した。Hard1追加fit=0。

継続価値teacherは、今のnext available regular raw openで売る価格に対する、strictly later available regular raw opensと予定closing auction closeの平均価格の差（%）。将来Highを最大化するteacherではない。raw targetを−10..10へclip。これはポジションに依存しない市場contextの継続価値なので、過去train sessionsのselected-watch minute contextsで学習し、Replayは既存Frozen Entry後だけで行った。学習時に新Entryを生成していない。

固定HistGradientBoostingRegressor: depth3 / learning_rate0.05 / max_iter100 / max_leaf_nodes31 / min_samples_leaf20 / L2=0 / early_stopping=false / random_state570926。元Entryと同じ5 chronological session foldsを使用。finite-label training rowsだけでmedian・missing indicator・one-hotをfitし、未知categoryはunknown bucket。OOF223,940 rows。Legacy State feature=0、V6 R2 score/probability/rank=0。

通常EXITはclosed1mの予測継続価値が2回連続で0以下になった最初の時刻でintentを固定。positive、raw minute gap、AM/PM切替でcounterをreset。next available regular raw openでLONG売却し、引けまで残れば予定closing auctionで売る。Entry後だけdecisionし、EXIT後decision=0。

Hard1は同じ予測と通常EXITにstanding stopを追加しただけ。raw line=Frozen Entry fill×0.99。observed eligible regular1mのopen<=lineならopen、そうでなければLow<=lineならlineで約定するOHLC proxy。同時刻の通常market sellは先に執行。mixed opening540/750とterminal auctionsをstop監視に含めない。sell price=raw reference×0.9995、commission0。Entryの+5bpsは既にfillに含まれ、二重計上しない。line touchのnet returnは約−1.0495%、gapではさらに下回る。

canonical LONG sellの符号・cost計算はFrozen HEADの`predict/trading/backtest-cost-model.js`で確認し、今回のresearch costをFrozen Entryと整合する5bps/sideに固定した。generic moduleのdefault presetを使用した成績ではない。closing liquidationは今回の新EXIT contractの予定動作。足内tick順序・約定保証・capacityを仮定した実運用Evidenceではない。

全Entryのうち通常arm sell-filled=1564、unresolved=36。Hard1 arm sell-filled=1571、unresolved=29。Primary paired N=1564。通常armのclosing source未取得で、Hard1だけ先にfilledとなった7件をPrimaryから除外し、single-arm panelに残した。source不足にlast-observed closeを代用していない。

| Primary paired metric | STATE_EXIT | STATE_EXIT_HARD1 |
|---|---:|---:|
| 実現return mean (%) | 0.060180 | 0.000919 |
| 実現return median (%) | -0.099950 | -0.099950 |
| MFE Realization mean (%) | -61.286146 | -61.812751 |
| MFE Realization median (%) | -0.667124 | -4.385870 |
| Held Peak Giveback mean (pp) | 0.727278 | 0.662778 |
| Held Peak Giveback median (pp) | 0.444693 | 0.578509 |
| Full-session opportunity giveback mean (pp) | 2.974833 | 3.034094 |
| Full-session opportunity giveback median (pp) | 1.516805 | 1.560568 |
| holding active minutes mean | 44.461637 | 28.187980 |
| holding active minutes median | 5.000000 | 4.000000 |

同一Entryのpaired Δ（Hard1 − normal）return mean=-0.059261pp、median=0.000000pp。改善191 / 悪化240 / 同値1,133。metric meanの差と、各Entryのpaired Δ medianを混同しない。

MFE Realizationはrealized return / positive observed same-session Entry→High ×100。PrimaryではN=1,397、比率はclipせず、小さいMFE分母の影響を受ける。負の実現returnでは負になる。Held Peak Givebackは売却barより前のclosed source Highで観測した保有中MFEから実現returnを引いたppで、fill-barとstop-barのHighを含めない。未来の売却後Highはfull-session opportunity givebackとして別表示する。gap up sellが保有中observed peakを超える場合はgivebackが負になり得る。全returnはEntry等重みの個別取引値であり、Capital/session/portfolio returnではない。

| Entry-relative observed Winner | denominator / paired | STATE_EXIT return mean / median (%) | HARD1 return mean / median (%) | STATE_EXIT MFE realization mean / median (%) | HARD1 MFE realization mean / median (%) |
|---|---:|---:|---:|---:|---:|
| ≥3% | 466 / 463 | 0.892954 / 0.336295 | 0.613990 / 0.167639 | 15.594581 / 5.743777 | 11.427754 / 2.197626 |
| ≥5% | 253 / 253 | 0.921325 / 0.246925 | 0.597786 / -0.099950 | 10.249657 / 2.233488 | 7.293847 / -0.314909 |

WinnerはSelector MFE bucketではなく、Frozen Entry後strictly-later observed HighをEntry価格で割った分母。source missing下のHighは下限なので、完全なsession pathとは扱わない。≥3% Winnerのfull remaining source completeは14件、≥5%は7件。旧EXITとの比較は0。

| Negative loss containment — paired N=1,564 | STATE_EXIT | STATE_EXIT_HARD1 |
|---|---:|---:|
| negative return N | 880.000000 | 971.000000 |
| net return <−1% N | 243.000000 | 465.000000 |
| net return <−2% N | 85.000000 | 7.000000 |
| worst return (%) | -14.330928 | -2.664173 |
| negative return mean / median (%) | -0.854394 / -0.519700 | -0.714744 / -0.899150 |

Hard1のraw lineはnet −1%上限ではないので、−1%未満Nは増える。−2%未満Nと最悪損失は別に表示した。missing barsがある区間では、未観測のstop touchが無かったとは証明できない。

| Hard1 observed event | N |
|---|---:|
| 発火 total / paired-known | 449 / 442 |
| gap open / intrabar line touch | 118 / 331 |
| 通常armのnegative returnを縮小 | 191 |
| Hard1発火によるpaired return改善 / 悪化 | 191 / 240 |
| stop後strictly-later ≥3% Winnerを切った confirmed | 99 |
| stop後≥3% hitの有無がsource missingでunknown | 340 |
| stop後strictly-later ≥5% Winnerを切った confirmed | 61 |
| stop後≥5% hitの有無がsource missingでunknown | 374 |

損失縮小191件の縮小幅mean=1.258525pp、median=0.717867pp。stop-bar Highの順序不明だけでWinner cutを数えていない。confirmed ≥5は≥3のsubsetであり、99+61を別件数として合算しない。

raw eligible execution pathが両armでcompleteのpaired subsetは651件。return meanはnormal=-0.050757%、Hard1=-0.061820%、paired Δ mean=-0.011063pp。これは早いEXITほどcompleteに残りやすい選別されたsubsetで、1,564件の代替populationではない。

今回の新EXITでは、≥5% Winnerの通常armのholding medianが2 active minutes、MFE Realization medianが2.233488%で、大Winnerの保有継続は明確な弱点として測定された。Hard1は大きいnegative lossを減らす一方、stop後に上昇したWinnerを切り、Primary paired mean returnも低下した。これらは2-arm内部の測定結果であり、旧EXITとの優劣判定や正式arm選定ではない。結果を見たteacher/threshold/model/policy追加は0。

独立別実装audit: PASS / mismatch=0 / checks=2336059 / future causal leakage=0 / audit fit=0。全teacher rows、train/test eligibility、train-only median/one-hot、全OOF予測、1,600件のfirst-exit/next-open/Hard1優先順位とreturn/Winnerを別経路で確認した。歴史的actual known_atはUNKNOWNで、Frozen RC2のbar-end availability仮定を継承する。prospective evidenceではない。

実行予算: new EXIT fits5/5、Hard1 fit0、search0、Entry fit0、old EXIT body read/replay/comparison0、provider0、Protected/Fresh/Validation/OOS/Prospective0、Re-entry0、Capital0、Portfolio Replay0、orders0、main merge0。sellはresearch replayの模擬記録だけで、executionAllowedなど全safety flags=false、productionReady=false。

最終status: `STATE_AWARE_EXIT_V1_TWO_ARM_OOF_EVIDENCE_READY`。STOP。人間確認後の別Workがなければ、arm Freeze・修正実験・Re-entry・Capitalへ進まない。
