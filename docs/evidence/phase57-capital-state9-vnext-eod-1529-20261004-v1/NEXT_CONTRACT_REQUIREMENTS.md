# 📝 次contractに必要な判断 — PROPOSED_NOT_AUTHORIZED

今回の15:29 ruleはSTOP。TSE pre-closingは約定がないため、exact15:29 regular trade Openを追加データで補えば成立する、という問題ではない。

次Workでは「売却完了deadlineをザラバ内に置く」か「注文受付deadlineと後刻auction fillを分ける」かを、新しい明示contractで決める必要がある。前者の例として15:24等が考えられるが、時刻選定・coverage測定・PnL検討を本Workでは行っていない。後者は今回禁止された15:30priceを使うため、別許可・別lineageが必要。いずれも既存sourceからOpen/auction・known-at・cash release・MTMの対応を監査し、実在しないfillやcashを作らない。

無約定/halt/source missing時に何を保証できるか、reference研究とruntime cash-knownの境界、exact mark source/cadenceとunknown equityの扱いを固定する。future-unfillable候補の事後除外・未決済Portfolioのcensoring・補間・fee追加は暗黙採用しない。Frozen v3 originalは継続して保存する。

新deadline/auction/provider/data/partial protocol/known-at assumptionの実験は0。この草案はPROPOSED_NOT_AUTHORIZEDであり、Capital replayや新policy候補を開始する許可ではない。
