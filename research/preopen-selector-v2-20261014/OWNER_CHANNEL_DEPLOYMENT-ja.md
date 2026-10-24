# MODE B owner環境の設置手順（未実行）

この文書、PR、生成したJSONは承認ではない。現在MODE A、owner設定は未設置。
承認原文・日付用途・保護解除の範囲・現在の利用根拠をownerが確認してから、
owner管理者が以下を実施する。Codexが自分で承認原文を作成して設置しない。

1. 実行ホストに専用の非rootアカウント `ark-v2-worker` を作る。
   Python3.12と固定lockを用意し、コードは承認したcommit/hashに固定する。
   workerはroot管理コード、設定、承認原文を変更できないようにする。
2. 既存原本の配置先をread-only mountする。再取得・再送は不要。
   `/srv/ark-v2/input`、`/srv/ark-v2/output/<run-id>`、
   `/var/lib/ark-v2/pins/<run-id>`を互いに包含しない別directoryにする。
   outputとjournalはworker所有、journalは0700。親もsymlinkにしない。
   journalをartifact directoryへ同梱・上書き復元しない。永続diskへ配置し、
   再起動後も同じnamespace/pinが残る運用にする。
3. ownerが別経路で確認した承認原文の完全なbytes、原文参照、timezone付き日時、
   approval/precommit/manifest hashを確認する。MODE Bのgrantだけを登録する。
   `OwnerGrant`の正確なfieldは `authority.py` のdataclassに従う。
   `approval_pin`は承認JSON全体、`original_pin`は原文bytes、
   `precommit_pin`は承認対象precommit、`parent_pin`は該当親承認に結合する。
   approval JSON側のtrue、CLI引数、環境変数を根拠にしない。
4. rootが固定path `/etc/ark-selector-v2/owner-channel.json` を設置する。
   schema=`ARK_V2_OS_OWNER_CHANNEL_V1`。必須fieldは
   `schema, worker_uid, source_root, output_root, journal_root, journal_namespace,
   manifest_pin, precommit, grants, test_only, fixture_pins` のみ。
   worker_uidは実UID、test_only=false、fixture_pins={}、grantsはBのみ。
   placeholderやdraftのnullを実行用値に自動補完しない。
   configと全親はroot所有・group/other書込不可、fileはroot:worker-group 0640を推奨。
   `/etc/ark-selector-v2`は0750。rootで市場CLIを実行しない。
5. workerとして、設定だけの検査を行う（原本・教師・モデルは開かない）。

```python
from ark_selector_v2.host_channel import installed_owner_channel
a = installed_owner_channel()
assert a is not None and not a.test_only
assert set(a.grants) == {'B'}
assert 'C' not in a.grants
```

6. owner承認済みrequestの `census` だけを実行する。manifest/precommit/allowlist/
   source-contract/code/config/schema、現在の権利、保護解決を全て一致させる。
   Bはcandidate/fit/cal各0。VALIDATION/FINAL教師descriptorを含めない。
   不一致ならpayloadを開く前に拒否し、scopeを広げて解消しない。
7. 独立journalの永続backupはowner管理とし、outputのsidecarだけから信頼を復元しない。
   START後失敗したrunは再利用せず、原因とaccess receiptを残す。
   MODE CはB結果のPASSとcensus hashを親として別承認するまで設置しない。

検証済み範囲は人工環境のOS所有権・symlink拒否、独立pin再接続、6別process、
偽pickle・偽承認拒否。rootまたはworker UIDが侵害された環境への防御認証ではない。
実ホストのaccount作成、root設定設置、永続disk再起動試験は未実施。
