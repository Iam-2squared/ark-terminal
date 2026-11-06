# 🏦 将来のCapital統合 Replay 仕様草案

Status: `PROPOSED_NOT_AUTHORIZED`。今回の新統合Replayは0。

旧funded集合固定のEXIT帰属比較からPortfolio final equityを作らない。次回は全凍結Entry streamを一度だけ時刻順に流し、確定約定時刻でcash/slotを解放する。未解決EXITはcash/slotを維持し、以前rejectされた同一Entryを復活させない。新しい別の凍結Entry eventだけをその時刻で判断する。

Capital v3-B saved score、R37 1/3 equity sizing、100株、¥1,000,000、MAX3同時保有を固定。候補同時刻の順位・EXIT fill→cash→mark→Entry→sizeの順序を維持。R1の旧未解決終端は0円扱いせず旧full equity=nullを保持し、新policyで回避した場合に理由を示す。全24 sessionのEOD連続・end-flat、未解決、mark、絶対/相対PnL、intraday/EOD MaxDD、turnoverを認証する。個人口座保有と研究ledgerは混ぜない。
