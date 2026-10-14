# MA4寄り前Selector — 実市場測定完了／品質未承認

2026-10-14 JST。1candidateの実市場学習・較正、7日事前固定候補、寄り→High/Low/Close、同条件基準、正確な旧Frozenの2表、元原本別算式再計数を完了。上昇機会は基準以下、品質合格・実運用可能とは判定しない。

| 寄り→日通しHigh | 新A件数/known率 | 前日売買代金B件数/率 | 同集合ランダム期待N | 旧D事後268銘柄日N/率（条件差） |
| --- | ---: | ---: | ---: | ---: |
| 0..<1% | 68/66.67% | 49/46.67% | 67.7120 | 98/36.57% |
| 1..<2% | 18/17.65% | 27/25.71% | 21.7811 | 33/12.31% |
| 2..<3% | 6/5.88% | 16/15.24% | 7.9385 | 26/9.70% |
| 3..<4% | 7/6.86% | 5/4.76% | 3.2543 | 11/4.10% |
| 4..<5% | 1/0.98% | 3/2.86% | 1.4116 | 24/8.96% |
| >=5% | 2/1.96% | 5/4.76% | 2.3068 | 76/28.36% |
| UNKNOWN | 3 | 0 | 0.5956 | 0 |
| exact0（第一bucket内数） | 28 | 1 | 19.2558 | 51 |

A/B選出105ずつ、known102/105、7日。A UNKNOWN3は当日無約定、結果差し替え0。ランダムは日別Kd*Bd/NdのFraction期待件数で実選出ではない。旧Dは選出前Highを含む事後記述。旧本来350日中events→future Highは別表、known348/UNKNOWN2/負11。

| 下落評価 | A | B |
| --- | ---: | ---: |
| Low≤−1/−2/−3/−5% | 20/7/5/0 | 66/37/17/1 |
| Close≤−1/−2/−3/−5% | 12/5/1/0 | 37/24/11/0 |
| Close負 | 35/102 | 55/105 |
| Low exact0 / Close exact0 | 41/22 | 0/1 |
| 最悪Open→Low | −3.5874439462% | −5.7160608885% |
| 最悪Open→Close | −3.2967032967% | −4.9083566325% |

High≥1% A34/105、B56/105、ランダム36.6924/105。下落tailは少ないが87/105が過去流動性LOW三分位。後半の5分以内価格参照不足が多い。日単位の対応bootstrap固定2,000回、up1 A−B=−20.9524pp、95%記述区間[−44.7619,+2.8571]。7日・既閲覧Development、IID105試行/Fresh/OOS/真の損失0ではない。良い結果までK/列/threshold/期間/モデルを変更・追加fitしていない。

開始HEAD 7ffaa8d452598a6f7ae937fd6e20048cbf7c77ca、計算HEAD c1529e7db10f0d5ecf11f0884d1644d31f5aa9ec。終了文書HEAD/同HEAD CIはPR593最新receiptとprivate最終indexで確認。Open/Draft維持、main/旧Frozen/No1/No1.1/State9/#591/口座/Excel原本不変更。

固定FIT30（2024-10-02〜11-14）/較正10（11-15〜11-28）/Report7（11-29〜12-09）。split e18a181197927bed31b22fb376c42eb35fd0ed42dcabbbb88f7ffcc0b7208325、sealed ledger c89f75b30d19038cdc7de8d4d785ce9ce50af1c633c0ad1c6dc55ab2e1eaf6e1を保持。許可済み9/10〜13はDAILY参照17,553source行のみ、教師追加0、元ledger書換え0。全5年FITへ拡張していない。

103 immutable原本/2,455,811,237bytesを復元照合。必要subset99/2,455,472,420bytes処理完了。178,945,640source入力行はeligible/feature/独立試行数ではない。SQLite normal1,531,418、readonly shared daily180,161、MINUTE+TICK compact395,018raw security-days。各197,509日次OHLC/Vo/Va不一致0。SQL1,608,687,616bytes、quick_check PASS。保護財務196はidentity/timeのみ。全月hash/展開/文字列通過と許可後数値化を分けた。

feature rows FIT112,144/較正37,484/Report26,269、計175,897普通株eligible銘柄日。known教師111,224/37,197、教師UNKNOWN920/287。Report eligible known26,120/UNKNOWN149。登録554、FIT観測464、fit使用463、90全欠測+1定数をFITのみで除外。private列別formula/version/units/source/PIT/欠損/実使用/更新/RSS台帳、public CSV非復元集計。price/出来高代金/需給proxy/下落/企業/市場業種/前日分足Tick/正式Stateを接続。Dictionary/板/本文ニュース/真のaggressorの未接続を接続済みと書かない。

日足MA5/15/25/75、分足MA5/15/30/60、週/月独立MAなし。cacheはcode/policy/schema/input/calendar/basisをbind。原本/正常sourceを再利用し、派生indexとrolling read cacheを追加。以前のState canaryはauctionの型違いでformal観測0、fit前に修正、再生成formal69,250/197,509。元rules/profile不変更・上流fit0、失敗ledger保持。

市場candidate1/base head fits10/calibration fits10。HGB固定lr.05/leaves15/iter120/minleaf40/L2=10/earlystopfalse/seed20261012。10head＋logistic較正→累積min envelope。rank=sum(up)−2sum(down)−closeNegative、EVではない。全class supportを初回fit前検査。modelSHA e82279729b9ccc02fbcf7a1ffced7ade9057d8be41b058963dc4133e4ea19b48、codeSHA3a2fb32dfad9e2ea4f9956038709f2a640a3380213f68ca7af8f1c9c621950ab、schemaSHA79a81013c5903913f531de6d97e402f5f19d7f13b6657e58363483128574f243。

実train06:09:36〜06:39:32UTC、1,796.196秒/RSS4,159,764KiB。feature4,028.053秒/2,537,352KiB、source再開1,645.423秒/355,796KiB、予測273.921秒/656,016KiB、評価303.608秒/841,680KiB。8GiB制約、threads1、float64。file-cacheをprocessRSSへ読み替えない。matrix779,575,504bytes/metadata3,494,751,206bytes。workspace disk差分は別cleanupも含むためstage増分と区別。

train processへReport feature/label descriptorを渡していない。別process trusted reload、7watchlistsを06:50:04.947617UTCに固定→Report label評価。後続Reportの因果的D-1として以前のReport OHLCを参照したので、全Report原本未開封とはしない。公開schedule仮定≠実受信ログ確認。利用根拠は所有者申告・current Work継続でprovider独立確認/実期限認証ではない。

旧active pointerとpayload、親CD40日/1,077,111rowsのFITを照合。7Report全て旧親FIT内。旧K5×10日中と新朝K15の情報差を明記し、旧モデルの朝への戻し/weights変更/原本変更0。主6bucket/累積/LowClose signed/up×down/固定Top1/3/5/15/day tail/市場業種流動性/後半機会を保存。小さいstratum詳細と個別行はprivate。元CSV/JSON＋Decimal整数比・cross multiplicationのA/B/C再計数PASS、同じ実装者の別経路で第三者盲検ではない。

計算HEAD専用CI run38515404839/job115692961244 SUCCESS、32旧+120preopen=152tests、synthetic native E2E/10head10較正、CI市場fit0。終了文書HEADも同じ専用CIで確認しPR/最終private receiptへhead/runを記録。

private original baseline13parts+prefit version7保持。source/State ZIP768,724,188bytes/4partsを保存→再回収、全hash/CRC/安全展開/SQL PASS。学習model ZIP6,500,960bytesを保存。完成feature/model/watch/label/Frozen/coverage/recount/resources92payload ZIP556,065,009bytes、SHA85f546a23e8b6cd38fe7a40f8af65ea3379acc61fff7965733f3f0da856aec3e、3parts。保存3partを再取得→archiveSHA/CRC/全entry/安全展開PASS。復元Report26,269行とtrusted modelから固定105候補の1,050head値を別processで再予測、最大差0。小さい最新ZIPは全payloadではなく再開index。コードZIPと区別。再学習不要、候補budgetは消費済み。

MARKET_MEASUREMENT_COMPLETE=true、LEGACY_COMPARISON_COMPLETE=true、RESEARCH_QUALITY=NOT_APPROVED、LIVE_READINESS=NOT_CERTIFIED。工学PASSは試験/入出力/再現で判断。残りは将来毎朝更新、実機RSS、流動性容量、Entry/EXIT/現金順次回転/実約定の後工程。追加fit/newcandidate自動許可なし。市場job0、バックグラウンド自動継続なし。

execution/broker/Excel/RSS注文/live/paper/promotion/production/transmitted/ready/entry全false。main_merge/force_push/provider_new_acquisition_requests/sourceRepoWrites=0。
