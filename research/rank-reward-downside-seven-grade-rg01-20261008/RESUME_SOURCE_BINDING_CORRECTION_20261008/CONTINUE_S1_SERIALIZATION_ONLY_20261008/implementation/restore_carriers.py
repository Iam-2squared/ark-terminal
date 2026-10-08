"""Offline exact-byte restore after checking out the research branch."""
import gzip,hashlib,json,pathlib,sys,tarfile,io
def pin(b):return {'bytes':len(b),'sha256':hashlib.sha256(b).hexdigest(),'git_blob':hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()}
def verify(b,p):assert all(pin(b)[k]==p[k] for k in ['bytes','sha256','git_blob'])
def main():
    root=pathlib.Path(sys.argv[1]).resolve()
    for p in root.glob('*.csv.MANIFEST.json'):
        m=json.loads(p.read_text());a=b''.join((root/x['path']).read_bytes() for x in m['parts']);verify(a,m['concatenated_archive_pin']);b=gzip.decompress(a);verify(b,m['CSV_full_pin']);dst=root/m['logical_basename']
        if dst.exists():assert dst.read_bytes()==b
        else:dst.write_bytes(b)
        print(m['logical_basename'],len(b),'PASS')
    manifest=root/'private/PRIVATE_CARRIER_MANIFEST.json'
    if manifest.exists():
        m=json.loads(manifest.read_text());a=b''.join((root/x['path']).read_bytes() for x in m['parts'])
        for x in m['parts']:verify((root/x['path']).read_bytes(),x)
        verify(a,m['archive_pin']);out=root/'RESTORED_PRIVATE_FULL_DETAILS';out.mkdir(exist_ok=True)
        with tarfile.open(fileobj=io.BytesIO(a),mode='r:xz') as t:
            files={x.name:x for x in t.getmembers() if x.isfile()};assert len(files)==m['member_N']
            for x in m['members']:
                b=t.extractfile(files[x['path']]).read();verify(b,x);dst=out/x['path'];assert dst.resolve().is_relative_to(out.resolve());dst.parent.mkdir(parents=True,exist_ok=True)
                if dst.exists():assert dst.read_bytes()==b
                else:dst.write_bytes(b)
        print('PRIVATE_FULL_DETAILS',m['member_N'],'PASS')
if __name__=='__main__':main()
