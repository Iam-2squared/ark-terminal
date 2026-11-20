"""Lossless deterministic aggregate partitions below connector payload bounds."""
import csv,io,json,gzip,hashlib
from pathlib import Path
def pin(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def encode(fields,rows):
    f=io.StringIO(newline='');w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader();w.writerows(rows);return f.getvalue().encode()
def project(output,private_destination):
    output=Path(output);private_destination=Path(private_destination);private_destination.mkdir(parents=True,exist_ok=True);receipts=[]
    for name in ['UPSIDE_AND_WINNER_PRESERVATION.csv','LEAVE_ONE_SYMBOL_DIAGNOSTIC.csv']:
        p=output/name;body=p.read_bytes();reader=csv.DictReader(io.StringIO(body.decode()));fields=reader.fieldnames;rr=list(reader)
        archived=private_destination/(name+'.gz');archived.write_bytes(gzip.compress(body,mtime=0))
        folder=output/'DIAGNOSTIC_DETAILS'/p.stem;folder.mkdir(parents=True,exist_ok=True);parts=[];chunk=[];size=len(encode(fields,[]))
        for r in rr:
            rowbytes=len(encode(fields,[r]))-len(encode(fields,[]))
            if chunk and size+rowbytes>480000:
                data=encode(fields,chunk);dest=folder/f'part{len(parts)+1:03d}.csv';dest.write_bytes(data);parts.append({'path':dest.relative_to(output).as_posix(),'rows':len(chunk),**pin(data)});chunk=[];size=len(encode(fields,[]))
            chunk.append(r);size+=rowbytes
        if chunk:
            data=encode(fields,chunk);dest=folder/f'part{len(parts)+1:03d}.csv';dest.write_bytes(data);parts.append({'path':dest.relative_to(output).as_posix(),'rows':len(chunk),**pin(data)})
        rebuilt=bytearray(encode(fields,[]))
        for part in parts:
            b=(output/part['path']).read_bytes();rebuilt.extend(b.split(b'\n',1)[1])
        assert bytes(rebuilt)==body,'PUBLIC_PARTITION_CHANGED_AGGREGATE_BYTES'
        if name.startswith('UPSIDE'):
            overview=[r for r in rr if r['scope']=='ALL'];p.write_bytes(encode(fields,overview));kind='ALL scope overview; all9450 scopes preserved in detail partitions'
        else:
            summary=[]
            for method in ['D-LINEAR','D-PRICE','D-FULL','B0']:
                for target in ['q5','q3','q2','qNEG']:
                    subset=[r for r in rr if r['method']==method and r['target']==target];r={'method':method,'target':target,'all_symbols_excluded_once_N':len(subset),'known_N_min':min(int(x['known_N']) for x in subset),'known_N_max':max(int(x['known_N']) for x in subset),'low_support_exclusions_N':sum(x['LOW_SUPPORT']=='True' for x in subset)}
                    for metric in ['Brier','binary_log_loss','AUROC','AP']:
                        nums=[float(x[metric]) for x in subset if x[metric]!=''];r[metric+'_min']=min(nums) if nums else None;r[metric+'_max']=max(nums) if nums else None
                    summary.append(r)
            p.write_bytes(encode(list(summary[0]),summary));kind='symmetric all-symbol exclusion range overview; every original metric row preserved in detail partitions'
        receipts.append({'original_table':name,'full_aggregate_pin':pin(body),'full_rows':len(rr),'overview_kind':kind,'overview_pin':pin(p.read_bytes()),'parts':parts,'all_rows_and_columns_preserved':True,'counts_masks_rates_changed_N':0,'full_reassembly_exact_bytes':True})
    result={'format':'public overview CSV plus lossless full aggregate partitions','max_part_bytes':480000,'reason':'bounded connector transport/readback payload; not research subset selection','projection_parameters_not_model_or_policy':True,'private_full_aggregate_gzip_retained':True,'tables':receipts}
    (output/'PUBLICATION_PARTITION_MANIFEST.json').write_bytes((json.dumps(result,sort_keys=True,separators=(',',':'))+'\n').encode());return result
if __name__=='__main__':
    import sys
    print(json.dumps(project(sys.argv[1],sys.argv[2])))
