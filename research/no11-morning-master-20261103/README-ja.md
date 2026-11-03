# No.1.1 当日入力：毎日の証拠提出・価格入力・個別承認を行わない

## 通常経路

**マスター更新は売買プロセスの内部処理。** 毎日ZIPを送る、確認書類を作る、前日終値を手入力する、銘柄ごとに承認する操作を通常運用の前提にしない。旧 `finalize --security-evidence ...` を必須とした案内は撤回。

新しい `automatic_morning.py` が、保存済み引継ぎを読み、選定済み銘柄のJPX情報更新 → 当日RSS価格取得 → 自動整合性判定 → datedMaster → 前日Context → Bootstrapを処理する。

```powershell
& $python -B -X utf8 $automaticRunner --runner $existingMorningRunner --handoff $savedHandoff
```

上記パスはアプリが保持して渡す想定で、毎日のチャット報告は不要。**既存UIへの配線とPC配布は未完了**であり、この追加だけでインストール済みアプリが切り替わったとはしない。

## 維持するもの

今週は先週の429銘柄を母集団として使う。既に選定済みの41銘柄と、その保存済み日足・前日1分足を使用する。4,328銘柄の再スキャン、モデル再学習、取得済み前日足の再取得は行わない。Frozenの計算・重み・閾値・Selector時計・Capital/EXIT、一般口座・100株・通常MAX3、RSS買付可能額は変更しない。銀行確認、シャドウ運用、限定注文も追加しない。

## 自動判定と従来の人手レビューは別物

新経路は `AUTO_SELECTED_JPX_RSS_UNADJUSTED_PRICE_CONSISTENCY_V1`。対象日の公開情報とRSS、市場区分、単位株数、日付、近接権利イベント表示、保存済み日足とRSS前日終値・当日基準値の無調整価格一致を機械的に判定する。未知や不一致を人の確認ボタンで上書きしない。

元runtime向けの互換フラグはこの限定された運用判定通過を意味する。masterへ `inputPolicy` と `admissionFlagsMeaning` を保存し、`humanReviewPerformed=false`、`exhaustiveCorporateActionsCertified=false` を明記する。網羅的な企業行動調査や人手レビューを済ませたと偽らず、`EXTERNALLY_REVIEWED` 証跡を生成しない。詳細は [AUTOMATIC_OPERATION-ja.md](AUTOMATIC_OPERATION-ja.md)。

## アプリ内部の記録

原本・時刻・ハッシュ・異常理由はprivateフォルダーに自動記録する。ユーザーへの提出依頼にしない。取得できない、対象日が違う、価格や銘柄属性が不整合な場合は入力を未完了として返す。別プロセスの既存保有・EXITを止める処理はない。

## 既存ツールの位置付け

`morning_master.py prepare` は前日資料の先行取得用、`scope_morning_master.py` は保存済み資料によるエントリー対象の整理用として保持する。既存 `morning_master.py finalize` は真正な外部レビューを入力する旧方式との互換用で、通常の自動運用では呼ばない。

`Prepare-MorningMaster.ps1` は旧ツール導入用で、新自動入口のインストーラーではない。再実行を要求しない。私有XLS読取ライブラリを含め、モデルの固定Python環境は変更しない。

## 実装と検証の境界

追加コードはPR #598の開発変更。main・ユーザーPC・ランチャー設定・発注許可を変更していない。自動入力判定、入力不整合拒否、元Node入力validatorとの互換性を合成fixtureで検証する。実RSS、非公開モデルによる終日推論、実約定やLIVE一括起動が成功した証明ではない。

次に接続すべきものは既存アプリからこの自動入口を呼ぶ配線と、生成済みBootstrapを既存RSS LIVE設定へ渡す部分。人手の証拠確認工程を追加して埋めない。
