"""Lossless closed per-run archives; verify all bytes and all agent-period IDs."""
import hashlib
import json
from pathlib import Path
import shutil
import tarfile


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def verify_archive(path,n=600,periods=120):
    hashes={};manifest=None;commit=None;count=0;members=0
    with tarfile.open(path,'r|xz') as tar:
        for member in tar:
            if not member.isfile():raise ValueError('Archive contains non-file member')
            name=member.name
            if name in hashes or name.startswith('/') or '..' in Path(name).parts:raise ValueError('Bad member')
            stream=tar.extractfile(member);h=hashlib.sha256();content=[];members+=1
            if name=='agent_period.csv':
                line=stream.readline();h.update(line)
                if line.split(b',',2)[:2]!=[b'period',b'id']:raise ValueError('Bad history header')
                for line in stream:
                    h.update(line);prefix=line.split(b',',2)
                    if len(prefix)!=3 or int(prefix[0])!=count//n or int(prefix[1])!=count%n:raise ValueError('Missing/duplicate history row')
                    count+=1
            else:
                for chunk in iter(lambda:stream.read(1024*1024),b''):
                    h.update(chunk)
                    if name in ('manifest.json','completed.json'):content.append(chunk)
            hashes[name]=h.hexdigest()
            if name=='manifest.json':manifest=json.loads(b''.join(content))
            if name=='completed.json':commit=json.loads(b''.join(content))
    if count!=n*(periods+1):raise ValueError('Incomplete agent history')
    if not manifest or not commit or commit['manifest_sha256']!=hashes['manifest.json']:raise ValueError('Manifest commit mismatch')
    expected=manifest['files_sha256']
    if set(hashes)!=set(expected)|{'manifest.json','completed.json'}:raise ValueError('Missing/extra archive member')
    if any(hashes[name]!=value for name,value in expected.items()):raise ValueError('File hash mismatch')
    return {'verified_archive_members':members,'verified_agent_period_rows':count}


def archive_run(target,out,row):
    archives=out/'archives';archives.mkdir(exist_ok=True)
    archive=archives/f"{row['run_id']}.tar.xz"
    if archive.exists():raise FileExistsError(archive)
    partial=archive.with_suffix('.partial')
    with tarfile.open(partial,'w:xz',preset=0) as tar:
        for path in sorted(target.rglob('*')):
            if path.is_file():tar.add(path,arcname=str(path.relative_to(target)),recursive=False)
    audit=verify_archive(partial)
    partial.rename(archive)
    folder=out/'tables'/row['run_id'];folder.mkdir(parents=True)
    names=('system_period.csv','classification_sensitivity.csv','reproduction_windows.csv')
    for name in names:shutil.copyfile(target/name,folder/name)
    return {**audit,'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,
        'tables_sha256':{name:sha(folder/name) for name in names}}


def verify_saved(out,run_id):
    row=json.loads((out/'records'/f'{run_id}.json').read_text())
    if sha(out/'archives'/f'{run_id}.tar.xz')!=row['archive_sha256']:raise ValueError('Archive changed')
    for name,digest in row['tables_sha256'].items():
        if sha(out/'tables'/run_id/name)!=digest:raise ValueError('Table changed')
    return row
