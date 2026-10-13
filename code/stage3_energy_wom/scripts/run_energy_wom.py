"""Energy x negative WOM x exact initial promoter counts: paired factorial v0.3.0."""
import argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
from dataclasses import asdict,replace
from datetime import datetime,timezone
import json
from pathlib import Path
import platform
import sys
import time
import traceback
import shutil
from archive_runs import archive_run, verify_saved

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'model'))
from article8 import __version__
from article8.analysis import AnalysisConfig,analyze_simulation
from article8.classification import classify_trajectory
from article8.energy import EnergyConfig
from article8.experience import ExperienceConfig
from article8.export import environment_fingerprint,export_analyzed_simulation,verify_export,sha256_file,write_json,write_csv
from article8.mixed import MixedSimulation,NegativeConfig
from article8.positive import PositiveConfig
from legacy_pilot import canonical_hash,verified_model_hash,audit_cohorts
from refined import CountConfig,classify_sustained,settings,first_reach,SustainedConfig

SEEDS=tuple(range(830001,830101))
COUNTS=(1,2)
ENERGIES=(.3,.6,.9)
WEIGHTS=(0.,1.,2.)
PERIODS=120
VERSION='0.3.0-energy-wom'


def scenarios():
    return [{'scenario':f'P{n}_E{int(e*10)}_W{int(w)}','count':n,'positive_energy':e,'negative_weight':w}
            for n in COUNTS for e in ENERGIES for w in WEIGHTS]


def initial_config(seed,count,energy=.6,weight=1.):
    return CountConfig(seed=seed,promoter_share=count/120,exact_promoters=count,
                       positive_energy=energy,negative_weight=weight)


def plan():
    return {'version':VERSION,'model_version':__version__,'model_source_manifest_sha256':verified_model_hash(),
        'observer_sources_sha256':{n:sha256_file(ROOT/'scripts'/n) for n in
          ('refined.py','run_energy_wom.py','legacy_pilot.py','archive_runs.py')},
        'seeds':list(SEEDS),'scenarios':scenarios(),'periods':PERIODS,'replicates':len(SEEDS),'planned_runs':1800,
        'initial_configs':{s['scenario']:asdict(initial_config(SEEDS[0],s['count'],s['positive_energy'],s['negative_weight'])) for s in scenarios()},
        'dynamics':asdict(PositiveConfig(periods=PERIODS,record_agents=True)),
        'experience':asdict(ExperienceConfig()),'energy':asdict(EnergyConfig()),'negative':asdict(NegativeConfig()),
        'primary_endpoint':'Historical sustained diffusion v0.2 d6_f050; unchanged',
        'revised_criterion':asdict(SustainedConfig()),'classification_sensitivity':{n:asdict(c) for n,c in settings()},
        'reference_m6':asdict(AnalysisConfig()),'reference_growth_sensitivity':[1.10,1.50],
        'inference':{'wilson_confidence':.95,'paired_bootstrap_resamples':20000,'bootstrap_seed':88301,
          'contrasts':'P2-P1 at each E,W; E0.6-E0.3 and E0.9-E0.6 at each P,W; W1-W0 and W2-W1 at each P,E; E x W high-low interaction for each P',
          'frontier_targets':[.25,.5,.75],'frontier_rule':'Minimum TESTED count crossing target; 1 is left-censored, neither is outside tested range; no interpolation',
          'intervals':'Pointwise exploratory intervals, no multiplicity adjustment'},
        'full_agent_history':True,'seed_pairing':'Same environment and indexed randomness in 18 cells; P1 subset of P2',
        'interpretation':{'energy':'Initial promoters only; new promoters remain at 0.6',
          'negative_weight':'Lambda multiplies purchase penalty and net-pressure subtraction. Lambda0 preserves negative events and detractor formation; it is not WOM off.',
          'negative_fixed':'Initial detractors6, initial and endogenous negative energy0.6; negative WOM enabled',
          'placement':'Distributed; P2 adds a second community, so count and coverage jointly change'},
        'rule_changes':'None in M6 or primary classifier; parameters and storage orchestration only.'}


def jobs(out,p):
    return [(str(out),i,seed,s,canonical_hash(p)) for i,seed in enumerate(SEEDS,1) for s in scenarios()]


def prepare(out):
    p=plan();out.mkdir(parents=True,exist_ok=True);path=out/'design.json'
    if path.exists():
        if json.loads(path.read_text())!=json.loads(json.dumps(p)):raise ValueError('Frozen plan changed')
    else:
        if any(out.iterdir()):raise FileExistsError('New experiment directory must be empty')
        write_json(path,p)
        write_csv(out/'planned_runs.csv',[{'run_id':f"r{i:03d}_{s['scenario']}",'replicate':i,'seed':seed,**s} for _,i,seed,s,_ in jobs(out,p)])
        write_json(out/'pre_execution_record.json',{'prepared_at_utc':datetime.now(timezone.utc).isoformat(),
            'plan_sha256':canonical_hash(p),'python_version':platform.python_version(),'planned_runs':1800,
            'note':'Frozen before outcomes; 100 new independent seeds, not pooled with previous pilots.'})
    return p


def run_one(task):
    out,rep,seed,scenario,digest=task
    n= scenario['count'];energy=scenario['positive_energy'];weight=scenario['negative_weight']
    run_id=f"r{rep:03d}_{scenario['scenario']}";target=Path(out)/'work'/run_id
    saved=Path(out)/'records'/f'{run_id}.json'
    if saved.exists():
        row=verify_saved(Path(out),run_id)
        if row['plan_sha256']!=digest or row['seed']!=seed:raise ValueError('Resume mismatch')
        return row
    if target.exists():raise FileExistsError('Incomplete result needs inspection: '+str(target))
    started=time.perf_counter();stamp=datetime.now(timezone.utc).isoformat()
    from article8.model import initialize
    cfg=initial_config(seed,n,energy,weight);initial=initialize(cfg)
    promoters=[a for a in initial.agents if a.initial_promoter]
    if len(promoters)!=n:raise ValueError('Exact count violated')
    sim=MixedSimulation(initial,PositiveConfig(periods=PERIODS,record_agents=True)).run()
    analysis=analyze_simulation(sim);checked=audit_cohorts(sim,analysis)
    s=sim.summary();a=analysis.summary;last=analysis.system[-1]
    if sim.time!=PERIODS or len(sim.agent_history)!=cfg.n*(PERIODS+1):raise ValueError('Incomplete history')
    if sum(r['messages_sent'] for r in sim.energy_updates)!=len(sim.events):raise ValueError('Event reconciliation failed')
    revised={name:classify_sustained(analysis.system,480,c) for name,c in settings()}
    main=revised['d6_f050']
    if n==0 and (s['cumulative_new_purchases'] or a['takeoff_ever'] or main['ever']):raise ValueError('Zero control failed')
    sensitivity=[]
    for name,result in revised.items():
        sensitivity.append({'run_id':run_id,'replicate':rep,'seed':seed,'count':n,'family':'v02','setting':name,
            'event':result['ever'],'confirmation':result['first_confirmation']})
    for name,config in [('M6',AnalysisConfig()),('M6_growth110',replace(AnalysisConfig(),growth_factor=1.1)),
                        ('M6_growth150',replace(AnalysisConfig(),growth_factor=1.5))]:
        alt=a if name=='M6' else classify_trajectory(analysis.system,config)[2]
        sensitivity.append({'run_id':run_id,'replicate':rep,'seed':seed,'count':n,'family':'M6','setting':name,
            'event':alt['takeoff_ever'],'confirmation':alt['takeoff_first_confirmation']})
    reachable=set().union(*(set(initial.eligible_contacts(x.id,'positive')) for x in promoters))
    row={'scenario':scenario['scenario'],'positive_energy':energy,'negative_weight':weight,'run_id':run_id,'replicate':rep,'seed':seed,'initial_promoters':n,'share':n/120,
        'plan_sha256':digest,'model_version':__version__,'experiment_version':VERSION,
        'environment_sha256':environment_fingerprint(initial),'network_sha256':initial.environment.network.fingerprint(),
        'initial_promoter_ids':json.dumps([a.id for a in promoters]),'initial_positive_capacity':sim.system[0]['positive_capacity'],
        'initial_unique_reachable':len(reachable),'new_purchases':s['cumulative_new_purchases'],
        'purchases_60':sim.system[60]['cumulative_new_purchases'],'extra_purchases_61_120':s['cumulative_new_purchases']-sim.system[60]['cumulative_new_purchases'],
        'final_customers':s['customers'],'remaining_susceptibles':s['susceptibles'],
        'new_promoters':s['cumulative_new_promoters'],'new_detractors':s['cumulative_new_detractors'],
        'positive_events':s['cumulative_positive_events'],'negative_events':s['cumulative_negative_events'],
        'peak_active_promoters':max(r['promoter_active'] for r in sim.system),'final_active_promoters':s['promoter_active'],
        'final_active_detractors':s['detractor_active'],'pending_experiences':s['pending_experience_customers'],
        'pending_promoter_activation':s['pending_activation_promoters'],
        'positive_process_absorbed':not(s['promoter_active'] or s['pending_experience_customers'] or s['pending_activation_promoters']),
        'last_purchase_period':max((d['period'] for d in sim.decisions if d['adopted']),default=None),
        'sustained_v02':main['ever'],'sustained_start':main['first_start'],'sustained_confirmation':main['first_confirmation'],
        'm6_takeoff':a['takeoff_ever'],'m6_confirmation':a['takeoff_first_confirmation'],
        'm6_terminal_class':a['terminal_class'],'m6_collapse':a['collapse_ever'],'m6_saturation':a['saturation_ever'],
        'm6_spike':a['spike_ever'],'m6_plateau':a['plateau_ever'],
        **{f'reach{int(f*100)}_time':first_reach(analysis.system,480,f) for f in (.10,.25,.50,.75)},
        'cohort_windows_checked':checked,'agent_period_rows':len(sim.agent_history),'invariants_passed':True,
        'started_at_utc':stamp}
    export_analyzed_simulation(sim,target)
    write_json(target/'sustained_audit.json',revised)
    write_csv(target/'classification_sensitivity.csv',sensitivity)
    row['elapsed_seconds']=time.perf_counter()-started;row['completed_at_utc']=datetime.now(timezone.utc).isoformat()
    write_json(target/'factorial_record.json',row)
    manifest=json.loads((target/'manifest.json').read_text())
    manifest.update(experiment_version=VERSION,plan_sha256=digest,
       reproducibility_note='Use scripts/run_energy_wom.py; CountConfig(**initial_state/config.json) preserves exact integer counts. M6 CLI alone does not accept exact_promoters.')
    manifest['files_sha256']={str(p.relative_to(target)):sha256_file(p) for p in sorted(target.rglob('*')) if p.is_file() and p!=target/'manifest.json'}
    write_json(target/'manifest.json',manifest);verify_export(target)
    write_json(target/'completed.json',{'run_id':run_id,'plan_sha256':digest,'manifest_sha256':sha256_file(target/'manifest.json')})
    row.update(archive_run(target,Path(out),row))
    saved.parent.mkdir(parents=True,exist_ok=True)
    write_json(saved,row)
    shutil.rmtree(target)
    return row


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--workers',type=int,default=4);p.add_argument('--prepare-only',action='store_true')
    args=p.parse_args();out=args.out.resolve()
    if not 1<=args.workers<=8:raise ValueError('workers outside [1,8]')
    experiment=prepare(out)
    if args.prepare_only:print(json.dumps({'runs':1800,'plan_sha256':canonical_hash(experiment)}));return
    start=time.perf_counter();complete=[];failures=[]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(run_one,j):j for j in jobs(out,experiment)}
        for future in as_completed(futures):
            job=futures[future]
            try:
                row=future.result();complete.append(row)
                if len(complete)%10==0 or len(complete)==1:print(f'Completed {len(complete)}/1800',flush=True)
            except Exception:
                failures.append({'replicate':job[1],'count':job[3],'error':traceback.format_exc()});print(failures[-1],flush=True)
    complete.sort(key=lambda r:(r['replicate'],r['initial_promoters']))
    if complete:write_csv(out/'run_manifest.csv',complete)
    summary={'version':VERSION,'plan_sha256':canonical_hash(experiment),'planned_runs':1800,'completed_runs':len(complete),
        'failed_runs':len(failures),'failures':failures,'workers':args.workers,'wall_seconds':time.perf_counter()-start,
        'python_version':platform.python_version(),'completed_at_utc':datetime.now(timezone.utc).isoformat()}
    write_json(out/'execution_summary.json',summary)
    if failures or len(complete)!=1800:raise RuntimeError('Incomplete experiment')
    for rep in range(1,101):
        block=[r for r in complete if r['replicate']==rep]
        if len(block)!=18 or len({r['environment_sha256'] for r in block})!=1:raise ValueError('Pairing failed')
        ids={n:{r['initial_promoter_ids'] for r in block if r['initial_promoters']==n} for n in COUNTS}
        if any(len(v)!=1 for v in ids.values()):raise ValueError('Promoter selection depends on energy or weight')
        if not set(json.loads(next(iter(ids[1]))))<=set(json.loads(next(iter(ids[2])))):raise ValueError('Nesting failed')
    print('Complete: 1800 verified runs, 100 matched environments across 18 cells',flush=True)


if __name__=='__main__':main()
