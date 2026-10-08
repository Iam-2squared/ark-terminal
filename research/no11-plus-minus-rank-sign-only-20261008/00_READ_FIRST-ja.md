# ARK No.1.1 — 新Ranking：Entry→EXITプラス／マイナスのみで学習・評価
**結果：NO_INCREMENT / 新ランキング昇格なし。2026-10-08。**
No.1.1 Freeze原本：`10c94c92c4bd2a59a22744667fd0210252602df4`（変更なし）。

今回の評価には**損益の大きさ、Big Winner、AUC、20日最終資産を用いない**。唯一のラベルは、既存Frozen SHARP_DROP EXITを通った**Entry→EXIT実現RがPLUSかMINUSか**。同じEntryの重複をサンプル水増ししない。

## 母集団
元1039候補 − Entry時PULLBACK/SHARP_DROPの81候補 − 既存ML<1の522候補 = 436候補。うち**既存Frozen EXIT符号が確認できる434候補（PLUS184、MINUS250）**で研究した。UNKNOWN2は別保持。正しいNo.1.1ではその日の最初の合法SELL約定後の新規買付は禁止なので、434件は**個別反実仮想の符号ラベル**であり、434件を実購入したとの主張ではない。

## 時系列ブロック外評価
元の学習ブロック1–3を使い、各追加ブロックを過去だけで再学習しながらBlock4–8をテスト。**279 distinct Entry、PLUS124・MINUS155**。判定閾値は事前固定50%と65%。

| 方法 | 正解/PLUS判定0.50 | PLUS的中率0.50 | 正解/PLUS判定0.65 | PLUS的中率0.65 |
|---|---:|---:|---:|---:|
| 全件PLUS仮定 | 124/279 | 44.4% | 124/279 | 44.4% |
| 既存H2/H3/H5で符号予測 | 3/5 | 60.0% | 0/1 | 0% |
| D-PRICE/D-FULLのマイナス予測 | 9/17 | 52.9% | 4/6 | 66.7% |
| **上昇＋マイナスの新結合** | **12/25** | **48.0%** | **4/7** | **57.1%** |

厳格な65%閾値でもマイナス予測4/6には**実際にマイナス2件**が入り、結合4/7は**実際にマイナス3件**。PLUSの大部分を見落とした。これで「安定したプラスだけ」を選ぶ能力は証明できない。4/6の二項95%正確区間22.3〜95.7%。

別感度分析：No.1.1実Funded64 uniqueのみ（7月Train26、8月Test38）では、上昇＋DownsideのPLUS予測は**3/10＝30%**で、結果がさらに悪い。こちらも実購入のみという強いSelection biasがある。

## 統合版No.1.1凍結
- Entry時 PULLBACK/SHARP_DROPの候補除外を初回・代替枠とも継続
- **その日の最初のSELL約定以降、新規BUY停止**を継続
- FIRST LAYER、Entry、State9、SHARP_DROP EXIT、Capital V5 MAX3/予約/配分、既存R0は一切変更なし
- 実注文・paper/live・本線merge・新Capital資産Replay・新Rank本線接続0

## 出典と検算
Private RG01原本：commit `e384a6c63de62c226ed8a6962b2a61a6addef1c9`。原COMPOSE SHA256 `72d410c68ef403325ecadc6fe6d4a5c0a98e457b4356bc08647353d41c1be36e`、新EXITラベルSHA256 `2d6f17b9cb917bdd8d404a9db7ee1a6d0899b77ab37ed07175c7a56194fcffbb`、State除外81は元の1039 streamから別に検証。PRIVATE branch内Precommitは`d4895c69235ca9dd7603fec41f39ab0790712d0a`でmodel fit前に保存。GitHub Actions run [37753580810](https://github.com/Iam-2squared/ark-capital-private-/actions/runs/37753580810) はSUCCESS。出力artifact [11539171377](https://github.com/Iam-2squared/ark-capital-private-/actions/runs/37753580810/artifacts/11539171377) には全5fold・全モデルの符号成績を保存。

**制限**：すべて以前から露出しているDevelopment。実市場受信時刻UNKNOWNでStrict BUY_INTENTの時点認証なし。検算は同一作者実装／元Frozenソース共有で独立した本番認証ではない。

**判定**：有望な新Rankとして採用する根拠なし。元No.1.1研究版は維持し、新しい未使用期間または適時情報証明を経ないまま従来の結果に合わせて閾値を調整しない。