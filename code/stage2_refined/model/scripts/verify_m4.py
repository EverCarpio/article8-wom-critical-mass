"""Verify M1–M4 plus 20 pairs with/without energy loss (40 diagnostic runs)."""
import argparse
from datetime import datetime, timezone
from dataclasses import replace
import io
import json
import math
import os
from pathlib import Path
import platform
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from article8 import __version__
from article8.config import Config
from article8.energy import EnergyConfig, EnergySimulation
from article8.export import environment_fingerprint, export_energy_simulation, verify_export, write_csv, write_json
from article8.model import initialize, make_environment
from article8.positive import PositiveConfig
from verify_m1 import RecordedResult, require


def verify(out):
    if out.exists() and (not out.is_dir() or any(out.iterdir())):
        raise FileExistsError("Verification output must be new or empty")
    out.mkdir(parents=True, exist_ok=True)
    log = io.StringIO()
    suite = unittest.TestSuite(unittest.defaultTestLoader.discover(str(ROOT / 'tests'), pattern=f'test_m{m}.py')
                               for m in range(1,5))
    result = unittest.TextTestRunner(stream=log, verbosity=2, resultclass=RecordedResult).run(suite)
    (out / 'unit_tests.log').write_text(log.getvalue(), encoding='utf-8')
    write_json(out / 'unit_tests.json', {'tests_run': result.testsRun, 'failures': len(result.failures),
                                       'errors': len(result.errors), 'skipped': len(result.skipped),
                                       'successful': result.wasSuccessful(), 'tests': result.records})
    require(result.wasSuccessful(), 'Unit tests failed')
    seeds = list(range(20260925, 20260935))
    conditions = [('baseline_energy', EnergyConfig()), ('no_energy_loss', EnergyConfig(0, 0))]
    runs, contrasts = [], []
    for seed in seeds:
        cfg = Config(seed=seed, negative_wom_enabled=False)
        env = make_environment(cfg)
        for distribution in ('distributed', 'concentrated'):
            initial = initialize(replace(cfg, distribution=distribution), env)
            pair = []
            for condition, energy in conditions:
                detailed = seed == seeds[0] and condition == 'baseline_energy'
                sim = EnergySimulation(initial, PositiveConfig(record_agents=detailed), energy=energy).run()
                s = sim.summary()
                require(len(sim.events) <= len(list(env.network.edges())), 'Finite-contact bound violated')
                require(all(0 <= a.positive_energy <= 1 for a in sim.agents), 'Energy outside [0,1]')
                require(all(r['energy_after'] <= r['energy_before'] for r in sim.energy_updates), 'Energy recovery')
                require(all(r['population'] == r['customers'] + r['susceptibles'] == 600 for r in sim.system),
                        'Population not conserved')
                require(sum(r['messages_sent'] for r in sim.energy_updates) == len(sim.events), 'Message cost mismatch')
                if condition == 'no_energy_loss':
                    require(s['cumulative_positive_energy_loss'] == 0 and s['cumulative_deactivated_by_energy'] == 0,
                            'Energy loss in control condition')
                if detailed:
                    path = out / 'examples' / distribution
                    export_energy_simulation(sim, path)
                    verify_export(path)
                row = {'seed': seed, 'distribution': distribution, 'condition': condition,
                       'environment_sha256': environment_fingerprint(initial), 'periods': sim.time,
                       'promoter_share': .15, 'initial_promoters': 18, 'initial_energy': .6,
                       'new_promoter_energy': .6, 'decay': energy.decay, 'message_cost': energy.message_cost,
                       'new_purchases': s['cumulative_new_purchases'], 'final_customers': s['customers'],
                       'positive_events': len(sim.events), 'unique_recipients': s['cumulative_unique_positive_recipients'],
                       'new_promoters': s['cumulative_new_promoters'],
                       'blocked_activations': s['cumulative_blocked_activations'],
                       'max_generation': s['max_promoter_generation'], 'final_active_promoters': s['promoter_active'],
                       'energy_only_exits': s['cumulative_deactivated_energy_only'],
                       'contacts_only_exits': s['cumulative_deactivated_contacts_only'],
                       'both_causes_exits': s['cumulative_deactivated_both'],
                       'energy_period_records': len(sim.energy_updates),
                       'total_energy_loss': s['cumulative_positive_energy_loss'],
                       'final_total_positive_energy': s['positive_energy_total'],
                       'final_active_positive_energy': s['positive_energy_active'],
                       'final_mean_active_positive_energy': s['mean_positive_energy_active'],
                       'pending_experience': s['pending_experience_customers'],
                       'pending_activation': s['pending_activation_promoters'],
                       'negative_events': sum(r['negative_events'] for r in sim.system),
                       'invariants_passed': True, 'classification': 'not_evaluated_m4'}
                runs.append(row)
                pair.append(row)
            a, b = pair
            require(a['environment_sha256'] == b['environment_sha256'], 'Unpaired energy comparison')
            contrasts.append({'seed': seed, 'distribution': distribution,
                              'comparison': 'baseline_energy minus no_energy_loss',
                              'new_purchase_difference': a['new_purchases'] - b['new_purchases'],
                              'new_promoter_difference': a['new_promoters'] - b['new_promoters'],
                              'message_difference': a['positive_events'] - b['positive_events'],
                              'same_initial_state': True})
    write_csv(out / 'diagnostic_runs.csv', runs)
    write_csv(out / 'paired_differences.csv', contrasts)
    summary = {'module_version': __version__, 'python_version': platform.python_version(),
               'verified_at_utc': datetime.now(timezone.utc).isoformat(), 'unit_tests': result.testsRun,
               **{f'm{m}_tests': sum(x['test'].startswith(f'test_m{m}.') for x in result.records) for m in range(1,5)},
               'failures': len(result.failures), 'errors': len(result.errors),
               'diagnostic_trajectories': len(runs), 'diagnostic_pairs': len(contrasts),
               'periods_per_trajectory': 60, 'seeds': seeds, 'diagnostic_failures': 0,
               'full_model_pilot_runs': 0,
               'first_seed_examples': [r for r in runs if r['seed'] == seeds[0]],
               'condition_means': [
                   {'condition': condition, 'runs': sum(r['condition'] == condition for r in runs),
                    **{f'mean_{key}': math.fsum(r[key] for r in runs if r['condition'] == condition) / 20
                       for key in ('new_purchases', 'new_promoters', 'positive_events', 'energy_only_exits',
                                   'contacts_only_exits', 'both_causes_exits')}}
                   for condition, _ in conditions]}
    write_json(out / 'verification_summary.json', summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    out = parser.parse_args().out.resolve()
    os.chdir(ROOT)
    print(json.dumps(verify(out), indent=2))


if __name__ == '__main__':
    main()
