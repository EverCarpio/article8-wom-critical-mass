"""Exploratory, paired analysis of the frozen 150-run Article 8 pilot."""
import argparse
from collections import Counter,defaultdict
import csv
import json
import math
from pathlib import Path
import statistics
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'model'))
from article8.export import write_csv,write_json,verify_export
from run_pilot import design,SEEDS,canonical_hash


def wilson(successes,n):
    if not n: return None,None
    z=1.959963984540054
    p=successes/n; scale=1+z*z/n
    center=(p+z*z/(2*n))/scale
    radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/scale
    # Exact binomial endpoints avoid roundoff outside the observed proportion.
    return (0.0 if successes==0 else max(0,center-radius),
            1.0 if successes==n else min(1,center+radius))


def bootstrap_difference(values,seed=88101,repeats=20000):
    import numpy as np
    x=np.asarray(values,dtype=float)
    if not len(x): return None,None
    rng=np.random.default_rng(seed)
    means=x[rng.integers(0,len(x),size=(repeats,len(x)))].mean(axis=1)
    lo,hi=np.quantile(means,[.025,.975])
    return float(lo),float(hi)


def read_csv(path):
    with path.open(encoding='utf-8',newline='') as f: return list(csv.DictReader(f))


def analyze(source,out):
    if out.exists() and any(out.iterdir()): raise FileExistsError('Analysis output must be new/empty')
    out.mkdir(parents=True,exist_ok=True)
    execution=json.loads((source/'execution_summary.json').read_text())
    if execution['completed_runs']!=150 or execution['failed_runs']:
        raise ValueError('Cannot analyze an incomplete pilot')
    records=[]; sensitivity=[]; cohort=[]; series=[]; checks=0
    # The frozen manifest, never incidental staging folders, defines the sample.
    planned=read_csv(source/'planned_runs.csv')
    if len(planned)!=150 or len({r['run_id'] for r in planned})!=150:
        raise ValueError('Unexpected planned run identifiers')
    folders=[source/'runs'/r['run_id'] for r in planned]
    if any(not p.is_dir() for p in folders): raise ValueError('Missing completed run folder')
    for folder in folders:
        verify_export(folder); checks+=1
        row=json.loads((folder/'pilot_record.json').read_text())
        records.append(row)
        sensitivity.extend(read_csv(folder/'classification_sensitivity.csv'))
        windows=read_csv(folder/'reproduction_windows.csv')
        for w in (3,6,12):
            r=next(x for x in windows if x['window_start']=='1' and x['window_width']==str(w))
            cohort.append({'run_id':row['run_id'],'replicate':row['replicate'],'scenario':row['scenario'],
                'width':w,'denominator':int(r['active_at_start']),
                'direct_children':int(r['cohort_children_observed']),
                'cohort_ratio':float(r['cohort_ratio']) if r['cohort_ratio'] else None,
                'window_ratio':float(r['window_ratio']) if r['window_ratio'] else None,
                'cohort_censored':r['cohort_censored']=='True'})
        for r in read_csv(folder/'system_period.csv'):
            series.append({'run_id':row['run_id'],'scenario':row['scenario'],'replicate':row['replicate'],
                **{k:float(r[k]) for k in ('time','new_purchases','cumulative_new_purchases','promoter_active',
                    'detractor_active','positive_capacity','negative_capacity','net_pressure','susceptible_fraction_initial')},
                'diffusion_class':r['diffusion_class']})
    records.sort(key=lambda x:(x['replicate'],x['scenario']))
    if len({r['run_id'] for r in records})!=150: raise ValueError('Duplicate run IDs')
    for seed in SEEDS:
        group=[r for r in records if r['seed']==seed]
        if len(group)!=15 or len({r['environment_sha256'] for r in group})!=1:
            raise ValueError('Pairing matrix violated')
    summaries=[]
    for scenario in design():
        group=[r for r in records if r['scenario']==scenario['scenario']]
        if len(group)!=10: raise ValueError('Missing scenario replicates')
        k=sum(r['takeoff_ever'] for r in group); lo,hi=wilson(k,10)
        y=[r['new_purchases'] for r in group]
        times=[r['takeoff_confirmation'] for r in group if r['takeoff_ever']]
        terminals=Counter(r['terminal_class'] for r in group)
        summaries.append({**scenario,'replicates':10,'initial_promoters':group[0]['initial_promoters'],
            'takeoffs':k,'takeoff_rate':k/10,'takeoff_wilson_low':lo,'takeoff_wilson_high':hi,
            'collapse_count':sum(r['collapse_ever'] for r in group),'collapse_at_risk':k,
            'saturation_count':sum(r['saturation_ever'] for r in group),
            'sales_mean':statistics.mean(y),'sales_median':statistics.median(y),
            'sales_sd':statistics.stdev(y),'sales_min':min(y),'sales_max':max(y),
            'takeoff_time_median_observed':statistics.median(times) if times else None,
            'new_promoters_mean':statistics.mean(r['new_promoters'] for r in group),
            'new_detractors_mean':statistics.mean(r['new_detractors'] for r in group),
            'initial_capacity_mean':statistics.mean(r['initial_positive_capacity'] for r in group),
            'initial_reach_mean':statistics.mean(r['initial_unique_reachable'] for r in group),
            'terminal_counts':json.dumps(dict(sorted(terminals.items())),sort_keys=True),
            'absorbed_runs':sum(r['positive_process_absorbed'] for r in group)})
    contrasts=[('energy_03_minus_06_distributed','E3_distributed','B06'),
               ('energy_09_minus_06_distributed','E9_distributed','B06'),
               ('concentrated_minus_distributed_E03','E3_concentrated','E3_distributed'),
               ('concentrated_minus_distributed_E09','E9_concentrated','E9_distributed'),
               ('energy_09_minus_03_distributed','E9_distributed','E3_distributed'),
               ('energy_09_minus_03_concentrated','E9_concentrated','E3_concentrated')]
    paired=[]; paired_summary=[]
    by_key={(r['replicate'],r['scenario']):r for r in records}
    for ci,(name,left,right) in enumerate(contrasts):
        group=[]
        for rep in range(1,11):
            a,b=by_key[(rep,left)],by_key[(rep,right)]
            r={'contrast':name,'replicate':rep,'seed':a['seed'],'left':left,'right':right,
               'sales_difference':a['new_purchases']-b['new_purchases'],
               'takeoff_difference':int(a['takeoff_ever'])-int(b['takeoff_ever']),
               'initial_capacity_difference':a['initial_positive_capacity']-b['initial_positive_capacity']}
            paired.append(r); group.append(r)
        sales=[r['sales_difference'] for r in group]; events=[r['takeoff_difference'] for r in group]
        slo,shi=bootstrap_difference(sales,seed=88101+ci)
        plo,phi=bootstrap_difference(events,seed=88101+ci)
        paired_summary.append({'contrast':name,'left':left,'right':right,'pairs':10,
            'mean_sales_difference':statistics.mean(sales),'median_sales_difference':statistics.median(sales),
            'sales_bootstrap_low':slo,'sales_bootstrap_high':shi,
            'mean_takeoff_difference':statistics.mean(events),'takeoff_bootstrap_low':plo,'takeoff_bootstrap_high':phi,
            'bootstrap_resamples':20000})
    sensitivity_summary=[]
    for setting in sorted({r['setting'] for r in sensitivity}):
        for scenario in design():
            group=[r for r in sensitivity if r['setting']==setting and r['scenario']==scenario['scenario']]
            sensitivity_summary.append({'setting':setting,**scenario,'replicates':len(group),
                'takeoffs':sum(r['takeoff_ever']=='True' for r in group),
                'collapses':sum(r['collapse_ever']=='True' for r in group),
                'saturations':sum(r['saturation_ever']=='True' for r in group)})
    baseline=[r for r in summaries if r['group']=='baseline']
    baseline.sort(key=lambda r:r['share'])
    frontiers=[]
    for threshold in (.25,.5,.75):
        passing=[r['share'] for r in baseline if r['takeoff_rate']>=threshold]
        frontiers.append({'target_probability':threshold,'minimum_tested_share':min(passing) if passing else None,
                          'all_passing_shares':passing,'not_identified':not bool(passing)})
    decreases=[{'from_share':a['share'],'to_share':b['share'],'from_rate':a['takeoff_rate'],'to_rate':b['takeoff_rate']}
               for a,b in zip(baseline,baseline[1:]) if b['takeoff_rate']<a['takeoff_rate']]
    total={'runs':150,'replicates':10,'scenarios':15,'manifest_checks':checks,
        'model_version':'0.6.0-m6','pilot_version':'0.1.0-pilot',
        'takeoffs':sum(r['takeoff_ever'] for r in records),'collapses':sum(r['collapse_ever'] for r in records),
        'saturations':sum(r['saturation_ever'] for r in records),'terminal_counts':dict(Counter(r['terminal_class'] for r in records)),
        'positive_process_absorbed':sum(r['positive_process_absorbed'] for r in records),
        'invariants_passed':sum(r['invariants_passed'] for r in records),
        'cohort_windows_checked':sum(r['cohort_windows_checked'] for r in records),
        'agent_period_rows':sum(r['agent_period_rows'] for r in records),
        'classification_evaluations':len(sensitivity),'frontiers_exploratory':frontiers,
        'nonmonotone_adjacent_baseline_rates':decreases,
        'runs_requiring_horizon_review':[r['run_id'] for r in records if not r['positive_process_absorbed']],
        'max_last_purchase_period':max(r['last_purchase_period'] or 0 for r in records),
        'median_run_seconds':statistics.median(r['elapsed_seconds'] for r in records),
        'wall_seconds':execution['wall_seconds'],
        'scenario_results':summaries,'paired_results':paired_summary}
    write_csv(out/'run_summary.csv',records)
    write_csv(out/'scenario_summary.csv',summaries)
    write_csv(out/'paired_differences.csv',paired)
    write_csv(out/'paired_summary.csv',paired_summary)
    write_csv(out/'classification_sensitivity.csv',sensitivity)
    write_csv(out/'classification_sensitivity_summary.csv',sensitivity_summary)
    write_csv(out/'initial_cohort_summary.csv',cohort)
    write_csv(out/'system_period_compact.csv',series)
    write_json(out/'analysis_summary.json',total)
    return total


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    args=p.parse_args(); s=analyze(args.source.resolve(),args.out.resolve())
    print(json.dumps({k:v for k,v in s.items() if k not in ('scenario_results','paired_results')},indent=2))


if __name__=='__main__': main()
