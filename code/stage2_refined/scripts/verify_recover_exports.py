"""After execution finishes, verify exports and deterministically repair damage.

No seed substitution. Damaged exports are quarantined, not silently overwritten.
Recreated deterministic files must match the original committed manifest.
"""
import argparse
import csv
import json
from pathlib import Path
import time
import shutil
import tempfile

from run_refined import run_one,canonical_hash
from article8.export import verify_export,sha256_file,write_csv,write_json


def verify_agent_history(path,n=600,periods=120):
    with path.open('rb') as stream:
        if stream.readline().split(b',',2)[:2]!=[b'period',b'id']:raise ValueError('Unexpected agent trace header')
        count=0
        for index,line in enumerate(stream):
            prefix=line.split(b',',2)
            if len(prefix)!=3 or int(prefix[0])!=index//n or int(prefix[1])!=index%n:
                raise ValueError('Agent trace is missing, duplicated or unordered at row '+str(index))
            count+=1
    if count!=n*(periods+1):raise ValueError('Incomplete agent trace: '+str(count))
    return count


def verify(root):
    verify_export(root)
    commit=json.loads((root/'completed.json').read_text())
    if commit['manifest_sha256']!=sha256_file(root/'manifest.json'):raise ValueError('Commit/manifest mismatch')
    verify_agent_history(root/'agent_period.csv')


def repair(source):
    execution=json.loads((source/'execution_summary.json').read_text())
    if execution['completed_runs']!=400 or execution['failed_runs']:raise ValueError('Wait for successful execution')
    p=json.loads((source/'design.json').read_text());digest=canonical_hash(p)
    with (source/'planned_runs.csv').open() as stream:planned=list(csv.DictReader(stream))
    if len(planned)!=400:raise ValueError('Bad plan')
    recovery=[];records=[];start=time.perf_counter()
    previous=source.parent/'export_quarantine'
    if previous.exists():
        for folder in sorted(previous.iterdir()):
            current=source/'runs'/folder.name
            if not current.exists():continue
            try:verify(current)
            except (OSError,ValueError):continue
            old=json.loads((folder/'manifest.json').read_text());new=json.loads((current/'manifest.json').read_text())
            matched=[name for name,digest0 in old['files_sha256'].items() if name!='refined_record.json' and new['files_sha256'].get(name)==digest0]
            if len(matched)!=len(old['files_sha256'])-1:raise ValueError('Prior recovery is not identical')
            old_row=json.loads((folder/'refined_record.json').read_text());new_row=json.loads((current/'refined_record.json').read_text())
            volatile={'elapsed_seconds','started_at_utc','completed_at_utc'}
            if {k:v for k,v in old_row.items() if k not in volatile}!={k:v for k,v in new_row.items() if k not in volatile}:raise ValueError('Prior outcomes changed')
            recovery.append({'run_id':folder.name,'reason':'Earlier verification retry; field name period corrected in history reader. Original deterministic content unchanged.',
                'same_seed':True,'outcomes_identical':True,'deterministic_files_matched':len(matched)})
    for entry in planned:
        folder=source/'runs'/entry['run_id'];error=None
        try:verify(folder)
        except (OSError,ValueError) as exc:error=str(exc)
        if error:
            old_record=json.loads((folder/'refined_record.json').read_text())
            if old_record['plan_sha256']!=digest or old_record['seed']!=int(entry['seed']):raise ValueError('Identity mismatch; cannot repair automatically')
            old_manifest=json.loads((folder/'manifest.json').read_text())
            if old_manifest['plan_sha256']!=digest:raise ValueError('Manifest identity mismatch')
            quarantine=source.parent/'export_quarantine'/folder.name
            quarantine.parent.mkdir(exist_ok=True)
            if not quarantine.exists():shutil.copytree(folder,quarantine)
            # Generate away from the live workspace; only copy a completed,
            # verified export back. Renaming an active workspace directory can
            # leave a stale materialized copy at its former path.
            with tempfile.TemporaryDirectory(prefix='article8_export_repair_') as tmp:
                row=run_one((tmp,int(entry['replicate']),int(entry['seed']),int(entry['count']),digest))
                rebuilt=Path(tmp)/'runs'/entry['run_id'];verify(rebuilt)
                shutil.rmtree(folder)
                shutil.copytree(rebuilt,folder)
            new_manifest=json.loads((folder/'manifest.json').read_text());matched=0
            for name,expected in old_manifest['files_sha256'].items():
                if name=='refined_record.json':continue
                if new_manifest['files_sha256'].get(name)!=expected:raise ValueError('Regenerated deterministic content differs: '+entry['run_id']+'/'+name)
                matched+=1
            volatile={'elapsed_seconds','started_at_utc','completed_at_utc'}
            if {k:v for k,v in old_record.items() if k not in volatile}!={k:v for k,v in row.items() if k not in volatile}:raise ValueError('Regenerated outcomes differ')
            recovery.append({'run_id':entry['run_id'],'reason':error,'same_seed':True,'outcomes_identical':True,'deterministic_files_matched':matched})
            print('Recovered '+entry['run_id'],flush=True)
        if error:verify(folder)
        records.append(json.loads((folder/'refined_record.json').read_text()))
    write_csv(source/'run_manifest.csv',records)
    result={'exports_verified':len(records),'regenerated_runs':len(recovery),'recovery':recovery,
        'verification_and_recovery_seconds':time.perf_counter()-start,'plan_sha256':digest,
        'agent_history_rows_checked':400*600*121,'complete_and_ordered_histories':400,
        'note':'Damaged export copies recovered only with identical seeds, frozen rules, and identical deterministic outputs; not additional independent replicates.'}
    write_json(source/'export_recovery.json',result)
    print(json.dumps(result),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True)
    args=p.parse_args();repair(args.source.resolve())
