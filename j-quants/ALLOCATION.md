J-Quants RAW 保存状況 — 2026-10-06T17:11:04+0900

固定listingのnative原本496個と、現契約で取得できたAPI原本1,222個を保存済み。計1,718個、24,103,114,219 bytes。未保存0 bytes。各原本は保存先から全体を読み戻してSHA256一致を確認済み。

|保存先|dataset|対象／保存済object|予定bytes|保存済bytes|未保存bytes|最大単一object bytes|通常Git／Private Release asset|
|---|---|---:|---:|---:|---:|---:|---:|
|[A](https://github.com/Iam-2squared/J-quants-A)|TICK|14／14|10387317454|10387317454|0|933947205|0／14|
|[B](https://github.com/Iam-2squared/J-quants-B)|TICK|13／13|9646782612|9646782612|0|1156873162|3／10|
|[C](https://github.com/Iam-2squared/J-Quants-C)|MINUTE|13／13|1136175906|1136175906|0|100144026|13／0|
|[D](https://github.com/Iam-2squared/J-quants-D)|MINUTE|14／14|1076069715|1076069715|0|110807696|11／3|
|[E](https://github.com/Iam-2squared/J-quants-E)|LIGHT_BASE_AND_API_ORIGINALS|1664／1664|1856768532|1856768532|0|2551500|1664／0|
|合計|固定取得対象|1718／1718|24103114219|24103114219|0|1156873162|1691／27|

native listingの固定時刻：2026-10-06 15:41:16 JST。Tick A/Bの圧縮bytes比は51.8481859%／48.1518141%、1分足 C/Dは51.3584882%／48.6415118%。境界・object・保存先の移動なし。

通常Gitの上限に抵触した27個・20,219,344,757 bytesは、元のgzipを変更せず、同じPrivate repoのDraft Releaseへ1原本＝1assetで保存済み。GitのBLOCKED_GITHUB_STORAGE_LIMIT記録は保持。現在の保存blockerは0件。最大assetは1,156,873,162 bytesで、GitHub公式の2GiB未満の条件内。

Privateの各repoはmainから保存状況を参照可能。Git保存分はraw/、Release保存分は各repoのReleasesとcontrol/provider/INTACT_RELEASE_RAW_STATE.json、全native原本の保存位置・SHA256はcontrol/provider/ALL_NATIVE_STORAGE_STATE.json。EのAPI原本はraw/api-originals/。

API照会1,230件の判定：原本保存1,222件、契約対象外403が5件、現在のAPI提供期間外400が3日（2021-10-01・04・05）。対象外を完全保存数に算入していない。完全原本cache147件を再取得せず再利用。

public ark-terminalへのRAW保存0。ここにはmanifest・hash・coverage・保存位置・取得状態・方針・実時計のみ保存。本線のSelector／Entry／EXIT・研究snapshot変更、新データ自動投入、契約変更、追加ストレージ契約、モデル学習、Capital Replayは0。本線run37408601154は別途16:11:53 JSTにcancelledを確認。J-Quants Workによる本線停止操作は0。

現状：全固定対象の保存・検証完了。次方針：自動取得・本線自動投入を追加せず、現契約の本人利用・保存条件に従って原本と取得証跡を保持。
