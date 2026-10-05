"""Package completed research without market/EXIT/policy computations."""
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import gzip,hashlib,json,shutil,zipfile
REPO=Path(__file__).resolve().parents[2];ROOT=REPO.parent
OUT=REPO/'docs/evidence/capital-full-r-spectrum-20261006-v1';PRIVATE=ROOT/'capital_r_spectrum_private'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):Path(p).parent.mkdir(parents=True,exist_ok=True);Path(p).write_text(json.dumps(d,sort_keys=True,indent=2,ensure_ascii=False)+'\n')
def main():
    now=datetime.now(ZoneInfo('Asia/Tokyo')).isoformat();binding=read(OUT/'START_AND_SOURCE_BINDING.json');refs=binding['source_refs']
    occupancy=read(OUT/'V5_R_OCCUPANCY.json');curves=[json.loads(s) for s in gzip.open(refs['inputs']['native_curve']['local_path'],'rt') if s.strip()]
    assert occupancy['total']['holding_minutes']==sum(c['concurrent'] for c in curves)
    assert sum(int(n)*minutes for n,minutes in occupancy['total']['position_minutes_at_concurrent'].items())==sum(c['concurrent']**2 for c in curves)
    delivery_audit=read(OUT/'DELIVERY_AUDIT.json');delivery_audit.update(occupancy_global_frame_checks=2,combined_check_N=delivery_audit['check_N']+2,
        occupancy_audit_jst=now,occupancy_audit_method='Sum saved N and N-squared over portfolio frames equals summed actual holding position-minutes and concurrent-position observations; no replay')
    save(OUT/'DELIVERY_AUDIT.json',delivery_audit)
    report=OUT/'REPORT-ja.md';text=report.read_text();marker='未funded候補には実購入quantityがないため'
    addition='保有全期間のconcurrent occupancyも保存curveへjoinした。tradeごとのholding minuteで平均2.3494、BUY debit×拘束時間で重み付けすると2.3237。全R帯の値はV5_R_OCCUPANCY.json/CSVへ保存。position-minuteは保有tradeの観測単位で、portfolio minuteの独立標本ではない。\n\n'
    assert addition not in text;report.write_text(text.replace(marker,addition+marker))
    state=read(OUT/'CURRENT_STATE.json');state['counts'].update(independent_delivery_check_N=delivery_audit['check_N'],independent_occupancy_global_frame_checks=2,
       new_fits=0,new_Capital_candidates=0,new_Capital_replays=0,R_market_EXIT_rematerializations=0,orders=0)
    state.update(exact_jst=now,delivery_status='ARTIFACTS_READY_FOR_FINAL_SAVE',graph_N=6)
    save(OUT/'CURRENT_STATE.json',state)
    final=read(OUT/'checkpoints/FINAL_R_SPECTRUM_COMPLETE.json');final['counts']=state['counts'];save(OUT/'checkpoints/FINAL_R_SPECTRUM_COMPLETE.json',final)
    event={**state,'event':'FINAL_DELIVERY_READY'};save(OUT/'checkpoints/FINAL_DELIVERY_READY.json',event)
    with (OUT/'WORK_STATUS_LOG.jsonl').open('a') as f:f.write(json.dumps(event,ensure_ascii=False)+'\n')
    (PRIVATE/'README.txt').write_text('Frozen original OOF Entry-level R anatomy only. All R/U labels are evaluation-only future outcomes. Never feed them into runtime decisions. Original V5 and saved reset ledgers are reused. No V5.2 policy/replay or fit. Public snapshots/plots are under public/. Original quantities are in source/ and evaluation-only/ENTRY_JOINED_ANATOMY.jsonl.gz. Unknown labels remain null. Added-lot tranches decompose already-filled orders; they are not recovered portfolio profit.\n')
    save(PRIVATE/'INPUT_REFERENCES.json',binding)
    def copy(src,relative):
        dest=PRIVATE/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dest)
    for role in ['native_decisions','native_trades','native_curve','candidate_stream']:
        copy(refs['inputs'][role]['local_path'],f'source/{role}.jsonl.gz')
    copy(ROOT/'capital_v51_private/evaluation-only/R_LABELS.jsonl.gz','source/EXISTING_R_LABELS.jsonl.gz')
    copy(ROOT/'capital_v51_private/evaluation-only/SCORE_SUPPORT_FULL.json','source/EXISTING_R5_R10_SCORE_SUPPORT.json')
    runtime=next(r['local_path'] for r in refs['expert_score_sources'] if Path(r['local_path']).name=='c7e10944822c_CURRENT_MRET_CAP_RUNTIME.jsonl.gz')
    copy(runtime,'source/EXISTING_CAUSAL_SCORES.jsonl.gz')
    for window in read(OUT/'RESET20_R_FLOW.json')['windows']:
        wid=window['window_id'];copy(ROOT/'capital_v51_private/runs/V5_RESET20'/wid/'COMPLETE.json',f'source/V5_RESET20/{wid}/COMPLETE.json')
        if window['R_flow'] is not None:
            for name in ['DECISIONS.jsonl.gz','TRADES.jsonl.gz']:
                copy(ROOT/'capital_v51_private/runs/V5_RESET20'/wid/name,f'source/V5_RESET20/{wid}/{name}')
    for p in OUT.rglob('*'):
        if p.is_file() and p.name not in ['MANIFEST.json','PRIVATE_ARTIFACT_REFERENCE.json','ACTUAL_GET_RECEIPT.json']:
            copy(p,Path('public')/p.relative_to(OUT))
    for p in Path(__file__).resolve().parent.glob('*'):
        if p.is_file():copy(p,Path('research')/p.name)
    entries=[{'path':p.relative_to(PRIVATE).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(PRIVATE.rglob('*')) if p.is_file() and p.name!='PRIVATE_MANIFEST.json']
    save(PRIVATE/'PRIVATE_MANIFEST.json',{'schema':'ARK_R_SPECTRUM_PRIVATE_DELIVERY_V1','exact_jst':now,'files':entries,'status':'R_SPECTRUM_INCONCLUSIVE','fit_replay_order_counts':0})
    dest=ROOT/'exports/Ark_Capital_Full_R_Spectrum_Anatomy_20261006_PRIVATE.zip';dest.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(PRIVATE.rglob('*')):
            if p.is_file():z.write(p,Path('Ark_Capital_Full_R_Spectrum_Anatomy_20261006_PRIVATE')/p.relative_to(PRIVATE))
    ref={'exact_jst':now,'filename':dest.name,'bytes':dest.stat().st_size,'sha256':sha(dest),
         'retention_status':'PENDING_SAVE','scope':'Private exact Entry R/score/decision/trade joins; authenticated original source ledgers; saved reset account ledgers; full public reports/tables/plots/code snapshot; no protected data'}
    save(OUT/'PRIVATE_ARTIFACT_REFERENCE.json',ref)
    with zipfile.ZipFile(dest) as z:
        assert z.testzip() is None
        for p in entries:
            member='Ark_Capital_Full_R_Spectrum_Anatomy_20261006_PRIVATE/'+p['path']
            assert hashlib.sha256(z.read(member)).hexdigest()==p['sha256']
    print(json.dumps({'private_zip':str(dest),'bytes':ref['bytes'],'sha256':ref['sha256'],'files':len(entries)+1,'zip_hash_binding':'PASS'}))
if __name__=='__main__':main()
