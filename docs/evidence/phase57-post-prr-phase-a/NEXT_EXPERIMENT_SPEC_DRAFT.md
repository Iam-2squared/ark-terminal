# 次の有限実験仕様 — 草案（未承認・未実行）

問い：CCMG初回SELL_INTENTで売る方が、同一Entryを凍結R50へ任せるより損益を残す条件はあるか。

根拠：A1 SHA-256 `acb3ef902ab0a7411f166709b4e2dfb647ac7f0ca2d6353c19dfe2b35b966dd6`。保存済みoutcomeの差分であり、Portfolio効果ではない。

## 案Bの成立条件

|arm／既存route|Entry|CCMG初回intent|両outcome既知のintent|非ゼロΔ|intentがあるセッション|完全stage-2 snapshot|
|---|---:|---:|---:|---:|---:|---:|
|IM ALL_ROUTES|819|376|296|278|24|0|
|IM DEFENSIVE_ELIGIBLE|276|74|55|51|23|0|
|IM CONTROL_DEFAULT|543|302|241|227|24|0|
|R1 ALL_ROUTES|795|343|263|249|24|0|
|R1 DEFENSIVE_ELIGIBLE|336|87|68|64|20|0|
|R1 CONTROL_DEFAULT|459|256|195|185|24|0|

意思決定はCCMG初回SELL_INTENTで一度だけ。候補行動は保存済みCCMG売却を許可するか、凍結R50を継続するか。変更後の挙動は次のPrecommitとReplayでのみ検証し、今回は走らせない。既存routeを維持する場合のsupportはDEFENSIVE行に限る。全intentへ広げる案は別の候補scopeであり未選択。

R50のMODEL_EXITの`controlNow`だけをmodel intentとし、強制終端925や保存fill時刻とは分離する。同時刻の扱い、未知outcome、約定条件は未確定。現在はguard traceのas-of状態があっても完全なstage-2特徴snapshotはゼロ。

## 案Aとの比較

Entry時点の既知paired教師はIM 728件／R1 706件、非ゼロ差はIM 278件／R1 249件。大量のゼロ、再閲覧済み24-session Development、独立期間の未確認を踏まえ、案Aも学習可能と判定しない。Potential順位は将来上昇幅用で、EXIT差分教師ではない。

## 実験前に固定する項目

- 対象routeの範囲、SELL_INTENTの同時刻と欠損時の扱い。
- arm／route／正負Δ／sessionごとの最小supportと許容する損失tail。
- 時系列分割とStage-2特徴量のcausal knownAt監査。現在のOOFを独立検証へ戻さない。
- 円PnLと平均Net％の両Gate、5–10%・≥10% Winner、<5%、損失集中、session、stressのGate。
- fit・calibration・Replayの有限予算、stop rule。

これらの数値は根拠なく設定しない。新fit 0、新policy Replay 0。次のPrecommitまで実験は開始しない。
