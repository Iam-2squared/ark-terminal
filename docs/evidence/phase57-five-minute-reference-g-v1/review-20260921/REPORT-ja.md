# G Gate — 5分Future State参照表の生成・検証結果

記録日時: **2026-09-21 18:23 JST**。
状態: **生成・再現・保存完了 / 入力制約あり / 人間確認待ち / C以降は未開始**。

## 結論

固定mechanical-v1で全2,155 Opportunitiesの77,214評価行を生成した。ただし、全行のStateが分かったわけではない。価格構造識別は8,809行（11.41%）。Directionや局面は別列として残す。

| 構造 | 行数 | 全77,214行比 |
|---|---:|---:|
| 上昇構造 | 2,358 | 3.05% |
| 下降構造 | 4,856 | 6.29% |
| レンジ構造 | 1,595 | 2.07% |
| 未識別 | 68,405 | 88.59% |

| 排他的な主理由 | 行数 | 全行比 |
|---|---:|---:|
| 現在の確定足がない | 30,986 | 40.13% |
| 前日尺度Sが作れない | 14,816 | 19.19% |
| 現在足・Sはあるが構造不成立 | 22,603 | 29.27% |
| 識別 | 8,809 | 11.41% |

最新5本完全観測28,474行（36.88%）、一部観測34,638行、全5本不在14,102行。
最新5本+Sが揃った22,289行でも、構造識別8,809行=39.52%、未識別13,480行。未識別のうちpivot4個未満11,326行、4個以上で構造不成立2,154行。最新5本が揃うことは過去の連続履歴も十分という意味ではない。
この率は未来なし予測の正解率ではなく、固定定義の識別coverage。未識別原因をすべてデータまたは定義だけへ帰属させない。

## 局面・方向

Direction: UP11,542 / DOWN12,753 / UNCHANGED4,179 / 窓不足48,740。
Phase: RECOVERY4,100 / CORRECTION2,763 / PROGRESSION2,743 / BALANCE1,595 / RESTRUCTURING2,974。Phaseは重複あり、合算して母数にしない。
複数Phase2,554行。StructureまたはPhaseあり12,719行=16.47%。このsemanticAnyはイベント/CHOPだけの行を含む万能なState識別率ではない。
比較可能な連続checkpoint21,821組のPhase集合変更5,415組。集合変更と経済的な方向転換は別。

## 入力present報告の補足

全2,155件の前日raw配列は存在するが、43件は15:30引け1本のみ、通常分足0。前日Sは1,005件で作成可。1,105件は完全5m block6個未満、43件は通常分足なし、1件basis不明、1件Sゼロ。
前日・当日rawの数値とIDを新規providerなしで検証。未観測の原因は無約定/売買停止/取得漏れ等のどれかを断定できず、架空足を作っていない。

## 引け近辺も対象

| 対象 | 全行数 | 最新5本完全 | 構造識別 |
|---|---:|---:|---:|
| 14:30以後の評価時点 | 24,786 | 8,489 | 2,416 |
| 15:00選出179件の評価時点 | 1,074 | 348 | 98 |

未来次10active分は完全観測20,941行、窓内欠測51,963行、引け右打切り4,310行。現在の観測と未来確認不足は別軸で保持。

## 検証・保存

G実行HEAD: 20ebb47323b7c1aca4e4579c7783fc9f48c75792。
専用CI run35581246681: verify/preserve両方SUCCESS。
定義93テスト、adapter22テストPASS。保存local manifestとCI生成manifest一致。
G Evidence保存HEAD: d8240b380fa0201ccca11e909665c9689300bdcb（2026-09-21 18:13:39 JST）。
artifact10630618102のZIP SHA256=cc921c476af1079344975daa78e89fe03ee0dfc20ee62333170199178ade795e。
measurement manifest SHA256=4e11b8eb576dcdd0552f2461c699f57bdabc1db37d8e4c2be9a389a80748d6d1。
このチャットで179ファイルを再hash確認。全77,214CSV行の一意性/集計一致と、独立計算の各時点のObservation/Direction/S/Future窓status一致を確認。構造ラベルを独立アルゴリズムで正解と証明した主張ではない。

入力・状態raw・contexts・全CSV・summary・admissionは ../measurement/。CI receiptとtestsは ../verification/。
可視化補遺は会話添付phase57_g_visual_review_20260921.zip（SHA256 9b3823a78b7767a3278b93dcafea9e83ab01a5cf755e5f2721ed510b17141a7d）。HTML自己完結レポート、6例の実チャートと全checkpoint、CSV、独立入力/coverageレビューを含む。画像本体をGitのmeasurementへ追加したとは言わない。

代表例は各条件を満たすIDの昇順で、重複なし・利益抽出なし。
- 上昇内の押し/回復を含む: 2025-05-30|45920
- 下降構造内の反発/回復: 2025-05-30|330A0
- レンジとCHOP: 2025-06-02|92350
- 最新5本とSがあっても構造未識別: 2025-05-30|24590
- 15:00選出: 2025-05-30|26730
- 前日の通常足なし: 2025-05-30|21960
タイトルは当日の一部時間帯の抽出条件であり、1日固定Pathではない。終値pathは欠測/昼休みで線を切り、High/Lowも保持。chart上の印は売買ではない。

## 留保・工程差分

同じRAW単位の価格basisと既存same-day metadataを継承。当日corporate-action原本再監査、独立取引calendar全体、historical receivedAtの認証は未完了。保存lagの内部一致と外部calendar検証を混同しない。
先のphase57-five-minute-state-reference-v1/PROTOCOL.mdにある暗号化原本からの日足action/calendar復元まで完了したものではない。今回実行されたphase57-five-minute-reference-g-v1は制約を明記したG出力であり、厳しいInput Admissionの全面PASSとはしない。
別workflowにFAILがあり、専用CI成功をPR全GREENと呼ばない。

## 次の1 GateとSTOP

まず人間がこのG結果を確認する。次に検討する問いは「必要観測が足りない未識別と、観測が揃っても固定定義で表せない未識別を分離できるか」。同じG内の診断を検討するが、今回自動開始しない。
mechanical-v1は変更せず一本化を維持。UNKNOWNを減らすための無断閾値変更、新規provider、v0.2への回帰、Causal Recognition/Signal/BUY-WAIT/学習/Dictionary/EXIT/Capital/Portfolioへ進行しない。
Frozen Selector・既存Entry/EXIT/Capital/main不変、main未merge。新規provider0、protected data開封0。出力契約のSafety9全false。
