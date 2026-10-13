"""Pack immutable verified run archives into portable blocks of three replicates."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import shutil
import tarfile
import time
from archive_runs import sha


def pack_block(source,out,lo):
    hi=min(100,lo+2);rows=[]
    for rep in range(lo,hi+1):
        files=sorted((source/'records').glob(f'r{rep:03d}_*.json'))
        if len(files)!=18:return None
        rows.extend(json.loads(p.read_text()) for p in files)
    name=f'Article_8_Energia_WOM_Trazas_r{lo:03d}_{hi:03d}_v0.3.0.tar';out.mkdir(parents=True,exist_ok=True)
    target=out/name;receipt=out/(name+'.json')
    if receipt.exists():
        old=json.loads(receipt.read_text())
        if not target.exists() or sha(target)!=old['sha256']:raise ValueError('Existing archive changed')
        return old
    paths={}
    for row in rows:
        run=row['run_id'];path=source/'archives'/f'{run}.tar.xz'
        if sha(path)!=row['archive_sha256']:raise ValueError('Run archive changed')
        paths[f'archives/{run}.tar.xz']=path
        paths[f'records/{run}.json']=source/'records'/f'{run}.json'
    for name0 in ('design.json','pre_execution_record.json','planned_runs.csv'):paths[name0]=source/name0
    expected={name0:sha(path) for name0,path in paths.items()}
    manifest={'replicate_first':lo,'replicate_last':hi,'runs':len(rows),'files_sha256':expected}
    data=json.dumps(manifest,sort_keys=True,indent=2).encode();partial=target.with_suffix('.partial')
    with tarfile.open(partial,'w') as tar:
        for name0,path in sorted(paths.items()):tar.add(path,arcname=name0,recursive=False)
        info=tarfile.TarInfo('block_manifest.json');info.size=len(data);tar.addfile(info,io.BytesIO(data))
    actual={}
    with tarfile.open(partial,'r|') as tar:
        for member in tar:
            h=hashlib.sha256();stream=tar.extractfile(member)
            for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
            actual[member.name]=h.hexdigest()
    if actual!={**expected,'block_manifest.json':hashlib.sha256(data).hexdigest()}:raise ValueError('Packed bytes differ')
    partial.rename(target)
    result={'name':target.name,'bytes':target.stat().st_size,'sha256':sha(target),'runs':len(rows),'first_replicate':lo,'last_replicate':hi,
        'all_members_verified':True,'agent_period_rows':sum(r['verified_agent_period_rows'] for r in rows)}
    receipt.write_text(json.dumps(result,indent=2)+'\n')
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--stage',type=Path);p.add_argument('--watch',action='store_true');a=p.parse_args();done={}
    while True:
        for lo in range(1,101,3):
            if lo in done:continue
            result=pack_block(a.source,a.out,lo)
            if result:
                if a.stage:
                    a.stage.mkdir(parents=True,exist_ok=True);dst=a.stage/result['name']
                    shutil.copyfile(a.out/result['name'],dst)
                    if sha(dst)!=result['sha256']:raise ValueError('Staged copy differs')
                done[lo]=result;print(json.dumps(result),flush=True)
        if len(done)==34:
            (a.out/'raw_archives_manifest.json').write_text(json.dumps([done[k] for k in sorted(done)],indent=2)+'\n');break
        if not a.watch:break
        if (a.source/'execution_summary.json').exists():
            x=json.loads((a.source/'execution_summary.json').read_text())
            if x['failed_runs']:raise RuntimeError('Cannot pack incomplete execution')
        time.sleep(10)

if __name__=='__main__':main()
