# 🧭 BUY_INTENT購入前監査（新Sign研究の準備）

新fit・新閾値選択・Capital Replayは未実行。通過PLUS率80%は未検証。

- `prebuy_projection.project(entry, trace)`：凍結State9/Pathの確定prefixをfirst_intent.intent_minuteまで切り出す。Fillの価格・時刻・遅延へ依存しない。構造距離とstrict prior local LHLを記述し、上流意味論を変更しない。欠けたschemaはnull/reason。これはproducer時点監査を代替しない。
- `missingness_reasons.explain_missingness(...)`：凍結P0のwindow/coverage/分母条件を監査する。新しい価格特徴量を計算せず、予定足gapを取得失敗と決めつけない。正当nullと実際の保存nullとの対応は別。
- `snapshot_audit.py`：保存済み旧入力3種をhash検証し、数値セルとEntryの欠測率、日付/銘柄coverage、旧group receiptと新intent境界の差を集計する。教師や損益は読まない。旧snapshotを新モデルへ自動採用しない。

原本の3ファイルは非公開ディレクトリに置く。結果ファイルは既存を上書きせず、未配置時はexit2とBLOCKEDを返す。公開GitHubにはRAW・行別入力/予測・モデルをcommitしない。

```bash
python research/sign-prebuy-quality-precision80-20261006-v2/snapshot_audit.py \
  --private-root /workspace/private/independent_sign_private \
  --expected-manifest docs/evidence/independent-entry-exit-sign-20261006-v1/SIGN_DATASET_MANIFEST.json \
  --registry docs/evidence/independent-entry-exit-sign-20261006-v1/FEATURE_REGISTRY.json \
  --output /workspace/private/audit-result.json
```

これだけではRAW原因配賦・State原prefix再extract・新P1全matrix接続・学習scoreのproducer監査は完了しない。`RESEARCH_DESIGN_DRAFT.json` は入力監査後に固定する有限案。現段階では未凍結・未実行。

合成検算：

```bash
python -m unittest discover -s research/sign-prebuy-quality-precision80-20261006-v2 -p 'test_*.py' -v
```
