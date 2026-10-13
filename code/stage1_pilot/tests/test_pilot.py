"""Only new orchestration risks; M6's 229 tests remain the established gate."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from run_pilot import design,plan,prepare,tasks,canonical_hash,verified_model_hash


class PilotDesignTests(unittest.TestCase):
    def test_exact_design_and_new_energy_only_initial_cohort(self):
        p=plan(); self.assertEqual(len(design()),15)
        self.assertEqual(sum(x['group']=='baseline' for x in design()),11)
        self.assertEqual(len({x['scenario'] for x in design()}),15)
        self.assertEqual(p['experience']['new_promoter_energy'],.6)
        self.assertTrue(p['dynamics']['record_agents'])
        self.assertEqual(p['model_version'],'0.6.0-m6')

    def test_unique_run_ids_and_paired_seed_matrix(self):
        jobs=tasks(Path('/tmp/unused'),plan())
        self.assertEqual(len(jobs),150)
        self.assertEqual(len({(r,s['scenario']) for _,r,_,s,_ in jobs}),150)
        for replicate in range(1,11):
            block=[x for x in jobs if x[1]==replicate]
            self.assertEqual(len(block),15); self.assertEqual(len({x[2] for x in block}),1)

    def test_prepare_resume_guard_preserves_plan(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp); first=prepare(out); second=prepare(out)
            self.assertEqual(canonical_hash(first),canonical_hash(second))
            (out/'design.json').write_text('{}')
            with self.assertRaises(ValueError): prepare(out)


if __name__=='__main__': unittest.main()
