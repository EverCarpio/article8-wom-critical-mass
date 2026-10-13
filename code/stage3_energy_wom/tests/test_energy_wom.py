from dataclasses import asdict
import json
from pathlib import Path
import sys
import tempfile
import tarfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import run_energy_wom as run
from refined import CountConfig
from article8.model import initialize
from article8.export import environment_fingerprint,sha256_file
from article8.mixed import MixedSimulation,mixed_adoption_probability
from article8.positive import PositiveConfig
from article8.experience import ExperienceConfig
from archive_runs import verify_archive,verify_saved

class FactorialTests(unittest.TestCase):
    def test_paired_environments_and_energy_only_initial_promoters(self):
        states=[initialize(run.initial_config(930001,s['count'],s['positive_energy'],s['negative_weight'])) for s in run.scenarios()]
        self.assertEqual(len({environment_fingerprint(s) for s in states}),1)
        sets={}
        for s in states:
            ids={a.id for a in s.agents if a.initial_promoter}
            self.assertEqual(len(ids),s.config.exact_promoters)
            self.assertTrue(all(s.agents[i].positive_energy==s.config.positive_energy for i in ids))
            sets.setdefault(s.config.exact_promoters,ids)
            self.assertEqual(sets[s.config.exact_promoters],ids)
        self.assertTrue(sets[1]<sets[2]);self.assertEqual(ExperienceConfig().new_promoter_energy,.6)

    def test_lambda_penalty_and_net_pressure_wiring(self):
        probs=[mixed_adoption_probability(.5,.5,1.,2.,True,weight=w) for w in run.WEIGHTS]
        self.assertGreater(probs[0],probs[1]);self.assertGreater(probs[1],probs[2])
        self.assertEqual(probs[0],mixed_adoption_probability(.5,.5,1.,0.,True,weight=1))
        for w in run.WEIGHTS:
            sim=MixedSimulation(initialize(run.initial_config(930002,1,.6,w)),PositiveConfig(periods=8)).run()
            for row in sim.system:
                self.assertAlmostEqual(row['net_pressure'],row['positive_capacity']-w*row['negative_capacity'])
            self.assertTrue(any(e['sign']=='negative' for e in sim.events))

    def test_baseline_equals_previous_driver(self):
        from run_refined import initial_config
        a=MixedSimulation(initialize(initial_config(930003,2)),PositiveConfig(periods=15)).run()
        b=MixedSimulation(initialize(run.initial_config(930003,2,.6,1)),PositiveConfig(periods=15)).run()
        self.assertEqual(a.system,b.system);self.assertEqual(a.events,b.events)
        self.assertEqual(a.agent_history,b.agent_history)

    def test_factorial_has_all_pairs_and_frozen_plan(self):
        p=run.plan();self.assertEqual(len(run.jobs(Path('/unused'),p)),1800)
        self.assertEqual(len(run.scenarios()),18);self.assertEqual(len(set(run.SEEDS)),100)
        self.assertEqual(p['dynamics']['periods'],120)
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.assertEqual(run.prepare(root),run.prepare(root))
            (root/'design.json').write_text('{}')
            with self.assertRaises(ValueError):run.prepare(root)

    def test_serialization_keeps_count_and_parameters(self):
        for s in run.scenarios():
            c=run.initial_config(930004,s['count'],s['positive_energy'],s['negative_weight'])
            self.assertEqual(CountConfig(**json.loads(json.dumps(asdict(c)))),c)
            c.validate()

    def test_full_export_archive_resume_and_corruption(self):
        with tempfile.TemporaryDirectory(prefix='article8_test_') as tmp:
            out=Path(tmp);s=run.scenarios()[0];task=(str(out),1,930005,s,'test-only')
            row=run.run_one(task);self.assertEqual(row['agent_period_rows'],72600)
            self.assertEqual(row['verified_agent_period_rows'],72600)
            self.assertEqual(run.run_one(task),row)
            self.assertFalse((out/'work'/row['run_id']).exists())
            path=out/'archives'/f"{row['run_id']}.tar.xz"
            data=path.read_bytes();path.write_bytes(data[:-100])
            with self.assertRaises(ValueError):verify_saved(out,row['run_id'])
            with self.assertRaises((ValueError,EOFError,tarfile.ReadError)):verify_archive(path)

if __name__=='__main__':unittest.main()
