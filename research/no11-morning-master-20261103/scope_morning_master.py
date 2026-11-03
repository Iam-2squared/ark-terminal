#!/usr/bin/env python3
"""Narrow an existing morning handoff from saved public observations only.

No network, Excel, order transmission, model change, new symbol ranking, or
historical recapture. Preserve held/Watch/pending charts even when BUY-ineligible.
Source eligibility is not independent corporate-action/price-basis clearance.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from urllib.parse import parse_qs, urlsplit

RUNNER_BLOB = '4887918a01751f5107b6d6f56c4d838d75107ed2'
POLICY = 'SAVED_SELECTED_LISTING_AND_NEAR_TERM_RIGHTS_EXCLUSION_NO_RERANK_V1'
SHA = re.compile(r'^[a-f0-9]{64}$')
SYMBOL = re.compile(r'^[0-9A-Z]{4}\.T$')


def need(ok, code):
    if not ok:
        raise ValueError('NO11_ENTRY_SCOPE_' + code)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def load_runner(path):
    path = Path(path)
    need(path.is_absolute() and path.is_file(), 'EXISTING_RUNNER_MISSING')
    for q in (path, *path.parents):
        need(not q.is_symlink() and not (getattr(q.lstat(), 'st_file_attributes', 0) & 1024),
             'RUNNER_REPARSE')
    raw = path.read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode('ascii') + b'\0' + raw).hexdigest()
    need(blob == RUNNER_BLOB, 'EXISTING_RUNNER_CHANGED')
    spec = importlib.util.spec_from_file_location('ark_existing_morning_master', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def eligible_scope(handoff, basis):
    selected = handoff.get('selectedSymbols')
    need(type(selected) is list and 1 <= len(selected) <= 47
         and all(type(s) is str and SYMBOL.fullmatch(s) for s in selected)
         and len(selected) == len(set(selected)), 'SELECTED_SYMBOLS')
    need(basis.get('schemaId') == 'ARK_NO11_MORNING_PUBLIC_SOURCE_BASIS_V1'
         and basis.get('sessionDate') == handoff.get('sessionDate')
         and basis.get('previousSession') == handoff.get('previousSession')
         and basis.get('selectedSymbols') == selected
         and basis.get('rightsSourceParsed') is True
         and basis.get('sourceBlockers') == []
         and basis.get('reviewStatus') == 'NOT_REVIEWED'
         and basis.get('corporateActionReviewPerformed') is False
         and basis.get('priceBasisCertified') is False
         and basis.get('datedMasterCreated') is False
         and basis.get('productionReady') is False
         and basis.get('orderTransmission') is False, 'PUBLIC_BASIS_NOT_USABLE')
    rows = basis.get('rows')
    need(type(rows) is list and all(type(r) is dict for r in rows)
         and [r.get('symbol') for r in rows] == selected, 'PUBLIC_ROWS_SCOPE')
    allowed, excluded = [], []
    for row in rows:
        need(type(row.get('eligible')) is bool
             and type(row.get('nearTermRightsEventListed')) is bool
             and type(row.get('listingSourceSha256')) is str
             and SHA.fullmatch(row['listingSourceSha256'])
             and row.get('reviewStatus') == 'NOT_REVIEWED', 'SOURCE_ROW_INCOMPLETE')
        if row['eligible'] and not row['nearTermRightsEventListed']:
            need(row.get('segment') in ('PRIME', 'STANDARD', 'GROWTH')
                 and type(row.get('sector')) is str and 0 < len(row['sector']) <= 100,
                 'ELIGIBLE_METADATA_INCOMPLETE')
            allowed.append(row['symbol'])
        else:
            excluded.append({'symbol': row['symbol'],
                             'listingEligible': row['eligible'],
                             'nearTermRightsEventListed': row['nearTermRightsEventListed'],
                             'sourceReason': row.get('reason', 'UNSPECIFIED')})
    need(bool(allowed), 'NO_ELIGIBLE_ENTRIES')
    return allowed, excluded


def verify_documents(m, handoff, basis):
    root = m.safe(Path(handoff['publicSourceBasis']).parent / 'public-source-documents', directory=True)
    docs = basis.get('documents')
    need(type(docs) is list and 2 <= len(docs) <= 100, 'DOCUMENT_INDEX')
    by_sha, rights = {}, []
    for doc in docs:
        need(type(doc) is dict and type(doc.get('sha256')) is str
             and SHA.fullmatch(doc['sha256']) and type(doc.get('url')) is str,
             'DOCUMENT_METADATA')
        url = urlsplit(doc['url'])
        need(url.scheme == 'https' and url.hostname in ('www.jpx.co.jp', 'www2.jpx.co.jp')
             and url.port in (None, 443) and not url.username and not url.password,
             'DOCUMENT_OFFICIAL_ORIGIN')
        file = m.safe(root / (doc['sha256'] + '.source'), maximum=8_000_000)
        need(digest(file.read_bytes()) == doc['sha256'], 'DOCUMENT_BYTES_CHANGED')
        by_sha.setdefault(doc['sha256'], []).append(url)
        if url.hostname == 'www.jpx.co.jp' and re.fullmatch(
                r'/listing/others/ex-rights/.*/[0-9]{8}\.xls', url.path):
            rights.append(url.path.rsplit('/', 1)[1][:8])
    published = basis.get('rightsPublishedOn')
    need(type(published) is str and published.replace('-', '') in rights,
         'RIGHTS_PUBLICATION_DOCUMENT_MISSING')
    for row in basis['rows']:
        choices = by_sha.get(row['listingSourceSha256'], [])
        need(any(u.hostname == 'www2.jpx.co.jp' and u.path == '/tseHpFront/StockSearch.do'
                 and parse_qs(u.query).get('topSearchStr') == [row['symbol'][:4]]
                 for u in choices), 'LISTING_DOCUMENT_SYMBOL_MISMATCH')
    return root


# Native chart validation is executed against both old and new plans. Import
# only the existing chart validator, without invoking a market/broker service.
NODE = r'''import fs from 'node:fs';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
const [module,chart,maskFile,eligibilityFile]=process.argv.slice(2);
const {validateNo11Chart50Plan}=await import(pathToFileURL(module).href);
const read=p=>JSON.parse(fs.readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const receipt=read(chart),mask=read(maskFile),evidence=read(eligibilityFile);
const old=receipt.chartPlan;
const selected=validateNo11Chart50Plan({chartPlan:old,mask,sessionDate:old.sessionDate});
const eligible=evidence.eligibleSymbols;
const need=(v,c)=>{if(!v)throw Error('NO11_ENTRY_SCOPE_'+c)};
need(evidence.schemaId==='ARK_NO11_AUTOMATIC_MASTER_ELIGIBILITY_V1'&&
 evidence.sessionDate===old.sessionDate&&evidence.parentChartPlanSha256===old.planSha256&&
 evidence.orderTransmission===false,'ELIGIBILITY_CONTRACT');
need(Array.isArray(eligible)&&eligible.length>0&&new Set(eligible).size===eligible.length&&
 eligible.every(s=>selected.includes(s))&&
 JSON.stringify(eligible)===JSON.stringify(selected.filter(s=>eligible.includes(s))),
 'NO_ADDITION_OR_RERANK');
const allowed=new Set(eligible),protectedSet=new Set(old.protectedChartSymbols);
const {planSha256,...body}=structuredClone(old);
body.scanChartSymbols=old.scanChartSymbols.filter(s=>allowed.has(s));
body.allRequestedChartSymbols=old.allRequestedChartSymbols.filter(s=>protectedSet.has(s)||allowed.has(s));
body.selectorInputSymbols=selected.filter(s=>allowed.has(s));
body.arkChartsUsed=body.allRequestedChartSymbols.length;
body.totalChartFunctionsBudgeted=body.arkChartsUsed+body.occupiedByOtherChartFunctions;
body.g1UnscannedCount=mask.observedPassSymbols.length-body.selectorInputSymbols.length;
if(body.entryUniverseMode!==undefined){
 body.reviewedEntrySymbols=body.reviewedEntrySymbols.filter(s=>allowed.has(s));
 body.unreviewedG1SymbolsExcludedFromEntry=mask.observedPassSymbols.length-body.reviewedEntrySymbols.length;
}
body.automaticMasterScope={schemaId:'ARK_NO11_AUTOMATIC_MASTER_SCOPE_V1',
 parentPlanSha256:planSha256,sourceEvidenceSha256:createHash('sha256').update(fs.readFileSync(eligibilityFile)).digest('hex'),
 excludedFromEntry:selected.filter(s=>!allowed.has(s)),aiUsed:false,
 protectedChartsRetained:true,noReranking:true,orderTransmission:false};
const plan={...body,planSha256:createHash('sha256').update(JSON.stringify(body)).digest('hex')};
validateNo11Chart50Plan({chartPlan:plan,mask,sessionDate:old.sessionDate});
need(old.protectedChartSymbols.every(s=>plan.allRequestedChartSymbols.includes(s)),'PROTECTED_CHART_REMOVED');
console.log(JSON.stringify({...structuredClone(receipt),chartPlan:plan,
 automaticMasterScopeApplied:true,parentChartPlanSha256:planSha256,
 automaticMasterEvidenceSha256:body.automaticMasterScope.sourceEvidenceSha256}));
'''


def narrow_chart(m, spec, evidence_file):
    module = m.safe(Path(spec['engineRoot']) / 'runtime/no11_rss_chart_50_prescreen.mjs')
    text = m.run(['node', '--input-type=module', '-', str(module),
                  spec['chartReceipt'], spec['passMask'], str(evidence_file)],
                 'ENTRY_SCOPE_NATIVE_VALIDATION', input_text=NODE)
    obj = json.loads(text)
    raw = text.encode('utf-8')
    root = m.safe(Path(spec['chartReceipt']).parent, directory=True)
    path = root / ('no11-chart50-private-' + digest(raw)[:16] + '.json')
    need(not path.is_symlink(), 'CHART_OUTPUT_REPARSE')
    if path.exists():
        need(path.read_bytes() == raw, 'CHART_OUTPUT_CHANGED')
    else:
        with path.open('xb') as stream:
            stream.write(raw)
    return path, obj, raw


def scope(m, handoff_file, expected_count=None):
    handoff, hb = m.read(handoff_file)
    m.verify_receipt(handoff_file, hb, 'morning-handoff', 64)
    need(handoff.get('schemaId') == 'ARK_NO11_MORNING_MASTER_HANDOFF_V1'
         and handoff.get('orderTransmission') is False
         and handoff.get('productionReady') is False
         and handoff.get('datedMasterCreated') is False, 'HANDOFF_CONTRACT')
    spec = handoff['spec']
    need(set(handoff.get('sourcePins', {})) == {'chartReceipt', 'passMask', 'previousStage'},
         'HANDOFF_SOURCE_PINS')
    objects, bytes_by = {}, {}
    for key, pin in handoff['sourcePins'].items():
        obj, raw = m.read(spec[key])
        need(digest(raw) == pin, 'PINNED_SOURCE_CHANGED')
        objects[key], bytes_by[key] = obj, raw
    selected, prior = m.validate_scope(spec, objects['chartReceipt'], objects['passMask'],
                                       objects['previousStage'])
    need(selected == handoff['selectedSymbols'] and prior == handoff['previousSession'],
         'HANDOFF_SELECTED_SCOPE')
    basis, bb = m.read(handoff['publicSourceBasis'])
    m.verify_receipt(handoff['publicSourceBasis'], bb, 'public-master-basis', 64)
    need(digest(bb) == handoff['publicSourceBasisSha256'], 'PUBLIC_BASIS_CHANGED')
    eligible, excluded = eligible_scope(handoff, basis)
    if expected_count is not None:
        need(len(eligible) == expected_count, 'EXPECTED_ENTRY_COUNT_CHANGED')
    verify_documents(m, handoff, basis)
    root = m.safe(spec['outputRoot'], directory=True)
    need(root == Path(handoff['publicSourceBasis']).parent, 'OUTPUT_MUST_RETAIN_SOURCE_DOCUMENTS')
    # This report declares only the exclusion scope, never reviewed master flags.
    evidence = {'schemaId': 'ARK_NO11_AUTOMATIC_MASTER_ELIGIBILITY_V1',
                'sessionDate': handoff['sessionDate'], 'policy': POLICY,
                'parentChartPlanSha256': objects['chartReceipt']['chartPlan']['planSha256'],
                'publicSourceBasisSha256': digest(bb), 'eligibleSymbols': eligible,
                'excludedFromEntry': excluded, 'reviewStatus': 'NOT_REVIEWED',
                'corporateActionsCertified': False, 'priceBasisCertified': False,
                'productionReady': False, 'orderTransmission': False}
    evidence_file = m.immutable(root, 'entry-eligibility', evidence)
    chart_file, chart, cb = narrow_chart(m, spec, evidence_file)
    need(chart['chartPlan']['selectorInputSymbols'] == eligible, 'NATIVE_SELECTED_SCOPE_DIFFERS')
    # Copy only the selected records. Keep original observed timestamps and bars.
    stage = deepcopy(objects['previousStage'])
    stage['chartPlanSha256'] = chart['chartPlan']['planSha256']
    stage['selectedSymbols'] = eligible
    stage['symbols'] = {s: stage['symbols'][s] for s in eligible}
    stage['omittedSymbols'] = {s: v for s, v in stage.get('omittedSymbols', {}).items() if s in eligible}
    stage['entryScopeParentStageSha256'] = digest(bytes_by['previousStage'])
    stage['entryScopeEligibilitySha256'] = digest(evidence_file.read_bytes())
    stage_file = m.immutable(root, 'previous-archive-stage', stage)
    # Retain all original raw documents while narrowing only their row selection.
    scoped_basis = deepcopy(basis)
    scoped_basis['selectedSymbols'] = eligible
    scoped_basis['rows'] = [r for r in basis['rows'] if r['symbol'] in set(eligible)]
    scoped_basis['parentPublicSourceBasisSha256'] = digest(bb)
    basis_file = m.immutable(root, 'public-master-basis', scoped_basis)
    new = deepcopy(handoff)
    new['selectedSymbols'] = eligible
    new['spec']['chartReceipt'] = str(chart_file)
    new['spec']['previousStage'] = str(stage_file)
    new['sourcePins']['chartReceipt'] = digest(cb)
    new['sourcePins']['previousStage'] = digest(stage_file.read_bytes())
    new['publicSourceBasis'] = str(basis_file)
    new['publicSourceBasisSha256'] = digest(basis_file.read_bytes())
    new['parentMorningHandoffSha256'] = digest(hb)
    new['entryEligibilityFile'] = str(evidence_file)
    new['entryEligibilitySha256'] = digest(evidence_file.read_bytes())
    new['excludedFromEntry'] = [r['symbol'] for r in excluded]
    m.validate_scope(new['spec'], chart, objects['passMask'], stage)
    new_file = m.immutable(root, 'morning-handoff', new)
    # Ensure writes did not overwrite source receipts or original handoff.
    need(Path(handoff_file).read_bytes() == hb, 'PARENT_HANDOFF_MODIFIED')
    for key, raw in bytes_by.items():
        need(Path(spec[key]).read_bytes() == raw, 'PARENT_SOURCE_MODIFIED')
    print('ENTRY_SCOPE=' + str(len(selected)) + '_TO_' + str(len(eligible)))
    print('EXCLUDED_FROM_NEW_BUY=' + ','.join(new['excludedFromEntry']))
    print('PROTECTED_CHARTS_RETAINED=True')
    print('SAVED_PREVIOUS_SCOPE=' + str(len(stage['symbols'])) + '/' + str(len(eligible)))
    print('SCOPED_CHART=' + str(chart_file))
    print('SCOPED_MORNING_HANDOFF=' + str(new_file))
    print('ENTRY_SCOPE_BINDING=PASS')
    print('SOURCE_REVIEW_STATUS=NOT_REVIEWED')
    print('ORIGINAL_RECEIPTS_MODIFIED=False\nHISTORICAL_DATA_RECAPTURED=False')
    print('ENGINE_FILES_MODIFIED=False\nLAUNCHER_REGISTERED=False')
    print('DATED_MASTER_CREATED=False\nTRADE_LAUNCHED=False\nORDER_TRANSMISSION=False')
    return new_file


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--runner', required=True, type=Path)
    p.add_argument('--handoff', required=True, type=Path)
    p.add_argument('--expected-count', type=int)
    a = p.parse_args()
    if a.expected_count is not None:
        need(1 <= a.expected_count <= 47, 'EXPECTED_COUNT_RANGE')
    scope(load_runner(a.runner), a.handoff, a.expected_count)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        message = str(error)
        code = message if re.fullmatch(r'NO11_[A-Z0-9_]+', message) else 'NO11_ENTRY_SCOPE_LOCAL_SOURCE_FAILURE'
        print('ENTRY_SCOPE_BINDING=BLOCKED|' + code, file=sys.stderr)
        print('ORDER_TRANSMISSION=False', file=sys.stderr)
        raise SystemExit(2)
