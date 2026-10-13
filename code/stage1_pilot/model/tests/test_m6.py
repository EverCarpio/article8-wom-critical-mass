"""M6 mathematical examples, synthetic trajectories and dynamics regressions."""
from copy import deepcopy
from dataclasses import asdict, replace
import csv
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest

from article8.analysis import (AnalysisConfig, active_at_close, analyze_simulation,
                              reproduction_windows, ratio)
from article8.classification import classify_trajectory
from article8.config import Config
from article8.energy import EnergyConfig
from article8.experience import ExperienceConfig
from article8.export import export_analyzed_simulation, verify_export
from article8.mixed import MixedSimulation
from article8.model import initialize
from article8.positive import PositiveConfig
from test_m2 import accept
from test_m3 import chain


def trajectory(sales, stocks=None, births=None, remaining=None, pressure=None,
               capacity=None, communities=None, external=None):
    n = len(sales)
    stocks = stocks if stocks is not None else [10]*(n+1)
    external = external if external is not None else [0]*n
    if births is None:
        births = [max(0,stocks[i+1]-stocks[i]-external[i]) for i in range(n)]
    remaining = remaining if remaining is not None else [1-sum(sales[:i])/1000 for i in range(n+1)]
    pressure = pressure if pressure is not None else [1]*(n+1)
    capacity = capacity if capacity is not None else [1]*(n+1)
    rows = []
    for t in range(n+1):
        y = sales[t-1] if t else 0
        rows.append({'time':t, 'new_purchases':y, 'promoter_active':stocks[t],
            'new_promoters':births[t-1] if t else 0,
            'deactivated_promoters':stocks[t-1]+births[t-1]+external[t-1]-stocks[t] if t else 0,
            'external_promoters':external[t-1] if t else 0,
            'susceptible_fraction_initial':remaining[t], 'positive_capacity':capacity[t],
            'net_pressure':pressure[t],
            'purchase_communities':(communities[t] if communities is not None else
                                    ((t%2,) if y else ()))})
    return rows


def takeoff(extra=0):
    return trajectory([1,1,2,2,2,2]+[0]*extra, births=[0,0,0,1,0,0]+[0]*extra)


def collapse():
    return trajectory([1,1,2,2,2,2]+[0]*6, stocks=[10]*7+[4]*6,
                      births=[0,0,0,1,0,0]+[0]*6,
                      pressure=[1]*7+[0]*6, capacity=[1]*7+[.1]*6)


def cohort_fixture(horizon=8):
    def agent(i, activation, deactivation=None, parent=None, purchase=None, positive=True):
        return SimpleNamespace(id=i,positive_eligible=positive,activation_time=activation,
            deactivation_time=deactivation,parent=parent,purchase_time=purchase,initial_customer=parent is None)
    # 0 active at time zero, exits at 1. Child 1 buys at 1, activates at 3.
    # Grandchild 2 buys at 3, activates at 5; not a direct child of cohort {0}.
    # Agent 3 purchases at 2 but never activates. Negative agent 4 is excluded.
    agents = [agent(0,0,1),agent(1,3,4,0,1),agent(2,5,None,1,3),
              agent(3,None,None,0,2),agent(4,0,None,positive=False)]
    rows = [{'time':t,'promoter_active':sum(active_at_close(a,t) for a in agents),
             'new_promoters':sum(a.activation_time==t for a in agents if not a.initial_customer)}
            for t in range(horizon+1)]
    return SimpleNamespace(time=horizon,agents=agents,system=rows)


class AnalysisConfigurationTests(unittest.TestCase):
    def test_default_configuration_and_json_roundtrip(self):
        a=AnalysisConfig(); a.validate()
        b=AnalysisConfig(**json.loads(json.dumps(asdict(a)))); b.validate()
        self.assertEqual(tuple(b.cohort_windows),(3,6,12))

    def test_invalid_configurations_rejected(self):
        invalid={'duration':[0,3,True], 'cohort_windows':[[],[3,3],[0],[True]],
                 'reproduction_window':[0,False], 'growth_factor':[1,math.nan,math.inf,True],
                 'require_positive_pressure':[0,'yes'],'saturation_remaining':[-.1,.2],
                 'collapse_remaining':[.1,1.1],'plateau_tolerance':[math.nan,-1]}
        for key,values in invalid.items():
            for value in values:
                with self.subTest(key=key,value=value),self.assertRaises(ValueError):
                    replace(AnalysisConfig(),**{key:value}).validate()

    def test_undefined_ratio_and_valid_zero(self):
        self.assertIsNone(ratio(0,0)); self.assertIsNone(ratio(3,0))
        self.assertEqual(ratio(0,3),0); self.assertEqual(ratio(6,3),2)

    def test_bad_series_rejected(self):
        for key,value in [('time',2),('new_purchases',-1),('net_pressure',math.nan),
                          ('positive_capacity',-1),('susceptible_fraction_initial',1.1),
                          ('purchase_communities',(9,10)),('promoter_active',20)]:
            rows=takeoff(); rows[1][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError): classify_trajectory(rows)


class ReproductionTests(unittest.TestCase):
    def get(self,sim,start=1,width=3):
        return next(r for r in reproduction_windows(sim) if r['window_start']==start and r['window_width']==width)

    def test_direct_child_count_excludes_grandchild_and_blocked_activation(self):
        row=self.get(cohort_fixture(),width=6)
        self.assertEqual(row['cohort_ratio'],1)
        self.assertEqual(row['window_ratio'],2)
        self.assertEqual(json.loads(row['direct_children_observed']),[1])

    def test_inactive_parent_and_inactive_child_remain_attributed(self):
        row=self.get(cohort_fixture())
        self.assertEqual(json.loads(row['cohort_members']),[0])
        self.assertEqual(row['cohort_children_observed'],1)

    def test_two_period_followup_required_at_exact_boundary(self):
        for horizon in (3,4):
            row=self.get(cohort_fixture(horizon))
            self.assertFalse(row['window_censored']); self.assertTrue(row['cohort_censored'])
            self.assertIsNone(row['cohort_ratio'])
        self.assertEqual(self.get(cohort_fixture(5))['cohort_ratio'],1)

    def test_incomplete_birth_window_is_not_zero(self):
        row=self.get(cohort_fixture(2))
        self.assertTrue(row['window_censored']); self.assertIsNone(row['window_ratio'])

    def test_empty_cohort_with_later_birth_keeps_na(self):
        row=self.get(cohort_fixture(),start=2)
        self.assertEqual(row['active_at_start'],0)
        self.assertEqual(row['window_births_observed'],1)
        self.assertIsNone(row['window_ratio']); self.assertIsNone(row['cohort_ratio'])

    def test_active_closure_excludes_same_period_deactivation(self):
        sim=cohort_fixture()
        self.assertTrue(active_at_close(sim.agents[0],0))
        self.assertFalse(active_at_close(sim.agents[0],1))
        self.assertTrue(active_at_close(sim.agents[1],3))
        self.assertFalse(active_at_close(sim.agents[1],4))

    def test_child_purchase_outside_window_excluded(self):
        sim=cohort_fixture(); sim.agents[1].purchase_time=0
        self.assertEqual(self.get(sim)['cohort_children_observed'],0)

    def test_stock_corruption_detected(self):
        sim=cohort_fixture(); sim.system[0]['promoter_active']+=1
        with self.assertRaises(ValueError): reproduction_windows(sim)


class ClassificationTests(unittest.TestCase):
    def summary(self,rows,cfg=AnalysisConfig()): return classify_trajectory(rows,cfg)[2]

    def test_takeoff_dates_and_confirmation_delay(self):
        series,_,s=classify_trajectory(takeoff())
        self.assertEqual((s['takeoff_first_start'],s['takeoff_first_confirmation']),(1,6))
        self.assertFalse(series[5]['takeoff_ever']); self.assertEqual(s['terminal_class'],'sustained_takeoff')

    def test_takeoff_exact_growth_boundary(self):
        rows=trajectory([1,1,2,1,2,2],births=[0,0,0,1,0,0])
        self.assertTrue(self.summary(rows)['takeoff_ever'])
        self.assertFalse(self.summary(trajectory([1,1,2,1,1,2],births=[0,0,0,1,0,0]))['takeoff_ever'])

    def test_takeoff_requires_positive_pressure_each_period(self):
        rows=takeoff(); rows[2]['net_pressure']=0
        self.assertFalse(self.summary(rows)['takeoff_ever'])
        self.assertTrue(self.summary(rows,replace(AnalysisConfig(),require_positive_pressure=False))['takeoff_ever'])

    def test_takeoff_requires_community_spread(self):
        rows=takeoff()
        for r in rows[1:]: r['purchase_communities']=(0,)
        self.assertFalse(self.summary(rows)['takeoff_ever'])

    def test_takeoff_requires_endogenous_activation(self):
        rows=trajectory([1,1,2,2,2,2])
        self.assertFalse(self.summary(rows)['takeoff_ever'])

    def test_takeoff_rejects_external_promoter_addition(self):
        rows=takeoff(); rows[3]['external_promoters']=1; rows[3]['deactivated_promoters']+=1
        self.assertFalse(self.summary(rows)['takeoff_ever'])

    def test_collapse_requires_earlier_takeoff(self):
        rows=trajectory([4,4,4]+[0]*6,stocks=[10]*4+[0]*6,pressure=[1]*4+[0]*6)
        s=self.summary(rows)
        self.assertFalse(s['collapse_ever']); self.assertFalse(s['takeoff_ever'])

    def test_abrupt_zero_sales_collapse_and_historical_takeoff(self):
        s=self.summary(collapse())
        self.assertEqual(s['terminal_class'],'collapse')
        self.assertEqual((s['collapse_first_start'],s['collapse_first_confirmation']),(7,12))
        self.assertEqual(s['takeoff_first_confirmation'],6)

    def test_exact_collapse_market_and_stock_limits(self):
        rows=trajectory([1,1,2,2,2,2]+[0]*6,stocks=[10]*7+[5]*6,
                        births=[0,0,0,1,0,0]+[0]*6,remaining=[1]*7+[.2]*6,
                        capacity=[1]*7+[.5]*6)
        self.assertTrue(self.summary(rows)['collapse_ever'])

    def test_grey_zone_not_forced_to_collapse_or_saturation(self):
        rows=collapse()
        for r in rows[7:]: r['susceptible_fraction_initial']=.15
        s=self.summary(rows)
        self.assertFalse(s['saturation_ever']); self.assertFalse(s['collapse_ever'])

    def test_saturation_exact_limit_priority(self):
        rows=collapse(); rows[-1]['susceptible_fraction_initial']=.1
        s=self.summary(rows)
        self.assertEqual(s['terminal_class'],'saturation'); self.assertFalse(s['collapse_ever'])

    def test_saturation_does_not_erase_earlier_collapse(self):
        rows=collapse(); last=deepcopy(rows[-1]); last.update(time=13,susceptible_fraction_initial=.1)
        rows.append(last)
        s=self.summary(rows)
        self.assertTrue(s['collapse_ever']); self.assertTrue(s['takeoff_ever'])
        self.assertEqual(s['terminal_class'],'saturation')

    def test_plateau_and_exact_tolerance(self):
        rows=trajectory([2,2,1,2,2,2])
        self.assertEqual(self.summary(rows)['terminal_class'],'plateau')

    def test_zero_sales_not_plateau(self):
        s=self.summary(trajectory([0]*12,stocks=[0]*13))
        self.assertFalse(s['plateau_ever']); self.assertEqual(s['terminal_class'],'no_confirmed_takeoff')

    def test_temporal_spike_initial_reference_zero(self):
        rows=trajectory([4,4,4,2,2,2],stocks=[10]*4+[5]*3)
        s=self.summary(rows)
        self.assertEqual(s['terminal_class'],'temporary_spike'); self.assertFalse(s['takeoff_ever'])

    def test_spike_has_no_negative_time_reference(self):
        rows=trajectory([0,5,5,0,0,0,0],stocks=[10]*4+[0]*4)
        _,audit,_=classify_trajectory(rows)
        window=next(r for r in audit if r['kind']=='spike' and r['window_start']==2)
        self.assertFalse(json.loads(window['criteria'])['full_reference'])

    def test_spike_decline_needs_followup(self):
        s=self.summary(trajectory([4,4,4],stocks=[10]*4))
        self.assertFalse(s['spike_ever']); self.assertTrue(s['incomplete_signal'])
        self.assertEqual(s['terminal_class'],'insufficient_followup')

    def test_short_and_zero_horizons_are_not_failures(self):
        for n in (0,1,5):
            s=self.summary(trajectory([0]*n,stocks=[0]*(n+1)))
            self.assertEqual(s['terminal_class'],'insufficient_followup')
            self.assertTrue(s['takeoff_time_censored'])

    def test_incomplete_collapse_not_confirmed(self):
        s=self.summary(collapse()[:-1])
        self.assertFalse(s['collapse_ever']); self.assertTrue(s['incomplete_signal'])

    def test_old_takeoff_expires_without_erasing_history(self):
        s=self.summary(takeoff(extra=12))
        self.assertTrue(s['takeoff_ever']); self.assertFalse(s['takeoff_current'])
        self.assertEqual(s['terminal_class'],'evolving')

    def test_prefix_invariance_no_future_information(self):
        rows=collapse(); full=classify_trajectory(rows)[0]
        for t in range(len(rows)):
            self.assertEqual(full[t],classify_trajectory(rows[:t+1])[0][-1])

    def test_alternative_durations_and_thresholds(self):
        for duration in (4,8):
            half=duration//2
            rows=trajectory([2]*half+[3]*half,births=[0]*half+[1]+[0]*(half-1))
            cfg=replace(AnalysisConfig(),duration=duration,growth_factor=1.5,
                        saturation_remaining=.05,collapse_remaining=.15)
            self.assertTrue(self.summary(rows,cfg)['takeoff_ever'])

    def test_no_censored_window_is_triggered(self):
        _,audit,_=classify_trajectory(takeoff())
        self.assertTrue(any(r['censored'] for r in audit))
        self.assertTrue(all(not r['triggered'] for r in audit if r['censored']))


class AnalysisIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sim=MixedSimulation(dynamics=PositiveConfig(periods=14,record_agents=False)).run()

    def test_analysis_does_not_mutate_any_dynamic_state_or_ledger(self):
        sim=deepcopy(self.sim); before=deepcopy(sim.__dict__)
        analyze_simulation(sim)
        self.assertEqual(sim.__dict__,before)

    def test_indicator_stock_flow_and_coverage(self):
        a=analyze_simulation(self.sim)
        for r in a.system:
            t=r['time']
            self.assertEqual(r['promoter_net_change'],r['new_promoters']-r['deactivated_promoters'])
            expected={d['community'] for d in self.sim.decisions if d['adopted'] and d['period']==t}
            self.assertEqual(set(r['purchase_communities']),expected)
        self.assertEqual(a.system[0]['cumulative_purchase_communities'],0)

    def test_no_lookahead_in_cohort_period_indicator(self):
        full=analyze_simulation(self.sim)
        prefix=MixedSimulation(dynamics=PositiveConfig(periods=14,record_agents=False)).run(until=8)
        partial=analyze_simulation(prefix)
        self.assertEqual(partial.system,full.system[:9])
        self.assertTrue(partial.summary['partial_run'])
        self.assertIsNone(full.system[7]['cohort_ratio_available'])
        self.assertEqual(full.system[8]['cohort_window_start'],1)

    def test_analysis_between_steps_preserves_later_dynamics(self):
        sim=MixedSimulation(dynamics=PositiveConfig(periods=14,record_agents=False)).run(until=6)
        analyze_simulation(sim); sim.run()
        self.assertEqual(sim.agents,self.sim.agents); self.assertEqual(sim.events,self.sim.events)

    def test_history_flag_independence(self):
        sim=MixedSimulation(dynamics=PositiveConfig(periods=14,record_agents=True)).run()
        self.assertEqual(analyze_simulation(sim),analyze_simulation(self.sim))

    def test_chain_cohort_counts_and_delay(self):
        initial,_,_=chain()
        initial=initialize(replace(initial.config,negative_wom_enabled=True),initial.environment)
        sim=MixedSimulation(initial,PositiveConfig(periods=8,opportunities=1),
            ExperienceConfig(quality=1,noise_amplitude=0,promoter_disposition_probability=1),
            EnergyConfig(decay=0,message_cost=0),draw=accept).run()
        a=analyze_simulation(sim)
        w=next(r for r in a.reproduction if r['window_start']==1 and r['window_width']==3)
        self.assertEqual(w['cohort_children_observed'],1)
        self.assertEqual(w['cohort_ratio'],1)

    def test_zero_promoters_and_zero_horizon(self):
        for n in (0,6):
            sim=MixedSimulation(initialize(Config(promoter_share=0)),PositiveConfig(periods=n)).run()
            a=analyze_simulation(sim)
            self.assertTrue(all(r['reproduction_ratio'] is None for r in a.system))
            self.assertFalse(a.summary['takeoff_ever'])

    def test_export_nulls_headers_checksums_and_no_overwrite(self):
        sim=MixedSimulation(dynamics=PositiveConfig(periods=0)).run()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); export_analyzed_simulation(sim,root); verify_export(root)
            for name in ('reproduction_windows','classification_windows'):
                self.assertEqual(len((root/(name+'.csv')).read_text().splitlines()),1)
            with (root/'system_period.csv').open() as f: row=next(csv.DictReader(f))
            self.assertEqual(row['replacement_ratio'],''); self.assertEqual(row['purchase_communities'],'[]')
            with self.assertRaises(FileExistsError): export_analyzed_simulation(sim,root)
            (root/'analysis_config.json').write_text('{}')
            with self.assertRaises(ValueError): verify_export(root)

    def test_export_analysis_and_dynamics_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); export_analyzed_simulation(self.sim,root); verify_export(root)
            s=json.loads((root/'run_summary.json').read_text())
            self.assertEqual(s['module'],'M6'); self.assertEqual(s['customers'],self.sim.summary()['customers'])
            self.assertEqual(s['diffusion_class'],analyze_simulation(self.sim).summary['terminal_class'])

    def test_cli_analysis_config_guards_and_hash_reproducibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); cfg=root/'config.json'; cfg.write_text(json.dumps({'duration':4}))
            base=[sys.executable,'-m','article8','--mode','mixed','--periods','8','--no-agent-history']
            bad=subprocess.run(base+['--analysis-config',str(cfg),'--out',str(root/'bad')],capture_output=True)
            self.assertNotEqual(bad.returncode,0)
            bad=subprocess.run([sys.executable,'-m','article8','--analysis','--out',str(root/'bad2')],capture_output=True)
            self.assertNotEqual(bad.returncode,0)
            paths=[root/'one',root/'two']
            for path,seed in zip(paths,('2','99')):
                out=subprocess.run(base+['--analysis','--analysis-config',str(cfg),'--out',str(path)],
                    env={**os.environ,'PYTHONHASHSEED':seed},capture_output=True,text=True,check=True)
                self.assertEqual(json.loads(out.stdout)['module'],'M6')
            self.assertEqual(*[{str(p.relative_to(path)):p.read_bytes() for p in path.rglob('*') if p.is_file()} for path in paths])


if __name__=='__main__': unittest.main()
