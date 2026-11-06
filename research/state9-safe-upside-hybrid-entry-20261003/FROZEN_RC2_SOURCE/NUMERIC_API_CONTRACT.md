# 4. 🔢 RC2の数値契約 — exact判定を採る

## 4.1 変更の種類

RC1の「分類演算precision=50」を、RC2では次の契約へ変更する。
  受理した有限10進入力を正確な数として保持し、State判定に関わる演算・比較をexactに行う。
これは新しい数値契約であり、F2修復copyをそのまま無条件承認したという扱いではない。
外部U/P_refと人工profileの値は変えない。市場のlog変換をこのWorkで実装しない。

RC2の判定経路では巨大絶対座標の丸めを避けるためのrecenterを必須にしない。
絶対normalized座標をexactに扱い、共有origin_ioによる減算→復元を判定/検算の前提から外す。
過去のrecenter案が厳密算術で平行移動として妥当であることと、50桁実装で全域保証できることは別として保存する。

単にDecimalで引算してから比較する、又はcross multiplicationの直前にfloat/丸め値へ変換する実装は不可。
大小比較だけでなく、加減算、極値、帯端、TV、net、進捗時計、protected level、構造/局所pivotまでexactにする。

## 4.2 受理する表現域【この指示書で新しく提案する入力契約】

無制限の文字列・指数展開による資源消費を避けるため、このWorkでは以下を固定する。
これは市場閾値ではなく、資源保護のための明示的なAPI制約。RC1に元からあった制約とは呼ばない。

|項目|RC2固定値/規約|
|---|---|
|transportの各数値token|ASCIIの符号付き有限10進文字列。最大2,048 bytes|
|非ゼロ値のcanonical係数|整数係数の末尾10進ゼロを除去した後、絶対値で最大256桁|
|canonical exponent|x=c×10^eのeが−512以上+512以下|
|ゼロ|canonical (c,e)=(0,0)。−0と+0は同値、時刻を更新する進捗にしない|
|拒否する値|NaN、Infinity、bool、binary float、非数値token、上記域外|
|Python内部API|上記文字列、又は正確なtupleを取得できる有限Decimal/intのlossless adapterのみ|
|派生値|入力制約を再適用して丸めない。必要な桁を正確に保持する|

この範囲は1e50共通原点だけでなく、大きな相対変位と小さな差を含む検査を可能にしつつ、
指数差の展開を有限に制限するために、この新依頼で選んだもの。成績に応じて増減しない。
固定profileはこの域内。事前にmetadataだけから既存fixtureの域内/域外を一覧化する。
既存fixtureが域外でも消さず、旧入力と新API受理域の差を明示し、旧期待値を無断で書き換えない。

数学的な値の意味と、有限資源で受理する表現域を分離する。
全有限Decimalに対する機械実装の完全保証を名乗らない。
この新入力制約そのものに意味上の矛盾が判明した場合、結果に合わせて制約を動かさずBLOCKEDとする。

## 4.3 演算と比率

candidate：整数係数＋10進指数による正確な演算/比較を使用する。
independent engine：別実装のparseを通した既約有理数等による正確な演算を使用する。
同じ数学でもよいが、candidateの状態関数、parse、recenter、serializerを呼ばない。

効率判定はTV≥0を確認して交差積を使える。
・Range Cのη≤0.25：TV>0なら4×|net|≤TV。
・fastのη≥0.8：TV>0なら5×|net|≥4×TV。
・TV=0はη=0。Range側の定義と一致させ、fastはfalse（履歴不足ならnull）。
fastには別途、局所方向に沿った正味変位≥5Uと6連続Closeの条件が必要。
交差積だけで方向条件・変位条件を省略しない。

判定経路はhostのDecimal precision/rounding/Emin/Emax/traps、floatの誤差に依存させない。
表示用近似を付ける場合は別フィールドで任意。正式価格はexact文字列、比率は既約num/denを保存する。
近似表示を省略してもよい。表示用Decimalを使う場合はローカルcontext全設定を記録し、判定へ戻さない。

## 4.4 I/Oの保証

close_uは受理入力Closeとexactに同じ値を再掲する。
pivot/Range端点/保護起点は、指す実観測Close及びその時刻と直接一致させる。
Stop帯や退出水準等の派生価格は、参照する値と固定幅からexactに再計算できるようにする。
時刻、known_at、source、auction、case IDを価格変換対象にしない。

全価格/幅/比率/時刻フィールドをNUMERIC_FIELD_SCHEMAへ列挙し、意味・単位・原点依存性・出典を定義する。
未知の出力価格フィールドを比較器が黙って無視することは禁止。
名前集合だけを双方で共有して漏れを消す設計にせず、照合器自身の独立なschema網羅性確認を持つ。

## 4.5 拒否・原子性・例外【新数値/API契約の一部】

数値の受理チェックは市場状態を更新する前に行う。
域外/非有限/不正tokenはprimary=null、observed=false、数値入力拒否reasonとする。第10Stateは作らない。
正しい予定tで入力拒否した場合、可用性側には失敗した予定時刻とrestart_requiredを記録し、
局所/構造/Stop/Range/clockの市場状態には入力を反映しない。次の受理足で区間resetする。
時刻重複・非整数・逆順呼出しはAPIプロトコル拒否として区別し、市場状態/時刻を上書きしない。

有効入力の処理はsnapshot/stagingで計算し、出力作成まで成功したときだけ市場状態をcommitする。
想定外の算術・出力エラーは握り潰さずNUMERIC_ENGINE_FAULT等として保存し、当該runはFAIL/ERROR。
失敗途中の状態を次の足に継承しない。故障注入でrollbackと再開境界を確認する。
想定された入力拒否の試験PASSと、engine故障を隠したPASSを分ける。


Grammar: ASCII [+-]?(digits(.digits*)?|.digits)([eE][+-]?digits)?; no whitespace. Canonical decimal output c[e]e (trailing coefficient zero removed, zero=0); input constraints never reapplied to derived output. Negative response schema as RC2 Contract. Arithmetic failure raises a dedicated EngineFault exception and preserves market snapshot.
