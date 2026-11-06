# 🔒 Semantic Freezeの限界

Freeze対象は **historical final-bar reconstruction上で、Frozen RC2 Contractの現在意味を一意・再現可能にすること**。正式statusはCandidateであり、production approval、main merge、予測・売買性能合格ではない。

| 項目 | 維持する制限 |
|---|---|
| 実受信履歴 | actual raw_received_at_history / known_atはUNKNOWN。後から履歴を作らない |
| 利用可能時刻 | assumed_available_at=bar_endは研究仮定。live receipt PITの証明ではない |
| feed coverage | certification未完。UNKNOWN gapをNO_TRADE/HALTと置換しない |
| 数値 | Decimal80/120一致はこの有限標本のcanonical一致。無限精度log完全証明・厳密誤差上界ではない。凍結kernelは受理済み有限10進座標をexactに扱う |
| U/M0 | 市場尺度としての最適性/妥当性は未認証。M0契約の遵守と尺度の有用性を分ける |
| 独立性 | candidate/independentは別状態実装・parse/算術。Direct I/Oは独立な照合の部分集合で第3完全classifierではない。同著者の過去露出、共通Contract、Pythonライブラリ等の共通性を消さない |
| reviewer provenance | Blind性はreviewer self-attestation。C016〜C027は元初回canonical欠落をNONBLOCKING limitationとして保持。全初回commitment認証済みではない |
| 標本 | 29case、観測Primary18、null11。21 distinct reviewed security/session、観測分10。重複prefix・同session再利用・State coverage補完は独立標本/Fresh/OOSではない |
| 露出 | 元667除外・旧44・既存25sessionのscan/exposure台帳維持。C028/C029は明示許可された2session再利用。Designerの以前のFULL/prefix露出は保持し、humanが一度も後続価格を見ていないとは主張しない。現在のclassifier input/asOf chartsはprefixのみ |
| 評価範囲 | 9/9は各Primaryの実case存在とContract再現の最小coverage。全市場/全API入力域の意味自然性・矛盾不在・分布代表性の証明ではない |
| 未来/売買 | future predictiveness、Entry/EXIT性能、profit、MFE/MAEは未評価。状態名へ未来継続や売買適格性を付けない |
| UI | scope注記は裁定文書。UI/production表示を実装・検証したとはしない。単独Primary文字列を無条件表示してよいという承認ではない |
| 旧履歴 | RC1 16 FAIL、全synthetic消費、既存市場消費、88-workflow scope incidentを保持。最終Candidateで旧失敗・違反履歴を0にしない |

このWorkの新market sample/provider/draw/scan/State再分類/engine run/old synthetic再テスト/protected・Holdout開封/Future性能/Entry・EXIT・利益/main merge/発注は全て0。既存prefixのread/hash/保存trace比較と裁定レイヤー作成のみ実施した。
