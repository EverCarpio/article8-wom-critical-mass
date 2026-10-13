"""Lossless tar.xz blocks; only committed files listed in run manifests."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import tarfile
from concurrent.futures import ProcessPoolExecutor,as_completed


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()


def package(source,out,first,last):
    if not (source/'execution_summary.json').exists():return None
    execution=json.loads((source/'execution_summary.json').read_text())
    if execution['completed_runs']!=400 or execution['failed_runs']:raise ValueError('Experiment is not complete')
    run_ids=[f'r{r:03d}_P{n}' for r in range(first,last+1) for n in range(4)]
    if not all((source/'runs'/name/'completed.json').is_file() for name in run_ids):return None
    name=f'Article_8_Refinado_Trazas_r{first:03d}_{last:03d}_v0.2.0.tar.xz'
    target=out/name;receipt=out/(name+'.receipt.json')
    if receipt.exists():
        record=json.loads(receipt.read_text())
        if sha(target)!=record['sha256']:raise ValueError('Archive changed')
        return record
    items=[];expected={}
    for run_id in run_ids:
        root=source/'runs'/run_id;manifest=json.loads((root/'manifest.json').read_text())
        complete=json.loads((root/'completed.json').read_text())
        if sha(root/'manifest.json')!=complete['manifest_sha256']:raise ValueError('Bad commit')
        for relative,digest in manifest['files_sha256'].items():
            arcname='runs/'+run_id+'/'+relative
            items.append((root/relative,arcname));expected[arcname]=digest
        for extra in ('manifest.json','completed.json'):
            arcname='runs/'+run_id+'/'+extra
            items.append((root/extra,arcname));expected[arcname]=sha(root/extra)
    for relative in ('design.json','planned_runs.csv','pre_execution_record.json','execution_summary.json','run_manifest.csv'):
        items.append((source/relative,relative));expected[relative]=sha(source/relative)
    with tarfile.open(target,'x:xz',preset=0,format=tarfile.PAX_FORMAT) as archive:
        for path,arcname in sorted(items,key=lambda x:x[1]):
            info=tarfile.TarInfo(arcname);info.size=path.stat().st_size;info.mtime=0;info.mode=0o644
            with path.open('rb') as stream:archive.addfile(info,stream)
    # This streaming read checks the compressed artifact against the original
    # run hashes, including every agent-period row; no trace sampling.
    names=set()
    with tarfile.open(target,'r|xz') as archive:
        for member in archive:
            if not member.isfile() or member.name not in expected or member.name in names:raise ValueError('Unexpected archive member')
            h=hashlib.sha256();stream=archive.extractfile(member)
            for b in iter(lambda:stream.read(1024*1024),b''):h.update(b)
            if h.hexdigest()!=expected[member.name]:raise ValueError('Archived content changed: '+member.name)
            names.add(member.name)
    if names!=set(expected):raise ValueError('Missing archive member')
    record={'file':name,'bytes':target.stat().st_size,'sha256':sha(target),'first_replicate':first,
        'last_replicate':last,'runs':len(run_ids),'members':len(names),'full_content_hashes_verified':True}
    receipt.write_text(json.dumps(record,indent=2)+'\n')
    return record


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--workers',type=int,default=2)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=True);records=[]
    if not 1<=a.workers<=4:raise ValueError('workers must be in [1,4]')
    with ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures=[pool.submit(package,a.source,a.out,first,first+9) for first in range(1,101,10)]
        for future in as_completed(futures):
            record=future.result()
            if not record:raise ValueError('Incomplete block')
            records.append(record);print(json.dumps(record),flush=True)
    records.sort(key=lambda r:r['first_replicate'])
    if len(records)==10:(a.out/'trace_archives.json').write_text(json.dumps(records,indent=2)+'\n')
