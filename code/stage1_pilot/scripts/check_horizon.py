"""Separate 120-period follow-up of only the six nonabsorbed pilot trajectories."""
import argparse
import csv
from dataclasses import replace
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'model'))
from article8.analysis import analyze_simulation
from article8.config import Config
from article8.export import export_analyzed_simulation,verify_export,write_csv,write_json,sha256_file
from article8.mixed import MixedSimulation
from article8.model import initialize
from article8.positive import PositiveConfig


def prefix_rows(path,limit):
    with path.open(newline='',encoding='utf-8') as f:
        reader=csv.DictReader(f)
        for index,row in enumerate(reader):
            if index>=limit: break
            yield row


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pilot',type=Path,required=True); p.add_argument('--analysis',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True); args=p.parse_args()
    pilot=args.pilot.resolve(); analysis=args.analysis.resolve(); out=args.out.resolve()
    if out.exists() and any(out.iterdir()): raise FileExistsError('Follow-up output must be new or empty')
    out.mkdir(parents=True,exist_ok=True)
    summary=json.loads((analysis/'analysis_summary.json').read_text())
    run_ids=summary['runs_requiring_horizon_review']
    write_json(out/'followup_design.json',{'reason':'Positive dynamics not absorbed at period 60',
        'run_ids':run_ids,'base_periods':60,'followup_periods':120,'independent_new_replicates':0,
        'base_model_version':'0.6.0-m6','changes':'Horizon only; original 150 runs remain unchanged'})
    rows=[]
    for run_id in run_ids:
        base=pilot/'runs'/run_id
        old=json.loads((base/'pilot_record.json').read_text())
        cfg=Config(**json.loads((base/'initial_state/config.json').read_text()))
        dynamics=replace(PositiveConfig(**json.loads((base/'dynamics_config.json').read_text())),periods=120)
        sim=MixedSimulation(initialize(cfg),dynamics).run()
        a=analyze_simulation(sim)
        target=out/run_id
        export_analyzed_simulation(sim,target); verify_export(target)
        for name,length in [('system_period.csv',61),('agent_period.csv',600*61)]:
            if list(prefix_rows(base/name,length))!=list(prefix_rows(target/name,length)):
                raise ValueError('120-period trajectory changed its original prefix: '+run_id+'/'+name)
        s=sim.summary()
        row={'run_id':run_id,'replicate':old['replicate'],'seed':old['seed'],'scenario':old['scenario'],
            'purchases_60':old['new_purchases'],'purchases_120':s['cumulative_new_purchases'],
            'additional_purchases':s['cumulative_new_purchases']-old['new_purchases'],
            'takeoff_60':old['takeoff_ever'],'takeoff_120':a.summary['takeoff_ever'],
            'collapse_60':old['collapse_ever'],'collapse_120':a.summary['collapse_ever'],
            'terminal_60':old['terminal_class'],'terminal_120':a.summary['terminal_class'],
            'remaining_60':old['remaining_fraction'],'remaining_120':a.system[-1]['susceptible_fraction_initial'],
            'positive_process_absorbed_120':not(s['promoter_active'] or s['pending_experience_customers'] or s['pending_activation_promoters']),
            'period_prefix_identical':True,'agent_prefix_identical':True}
        rows.append(row)
        print(json.dumps(row),flush=True)
    if rows: write_csv(out/'horizon_comparison.csv',rows)
    write_json(out/'horizon_summary.json',{'followups':len(rows),'independent_new_replicates':0,
        'all_prefixes_identical':all(r['period_prefix_identical'] and r['agent_prefix_identical'] for r in rows),
        'all_absorbed_120':all(r['positive_process_absorbed_120'] for r in rows),
        'additional_purchases_total':sum(r['additional_purchases'] for r in rows),
        'takeoff_changes':sum(r['takeoff_60']!=r['takeoff_120'] for r in rows),
        'collapse_changes':sum(r['collapse_60']!=r['collapse_120'] for r in rows),'runs':rows})


if __name__=='__main__': main()
