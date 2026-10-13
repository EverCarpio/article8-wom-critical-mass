"""Paired, prespecified analysis; no pooling with the previous pilot."""
import argparse
from collections import Counter
import csv
import json
import math
from pathlib import Path
import statistics
import sys
import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'model'))
from article8.export import write_csv,write_json,verify_export,sha256_file
from run_refined import SEEDS,COUNTS,canonical_hash


def read_csv(path):
    with path.open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))


def wilson(k,n):
    z=1.959963984540054;p=k/n;scale=1+z*z/n
    center=(p+z*z/(2*n))/scale;radius=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/scale
    return (0. if k==0 else max(0.,center-radius),1. if k==n else min(1.,center+radius))


def bootstrap(values,seed):
    x=np.asarray(values,dtype=float);rng=np.random.default_rng(seed)
    means=x[rng.integers(0,len(x),size=(20000,len(x)))].mean(axis=1)
    return [float(v) for v in np.quantile(means,[.025,.975])]


def analyze(source,out):
    if out.exists() and any(out.iterdir()):raise FileExistsError('Analysis output must be empty')
    out.mkdir(parents=True,exist_ok=True)
    execution=json.loads((source/'execution_summary.json').read_text())
    p=json.loads((source/'design.json').read_text());digest=canonical_hash(p)
    if execution['completed_runs']!=400 or execution['failed_runs']:raise ValueError('Incomplete experiment')
    planned=read_csv(source/'planned_runs.csv')
    if len(planned)!=400 or len({r['run_id'] for r in planned})!=400:raise ValueError('Invalid sample')
    records=[];sens=[];series=[];cohort=[];discordant=[]
    for planned_row in planned:
        folder=source/'runs'/planned_row['run_id'];verify_export(folder)
        completion=json.loads((folder/'completed.json').read_text())
        if completion['manifest_sha256']!=sha256_file(folder/'manifest.json'):raise ValueError('Commit manifest mismatch')
        row=json.loads((folder/'refined_record.json').read_text())
        if row['plan_sha256']!=digest or row['run_id']!=planned_row['run_id']:raise ValueError('Run plan mismatch')
        records.append(row);sens.extend(read_csv(folder/'classification_sensitivity.csv'))
        for r in read_csv(folder/'system_period.csv'):
            series.append({'run_id':row['run_id'],'replicate':row['replicate'],'count':row['initial_promoters'],
                **{k:float(r[k]) for k in ('time','new_purchases','cumulative_new_purchases','promoter_active','detractor_active',
                    'positive_capacity','negative_capacity','net_pressure','susceptible_fraction_initial')},'m6_class':r['diffusion_class']})
        for r in read_csv(folder/'reproduction_windows.csv'):
            if r['window_start']=='1' and r['window_width'] in ('3','6','12'):
                cohort.append({'run_id':row['run_id'],'count':row['initial_promoters'],'replicate':row['replicate'],
                    'width':int(r['window_width']),'active_at_start':int(r['active_at_start']),
                    'direct_children':int(r['cohort_children_observed']),
                    'cohort_ratio':float(r['cohort_ratio']) if r['cohort_ratio'] else None})
        if row['sustained_v02']!=row['m6_takeoff']:
            discordant.append({k:row[k] for k in ('run_id','seed','initial_promoters','new_purchases','sustained_v02','sustained_confirmation','m6_takeoff','m6_confirmation','m6_terminal_class')})
    for rep,seed in enumerate(SEEDS,1):
        group=[r for r in records if r['replicate']==rep]
        if len(group)!=4 or {r['seed'] for r in group}!={seed} or len({r['environment_sha256'] for r in group})!=1:raise ValueError('Pairing failure')
        group.sort(key=lambda r:r['initial_promoters']);sets=[set(json.loads(r['initial_promoter_ids'])) for r in group]
        if any(not a<=b for a,b in zip(sets,sets[1:])):raise ValueError('Promoter nesting failure')
    summaries=[];cross=[]
    for count in COUNTS:
        group=[r for r in records if r['initial_promoters']==count]
        if len(group)!=100:raise ValueError('Missing repetitions')
        y=[r['new_purchases'] for r in group]
        result={'count':count,'share':count/120,'replicates':100,'sales_mean':statistics.mean(y),
            'sales_median':statistics.median(y),'sales_sd':statistics.stdev(y),'sales_min':min(y),'sales_max':max(y),
            'sales_q25':float(np.quantile(y,.25)),'sales_q75':float(np.quantile(y,.75)),
            'purchases60_mean':statistics.mean(r['purchases_60'] for r in group),
            'extra_purchases_mean':statistics.mean(r['extra_purchases_61_120'] for r in group),
            'runs_with_late_purchases':sum(r['extra_purchases_61_120']>0 for r in group),
            'absorbed_count':sum(r['positive_process_absorbed'] for r in group),
            'm6_collapse_count':sum(r['m6_collapse'] for r in group),'m6_saturation_count':sum(r['m6_saturation'] for r in group)}
        for field in ('sustained_v02','m6_takeoff'):
            k=sum(r[field] for r in group);lo,hi=wilson(k,100)
            result.update({field+'_count':k,field+'_rate':k/100,field+'_low':lo,field+'_high':hi})
        for field in ('sustained_confirmation','m6_confirmation'):
            times=[r[field] for r in group if r[field] is not None]
            result[field+'_median_among_events']=statistics.median(times) if times else None
        for level in (10,25,50,75):
            times=[r[f'reach{level}_time'] for r in group if r[f'reach{level}_time'] is not None]
            result[f'reach{level}_events']=len(times)
            result[f'reach{level}_median_among_events']=statistics.median(times) if times else None
        summaries.append(result)
        for old in (False,True):
            for new in (False,True):cross.append({'count':count,'m6_takeoff':old,'sustained_v02':new,'runs':sum(r['m6_takeoff']==old and r['sustained_v02']==new for r in group)})
    paired=[];paired_summary=[];by={(r['replicate'],r['initial_promoters']):r for r in records}
    for ci,(left,right) in enumerate(((1,0),(2,1),(3,2),(3,1))):
        block=[]
        for rep in range(1,101):
            a,b=by[rep,left],by[rep,right]
            row={'contrast':f'P{left}-P{right}','replicate':rep,'seed':a['seed'],
                'sales_difference':a['new_purchases']-b['new_purchases'],
                'sustained_difference':int(a['sustained_v02'])-int(b['sustained_v02']),
                'm6_difference':int(a['m6_takeoff'])-int(b['m6_takeoff'])}
            paired.append(row);block.append(row)
        for metric in ('sales_difference','sustained_difference','m6_difference'):
            values=[r[metric] for r in block];lo,hi=bootstrap(values,88201+ci)
            paired_summary.append({'contrast':f'P{left}-P{right}','metric':metric,'pairs':100,
                'mean':statistics.mean(values),'median':statistics.median(values),'low':lo,'high':hi,
                'positive_pairs':sum(v>0 for v in values),'negative_pairs':sum(v<0 for v in values),'zero_pairs':sum(v==0 for v in values),
                'resamples':20000,'bootstrap_seed':88201+ci})
    sensitivity=[]
    for setting in sorted({r['setting'] for r in sens}):
        for count in COUNTS:
            block=[r for r in sens if r['setting']==setting and int(r['count'])==count]
            if len(block)!=100:raise ValueError('Incomplete classification sensitivity')
            k=sum(r['event']=='True' for r in block);lo,hi=wilson(k,100)
            sensitivity.append({'setting':setting,'family':block[0]['family'],'count':count,'events':k,'n':100,'rate':k/100,'low':lo,'high':hi})
    # Denominator remains 100. No successful-only survival curve.
    incidence=[]
    for count in COUNTS:
        block=[r for r in records if r['initial_promoters']==count]
        for field in ('sustained_confirmation','m6_confirmation','reach10_time','reach25_time','reach50_time','reach75_time'):
            for t in range(121):
                k=sum(r[field] is not None and r[field]<=t for r in block)
                incidence.append({'count':count,'endpoint':field,'period':t,'events_by_t':k,'n':100,'cumulative_incidence':k/100})
    frontier=[]
    for field in ('sustained_v02','m6_takeoff'):
        for target in (.25,.5,.75):
            passing=[r['count'] for r in summaries if r[field+'_rate']>=target]
            lower_supported=[r['count'] for r in summaries if r[field+'_low']>=target]
            possible=[r['count'] for r in summaries if r[field+'_high']>=target]
            frontier.append({'endpoint':field,'target':target,'minimum_tested_count':min(passing) if passing else None,
                'minimum_tested_share':min(passing)/120 if passing else None,
                'minimum_count_with_pointwise_lower_bound_at_target':min(lower_supported) if lower_supported else None,
                'minimum_count_with_pointwise_upper_bound_at_target':min(possible) if possible else None,
                'note':'Discrete tested crossing, conditional; pointwise bounds are not threshold confidence intervals'})
    total={'runs':400,'paired_blocks':100,'periods':120,'plan_sha256':digest,
        'manifest_checks':400,'cohort_windows_checked':sum(r['cohort_windows_checked'] for r in records),
        'agent_period_rows':sum(r['agent_period_rows'] for r in records),'invariants_passed':sum(r['invariants_passed'] for r in records),
        'classification_evaluations':len(sens),'discordant_classifications':len(discordant),
        'sustained_v02':sum(r['sustained_v02'] for r in records),'m6_takeoff':sum(r['m6_takeoff'] for r in records),
        'absorbed_count':sum(r['positive_process_absorbed'] for r in records),
        'unabsorbed_run_ids':[r['run_id'] for r in records if not r['positive_process_absorbed']],
        'late_purchases':sum(r['extra_purchases_61_120'] for r in records),
        'runs_with_late_purchases':sum(r['extra_purchases_61_120']>0 for r in records),
        'last_purchase_period_max':max(r['last_purchase_period'] or 0 for r in records),
        'wall_seconds':execution['wall_seconds'],'scenarios':summaries,'paired':paired_summary,'frontier':frontier,
        'm6_terminal_counts':dict(Counter(r['m6_terminal_class'] for r in records))}
    for name,rows in [('run_summary',records),('scenario_summary',summaries),('paired_differences',paired),('paired_summary',paired_summary),
                      ('classification_sensitivity',sens),('classification_sensitivity_summary',sensitivity),
                      ('classification_cross_table',cross),('system_period_compact',series),('initial_cohort_summary',cohort),
                      ('cumulative_incidence',incidence),('discrete_frontier',frontier)]:write_csv(out/(name+'.csv'),rows)
    write_csv(out/'classification_disagreements.csv',discordant,list(discordant[0]) if discordant else ['run_id','seed','initial_promoters','new_purchases','sustained_v02','sustained_confirmation','m6_takeoff','m6_confirmation','m6_terminal_class'])
    write_json(out/'analysis_summary.json',total)
    return total


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    args=p.parse_args();result=analyze(args.source,args.out)
    print(json.dumps({k:v for k,v in result.items() if k not in ('scenarios','paired','frontier')},indent=2))
