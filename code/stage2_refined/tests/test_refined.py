import copy
from dataclasses import asdict
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from refined import CountConfig,SustainedConfig,classify_sustained,first_reach
from run_refined import initial_config,plan,prepare,jobs
from article8.config import Config
from article8.model import initialize
from article8.export import environment_fingerprint
from article8.classification import classify_trajectory
from article8.mixed import MixedSimulation
from article8.positive import PositiveConfig
from verify_recover_exports import verify_agent_history


def trajectory(sales):
    rows=[{'time':0,'new_purchases':0,'promoter_active':3,'new_promoters':0,
        'deactivated_promoters':0,'external_promoters':0,'positive_capacity':2.,
        'net_pressure':1.,'susceptible_fraction_initial':1.,'purchase_communities':[]}]
    total=0
    for t,y in enumerate(sales,1):
        total+=y
        rows.append({'time':t,'new_purchases':y,'promoter_active':3+t,'new_promoters':1,
            'deactivated_promoters':0,'external_promoters':0,'positive_capacity':2.,
            'net_pressure':1.,'susceptible_fraction_initial':1-total/480,
            'purchase_communities':[t%2] if y else []})
    return rows


class InputTests(unittest.TestCase):
    def test_exact_counts_nested_and_environment_matched(self):
        states=[initialize(initial_config(920001,n)) for n in range(4)]
        self.assertEqual(len({environment_fingerprint(s) for s in states}),1)
        ids=[{a.id for a in s.agents if a.initial_promoter} for s in states]
        self.assertEqual(list(map(len,ids)),[0,1,2,3])
        self.assertTrue(all(a<=b for a,b in zip(ids,ids[1:])))
        self.assertEqual([len({s.agents[i].community for i in group}) for s,group in zip(states,ids)],[0,1,2,3])

    def test_adapter_preserves_existing_three_promoter_dynamics(self):
        old=initialize(Config(seed=920002,promoter_share=.025))
        new=initialize(initial_config(920002,3))
        self.assertEqual([asdict(a) for a in old.agents],[asdict(a) for a in new.agents])
        a=MixedSimulation(old,PositiveConfig(periods=12)).run()
        b=MixedSimulation(new,PositiveConfig(periods=12)).run()
        self.assertEqual(a.system,b.system);self.assertEqual(a.events,b.events)
        self.assertEqual(a.agent_history,b.agent_history)

    def test_invalid_counts_and_inconsistent_share_rejected(self):
        for count in (True,-1,121,1.0):
            with self.subTest(count=count),self.assertRaises(ValueError):CountConfig(exact_promoters=count).validate()
        with self.assertRaises(ValueError):CountConfig(exact_promoters=1,promoter_share=.025).validate()

    def test_serialization_reconstructs_exact_input(self):
        for n in range(4):
            cfg=initial_config(920003,n);restored=CountConfig(**asdict(cfg));restored.validate()
            self.assertEqual(restored.promoter_count(),n)

    def test_design_and_resume_are_fixed(self):
        p=plan();tasks=jobs(Path('/unused'),p)
        self.assertEqual(len(tasks),400);self.assertEqual(len({(t[1],t[3]) for t in tasks}),400)
        self.assertEqual(p['periods'],120);self.assertEqual(p['experience']['new_promoter_energy'],.6)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.assertEqual(prepare(root),prepare(root))
            (root/'design.json').write_text('{}')
            with self.assertRaises(ValueError):prepare(root)


class CriterionTests(unittest.TestCase):
    def test_steady_diffusion_can_qualify_without_acceleration(self):
        rows=trajectory([4]*6);res=classify_sustained(rows,480)
        self.assertTrue(res['ever']);self.assertEqual(res['first_confirmation'],6)
        self.assertFalse(classify_trajectory(rows)[2]['takeoff_ever'])

    def test_acceleration_is_not_sufficient_for_revised_volume(self):
        rows=trajectory([1,2,3,4,5,6])
        self.assertTrue(classify_trajectory(rows)[2]['takeoff_ever'])
        self.assertFalse(classify_sustained(rows,480)['ever'])

    def test_spike_and_incomplete_window_do_not_qualify(self):
        self.assertFalse(classify_sustained(trajectory([20,20,20,0,0,0]),480)['ever'])
        res=classify_sustained(trajectory([8]*5),480)
        self.assertFalse(res['ever']);self.assertEqual(res['complete_windows'],0)

    def test_each_substantive_requirement_can_block_label(self):
        for key in ('pressure','community','births','stock','external'):
            rows=trajectory([4]*6)
            if key=='pressure':rows[3]['net_pressure']=0
            if key=='community':
                for r in rows[1:]:r['purchase_communities']=[0]
            if key=='births':
                for r in rows[1:]:r.update(new_promoters=0,promoter_active=3)
            if key=='stock':
                for r in rows[1:]:r.update(new_promoters=1,deactivated_promoters=2,promoter_active=max(0,3-r['time']))
                # A coherent declining stock, then stable at zero.
                for r in rows[4:]:r.update(new_promoters=1,deactivated_promoters=1,promoter_active=0)
            if key=='external':
                rows[3]['external_promoters']=1
                for r in rows[3:]:r['promoter_active']+=1
            with self.subTest(key=key):self.assertFalse(classify_sustained(rows,480)['ever'])

    def test_threshold_boundary_and_sensitivity(self):
        self.assertFalse(classify_sustained(trajectory([4,4,4,4,4,3]),480)['ever'])
        self.assertTrue(classify_sustained(trajectory([4]*6),480)['ever'])
        self.assertFalse(classify_sustained(trajectory([4]*6),480,SustainedConfig(6,.1))['ever'])

    def test_observer_is_read_only_and_uses_no_future(self):
        rows=trajectory([4]*9);before=copy.deepcopy(rows)
        full=classify_sustained(rows,480)
        prefix=classify_sustained(rows[:7],480)
        self.assertEqual(rows,before);self.assertEqual(full['first_confirmation'],prefix['first_confirmation'])
        self.assertEqual(full['windows'][0],prefix['windows'][0])

    def test_reach_is_historical_and_missing_is_censored(self):
        rows=trajectory([8]*6)
        self.assertEqual(first_reach(rows,480,.1),6)
        self.assertIsNone(first_reach(rows,480,.25))


class ExportIntegrityTests(unittest.TestCase):
    def test_complete_agent_trace(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'history.csv'
            p.write_text('period,id,value\n0,0,x\n0,1,x\n1,0,x\n1,1,x\n')
            self.assertEqual(verify_agent_history(p,n=2,periods=1),4)

    def test_truncation_and_duplicate_rows_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'history.csv'
            for text in ('period,id,value\n0,0,x\n0,1,x\n1,0,x\n','period,id,value\n0,0,x\n0,1,x\n1,0,x\n1,0,x\n'):
                p.write_text(text)
                with self.assertRaises(ValueError):verify_agent_history(p,n=2,periods=1)


if __name__=='__main__':unittest.main()
