"""Package each paired replicate separately, using only committed plan IDs."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import zipfile


def archive(target,items):
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for path,name in items:
            info=zipfile.ZipInfo(name,(2026,9,27,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED; info.external_attr=0o100644<<16
            z.writestr(info,path.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=6)
    with zipfile.ZipFile(target) as z:
        if z.testzip() is not None: raise ValueError('Archive integrity failed')
    return {'file':target.name,'bytes':target.stat().st_size,
            'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'members':len(items)}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pilot',type=Path,required=True); p.add_argument('--followup',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True); args=p.parse_args()
    out=args.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    with (args.pilot/'planned_runs.csv').open() as f: runs=list(csv.DictReader(f))
    records=[]
    for rep in range(1,11):
        items=[]; group=[r for r in runs if int(r['replicate'])==rep]
        if len(group)!=15: raise ValueError('Expected fifteen scenarios per replicate')
        for r in group:
            root=args.pilot/'runs'/r['run_id']
            manifest=json.loads((root/'manifest.json').read_text())
            for name in sorted(set(manifest['files_sha256'])|{'manifest.json'}):
                items.append((root/name,'runs/'+r['run_id']+'/'+name))
        for name in ('design.json','planned_runs.csv','parameters.csv','pre_execution_record.json','execution_summary.json'):
            items.append((args.pilot/name,name))
        target=out/f'Article_8_Piloto_Trazas_r{rep:02d}_v0.1.0.zip'
        record=archive(target,items); record.update(replicate=rep,seed=group[0]['seed'],runs=15)
        records.append(record); print(json.dumps(record),flush=True)
    follow=args.followup
    items=[(follow/name,'horizon_followup/'+name) for name in
           ('followup_design.json','horizon_comparison.csv','horizon_summary.json')]
    for run_id in json.loads((follow/'followup_design.json').read_text())['run_ids']:
        root=follow/run_id
        manifest=json.loads((root/'manifest.json').read_text())
        for name in sorted(set(manifest['files_sha256'])|{'manifest.json'}):
            items.append((root/name,'horizon_followup/'+run_id+'/'+name))
    target=out/'Article_8_Piloto_Seguimiento_120_v0.1.0.zip'
    record=archive(target,items); record.update(runs=6,independent_new_replicates=0)
    records.append(record); print(json.dumps(record),flush=True)
    (out/'trace_archives.json').write_text(json.dumps(records,indent=2)+'\n')


if __name__=='__main__': main()
