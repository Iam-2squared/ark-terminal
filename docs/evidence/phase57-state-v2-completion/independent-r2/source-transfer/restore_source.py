"""Verify and restore the append-only completion source archive. Offline, no writes to Git."""
import argparse,base64,gzip,hashlib,json
from pathlib import Path, PurePosixPath

def restore(folder:Path, output:Path):
 m=json.loads((folder/'manifest.json').read_text());parts=[]
 for p in m['parts']:
  b=(folder/p['file']).read_bytes();fix=m.get('transportCorrections',{}).get(p['file'])
  if fix:
   git=hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
   assert git==fix['storedGitBlobSHA1'] and len(b)==fix['storedByteN'],'STORED_TRANSPORT_PIN'
   text=b.decode('ascii');assert text.count(fix['old'])==fix['count'],'TRANSPORT_OPERATION_COUNT'
   b=text.replace(fix['old'],fix['new'],fix['count']).encode('ascii')
  assert len(b)==p['bytes'] and hashlib.sha256(b).hexdigest()==p['sha256'],'ORIGINAL_PART_PIN'
  parts.append(b)
 archive=base64.b64decode(b''.join(parts),validate=True)
 assert hashlib.sha256(archive).hexdigest()==m['archiveSHA256'],'ARCHIVE_PIN'
 data=gzip.decompress(archive)
 assert hashlib.sha256(data).hexdigest()==m['uncompressedSHA256'],'SOURCE_ARCHIVE_PIN'
 files=json.loads(data);assert set(files)==set(m['fileSHA256']),'SOURCE_FILE_SET'
 for name,text in files.items():
  path=PurePosixPath(name);assert not path.is_absolute() and '..' not in path.parts,'UNSAFE_SOURCE_PATH'
  b=text.encode('utf-8');assert hashlib.sha256(b).hexdigest()==m['fileSHA256'][name],name
  dest=output/name;dest.parent.mkdir(parents=True,exist_ok=True)
  if dest.exists():assert dest.read_bytes()==b,'NO_OVERWRITE_OF_DIFFERENT_SOURCE'
  else:dest.write_bytes(b)
 print(f'Verified and restored {len(files)} source files. No Acceptance claim.')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--output',required=True,type=Path);a=p.parse_args();restore(Path(__file__).parent,a.output)
