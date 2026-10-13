"""M1–M5 tests and 80 diagnostic runs: off, lambda=0, lambda=1 and lambda=2."""
import argparse
from dataclasses import replace
from datetime import datetime,timezone
import io
import json
import math
import os
from pathlib import Path
import platform
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from article8 import __version__
from article8.config import Config
from article8.export import environment_fingerprint,export_mixed_simulation,verify_export,write_csv,write_json
from article8.mixed import MixedSimulation
from article8.model import initialize,make_environment
from article8.positive import PositiveConfig
from verify_m1 import RecordedResult,require


def verify(out):
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise FileExistsError('Verification output must be new or empty')
    out.mkdir(parents=True,exist_ok=True)
    log=io.StringIO()
    result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=RecordedResult).run(
        unittest.TestSuite(unittest.defaultTestLoader.discover(str(ROOT/'tests'), pattern=f'test_m{m}.py')
                           for m in range(1,6)))
    (out/'unit_tests.log').write_text(log.getvalue(),encoding='utf-8')
    write_json(out/'unit_tests.json',{'tests_run':result.testsRun,'successful':result.wasSuccessful(),
        'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'tests':result.records})
    require(result.wasSuccessful(),'Unit tests failed')
    seeds=list(range(20260925,20260935))
    conditions=[('negative_off',False,1),('lambda_0',True,0),('lambda_1',True,1),('lambda_2',True,2)]
    rows,pairs=[],[]
    for seed in seeds:
        cfg=Config(seed=seed); env=make_environment(cfg)
        for distribution in ('distributed','concentrated'):
            signatures={}; group=[]
            for name,enabled,weight in conditions:
                initial=initialize(replace(cfg,distribution=distribution,negative_wom_enabled=enabled,negative_weight=weight),env)
                detailed=seed==seeds[0] and name=='lambda_1'
                sim=MixedSimulation(initial,PositiveConfig(record_agents=detailed)).run()
                s=sim.summary()
                require(len(sim.events)<=len(list(env.network.edges())),'Finite network contact bound violated')
                require(all(0<=a.positive_energy<=1 and 0<=a.negative_energy<=1 for a in sim.agents),'Energy out of range')
                require(sum(r['messages_sent'] for r in sim.energy_updates)==len(sim.events),'Message-cost accounting mismatch')
                signatures[name]=[(d['period'],d['receiver'],d['parent']) for d in sim.decisions if d['adopted']]
                if name=='negative_off':
                    require(s['cumulative_negative_events']==s['cumulative_new_detractors']==0,'Negative mechanism active while off')
                if detailed:
                    path=out/'examples'/distribution
                    export_mixed_simulation(sim,path); verify_export(path)
                row={'seed':seed,'distribution':distribution,'condition':name,'negative_enabled':enabled,'negative_weight':weight,
                    'environment_sha256':environment_fingerprint(initial),'periods':sim.time,'initial_promoters':18,'initial_detractors':6,
                    'new_purchases':s['cumulative_new_purchases'],'final_customers':s['customers'],
                    'positive_events':s['cumulative_positive_events'],'negative_events':s['cumulative_negative_events'],
                    'new_promoters':s['cumulative_new_promoters'],'new_detractors':s['cumulative_new_detractors'],
                    'satisfied_new_customers':sum(e['experience']=='satisfied' for e in sim.experience_events),
                    'dissatisfied_new_customers':sum(e['experience']=='dissatisfied' for e in sim.experience_events),
                    'new_potential_detractors':sum(e['negative_disposition'] for e in sim.experience_events),
                    'blocked_detractor_activations':s['cumulative_negative_blocked_activations'],
                    'final_active_promoters':s['promoter_active'],'final_active_detractors':s['detractor_active'],
                    'negative_energy_only_exits':s['cumulative_negative_deactivated_energy_only'],
                    'negative_contacts_only_exits':s['cumulative_negative_deactivated_contacts_only'],
                    'negative_both_causes_exits':s['cumulative_negative_deactivated_both'],
                    'total_positive_energy_loss':s['cumulative_positive_energy_loss'],
                    'total_negative_energy_loss':s['cumulative_negative_energy_loss'],
                    'mixed_exposure_decisions':sum(d['new_positive_messages']>0 and d['new_negative_messages']>0 for d in sim.decisions),
                    'negative_only_exposures':sum(not d['eligible_to_buy'] for d in sim.decisions),
                    'pending_experience':s['pending_experience_customers'],'pending_positive_activation':s['pending_activation_promoters'],
                    'pending_negative_activation':s['pending_activation_detractors'],
                    'invariants_passed':True,'classification':'not_evaluated_m5'}
                rows.append(row); group.append(row)
            require(signatures['negative_off']==signatures['lambda_0'],'Lambda=0 changed the purchase trajectory')
            require(len({r['environment_sha256'] for r in group})==1,'Comparison not paired on environment')
            off=group[0]
            for row in group[1:]:
                pairs.append({'seed':seed,'distribution':distribution,'condition':row['condition'],
                    'reference':'negative_off','new_purchase_difference':row['new_purchases']-off['new_purchases'],
                    'new_promoter_difference':row['new_promoters']-off['new_promoters'],
                    'positive_event_difference':row['positive_events']-off['positive_events'],
                    'negative_events':row['negative_events'],'new_detractors':row['new_detractors']})
    write_csv(out/'diagnostic_runs.csv',rows); write_csv(out/'paired_differences.csv',pairs)
    summary={'module_version':__version__,'python_version':platform.python_version(),
        'verified_at_utc':datetime.now(timezone.utc).isoformat(),'unit_tests':result.testsRun,
        **{f'm{m}_tests':sum(r['test'].startswith(f'test_m{m}.') for r in result.records) for m in range(1,6)},
        'failures':len(result.failures),'errors':len(result.errors),'diagnostic_trajectories':len(rows),
        'paired_groups':20,'paired_differences':len(pairs),'periods_per_trajectory':60,'seeds':seeds,
        'diagnostic_failures':0,'full_model_pilot_runs':0,'off_lambda_zero_purchase_equivalence_checks':20,
        'first_seed_examples':[r for r in rows if r['seed']==seeds[0]],
        'condition_means':[{'condition':name,'runs':20,
            **{'mean_'+key:math.fsum(r[key] for r in rows if r['condition']==name)/20
               for key in ('new_purchases','new_promoters','new_detractors','positive_events','negative_events')}}
            for name,_,_ in conditions]}
    write_json(out/'verification_summary.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--out',type=Path,required=True)
    out=parser.parse_args().out.resolve(); os.chdir(ROOT)
    print(json.dumps(verify(out),indent=2))


if __name__=='__main__': main()
