# 🧠 State Definition — 機械契約・合成検証結果

記録日時: **2026-09-21 16:27 JST**
作業開始: 2026-09-21 16:04 JST
開始HEAD: `907f1016cd46dd784b2a7269aa10945e75e12543`
状態: **MECHANICAL_CANDIDATE_LOCKED / SYNTHETIC_PASS / STOP FOR HUMAN REVIEW**

## 結論

Stateの意味だけでなく、Swing・Structure・Range・CHOP・Recovery・cross・Future確認期限・欠測時の扱いを、1つの再現可能な機械定義候補として固定した。参照コードを実際に動かし、合成93テストを通した。

**実際の2,155 Opportunitiesや75,059試作区間を再分類した結果ではない。**
実市場の分類率・UNKNOWN率・認識精度・利益は未測定。正式採用と実市場Ground Truth開始は人間確認が必要。

## 固定した主な内容

|対象|今回のv1候補|
|---|---|
|最新5分の方向|終値対先頭始値の符号。微小上昇を任意bpsでFLATへしない|
|基準S|前日完全5分blockのTrue Range中央値、最低6block|
|Swing|終値1S反転で確認。小さな揺れとの区別に当日固定の前日尺度を使用|
|上昇/下降構造|交互4pivotでHH/HLまたはLH/LL。保護水準を終値で破れば失効|
|レンジ|30連続1m、幅/効率/複数接触。上下境界は成立時点で固定|
|CHOP|最新5本の終値反転と効率・幅。Recovery等と併存可能|
|押し・回復|構造に対する逆行と、特定HIGH→LOW episodeの回復を分離|
|回復完了|episode開始Highを取り戻す。これだけで上昇トレンド復帰とはしない|
|Breakout/Reclaim|前日高値など水準IDを残し、wick・close cross・維持確認を分ける|
|未来確認|同日次10 active minutesの単一案。終端は確認だけ右打切り|

全パラメータと手順は[SPEC-ja.md](SPEC-ja.md)、機械可読値は[contract.json](contract.json)。数値は設計上の1候補であり、市場結果からの最適化ではない。

## 検証の実績

|検証|結果|
|---|---:|
|最終named unit tests|**93 / 93 PASS**|
|最終failures / errors|**0 / 0**|
|二重実行|両回93 PASS、summary/snapshotのSHA・manifest一致|
|保存した模式snapshot|6|
|独立の拒否guard|既存output上書き拒否、source破損拒否の2確認PASS|
|テスト環境|local Python 3.13.5|
|実市場State生成|**0**|
|実市場ファイル読取|**0**|
|学習・Signal・BUY/WAIT・EXIT測定|**0**|
|新規provider取得・保護データ開封|**0**|

Future拒否、availableAt遅延、Tで初回、15:00付近、昼休み、同一足順序、欠測、価格basis、正確な前日/日足lag、上昇内の押し、下落内の反発＋回復、構造破壊、レンジ退出、価格尺度変更、不変suffixを含む。

2つのnamed tests内には固定seedで各25パスのproperty checkを含むが、これを50銘柄や独立市場標本とは数えない。過去Workの19 tests、旧CI、旧State成績は今回の93件に流用しない。

初回に1件、更新済みprotectedLowの期待値を旧101と置いたsynthetic assertionが失敗した。ルール通り新Low102となるためテスト期待値を訂正し、最終ルールで93件を再実行した。市場結果に合わせた閾値変更ではない。codeの空行転記差も最終Git blobとローカルbyteを揃えてから再検証した。

## 残したEvidence

- `reference.py`: 純粋関数の機械定義。市場dataset loader、provider、注文、旧Signal importなし。
- `test_reference.py`: 93合成テスト。市場銘柄への検証ではない。
- `verify.py`: source-lock検証→合成test→6fixture出力。既存output上書き拒否。
- `source-lock.json`: contract/仕様/code/test/verifierのSHA-256固定。
- `verification/summary.json`: 実行件数、test名、source hash、scopeとSafety。
- `verification/synthetic-snapshots.json.gz`: 全6模式pathと状態出力。
- `verification/producer-manifest.json`: 二重実行で一致したuncompressed出力hash。
- `verification/guard-checks.json`: source破損/上書き拒否。
- `verification/STORAGE.md`: 圧縮/非圧縮hashと検証の境界。

GitHub上のsource blobとlocalで実行したbyteの一致を照合する。実研究workflowは起動しない。これはlocal合成PASSであり、GitHub専用CI PASSやPR全GREENではない。

## 重要な留保

1. 前日尺度Sが少標本/ゼロ/価格basis不明ならSwing等は未識別となり得る。Direction等まで全部捨てないが、未知0を保証しない。
2. 終値pivot方式はHigh/Low intrabarの全変化を復元しない。High/Low・wick・順序不明は別に残す。
3. future10分は最適値ではなく事前固定の1候補。10分を超える長い転換は未確認や打切りとして残る。
4. 原データをSession/Barに変換するadapterとInput Admissionは次のG Gateで検証する。receivedAt/knownAtの実市場証跡は今回証明していない。
5. 合成テストは定義と実装の整合確認。定義が実相場の構造を適切に表現できるかは、実データの正解表と代表チャートのレビューが必要。

## 次の1 Gate

**人間がこのv1候補を採用することを確認した後、G: 5分ごとのFuture reference table作成。**

既存Developmentの入力だけを検証し、全Opportunityの同じcheckpointを定義通り処理する。前日1m、D-5..D-1、Today、最新5本を区別し、State(t)と次5分・終日ラベルを混ぜない。
分類割合・観測品質・未識別reason・14:30/15:00以後・代表経路を保存する。結果を見て定義をその場で変えない。Gの後もSTOPし、Causal RecognitionやSignal/BUYへ進まない。

今回のv1候補は**機械ルール固定まで完了**。正式採用・市場正解表生成は未実施。

## Safety

LONG-only / cash-equity-only。Frozen Selector、旧Evidence、既存Entry/EXIT/Capital、mainを変更しない。
executionAllowed=false / brokerWriteAllowed=false / excelOrderWriteAllowed=false / rssOrderFunctionAllowed=false / liveTradingAllowed=false / paperTradingAllowed=false / automaticPromotionAllowed=false / productionUpdateAllowed=false / transmitted=false。
