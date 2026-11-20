"""Research-only, trait-level causal dispatch. No trading or model decisions."""
import copy,collections,math
from scripts import phase57_behavior_reader_v2 as reader


def payload(snapshot,decision_time):
    reader.validate_snapshot(snapshot,decision_time)
    decision=reader.timestamp(decision_time);out=[]
    for cell in snapshot['traits']:
        reasons=[]
        for key in ['computedThrough','peerArtifactThrough','normalizationThrough','referenceScaleThrough','identityComputedThrough']:
            if reader.timestamp(cell[key])>=decision:reasons.append('FUTURE_'+key)
        for key in ['availableAt','definitionAvailableAt','identityAvailableAt']:
            if reader.timestamp(cell[key])>decision:reasons.append('NOT_AVAILABLE_'+key)
        temporal=cell['temporalReliability']
        if reader.timestamp(temporal['computedThrough'])>=decision or reader.timestamp(temporal['availableAt'])>decision:reasons.append('TEMPORAL_NOT_AVAILABLE_ASOF')
        if cell['globalStatus']!='USABLE':reasons.append('GLOBAL_NOT_USABLE')
        if cell['sampleConfidence'] not in ['HIGH','MEDIUM']:reasons.append('SAMPLE_'+cell['sampleConfidence'])
        if temporal['status']!='PASS':reasons.append('TEMPORAL_'+temporal['status'])
        if cell['drift'] is True:reasons.append('DRIFT_TRUE')
        if cell['identityStatus']!='DATED_MASTER_CODE_RESEARCH_ONLY':reasons.append('IDENTITY_UNAVAILABLE')
        if cell.get('posterior') is None or not math.isfinite(cell['posterior']):reasons.append('NONFINITE_VALUE')
        uncertainty=cell.get('uncertainty',{}).get('posteriorSD')
        if uncertainty is None or not math.isfinite(uncertainty) or uncertainty<0:reasons.append('UNCERTAINTY_UNAVAILABLE')
        if cell.get('nEff') is None or not math.isfinite(cell['nEff']):reasons.append('NEFF_UNAVAILABLE')
        out.append({'symbol':cell['symbol'],'lane':cell['lane'],'trait_id':cell['trait_id'],
                    'value':cell['posterior'] if not reasons else None,'valueSpace':cell['transform']+' posterior',
                    'availability':'AVAILABLE' if not reasons else 'UNAVAILABLE','reasons':reasons,
                    'sampleConfidence':cell['sampleConfidence'],'temporalReliability':temporal,
                    'uncertainty':cell['uncertainty'],'nEff':cell['nEff'],'computedThrough':cell['computedThrough'],
                    'availableAt':cell['availableAt'],'definitionHash':cell['definitionHash'],
                    'evidenceClass':cell['evidenceClass'],'drift':cell['drift'],
                    'warning':'DRIFT_UNTESTED' if cell['drift'] is None else None})
    return out


def reader_context(day,asof,minute_rows,previous,history,calendar,snapshot):
    decision=day+'T%02d:%02d:00+09:00'%divmod(asof,60)
    cells=payload(snapshot,decision)
    admitted={(x['lane'],x['trait_id']) for x in cells if x['availability']=='AVAILABLE'}
    safe=copy.copy(snapshot);safe['traits']=[x for x in snapshot['traits'] if (x['lane'],x['trait_id']) in admitted]
    context=reader.context(day,asof,minute_rows,previous,history,calendar,safe)
    context['dictionaryFeaturePayload']=cells
    return context


def coverage(profiles,decision):
    families={};groups={};qualified={}
    for profile in profiles:
        cells=payload(profile,decision);groups[profile['symbol']]=set();qualified[profile['symbol']]=set()
        for cell,record in zip(cells,profile['traits']):
            key=record['lane']+'/'+record['trait_id']
            f=families.setdefault(key,{'family':key,'globalStatus':record['globalStatus'],'evaluated':0,'PASS':0,'FAIL':0,'INSUFFICIENT':0,'HIGH_PASS':0,'MEDIUM_PASS':0,'LOW':0,'sampleINSUFFICIENT':0,'available':0,'availableHIGH':0,'availableMEDIUM':0})
            f['evaluated']+=1;f[record['temporalReliability']['status']]+=1
            conf=record['sampleConfidence']
            if conf=='LOW':f['LOW']+=1
            if conf=='INSUFFICIENT':f['sampleINSUFFICIENT']+=1
            if conf in ['HIGH','MEDIUM'] and record['temporalReliability']['status']=='PASS':f[conf+'_PASS']+=1
            if cell['availability']=='AVAILABLE':
                f['available']+=1;f['available'+conf]+=1
                groups[profile['symbol']].add(record['trait_id']);qualified[profile['symbol']].add(key)
    def distribution(values):
        bins={k:0 for k in ['0','1','2','3','4','5+']}
        for traits in values:
            n=len(traits);bins[str(n) if n<5 else '5+']+=1
        return bins
    metrics=['evaluated','PASS','FAIL','INSUFFICIENT','HIGH_PASS','MEDIUM_PASS','LOW','sampleINSUFFICIENT','available','availableHIGH','availableMEDIUM']
    usable=[v for v in families.values() if v['globalStatus']=='USABLE']
    return {'families':list(families.values()),'oldUsableTotals':{m:sum(f[m] for f in usable) for m in metrics},'all32Totals':{m:sum(f[m] for f in families.values()) for m in metrics},'symbols':len(profiles),'symbolBins':distribution(groups.values()),'laneQualifiedSymbolBins':distribution(qualified.values()),'atLeast':{str(k):sum(len(v)>=k for v in groups.values()) for k in [1,2,3]},'countSemantics':'Cell counts use symbol x lane x trait,9 old-USABLE families. Primary symbol trait bins deduplicate identical trait_id across lanes (e.g. Amihud). Lane-qualified bins also retained. Neither requires all traits to pass.','decisionTime':decision}
