# No.1.1：2026年P1適用規則とSelector→Watch→初回Entry候補の接続

作業日：2026-10-24。対象：PR #592、research/no12-prebuy-causal-runtime-20261011。
新学習・閾値探索・原本モデル変更・注文送信は行わない。

## 今回追加する適用規則

元のP1は2025年の外側OOF 5組で、2026年の日付への割当は原本に存在しない。2026-10-26以降の年内Shadowに対して、保存済み学習期間の末尾が最も新しいF5を明示指定する。F5の学習末尾は2025-08-06、元の外側テスト末尾は2025-08-25。成績を見て良いfoldを選んだものではなく、全データ再学習でもない。

同じF5のUPSIDE・QUALITY・ADVERSEの3モデル、前処理、訓練予測分布、保存済みQ70閾値を一体で使用する。**Q70をスコア0.7へ置換しない**。元の校正ファイルの数値をそのまま読む。既存の15モデルと2025年OOFの割当を上書きしない。

これは新しい将来日向けのShadow配備規則であり、原本Frozenに元から存在したルール、2026年の成績保証、実注文解禁とは呼ばない。RSS由来の推定Va・変更された候補集合は入力分布の変更として記録する。

## 接続の実装

`tools/no11_p1_forward_shadow.py` を追加。

- `FrozenP1Scorer`：既存 `no11_frozen_p1_score_replay.FrozenP1Fold` を再利用。9個のF5推論アセットを元のpublic receiptに対して検証してから読む。モデルを新たにfitしない。既存runtimeインストールの `ORIGINAL_P1` ディレクトリをそのまま利用できる。
- `ForwardP1Session.register_selector`：元SelectorのTop5/Watchイベントを受け取る。初回選定の時刻・価格は保持し、再選定はrefreshとして追加する。
- `assemble_feature_event`：元の価格110数値特徴量に、既存StateFeatureStreamの38数値・14カテゴリと実source_statusを結合する。計148数値・15カテゴリの順序を維持する。State9をP1の後で新規計算したように扱わない。
- `ForwardP1Session.evaluate`：Q70を最初に満たした時点で `FIRST_ENTRY_CANDIDATE` を一度だけ記録する。条件は元どおり `score >= threshold`。再選定、再送、再起動で初回候補ロックを解除しない。
- 元の `prepare.py:grid` は `closed_raw_start + 1 >= selector_minute`。そのため、Selector時刻と同じ時刻に閉じた1分足も、そのSelectorイベントを先に受領した後なら判定可能とする。前の時刻の足は拒否する。
- SQLiteの同一トランザクションで初回候補・Watchロック・判定ログを保存する。失敗時は巻き戻す。同じ1分足の内容が変わった再送は、新規Entryでなくエラーにする。
- 未来のState9・特徴量、未登録Watch、時間逆行、未知の日付、異なる校正・モデル設定の既存DB再利用を拒否する。元の欠損値表現は維持し、勝手なゼロ補完をしない。

## 実行入口

原本の公開契約と2026年Shadowのモデル指定だけを確認する場合：

    python tools/no11_p1_forward_shadow.py --session 2026-10-26 --policy-only

既存の検証済み推論アセットと、因果的に作成されたSelector/特徴量イベントJSONLを与える場合：

    python tools/no11_p1_forward_shadow.py --session 2026-10-26 --runtime-root <private-verified-root> --private-root <private-output-dir> --events <private-events.jsonl>

イベントJSONLは `{"kind":"selector","payload":<元Selector結果>}` と `{"kind":"p1_features","payload":<P1_CAUSAL_FEATURE_ROW>}` を時系列で渡す。口座や注文には接続しない。標準出力は集計のみ、個別銘柄・スコア・候補はPC内SQLiteに保持する。

## テスト範囲

Pythonの22項目：F5/Q70契約、元の公開原本との結合、初回閾値境界、Selector同時刻の閉じた足、Watch刷新、二重候補防止、再起動、同じ入力再送、異なる再送拒否、二つのDBハンドル、モデル例外の巻き戻し、未来データ拒否など。既存Windows/Linux CIからNodeの新テストで起動する。

ローカル単独環境では合成21項目がPASS、公開原本結合の1項目はリポジトリ原本がないためskip。GitHub CIでは原本結合のskipを許容せずに検査する。合成のライフサイクル確認と、非公開モデルを実際に動かした確認は区別する。今回の単独ローカル試験では非公開モデルの実行は0。

## まだ完成していないこと

この変更は**Selectorイベント＋既に作成されたP1/State9特徴量から初回Entry候補を永続化する接続部**。RSS→完全State9→P1特徴量を自動供給する終日runner、実機でのF5連続推論、H2/H3/H5の2026年配備、Capital/EXIT、実発注・取消・部分約定・残高照合はまだ別工程である。候補が出ても注文を送らない。`productionReady=false`、`orderTransmission=false`、`orderAuthorized=false`を維持する。

元Frozenソース、既存の推論・原本再現ツール、main、別モデルブランチは変更しない。
