"""Back up and atomically replace only the RSS-funding integration files.

No git checkout/reset, data scan, Excel attachment, config activation or trading.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import uuid

from patches import ENGINE, TRANSFORMS, ADDITIONS, transform

HERE=Path(__file__).resolve().parent

def digest(data):return hashlib.sha256(data).hexdigest()

def canonical(data):return data.decode('utf-8').replace('\r\n','\n').encode('utf-8')

def safe(path):
    path=Path(path).absolute()
    for p in (path,*path.parents):
        if p.exists() or p.is_symlink():
            s=p.lstat()
            if stat.S_ISLNK(s.st_mode) or getattr(s,'st_file_attributes',0)&1024:
                raise ValueError('NO11_RSS_INSTALL_REPARSE_PATH')
    return path


def plan(root, here=HERE):
    root=safe(root)
    if not root.is_dir():raise ValueError('NO11_RSS_INSTALL_ROOT_MISSING')
    manifest=json.loads((here/'package_manifest.json').read_text(encoding='utf-8'))
    if manifest.get('schemaId')!='ARK_NO11_RSS_FUNDING_PACKAGE_V1':
        raise ValueError('NO11_RSS_INSTALL_MANIFEST')
    for name,sha in manifest['packageFiles'].items():
        if Path(name).name!=name or digest((here/name).read_bytes())!=sha:
            raise ValueError('NO11_RSS_INSTALL_PACKAGE_HASH')
    result=[]
    for name in TRANSFORMS:
        target=safe(root/ENGINE/name)
        old=target.read_bytes()
        expected=manifest['sourceSha256'].get(name)
        if expected and digest(canonical(old))!=expected:
            raise ValueError('NO11_RSS_INSTALL_LOCAL_SOURCE_CHANGED:'+name)
        new=transform(name,old)
        result.append((name,target,old,new))
    for source,name in ADDITIONS.items():
        target=safe(root/ENGINE/name)
        if target.exists():raise ValueError('NO11_RSS_INSTALL_NEW_FILE_EXISTS:'+name)
        if not target.parent.is_dir():raise ValueError('NO11_RSS_INSTALL_TARGET_PARENT')
        result.append((name,target,None,(here/source).read_bytes()))
    if len({str(p) for _,p,_,_ in result})!=len(result):
        raise ValueError('NO11_RSS_INSTALL_DUPLICATE_TARGET')
    return result


def atomic(target, data):
    temp=target.with_name(target.name+'.rss-'+uuid.uuid4().hex+'.tmp')
    try:
        with temp.open('xb') as f:
            f.write(data);f.flush();os.fsync(f.fileno())
        os.replace(temp,target)
    finally:
        if temp.exists():temp.unlink()


def apply(root, backup_parent, *, here=HERE, writer=atomic):
    operations=plan(root,here)
    parent=safe(backup_parent)
    if not parent.is_dir():raise ValueError('NO11_RSS_INSTALL_BACKUP_PARENT_MISSING')
    root=Path(root).absolute()
    if parent==root or root in parent.parents:raise ValueError('NO11_RSS_INSTALL_BACKUP_IN_ENGINE')
    backup=parent/('rss-funding-backup-'+uuid.uuid4().hex)
    backup.mkdir()
    records=[]
    for name,target,old,new in operations:
        if old is not None:
            b=backup/name;b.parent.mkdir(parents=True,exist_ok=True);b.write_bytes(old)
            if b.read_bytes()!=old:raise ValueError('NO11_RSS_INSTALL_BACKUP_HASH')
        records.append({'path':name,'before':None if old is None else digest(old),'after':digest(new)})
    (backup/'transaction.json').write_text(json.dumps({'root':str(root),'files':records},indent=2),encoding='utf-8')
    attempted=[]
    try:
        for name,target,old,new in operations:
            safe(target)
            if (old is None and target.exists()) or (old is not None and target.read_bytes()!=old):
                raise ValueError('NO11_RSS_INSTALL_SOURCE_RACE:'+name)
            attempted.append((name,target,old,new))
            if old is None:
                with target.open('xb') as f:
                    f.write(new);f.flush();os.fsync(f.fileno())
            else:writer(target,new)
        for _,target,_,new in operations:
            if target.read_bytes()!=new:raise ValueError('NO11_RSS_INSTALL_POST_HASH')
    except BaseException as cause:
        failures=[]
        for name,target,old,new in reversed(attempted):
            try:
                current=target.read_bytes() if target.exists() else None
                if current==old:continue
                if current!=new:raise ValueError('CONCURRENT_OR_PARTIAL_WRITE')
                if old is None:target.unlink()
                else:atomic(target,old)
                if (target.read_bytes() if target.exists() else None)!=old:raise ValueError('RESTORE_HASH')
            except BaseException:failures.append(name)
        status='PASS' if not failures else 'INCOMPLETE:'+','.join(failures)
        raise RuntimeError('NO11_RSS_INSTALL_FAILED;ROLLBACK='+status+';BACKUP='+str(backup)) from cause
    receipt={'files':len(operations),'backup':str(backup),'orderSentByInstaller':False,'tradeLaunched':False}
    (backup/'applied.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    return receipt


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',required=True,type=Path)
    p.add_argument('--backup-parent',type=Path)
    p.add_argument('--apply',action='store_true')
    a=p.parse_args()
    if a.apply:
        if a.backup_parent is None:p.error('--backup-parent required with --apply')
        r=apply(a.root,a.backup_parent)
        print('RSS_FUNDING_INSTALL=PASS')
        print('UPDATED_FILES='+str(r['files']))
        print('BACKUP_ROOT='+r['backup'])
    else:
        print('RSS_FUNDING_AUDIT=PASS')
        print('PLANNED_FILES='+str(len(plan(a.root))))
    print('TRADE_LAUNCHED=False')
    print('ORDER_SENT_BY_INSTALLER=False')


if __name__=='__main__':main()
