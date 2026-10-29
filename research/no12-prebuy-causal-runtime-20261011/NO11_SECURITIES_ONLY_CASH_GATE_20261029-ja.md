# No.1.1 実運用資金：楽天証券口座内現金限定ゲート（2026-10-29）

状態：**実装＋オフラインCI試験／実口座LIVE未認証**。既存 Frozen No.1.1、原本 Capital V5、MAX3、100株、現物LONG、個人保有の除外、注文OFFを維持する。元のExcel2冊・補助1冊・旧デスクトップランチャーを変更しない。

## 公式の項目を取り違えない

MarketSpeed II「総合サマリー → 余力・維持率 → 国内株式」の**楽天証券買付可能額**のみを開始時の証券口座内資金とする。「現物買付可能額」は銀行分を含む可能性があるため採用しない。信用余力、NISA枠、楽天銀行利用可能額、マネーブリッジ、自動入出金、入金予定、預り金総額から推定した額は採用しない。

楽天公式：https://marketspeed.jp/ms2/onlinehelp/ohm_004/ohm_004_01.html

## LIVE初期配分のコード契約（発注OFF）

- LIVE設定の `ledger.allocatedCashJpy` は固定金額でなく、**`"AUTO_SECURITIES_ACCOUNT_CASH_ONLY"`** という厳密な指定だけを受け付ける。
- LIVE設定に `securitiesCashEvidenceFile` という**非公開絶対パス**が必須。その JSON は `ARK_NO11_SECURITIES_ONLY_OPENING_CASH_V1` スキーマで、同日、正しい口座区分、`楽天証券買付可能額`、手動レビュー時刻、銀行分除外・自動スイープ無効・信用不使用の明示的確認を要求する。
- 出典画面のファイルをローカルに残し、その SHA256 と JSON が一致することを検査する。**画像の表示内容をコードが自動検証したわけではない**。金額の読み違いを自動的に検知できるとの主張は禁止する。
- 初回台帳作成時、直近15分以内のレビュー証拠だけを使って実際の数値を **BROKER ledger** に初期化する。同じ日の再起動は同一 JSON bytes と出典画像 SHA、台帳の構成・イベント履歴との一致が必須。資金を再度補充した扱いにしない。
- 以降の BUY はこれまでどおり、**台帳残高 − 予約資金**と**独立して観測したRSS買付余力**の小さい方を超えない。資金を含む LIVE 注文は、さらに独立した30秒以内の買付余力更新証拠・操作者の当日許可・当日実データ/EXITゲートが揃わない限り停止する。*口座内現金限定*と*注文が安全に成立する*は別の認証である。

## PCでの非公開証拠作成（まだ注文は送信しない）

1. MarketSpeed II へログインし、総合サマリーの「楽天証券買付可能額」を確認する。楽天銀行分は使わない。マネーブリッジ自動スイープが本当に無効であることを設定画面で確認する。信用は使わない。
2. その表示の**新しいスクリーンショット**をPC内に保存する（GitHub・チャットへ画像、金額をアップロードしない）。画像の作成時刻から15分を超えると停止する。
3. 口座区分を自分で確認して `特定` / `一般` / `NISA（NISA成長投資枠）` / `旧NISA` から指定する。証券口座内の買付可能額を数字だけでローカル入力し、以下のオプションを**実際に確認できたときだけ**使用する。

```powershell
$engine = Join-Path $env:LOCALAPPDATA 'ArkTerminal\No12\physical-account-overlay\source\research\no12-prebuy-causal-runtime-20261011'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $engine 'windows\New-No11SecuritiesCashEvidenceReadOnly.ps1') `
    -ScreenshotFile 'C:\<private>\new-rakuten-summary.png' `
    -SecuritiesAvailableJpy '<confirmed exact amount, digits only>' `
    -Account '<verified account type>' `
    -IReviewedExactSecuritiesAmount -IConfirmedAutoSweepDisabled
```

ローカルに `NO11_SECURITIES_CASH_EVIDENCE_FILE=...` と表示されたパスを将来の LIVE 設定の `securitiesCashEvidenceFile` に渡す。スクリーンショット・現金額・口座情報を GitHub に保存しない。

**注意：** このスクリプトはExcelを開かず、注文もしない。「元のArkのワンクリック起動をLIVE化するスクリプト」ではない。口座画面を人がレビューした証拠を準備するだけ。

## 残るLIVEの条件

- 当日の実G1 / Chart50 / 前日分足 / 独立レビュー済み企業行動 / 価格基準、Frozen P1/H235/Capital/EXIT の実市場一連実行。
- broker observerでの現実の発注ID・注文番号・実約定・手数料・税金・入出金・外部保有の一致。個人手動注文がArk保有と混ざる場合は安全に停止。
- 初回のみ元の正規Capital判断から発注し、実Excel/MarketSpeed IIの注文受付・未約定/部分約定・取消・実保有EXIT・通信断を最低限検証。**当日の本人承認がない限り送信OFF**。不具合を隠して通常運用へ進めない。

### テスト

`test_no11_frozen_p1_securities_cash_only.py` は証拠の厳密な形式、日付、出典ファイルSHA、銀行・信用除外、初回台帳の金額初期化、復帰時の固定証拠一致を検査する。GitHub CIの緑は実口座の出典画像の中身や、実発注/EXITの成功を示すものではない。
