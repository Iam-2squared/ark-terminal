# 📝 Late-entry Admission — 草案のみ

**PROPOSED_NOT_AUTHORIZED / NOT EXECUTED**

現行precommitはEntryが15:20より前にある候補だけを15:20 openと認める。全1,600 identitiesは保持し、6件の15:20同時刻Entryと16件の15:20後Entryを機械的に除外しない。Frozenではこの22件中20件がFILLED、2件がUNRESOLVED。新overlay上の契約gapを市場で売却不能な22件と呼ばない。

| 論点 | 明示が必要な境界 | 未実行の契約候補 |
|---|---|---|
| 同時刻6件 | minute Openは15:20の最初のtrade。Entry確認とEOD intentの順序をbar labelだけでは証明できない | 確認済みpositionに対するEOD順序を明示。注文前のtradeを売りfillへ逆用しない |
| 15:20後16件 | 15:20にはpositionが存在しない。保有前のSELLを作れない | Capitalの因果的allocation cutoff、または新規position確認後の即時liquidation safety ruleを明示 |
| old unresolved2件 | 上記16件中の2件。既存15:20 intentは適用できない | 同じlate-entry契約を全対象に適用。2件だけ救済しない |
| source18件 | exact post-intent trade/auction、欠損とno-trade区別 | 既に許可済みJ-Quants execution-window source/receiptのみ |

時刻sweep・収益比較・Entryの削除・Frozen fill移動・追加fitは0。どの候補も本Workでは採用しない。現在の15:20 policy、旧15:29 negative、Frozen receiptはimmutable。資料不足からhalt/no-tradeを推測しない。
