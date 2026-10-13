"""M1–M6 tests; 12 verification trajectories and eight classification settings.

These checks are not the 150-run pilot or the main experiment.
"""
import argparse
from collections import Counter
from dataclasses import asdict, replace
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import platform
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'tests'))
from article8 import __version__
from article8.analysis import AnalysisConfig, analyze_simulation
from article8.classification import classify_trajectory
from article8.config import Config
from article8.export import (environment_fingerprint, export_analyzed_simulation,
                            verify_export, write_csv, write_json)
from article8.mixed import MixedSimulation
from article8.model import WOM, initialize, make_environment
from article8.positive import PositiveConfig
from verify_m1 import RecordedResult, require
from test_m6 import trajectory, takeoff, collapse


def independent_cohort_checks(sim, analysis):
    initial = {a.id for a in sim.initial.agents if a.wom == WOM.PROMOTER_ACTIVE}
    births = [e for e in sim.activation_events if e['sign']=='positive' and e['activated']]
    exits = [e for e in sim.energy_updates if e['sign']=='positive' and e['deactivated']]
    for row in analysis.reproduction:
        a,b = row['window_start'],row['window_end']
        cohort = (initial | {e['agent'] for e in births if e['period'] < a}) - {
            e['agent'] for e in exits if e['period'] < a}
        descendants = {e['agent'] for e in births if e['parent'] in cohort
                       and a <= e['purchase_time'] <= b and e['period'] <= b+2}
        entries = sum(a <= e['period'] <= b for e in births)
        require(cohort == set(json.loads(row['cohort_members'])),'Cohort member reconciliation failed')
        require(descendants == set(json.loads(row['direct_children_observed'])),'Direct child reconciliation failed')
        require(entries == row['window_births_observed'],'Window entries reconciliation failed')
        expected = len(descendants)/len(cohort) if cohort and b+2 <= sim.time else None
        require(expected == row['cohort_ratio'],'Cohort ratio mismatch')
    return len(analysis.reproduction)


def synthetic_cases(out):
    cases=[('takeoff',takeoff(),'sustained_takeoff'),
           ('collapse',collapse(),'collapse'),
           ('plateau',trajectory([2,2,1,2,2,2]),'plateau'),
           ('spike',trajectory([4,4,4,2,2,2],stocks=[10]*4+[5]*3),'temporary_spike'),
           ('no_takeoff',trajectory([0]*12,stocks=[0]*13),'no_confirmed_takeoff'),
           ('short_followup',takeoff()[:5],'insufficient_followup'),
           ('expired_takeoff',takeoff(extra=12),'evolving')]
    saturation=collapse(); saturation[-1]['susceptible_fraction_initial']=.1
    cases.append(('saturation',saturation,'saturation'))
    records=[]
    for name,rows,expected in cases:
        series,windows,summary=classify_trajectory(rows)
        require(summary['terminal_class']==expected,'Synthetic classification failed: '+name)
        root=out/'synthetic'/name; root.mkdir(parents=True)
        write_json(root/'input.json',rows); write_json(root/'summary.json',summary)
        write_csv(root/'classification.csv',series); write_csv(root/'windows.csv',windows)
        records.append({'case':name,'expected':expected,'observed':summary['terminal_class'],
                        'takeoff':summary['takeoff_ever'],'collapse':summary['collapse_ever'],
                        'passed':True})
    write_csv(out/'synthetic_cases.csv',records)
    return records


def verify(out):
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise FileExistsError('Verification output must be new or empty')
    out.mkdir(parents=True,exist_ok=True)
    log=io.StringIO()
    result=unittest.TextTestRunner(stream=log,verbosity=2,resultclass=RecordedResult).run(
        unittest.defaultTestLoader.discover(str(ROOT/'tests')))
    (out/'unit_tests.log').write_text(log.getvalue(),encoding='utf-8')
    write_json(out/'unit_tests.json',{'tests_run':result.testsRun,'successful':result.wasSuccessful(),
        'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'tests':result.records})
    require(result.wasSuccessful(),'Unit tests failed')
    print(f'Passed {result.testsRun} tests',flush=True)
    synthetic=synthetic_cases(out)
    cfg=AnalysisConfig()
    settings=[('base',cfg),('duration4',replace(cfg,duration=4)),('duration8',replace(cfg,duration=8)),
              ('growth1_10',replace(cfg,growth_factor=1.1)),('growth1_50',replace(cfg,growth_factor=1.5)),
              ('without_pressure',replace(cfg,require_positive_pressure=False)),
              ('limits05_15',replace(cfg,saturation_remaining=.05,collapse_remaining=.15)),
              ('limits15_30',replace(cfg,saturation_remaining=.15,collapse_remaining=.30))]
    write_json(out/'analysis_settings.json',{name:asdict(config) for name,config in settings})
    runs,sensitivity=[],[]; checks=0
    for seed in (20260925,20260926):
        base=Config(seed=seed); environment=make_environment(base)
        for distribution in ('distributed','concentrated'):
            for share in (0,.15,.30):
                config=replace(base,distribution=distribution,promoter_share=share)
                detailed=seed==20260925 and share==.15
                sim=MixedSimulation(initialize(config,environment),PositiveConfig(record_agents=detailed)).run()
                observed=analyze_simulation(sim)
                checks+=independent_cohort_checks(sim,observed)
                if share==0:
                    require(sim.summary()['cumulative_new_purchases']==0,'Zero promoters generated purchases')
                    require(not observed.summary['takeoff_ever'],'Zero promoters ignited')
                for name,analysis_config in settings:
                    _,_,summary=classify_trajectory(observed.system,analysis_config)
                    sensitivity.append({'seed':seed,'distribution':distribution,'share':share,
                        'setting':name,'terminal_class':summary['terminal_class'],
                        'takeoff_ever':summary['takeoff_ever'],'takeoff_confirmation':summary['takeoff_first_confirmation'],
                        'collapse_ever':summary['collapse_ever'],'collapse_confirmation':summary['collapse_first_confirmation'],
                        'saturation_ever':summary['saturation_ever'],'spike_ever':summary['spike_ever']})
                row={'seed':seed,'distribution':distribution,'share':share,
                    'environment_sha256':environment_fingerprint(sim.initial),
                    'new_purchases':sim.summary()['cumulative_new_purchases'],
                    'new_promoters':sim.summary()['cumulative_new_promoters'],
                    'new_detractors':sim.summary()['cumulative_new_detractors'],
                    'remaining_fraction':observed.system[-1]['susceptible_fraction_initial'],
                    'terminal_class':observed.summary['terminal_class'],
                    'takeoff_ever':observed.summary['takeoff_ever'],
                    'takeoff_start':observed.summary['takeoff_first_start'],
                    'takeoff_confirmation':observed.summary['takeoff_first_confirmation'],
                    'collapse_ever':observed.summary['collapse_ever'],
                    'collapse_confirmation':observed.summary['collapse_first_confirmation'],
                    'saturation_ever':observed.summary['saturation_ever'],
                    'saturation_time':observed.summary['saturation_first_confirmation'],
                    'spike_ever':observed.summary['spike_ever'],
                    'cohort_windows_checked':len(observed.reproduction),'invariants_passed':True}
                runs.append(row)
                if detailed:
                    path=out/'examples'/distribution
                    export_analyzed_simulation(sim,path); verify_export(path)
                print(f'Verified seed={seed} distribution={distribution} share={share}: {row["terminal_class"]}',flush=True)
    write_csv(out/'diagnostic_runs.csv',runs)
    write_csv(out/'classification_sensitivity.csv',sensitivity)
    summary={'module_version':__version__,'python_version':platform.python_version(),
        'verified_at_utc':datetime.now(timezone.utc).isoformat(),'unit_tests':result.testsRun,
        **{f'm{m}_tests':sum(r['test'].startswith(f'test_m{m}.') for r in result.records) for m in range(1,7)},
        'failures':len(result.failures),'errors':len(result.errors),'synthetic_cases':len(synthetic),
        'verification_trajectories':len(runs),'periods_per_trajectory':60,
        'classification_settings':len(settings),'classification_evaluations':len(sensitivity),
        'independent_cohort_reconciliations':checks,'full_model_pilot_runs':0,
        'terminal_counts':dict(Counter(r['terminal_class'] for r in runs)),
        'historical_takeoffs':sum(r['takeoff_ever'] for r in runs),
        'historical_collapses':sum(r['collapse_ever'] for r in runs),
        'historical_saturation':sum(r['saturation_ever'] for r in runs),
        'settings_summary':[{'setting':name,
            'terminal_counts':dict(Counter(r['terminal_class'] for r in sensitivity if r['setting']==name)),
            'takeoffs':sum(r['takeoff_ever'] for r in sensitivity if r['setting']==name),
            'collapses':sum(r['collapse_ever'] for r in sensitivity if r['setting']==name)} for name,_ in settings],
        'runs':runs}
    write_json(out/'verification_summary.json',summary)
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    out=parser.parse_args().out.resolve(); os.chdir(ROOT)
    summary=verify(out)
    print(json.dumps({k:v for k,v in summary.items() if k not in ('runs','settings_summary')},indent=2))


if __name__=='__main__': main()
