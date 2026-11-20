# 🚀 Exceptional Extension 設計草案

Status: `PROPOSED_NOT_AUTHORIZED`。本cycleで延長policy実データ評価 0。

最初の有効な +3% closed Target 判断時刻で、旧R50判断が先行・pendingでなければ一度だけ gate を問う。FALSE/UNKNOWN は同じ固定Target売却へ進む。TRUE なら最小の continuation comparator は `DEFER_TO_FROZEN_R50` とし、同じ日のR50 ceiling と正確な終端を守る。Target後にもう一度gateを問わず、部分利確や再購入はしない。

延長の採否は `Net_R50Continuation − Net_TargetSale` の同一Entry/quantity・両枝既知集合で検討する。R50がTarget時点より前に判断する行は比較対象外。今回のState/6 Signal値はtarget時点joinできず、量・VWAP入力も部分的である。TRUE条件、構造崩れEXIT、floor/giveback、queue/retry、support/Gate/Replay予算は未固定のまま。最終Highを売却価格にしない。

CCMG pretarget は初期familyでOFF。追加するなら固定Targetとcontinuationを同条件にしたOFF/ON ablationを別の有限実験にする。未来Winner bandで当時のroutingを選ばない。
