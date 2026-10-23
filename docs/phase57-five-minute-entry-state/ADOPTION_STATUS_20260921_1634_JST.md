# State機械定義 — 同時更新の保全・採用状態

記録日時: **2026-09-21 16:34 JST**
本チャットの作業開始: 2026-09-21 16:04 JST
機械定義と合成検証の結果整理: 2026-09-21 16:27 JST
状態: **TWO_DISTINCT_D_CANDIDATES / ADOPTION_UNRESOLVED / STOP_FOR_HUMAN_REVIEW**

## 保存直前に確認した変更

開始時remote HEADは`907f1016cd46dd784b2a7269aa10945e75e12543`だった。
本作業の保存準備commit `ee0387378232d754a80263609f4f208bf145e939`を作った後、branch更新直前の再読でremoteが`686bad3fa0c2283a776d1434f30820c3d1e35fb5`まで5 commits進んでいることを確認した。

同時更新には、既存STATE_DEFINITION_v0.1.mdへのMechanical Parameter Lock v0.2追記、scriptsのhelper/test、CURRENT更新、WORK_LOG追記が含まれる。これらを削除・巻き戻し・上書きしない。

**開始SHAに親を固定した旧準備commitをforce pushしない。** 新remoteを親にして、今回の独立mechanical-v1 packageを追加し、CURRENTの状態を両案が分かるよう調整、WORK_LOGは既存履歴へ追記する。機械定義source/hashは実行済みbyteのまま維持する。

## 同じ案ではない

|項目|今回作成・合成検証したmechanical-v1|保存直前に見つかったv0.2追記案|
|---|---|---|
|尺度S|前日完全5m block True Range中央値、最低6block、当日固定、fallbackなし|前日1m絶対log return中央値×現在価格、Todayへのfallback等|
|Swing|終値の1S反転、同値極値は最初|High/Lowベース3S反転、2tick floor案|
|Range|30連続1m、幅<=2S、効率<=1/3、両端各2block接触|20active分、3交互pivot、効率<=0.35、幅capなし|
|Phase判定|確認済みpivotからの脚＋episode|最新5分Direction＋episode回復率の増加|
|CHOP|反転>=2、効率<=1/3、幅>=0.5S|反転>=2、効率<=0.35、幅>=2S|
|Future確認上限|次10 active minutes|次15 active minutes|
|検証状態|local合成93 PASS、2回manifest一致、2guard確認|取得したCURRENT/WORK_LOGではtests追加・実行前と記録|

v0.2側の未実行は取得時点の記録に基づく。本作業でv0.2側testを実行・再採点していない。93件はmechanical-v1専用で、v0.2の合格証拠に使わない。

異なるSの1倍と3倍を同一単位として大小比較しない。今回の表は仕様の差であって性能比較ではない。

## 採用判断

今回のmechanical-v1は**単独候補として機械ルール固定・合成検証まで完了**。ただし、branch全体で新Stateの定義が一つに最終確定したとは呼ばない。

合成PASS数だけで相場をより正確に表現する案が決まるわけではない。v0.2を無断で廃止したり、両案の都合のよい箇所を混ぜた新しい第3案を作ったりしない。

**次にすることはDefinition Gate内の採用整理のみ。** 人間が、どの定義を正式な正解表の基準とするか確認する。その決定も日時・選択したcontract/hash・不採用案の扱いとともに保存する。
GのFuture正解表は採用された定義が一つになり、人間がG開始を承認してから。Causal Recognition、Signal、Entryへ自動進行しない。

## Evidence・実行境界

mechanical-v1/REPORT-ja.mdは16:27時点の候補実装結果を保存したもの。最新のbranch横断の採用状態・次作業については本記録とdocs/PHASE57_LONG_ONLY_NEXT.mdを優先する。

実市場分類0、新規provider0、Holdout/Fresh/OOS/Prospective開封0、モデルfit0、Signal/BUY-WAIT/EXIT評価0。新しい候補を実行系へ接続していない。
既存Selector・Entry・EXIT・Capital、旧Evidenceと同時更新のscriptsは変更しない。Safety9項目false。新旧同時更新を保持したまま、研究の混線を防いでSTOPする。
