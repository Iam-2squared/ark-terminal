# 🚀 Ark Terminal — Codex引き継ぎ

文書ID: ARK_TERMINAL_CODEX_COMPLETE_HANDOFF_V1_20261006
記録実時計JST: 2026-10-06T13:15:40+09:00
状態: HANDOFF_PREPARED_NOT_NEW_EXPERIMENT
依頼: ユーザーは今後のArk Terminal作業をCodexへ移し、引き継ぎZIPを要求した。

## 🧭 最新確認と現在地

| レーン | branch | 保存前actual GET HEAD | 状態 |
|---|---|---|---|
| 本線 | capital-main-reallocation-20261005 | a295df739a6810dd0081becd04a3380f6136b6ef | Independent Sign V1 CLOSED／SIGN_NOT_SEPARATED_IN_THIS_RUN |
| RAW保存 | data/jquants-raw-cache-20261006-v1 | f5347ecbb44466045eae92650304154d5fc940b2 | 保存CURRENT_STATEはDESIGN_READY_NOT_EXECUTED。別環境の未保存processは未確認 |

独立Sign V1の新fit43・等価再利用5、旧Sign-onlyの32fit、旧RNEGのD1/D2計16fitを実行済みとして保持する。未実行扱いで再走しない。V5をControlとして保持。V5.1、RNEG Defense、旧Sign-only、独立Sign V1の終了判定を変更しない。

## 🎯 次の本線

購入前入力の品質・欠測原因監査を引き継ぐ。G_PRICE62.57%／G_STATE24.90%は特徴量セルの欠測集計であり、RAW取得失敗率とみなさない。分母、適用外、履歴不足、無約定、gap、前日依存、identity／join、field mapping、as-of、未取得を既存原本から分解する。

保存予測を品質群へ結合する場合も記述診断だけ。完全caseの性能が高いことだけで欠測が失敗原因だったと断定しない。初回本線は新fit0・新閾値選定0・Capital接続0・Replay0・第2層学習0・本線provider取得0。原因と次の有限設計草案まで。

## 🔒 固定方針

Selector／FIRST ENTRY v2 P1_Q70／Structural EXIT v3 Local Guard／EOD・費用・約定を完全freeze。State9／Pathと既存Rankも変更しない。Entry／EXITへ責任を戻して再設計しない。

最上位目標は100万円→約200万円／20sessions。ただし今のLayer1はEntry→固定EXIT/EODの費用後PLUS/MINUSだけを教師・学習・比較・閾値・合否に使う。利益額・Rの大きさ・U5/U10・数量・資産を混ぜない。Layer2へ既存Rankを再利用する構想は保持し、今は接続しない。

J-Quants保存は既存指示書の範囲で別branch・別process。本線snapshotを差し替えず、共有API上限を保護する。現在の実契約・利用権・永続保存先とownerを確認してから取得。契約変更・追加課金・解約後利用・RAW公開はしない。公式FAQの利用終了後の扱いは https://jpx-jquants.com/ja/help/usage を再確認。

## 📦 引き継ぐ原本

本人用bundleに主要PRIVATE原ZIP6本（合計216,013,967 bytes）をbytes不変で同梱する。最新Independent Sign、旧RNEG、V5.1 reset、Full R Spectrum、Main Capital/Rank、EXIT v3 freeze/State traceの系列。旧Sign-only32fitの原ZIPは最新Independent内に内包され、二重同梱しない。

各原ZIPのSHA256／CRC、内包ZIPを含む24archiveのCRCを確認。common secret pattern・sensitive filenameの限定scanでは994 text／24 ZIPの該当0。これは全binaryの完全秘密検査や、市場・モデル意味の再監査ではない。故障証跡TRUNCATED gzipは元のforensic原本として保持し、runtime入力へ使わない。

このbundleは全Git履歴・全branch、全市場J-Quants RAW、APIキー、復号鍵、ユーザーPC／Excel workbook／現在口座を含む完全バックアップではない。必要な公開codeはpinからGitHubで取得する。元の古いWork指示は履歴であり再開指示ではない。

## 💾 Codexの運用

最新HEAD・dirty state・owner確認→既存資産再利用→許可範囲をまとめて実施→現在地・方針・実時計JST/UTC・実行量・source/hash・blockerをappend-only保存→actual GET読み戻し。CI待ち中は独立な作業を進める。Claude原則0。日本語の見出し＋絵文字、主要数値は表で報告する。

この引継ぎ作成turnの新fit／市場Replay／provider市場取得／upstream変更／契約変更／RAW削除／発注／main merge／force pushは全て0。Codex taskをこちらから起動したとは扱わない。

ZIPの最終hash・sizeはDELIVERY.jsonへ別途保存する。PRIVATE本体をGitHubへcommitしない。
