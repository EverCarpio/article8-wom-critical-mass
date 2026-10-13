"""Prespecified paired analysis of the 18-cell energy/WOM experiment."""
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
import statistics as st
import numpy as np
from run_energy_wom import SEEDS,COUNTS,ENERGIES,WEIGHTS,scenarios,canonical_hash
from archive_runs import verify_saved
from article8.export import write_csv,write_json


def read_csv(path):
    with path.open(newline='',encoding='utf-8') as stream:return list(csv.DictReader(stream))


def wilson(k,n):
    z=1.959963984540054;p=k/n;d=1+z*z/n
    c=(p+z*z/(2*n))/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,c-h) if k else 0., min(1,c+h) if k<n else 1.


def bootstrap(values,seed):
    x=np.asarray(values,dtype=float);rng=np.random.default_rng(seed)
    means=x[rng.integers(0,len(x),(20000,len(x)))].mean(axis=1)
    return list(map(float,np.quantile(means,[.025,.975])))


def contrast_specs():
    result=[]
    def add(name,kind,terms):result.append((name,kind,terms))
    for e in ENERGIES:
        for w in WEIGHTS:add(f'P2-P1_E{e}_W{w}','promoters',[(1,(2,e,w)),(-1,(1,e,w))])
    for p in COUNTS:
        for w in WEIGHTS:
            for low,high in zip(ENERGIES,ENERGIES[1:]):add(f'E{high}-E{low}_P{p}_W{w}','energy',[(1,(p,high,w)),(-1,(p,low,w))])
        for e in ENERGIES:
            for low,high in zip(WEIGHTS,WEIGHTS[1:]):add(f'W{high}-W{low}_P{p}_E{e}','negative_weight',[(1,(p,e,high)),(-1,(p,e,low))])
        add(f'Energy_x_WOM_P{p}','interaction',[(1,(p,.9,2.)),(-1,(p,.3,2.)),(-1,(p,.9,0.)),(1,(p,.3,0.))])
    return result


def analyze(source,out):
    execution=json.loads((source/'execution_summary.json').read_text())
    if execution['completed_runs']!=1800 or execution['failed_runs']:raise ValueError('Incomplete experiment')
    plan=json.loads((source/'design.json').read_text());digest=canonical_hash(plan)
    planned=read_csv(source/'planned_runs.csv')
    if len(planned)!=1800 or len({r['run_id'] for r in planned})!=1800:raise ValueError('Invalid plan')
    records=[];sensitivity=[];series=[];cohorts=[]
    for entry in planned:
        row=verify_saved(source,entry['run_id'])
        if row['plan_sha256']!=digest or row['seed']!=int(entry['seed']):raise ValueError('Wrong plan/seed')
        if row['scenario']!=entry['scenario']:raise ValueError('Wrong cell')
        records.append(row);folder=source/'tables'/row['run_id']
        meta={k:row[k] for k in ('run_id','scenario','replicate','seed','initial_promoters','positive_energy','negative_weight')}
        sensitivity.extend({**meta,**r} for r in read_csv(folder/'classification_sensitivity.csv'))
        for r in read_csv(folder/'system_period.csv'):
            series.append({**meta,**{k:float(r[k]) for k in ('time','new_purchases','cumulative_new_purchases','promoter_active','detractor_active','positive_capacity','negative_capacity','net_pressure','susceptible_fraction_initial')},'m6_class':r['diffusion_class']})
        for r in read_csv(folder/'reproduction_windows.csv'):
            if r['window_start']=='1' and r['window_width'] in ('3','6','12'):
                cohorts.append({**meta,'width':int(r['window_width']),'active_at_start':int(r['active_at_start']),
                    'direct_children':int(r['cohort_children_observed']),'cohort_ratio':float(r['cohort_ratio']) if r['cohort_ratio'] else None})
    for rep,seed in enumerate(SEEDS,1):
        group=[r for r in records if r['replicate']==rep]
        if len(group)!=18 or {r['seed'] for r in group}!={seed} or len({r['environment_sha256'] for r in group})!=1:raise ValueError('Pairing failure')
        ids={p:{r['initial_promoter_ids'] for r in group if r['initial_promoters']==p} for p in COUNTS}
        if any(len(v)!=1 for v in ids.values()) or not set(json.loads(next(iter(ids[1]))))<set(json.loads(next(iter(ids[2])))):raise ValueError('Bad promoter sets')
    summaries=[]
    for sc in scenarios():
        block=[r for r in records if r['scenario']==sc['scenario']];sales=[r['new_purchases'] for r in block]
        if len(block)!=100:raise ValueError('Missing replicate')
        result={**sc,'replicates':100,'sales_mean':st.mean(sales),'sales_median':st.median(sales),'sales_sd':st.stdev(sales),
            'sales_min':min(sales),'sales_max':max(sales),'sales_q25':float(np.quantile(sales,.25)),'sales_q75':float(np.quantile(sales,.75)),
            'purchases60_mean':st.mean(r['purchases_60'] for r in block),'late_purchases_mean':st.mean(r['extra_purchases_61_120'] for r in block),
            'absorbed_count':sum(r['positive_process_absorbed'] for r in block),'m6_collapse_count':sum(r['m6_collapse'] for r in block),
            'm6_saturation_count':sum(r['m6_saturation'] for r in block),'negative_events_mean':st.mean(r['negative_events'] for r in block),
            'new_promoters_mean':st.mean(r['new_promoters'] for r in block),'new_detractors_mean':st.mean(r['new_detractors'] for r in block)}
        for field in ('sustained_v02','m6_takeoff'):
            k=sum(r[field] for r in block);lo,hi=wilson(k,100)
            result.update({field+'_count':k,field+'_rate':k/100,field+'_low':lo,field+'_high':hi})
        for field in ('sustained_confirmation','m6_confirmation','reach10_time','reach25_time','reach50_time','reach75_time'):
            times=[r[field] for r in block if r[field] is not None]
            result[field+'_events']=len(times);result[field+'_median_among_events']=st.median(times) if times else None
        summaries.append(result)
    by={(r['replicate'],r['initial_promoters'],r['positive_energy'],r['negative_weight']):r for r in records}
    paired=[];effects=[]
    for ci,(name,kind,terms) in enumerate(contrast_specs()):
        block=[]
        for rep in range(1,101):
            r={'contrast':name,'kind':kind,'replicate':rep,'seed':SEEDS[rep-1]}
            for field in ('new_purchases','sustained_v02','m6_takeoff'):
                r[field+'_difference']=sum(sign*int(by[(rep,)+key][field]) for sign,key in terms)
            block.append(r);paired.append(r)
        for field in ('new_purchases','sustained_v02','m6_takeoff'):
            values=[r[field+'_difference'] for r in block];lo,hi=bootstrap(values,88301+ci)
            effects.append({'contrast':name,'kind':kind,'metric':field,'pairs':100,'mean':st.mean(values),'median':st.median(values),
                'low':lo,'high':hi,'positive_pairs':sum(v>0 for v in values),'negative_pairs':sum(v<0 for v in values),'zero_pairs':sum(v==0 for v in values),
                'resamples':20000,'bootstrap_seed':88301+ci})
    sens_summary=[];incidence=[];frontier=[];cohort_summary=[]
    for sc in scenarios():
        cell=sc['scenario'];block=[r for r in records if r['scenario']==cell]
        for setting in sorted({r['setting'] for r in sensitivity}):
            group=[r for r in sensitivity if r['scenario']==cell and r['setting']==setting]
            if len(group)!=100:raise ValueError('Sensitivity sample incomplete')
            k=sum(r['event']=='True' for r in group);lo,hi=wilson(k,100)
            sens_summary.append({**sc,'setting':setting,'events':k,'n':100,'rate':k/100,'low':lo,'high':hi})
        for field in ('sustained_confirmation','m6_confirmation','reach10_time','reach25_time','reach50_time','reach75_time'):
            for t in range(121):
                k=sum(r[field] is not None and r[field]<=t for r in block)
                incidence.append({**sc,'event':field,'time':t,'events':k,'n':100,'rate':k/100})
        for width in (3,6,12):
            group=[r for r in cohorts if r['scenario']==cell and r['width']==width]
            values=[r['cohort_ratio'] for r in group if r['cohort_ratio'] is not None]
            cohort_summary.append({**sc,'width':width,'observed_ratios':len(values),'ratio_mean':st.mean(values) if values else None,
                'ratio_median':st.median(values) if values else None,'ratio_at_least_one':sum(v>=1 for v in values)})
    for e in ENERGIES:
        for w in WEIGHTS:
            block=sorted((r for r in summaries if r['positive_energy']==e and r['negative_weight']==w),key=lambda r:r['count'])
            for target in (.25,.5,.75):
                for field in ('sustained_v02','m6_takeoff'):
                    crosses=[r['count'] for r in block if r[field+'_rate']>=target]
                    lower=[r['count'] for r in block if r[field+'_low']>=target]
                    frontier.append({'positive_energy':e,'negative_weight':w,'target':target,'criterion':field,
                        'minimum_tested_count':min(crosses) if crosses else None,'minimum_tested_lower_bound_count':min(lower) if lower else None,
                        'status':'left_boundary_at_one' if 1 in crosses else 'crossing_at_two' if 2 in crosses else 'not_reached_in_tested_grid'})
    if out.exists() and any(out.iterdir()):raise FileExistsError('Analysis destination must be empty')
    out.mkdir(parents=True,exist_ok=True)
    datasets={'runs':records,'cell_summary':summaries,'paired_differences':paired,'paired_summary':effects,
        'classification_sensitivity':sensitivity,'sensitivity_summary':sens_summary,'system_period_all':series,
        'incidence':incidence,'cohort_initial':cohorts,'cohort_summary':cohort_summary,'discrete_frontier':frontier,
        'classification_disagreements':[r for r in records if r['sustained_v02']!=r['m6_takeoff']],
        'open_trajectories':[r for r in records if not r['positive_process_absorbed']]}
    for name,rows in datasets.items():write_csv(out/f'{name}.csv',rows,list(records[0]) if not rows else None)
    summary={'plan_sha256':digest,'runs':1800,'cells':18,'paired_environments':100,
        'agent_period_rows':sum(r['verified_agent_period_rows'] for r in records),
        'archive_members_verified':sum(r['verified_archive_members'] for r in records),
        'cohort_windows_checked':sum(r['cohort_windows_checked'] for r in records),
        'classification_evaluations':len(sensitivity),'classification_disagreements':len(datasets['classification_disagreements']),
        'open_trajectories':len(datasets['open_trajectories']),'archived_bytes':sum(r['archive_bytes'] for r in records),
        'terminal_counts':dict(Counter(r['m6_terminal_class'] for r in records)),
        'late_purchases':sum(r['extra_purchases_61_120'] for r in records),
        'runs_with_late_purchases':sum(r['extra_purchases_61_120']>0 for r in records)}
    write_json(out/'analysis_summary.json',summary)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--out',required=True,type=Path)
    a=p.parse_args();analyze(a.source,a.out)
