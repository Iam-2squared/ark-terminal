# No.1.2 — MSII RssChart 5分足・READ ONLY入力契約 (2026-10-11)

Authority: user-uploaded Rakuten MarketSpeed II RSS function guide 2026/3/30 pages 18, 33, 38. Function **RssChart** accepts a market symbol, period **5M** and count 1–3000. Each row provides 銘柄名称, 市場名称, 足種, 日付, 時刻, 始値, 高値, 安値, 終値, 出来高.

The vendor document does **not** define whether the bar's displayed 時刻 is the open or close time, nor whether Excel cell update instant is an authenticated broker feed-delivery timestamp. The adapter therefore:
- captures local observation time and never claims certified broker market arrival;
- waits an entire additional five-minute interval from the displayed bar label before considering the OHLCV row complete (conservative for either start/end timestamp conventions);
- excludes current unfinished and prior-session rows from same-session candidate pricing;
- checks official column names, 5M period, date/time, OHLCV consistency, duplicate bars and 30-second freshness;
- signs only a local *checksum* of the full accepted OHLCV payload to catch accidental value changes. It is NOT source authentication or native training proof;
- explicitly binds a synthetic pre-BUY candidate to the same-symbol observed row instead of trusting a caller's arbitrary referencePrice.

This is data normalization only. It does not generate the original Frozen No.1.1 Selector, State9, Entry or EXIT, and does not certify No.1.2 profitability or real broker execution. No real RSS function is called; tests use synthetic rows. No LIVE flag can be enabled by this stage.

Important Windows constraint: existing V3 account READ ONLY collector checks exactly one Excel Workbook. **Do not open an additional RssChart workbook in the same Excel instance while the existing 30-second account UI refresh is running.** A separate, deliberate market probe must be isolated so as not to disrupt the existing account capture or alter the private Ownership baseline. Excel order permission stays OFF.
