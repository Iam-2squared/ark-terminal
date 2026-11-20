# No.1.1 — 週次Yahoo＋平日RSS（日足・発注OFF）

## 運用

- 金曜19:00以降：Yahoo由来の過去日足から、固定4,328銘柄を既存G1（5・15・25・75日）で選別。元の4,328銘柄RSS全走査は、Yahooモードでは実行しない。
- 金曜の後段：Yahooで通過した候補だけを、楽天RSSの実日足 D100 で再確認。Chart50候補選定、前日1分足は従来のRSS。価格取得時刻を捏造しない。
- 月〜木引け後：金曜固定候補集合だけをRSS D100で再確認し、Chart50と前日1分足を更新。新規の候補外銘柄は次の金曜まで追加しない。
- 取引時間中：これまで通り楽天RSSのみ。Frozen Selector、P1、H235、Capital V5、Structural EXITの内容は変更しない。

## Yahoo利用条件

日本版Yahoo!ファイナンスはプログラムによる自動取得を明示的に禁止し、VIP倶楽部では利用者操作による時系列CSVを案内している。

https://support.yahoo-net.jp/SccFinance/s/article/H000011276
https://support.yahoo-net.jp/PccFinance/s/article/H000011281

yfinanceはYahoo非公式の調査・教育用ライブラリ。Yahooの米国利用規約は、原則として事前の明示的許可がない自動収集を禁止している。

https://ranaroussi.github.io/yfinance/
https://legal.yahoo.com/us/en/yahoo/terms/otos/index.html

よって実際に許可が確認できるまでは、4,328銘柄のYahoo一括ネットワーク取得はOFF。RSSを毎朝起動することはYahooのアクセス許可にはならない。Yahooが許可した用途でのみ試す。

## コード入口

- tools/no11_yahoo_weekly_history.py：Yahoo利用許可の明示的確認がある場合のみ、別Python環境のyfinanceを使って金曜時点の過去日足を控えめな小バッチで取得。元のFrozen実行環境へライブラリを追加しない。
- tools/no11_yahoo_weekly_seed.mjs：YahooとRSSを別スキーマに分離。4,328銘柄の元対象集合、データのハッシュ、76営業日、G1判定、UNKNOWN比率を検査。
- windows/Run-No11YahooWeeklySeedReadOnly.ps1：許可条件を満たす既取得データだけで週次候補を生成可能。ネット取得は別途明示されたときのみ。
- windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1：-WeeklySourcePolicy YAHOO_WEEKLY_RSS_DAILY 指定時、金曜の4,328銘柄RSS全走査を実施しない。Yahoo週次が欠けていたら停止し、RSS全数へ自動フォールバックしない。金曜のYahoo候補と月〜木の候補集合はRSSで再計算する。

YahooのCloseはauto_adjust=Falseを要求するが、株式分割などによる履歴調整がないことを保証しない。実証できていない価格基準、企業行動、銘柄属性はEXTERNALLY_REVIEWEDとみなさず、正式Shadow/実売買への昇格を拒否する。

## 例：金曜2026年10月30日（許可と専用環境がある場合のみ）

1. 金曜19:00以降、Yahoo用の独立したPython仮想環境にyfinanceがあり、Yahooの事前許可を確認しているときだけ：

   powershell.exe -NoProfile -File windows/Run-No11YahooWeeklySeedReadOnly.ps1 -AsOfSession 2026-10-30 -FetchYahoo -PersonalResearchTermsAcknowledged -YahooAutomatedAccessPermissionConfirmed

2. Yahooの週次ソースが検証されたら、RSS原本2冊を開いて金曜候補だけ確認：

   powershell.exe -NoProfile -File windows/Prepare-No11WeeklyAfterCloseReadOnly.ps1 -WeeklySourcePolicy YAHOO_WEEKLY_RSS_DAILY

3. 月〜木は2番だけ繰り返し。ソース欠損・多数UNKNOWN・未許可の場合は安全停止し、代替データを自動捏造しない。

この変更はPR #592にある試験段階のコード。PC側には自動反映されない。実注文は常にOFF。
