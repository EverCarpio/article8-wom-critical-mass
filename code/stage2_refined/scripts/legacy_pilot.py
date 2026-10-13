"""Article 8 pilot v0.1.0: 150 runs, frozen M6, complete trace per run."""
import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[1]
MODEL=ROOT/'model'
sys.path.insert(0,str(MODEL))
from article8 import __version__
from article8.analysis import AnalysisConfig, analyze_simulation
from article8.classification import classify_trajectory
from article8.config import Config
from article8.energy import EnergyConfig
from article8.experience import ExperienceConfig
from article8.export import (environment_fingerprint, export_analyzed_simulation, sha256_file,
                            verify_export, write_csv, write_json)
from article8.mixed import MixedSimulation, NegativeConfig
from article8.model import WOM, initialize
from article8.positive import PositiveConfig

PILOT_VERSION='0.1.0-pilot'
SHARES=(0,.025,.05,.075,.10,.125,.15,.175,.20,.25,.30)
SEEDS=tuple(range(810001,810011))


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()


def verified_model_hash():
    path=MODEL/'SOURCE_SHA256.json'
    for name,expected in json.loads(path.read_text()).items():
        if sha256_file(MODEL/name)!=expected:
            raise ValueError('Frozen M6 file changed: '+name)
    return sha256_file(path)


def design():
    scenarios=[]
    for i,share in enumerate(SHARES):
        scenarios.append({'scenario':f'B{i:02d}','group':'baseline','share':share,
                          'positive_energy':.6,'distribution':'distributed'})
    for energy in (.3,.9):
        for distribution in ('distributed','concentrated'):
            scenarios.append({'scenario':f'E{int(energy*10)}_{distribution}', 'group':'contrast',
                              'share':.15,'positive_energy':energy,'distribution':distribution})
    return scenarios


def settings():
    cfg=AnalysisConfig()
    return [('base',cfg),('duration4',replace(cfg,duration=4)),('duration8',replace(cfg,duration=8)),
        ('growth1_10',replace(cfg,growth_factor=1.1)),('growth1_50',replace(cfg,growth_factor=1.5)),
        ('without_pressure',replace(cfg,require_positive_pressure=False)),
        ('limits05_15',replace(cfg,saturation_remaining=.05,collapse_remaining=.15)),
        ('limits15_30',replace(cfg,saturation_remaining=.15,collapse_remaining=.30))]


def plan():
    return {'pilot_version':PILOT_VERSION,'model_version':__version__,
        'model_source_manifest_sha256':verified_model_hash(),'seeds':list(SEEDS),'scenarios':design(),
        'initial_base':asdict(Config()),'dynamics':asdict(PositiveConfig()),
        'experience':asdict(ExperienceConfig()),'positive_energy_dynamics':asdict(EnergyConfig()),
        'negative_dynamics':asdict(NegativeConfig()),
        'classification_settings':{name:asdict(cfg) for name,cfg in settings()},
        'planned_runs':150,'replicates':10,'baseline_runs':110,'contrast_runs':40,
        'periods':60,'full_agent_history':True,
        'primary_outcome':'Historical observed takeoff, not terminal class',
        'initial_share_denominator':'Initial customers C0=120',
        'new_promoter_energy_fixed':.6,'new_detractor_energy_fixed':.6}


def audit_cohorts(sim,analysis):
    initial={a.id for a in sim.initial.agents if a.wom==WOM.PROMOTER_ACTIVE}
    births=[e for e in sim.activation_events if e['sign']=='positive' and e['activated']]
    exits=[e for e in sim.energy_updates if e['sign']=='positive' and e['deactivated']]
    for row in analysis.reproduction:
        a,b=row['window_start'],row['window_end']
        cohort=(initial | {e['agent'] for e in births if e['period']<a}) - {e['agent'] for e in exits if e['period']<a}
        children={e['agent'] for e in births if e['parent'] in cohort
                  and a<=e['purchase_time']<=b and e['period']<=b+2}
        if (cohort!=set(json.loads(row['cohort_members'])) or children!=set(json.loads(row['direct_children_observed']))
                or row['window_births_observed']!=sum(a<=e['period']<=b for e in births)):
            raise ValueError('Independent cohort reconciliation failed')
        expected=len(children)/len(cohort) if cohort and b+2<=sim.time else None
        if expected!=row['cohort_ratio']:
            raise ValueError('Cohort ratio differs from event ledger')
    return len(analysis.reproduction)


def tasks(out,experiment_plan):
    digest=canonical_hash(experiment_plan)
    return [(str(out),replicate,seed,scenario,digest)
            for replicate,seed in enumerate(SEEDS,1) for scenario in design()]


def run_one(task):
    out,replicate,seed,scenario,digest=task
    run_id=f"r{replicate:02d}_{scenario['scenario']}"
    final=Path(out)/'runs'/run_id
    if final.exists():
        verify_export(final)
        row=json.loads((final/'pilot_record.json').read_text())
        if row['plan_sha256']!=digest or row['seed']!=seed or row['scenario']!=scenario['scenario']:
            raise ValueError('Existing result does not match frozen plan')
        return row
    stage=final.with_name(run_id+'_inprogress')
    if stage.exists():
        raise FileExistsError('Incomplete result requires inspection: '+str(stage))
    start=time.perf_counter(); started=datetime.now(timezone.utc).isoformat()
    cfg=Config(seed=seed,promoter_share=scenario['share'],positive_energy=scenario['positive_energy'],
               distribution=scenario['distribution'])
    initial=initialize(cfg)
    sim=MixedSimulation(initial,PositiveConfig(periods=60,record_agents=True)).run()
    analysis=analyze_simulation(sim)
    checked=audit_cohorts(sim,analysis)
    if sim.time!=60 or len(sim.agent_history)!=cfg.n*61:
        raise ValueError('Incomplete run or individual history')
    if sum(r['messages_sent'] for r in sim.energy_updates)!=len(sim.events):
        raise ValueError('Energy/event mismatch')
    s=sim.summary(); a=analysis.summary
    if scenario['share']==0 and (s['cumulative_new_purchases'] or a['takeoff_ever']):
        raise ValueError('Zero-promoter condition created positive diffusion')
    sensitivity=[]
    for name,config in settings():
        _,_,alternative=classify_trajectory(analysis.system,config)
        sensitivity.append({'run_id':run_id,'replicate':replicate,'seed':seed,**scenario,'setting':name,
            'terminal_class':alternative['terminal_class'],'takeoff_ever':alternative['takeoff_ever'],
            'takeoff_confirmation':alternative['takeoff_first_confirmation'],
            'collapse_ever':alternative['collapse_ever'],'saturation_ever':alternative['saturation_ever'],
            'spike_ever':alternative['spike_ever']})
    initial_promoters=[x for x in initial.agents if x.initial_promoter]
    reachable=set().union(*(set(initial.eligible_contacts(x.id,'positive')) for x in initial_promoters))
    last=analysis.system[-1]
    row={'run_id':run_id,'replicate':replicate,'seed':seed,**scenario,
        'plan_sha256':digest,'model_version':__version__,'python_version':platform.python_version(),
        'environment_sha256':environment_fingerprint(initial),'network_sha256':initial.environment.network.fingerprint(),
        'initial_promoters':len(initial_promoters),'initial_active_promoters':sim.system[0]['promoter_active'],
        'initial_positive_capacity':sim.system[0]['positive_capacity'],
        'initial_unique_reachable':len(reachable),
        'initial_mean_promoter_degree':sum(len(initial.environment.network.neighbors[x.id]) for x in initial_promoters)/len(initial_promoters) if initial_promoters else None,
        'new_purchases':s['cumulative_new_purchases'],'final_customers':s['customers'],
        'remaining_susceptibles':s['susceptibles'],'remaining_fraction':last['susceptible_fraction_initial'],
        'new_promoters':s['cumulative_new_promoters'],'new_detractors':s['cumulative_new_detractors'],
        'positive_events':s['cumulative_positive_events'],'negative_events':s['cumulative_negative_events'],
        'peak_active_promoters':max(r['promoter_active'] for r in sim.system),
        'final_active_promoters':s['promoter_active'],'final_active_detractors':s['detractor_active'],
        'pending_experiences':s['pending_experience_customers'],
        'pending_promoter_activation':s['pending_activation_promoters'],
        'pending_detractor_activation':s['pending_activation_detractors'],
        'positive_process_absorbed':not(s['promoter_active'] or s['pending_experience_customers'] or s['pending_activation_promoters']),
        'last_purchase_period':max((d['period'] for d in sim.decisions if d['adopted']),default=None),
        'last_positive_event':max((e['period'] for e in sim.events if e['sign']=='positive'),default=None),
        'last_negative_event':max((e['period'] for e in sim.events if e['sign']=='negative'),default=None),
        'terminal_class':a['terminal_class'],'takeoff_ever':a['takeoff_ever'],
        'takeoff_start':a['takeoff_first_start'],'takeoff_confirmation':a['takeoff_first_confirmation'],
        'collapse_ever':a['collapse_ever'],'collapse_confirmation':a['collapse_first_confirmation'],
        'saturation_ever':a['saturation_ever'],'saturation_time':a['saturation_first_confirmation'],
        'spike_ever':a['spike_ever'],'plateau_ever':a['plateau_ever'],
        'cohort_windows_checked':checked,'agent_period_rows':len(sim.agent_history),
        'invariants_passed':True,'started_at_utc':started}
    export_analyzed_simulation(sim,stage)
    write_csv(stage/'classification_sensitivity.csv',sensitivity)
    row['elapsed_seconds']=time.perf_counter()-start
    row['completed_at_utc']=datetime.now(timezone.utc).isoformat()
    write_json(stage/'pilot_record.json',row)
    manifest=json.loads((stage/'manifest.json').read_text())
    manifest['pilot_version']=PILOT_VERSION
    manifest['plan_sha256']=digest
    manifest['files_sha256']={str(p.relative_to(stage)):sha256_file(p) for p in sorted(stage.rglob('*'))
                              if p.is_file() and p!=stage/'manifest.json'}
    write_json(stage/'manifest.json',manifest)
    verify_export(stage)
    stage.rename(final)
    return row


def prepare(out):
    current=plan()
    out.mkdir(parents=True,exist_ok=True)
    path=out/'design.json'
    if path.exists():
        if json.loads(path.read_text())!=json.loads(json.dumps(current)):
            raise ValueError('Existing pilot plan changed')
    elif any(out.iterdir()):
        raise FileExistsError('New pilot directory must be empty')
    else:
        write_json(path,current)
        rows=[]
        for scenario in design():
            cfg=asdict(Config(seed=SEEDS[0],promoter_share=scenario['share'],positive_energy=scenario['positive_energy'],
                              distribution=scenario['distribution']))
            cfg.pop('seed')
            rows.append({**scenario,**{'initial_'+k:v for k,v in cfg.items()},
                **{'dynamics_'+k:v for k,v in asdict(PositiveConfig()).items()},
                **{'experience_'+k:v for k,v in asdict(ExperienceConfig()).items()},
                **{'energy_'+k:v for k,v in asdict(EnergyConfig()).items()},
                **{'negative_'+k:v for k,v in asdict(NegativeConfig()).items()}})
        write_csv(out/'parameters.csv',rows)
        write_csv(out/'planned_runs.csv',[{'run_id':f"r{r:02d}_{s['scenario']}",'replicate':r,'seed':seed,**s}
                  for r,seed in enumerate(SEEDS,1) for s in design()])
        write_json(out/'pre_execution_record.json',{'created_at_utc':datetime.now(timezone.utc).isoformat(),
                    'plan_sha256':canonical_hash(current),'runner_sha256':sha256_file(Path(__file__))})
    (out/'runs').mkdir(exist_ok=True)
    return current


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--prepare-only',action='store_true')
    args=parser.parse_args(); out=args.out.resolve()
    if args.workers<1 or args.workers>8: raise ValueError('workers must be in [1,8]')
    experiment=prepare(out)
    if args.prepare_only:
        print(json.dumps({'planned_runs':150,'plan_sha256':canonical_hash(experiment)})); return
    started=time.perf_counter(); failures=[]; completed=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(run_one,task):task for task in tasks(out,experiment)}
        for future in as_completed(futures):
            task=futures[future]
            try:
                row=future.result(); completed.append(row)
                if len(completed)%5==0 or len(completed)==1:
                    print(f"Completed {len(completed)}/150; latest {row['run_id']}: {row['terminal_class']}",flush=True)
            except Exception:
                failures.append({'replicate':task[1],'scenario':task[3]['scenario'],'error':traceback.format_exc()})
                print('FAILED '+str(failures[-1]),flush=True)
    completed.sort(key=lambda r:(r['replicate'],r['scenario']))
    if completed: write_csv(out/'run_manifest.csv',completed)
    write_json(out/'execution_summary.json',{'pilot_version':PILOT_VERSION,'model_version':__version__,
        'plan_sha256':canonical_hash(experiment),'planned_runs':150,'completed_runs':len(completed),
        'failed_runs':len(failures),'failures':failures,'workers':args.workers,
        'wall_seconds':time.perf_counter()-started,'python_version':platform.python_version(),
        'completed_at_utc':datetime.now(timezone.utc).isoformat()})
    if failures or len(completed)!=150: raise RuntimeError('Pilot incomplete; inspect execution_summary.json')
    for seed in SEEDS:
        if len({r['environment_sha256'] for r in completed if r['seed']==seed})!=1:
            raise ValueError('Environment pairing failed')
    if len({r['run_id'] for r in completed})!=150: raise ValueError('Duplicate run identifiers')
    print('Pilot complete: 150 verified runs',flush=True)


if __name__=='__main__': main()
