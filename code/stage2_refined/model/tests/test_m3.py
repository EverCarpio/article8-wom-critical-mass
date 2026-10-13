"""Hand-built temporal chains, boundary cases, accounting and M1/M2 regressions."""
from collections import Counter
from copy import deepcopy
import csv
from dataclasses import asdict, replace
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from article8.config import Config
from article8.experience import ExperienceConfig, ExperienceSimulation, assess_experience
from article8.export import export_experience_simulation, verify_export
from article8.model import Commercial, Experience, WOM, initialize
from article8.network import Network
from article8.positive import PositiveConfig, PositiveSimulation
from test_m2 import fixture, accept


CERTAIN = ExperienceConfig(quality=1, fit_effect=0, noise_amplitude=0,
                           promoter_disposition_probability=1)


def chain():
    """One initial promoter, four susceptibles in a path; one isolated customer."""
    initial, roots, targets = fixture(target_count=4)
    nodes = roots + targets
    adj = [set() for _ in initial.agents]
    for i, j in zip(nodes, nodes[1:]):
        adj[i].add(j); adj[j].add(i)
    env = replace(initial.environment,
                  network=Network(initial.environment.network.community,
                                  tuple(frozenset(x) for x in adj)))
    return initialize(initial.config, env), roots[0], targets


def chain_sim(periods=10, experience=CERTAIN, draw=accept, record_agents=True):
    initial, root, targets = chain()
    return (ExperienceSimulation(initial, PositiveConfig(periods=periods, opportunities=1,
                                                          record_agents=record_agents), experience, draw),
            root, targets)


class AssessmentTests(unittest.TestCase):
    def test_defaults_match_v01(self):
        self.assertEqual(asdict(ExperienceConfig()), {
            'quality': .7, 'fit_effect': .2, 'noise_amplitude': .4,
            'satisfied_threshold': .75, 'dissatisfied_threshold': .35,
            'promoter_disposition_probability': .8, 'new_promoter_energy': .6})

    def test_hand_calculated_satisfaction(self):
        noise, raw, value, category = assess_experience(.8, .75)
        self.assertAlmostEqual(noise, .2)
        self.assertAlmostEqual(raw, .96)
        self.assertAlmostEqual(value, .96)
        self.assertEqual(category, Experience.SATISFIED)

    def test_inclusive_thresholds_and_neutral_interior(self):
        for value, category in ((.75, Experience.SATISFIED), (.7499, Experience.NEUTRAL),
                                (.3501, Experience.NEUTRAL), (.35, Experience.DISSATISFIED)):
            with self.subTest(value=value):
                result = assess_experience(.5, .5, replace(CERTAIN, quality=value))
                self.assertEqual(result[2:], (value, category))

    def test_clipping_both_ends(self):
        low = assess_experience(0, 0, ExperienceConfig(quality=0))
        high = assess_experience(1, .99999, ExperienceConfig(quality=1))
        self.assertLess(low[1], 0)
        self.assertEqual(low[2], 0)
        self.assertGreater(high[1], 1)
        self.assertEqual(high[2], 1)

    def test_configuration_and_draw_validation(self):
        for field in asdict(CERTAIN):
            for value in (-.1, 1.1, math.nan, math.inf, True, '0.7'):
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    replace(CERTAIN, **{field: value}).validate()
        for low, high in ((.75, .75), (.8, .7)):
            with self.assertRaises(ValueError):
                replace(CERTAIN, dissatisfied_threshold=low, satisfied_threshold=high).validate()
        for fit, draw in ((-1, .5), (math.nan, .5), (.5, 1), (.5, -.1), (.5, math.inf)):
            with self.assertRaises(ValueError):
                assess_experience(fit, draw)


class LifecycleTests(unittest.TestCase):
    def test_exact_purchase_experience_activation_delays(self):
        sim, root, targets = chain_sim()
        child = targets[0]
        sim.run(until=1)
        self.assertEqual(sim.agents[child].commercial, Commercial.PENDING)
        self.assertIsNone(sim.agents[child].satisfaction)
        self.assertFalse(sim.experience_events)
        sim.run(until=2)
        a = sim.agents[child]
        self.assertEqual((a.purchase_time, a.experience_time, a.activation_time), (1, 2, None))
        self.assertEqual(a.wom, WOM.PROMOTER_POTENTIAL)
        self.assertIsNone(a.generation)
        self.assertEqual(sim.system[-1]['new_promoters'], 0)
        self.assertFalse(any(e['sender'] == child for e in sim.events))
        sim.run(until=3)
        self.assertEqual(sim.agents[child].activation_time, 3)
        self.assertEqual(sim.agents[targets[1]].purchase_time, 3)
        self.assertEqual(sim.system[-1]['new_promoters'], 1)
        self.assertEqual(sim.system[-1]['deactivated_promoters'], 1)

    def test_multiple_generations_after_parent_deactivation(self):
        sim, root, targets = chain_sim()
        sim.run()
        self.assertEqual([sim.agents[i].purchase_time for i in targets], [1, 3, 5, 7])
        self.assertEqual([sim.agents[i].experience_time for i in targets], [2, 4, 6, 8])
        self.assertEqual([sim.agents[i].generation for i in [root] + targets], [0, 1, 2, 3, None])
        self.assertEqual([sim.agents[i].parent for i in targets], [root] + targets[:-1])
        for parent, child in zip([root] + targets, targets):
            if sim.agents[child].activation_time is not None:
                self.assertLess(sim.agents[parent].deactivation_time, sim.agents[child].activation_time)
        self.assertTrue(all(r['initial_root'] == root for r in sim.lineage_rows()))
        self.assertEqual(sim.summary()['cumulative_new_promoters'], 3)

    def test_satisfied_does_not_guarantee_disposition(self):
        def draw(agent, period, mechanism, slot):
            return .8 if mechanism == 'positive_disposition' else 0
        sim, _, targets = chain_sim(experience=replace(CERTAIN, promoter_disposition_probability=.8), draw=draw)
        sim.run()
        child = sim.agents[targets[0]]
        self.assertEqual(child.experience, Experience.SATISFIED)
        self.assertEqual(child.wom, WOM.NONE)
        self.assertFalse(child.positive_eligible)
        self.assertFalse(sim.activation_events)
        self.assertEqual(len(sim.decisions), 1)

    def test_disposition_probability_zero_and_one(self):
        for p, expected in ((0, 0), (1, 3)):
            sim, _, _ = chain_sim(experience=replace(CERTAIN, promoter_disposition_probability=p))
            sim.run()
            self.assertEqual(sim.summary()['cumulative_new_promoters'], expected)

    def test_one_experience_and_one_disposition_draw_per_customer(self):
        calls = Counter()
        def draw(agent, period, mechanism, slot):
            calls[(agent, mechanism)] += 1
            return 0
        sim, _, targets = chain_sim(draw=draw)
        sim.run()
        for child in targets:
            self.assertEqual(calls[(child, 'experience')], 1)
            self.assertEqual(calls[(child, 'positive_disposition')], 1)
        self.assertEqual(len(sim.experience_events), 4)
        self.assertEqual(len(sim.activation_events), 4)

    def test_neutral_and_dissatisfied_customers_do_not_promote(self):
        for q, category in ((.5, Experience.NEUTRAL), (.2, Experience.DISSATISFIED)):
            calls = []
            def draw(agent, period, mechanism, slot):
                calls.append(mechanism)
                return 0
            sim, _, targets = chain_sim(experience=replace(CERTAIN, quality=q), draw=draw)
            sim.run()
            child = sim.agents[targets[0]]
            self.assertEqual(child.experience, category)
            self.assertEqual(child.wom, WOM.NONE)
            self.assertFalse(child.negative_eligible)
            self.assertNotIn('positive_disposition', calls)
            self.assertFalse(sim.activation_events)

    def test_initial_customers_are_not_reassessed(self):
        cfg = Config(negative_wom_enabled=False)
        sim = ExperienceSimulation(initialize(cfg), PositiveConfig(periods=6, record_agents=False)).run()
        evaluated = {e['agent'] for e in sim.experience_events}
        for a in sim.agents:
            if a.initial_customer:
                old = sim.initial.agents[a.id]
                self.assertEqual((a.satisfaction, a.experience, a.experience_time),
                                 (old.satisfaction, old.experience, 0))
                self.assertNotIn(a.id, evaluated)

    def test_new_energy_is_independent_of_initial_energy(self):
        initial, root, targets = chain()
        for initial_energy in (.2, 1):
            state = initialize(replace(initial.config, positive_energy=initial_energy), initial.environment)
            sim = ExperienceSimulation(state, PositiveConfig(periods=3, opportunities=1), CERTAIN, accept).run()
            self.assertEqual(sim.agents[root].positive_energy, initial_energy)
            self.assertEqual(sim.agents[targets[0]].positive_energy, .6)
            self.assertEqual(sim.activation_events[0]['positive_energy'], .6)

    def test_activation_energy_threshold_is_strict_and_not_retried(self):
        for energy, succeeds in ((0, False), (.05, False), (.050001, True)):
            sim, _, targets = chain_sim(experience=replace(CERTAIN, new_promoter_energy=energy))
            sim.run()
            a = sim.agents[targets[0]]
            attempts = [e for e in sim.activation_events if e['agent'] == a.id]
            self.assertEqual(len(attempts), 1)
            self.assertEqual(attempts[0]['activated'], succeeds)
            if not succeeds:
                self.assertEqual(a.wom, WOM.PROMOTER_POTENTIAL)
                self.assertEqual(a.inactivity_reasons, ('energy_exhausted',))
                self.assertIsNone(a.activation_time)
                self.assertIsNone(a.deactivation_time)
                self.assertEqual(sim.summary()['pending_activation_promoters'], 0)

    def test_no_contacts_leaves_potential_with_no_retry(self):
        initial, _, targets = fixture()
        sim = ExperienceSimulation(initial, PositiveConfig(periods=10), CERTAIN, accept).run()
        a = sim.agents[targets[0]]
        self.assertEqual(a.wom, WOM.PROMOTER_POTENTIAL)
        self.assertEqual(a.inactivity_reasons, ('contacts_exhausted',))
        self.assertEqual(len(sim.activation_events), 1)
        self.assertIsNone(a.generation)
        self.assertEqual(sim.system[3]['blocked_activations'], 1)

    def test_contacts_are_checked_at_activation_not_at_purchase(self):
        initial, _, targets = fixture(target_count=2)
        adj = [set(x) for x in initial.environment.network.neighbors]
        i, j = targets
        adj[i].add(j); adj[j].add(i)
        env = replace(initial.environment, network=Network(initial.environment.network.community,
                                                           tuple(frozenset(x) for x in adj)))
        initial = initialize(initial.config, env)
        sim = ExperienceSimulation(initial, PositiveConfig(periods=4), CERTAIN, accept).run()
        self.assertEqual([sim.agents[i].purchase_time for i in targets], [1, 1])
        self.assertEqual(len(sim.activation_events), 2)
        self.assertTrue(all(not e['activated'] and e['eligible_contacts'] == 0 for e in sim.activation_events))

    def test_both_activation_failure_reasons_are_retained(self):
        initial, _, targets = fixture()
        sim = ExperienceSimulation(initial, PositiveConfig(periods=4),
                                   replace(CERTAIN, new_promoter_energy=0), accept).run()
        self.assertEqual(sim.agents[targets[0]].inactivity_reasons,
                         ('energy_exhausted', 'contacts_exhausted'))

    def test_horizon_censors_experience_and_activation_separately(self):
        one, _, targets = chain_sim(periods=1)
        one.run()
        self.assertEqual(one.summary()['pending_experience_customers'], 1)
        self.assertEqual(one.summary()['pending_activation_promoters'], 0)
        self.assertFalse(one.experience_events)
        two, _, targets = chain_sim(periods=2)
        two.run()
        self.assertEqual(two.summary()['pending_experience_customers'], 0)
        self.assertEqual(two.summary()['pending_activation_promoters'], 1)
        self.assertEqual(two.summary()['cumulative_blocked_activations'], 0)
        self.assertEqual(two.lineage_rows()[0]['activation_status'], 'pending')
        self.assertIsNone(two.lineage_rows()[0]['generation'])

    def test_no_spontaneous_acquisition_without_sources(self):
        initial = initialize(Config(promoter_share=0, negative_wom_enabled=False))
        sim = ExperienceSimulation(initial, PositiveConfig(periods=5, record_agents=False), CERTAIN, accept).run()
        self.assertFalse(sim.events or sim.decisions or sim.experience_events or sim.activation_events)
        self.assertEqual(sim.summary()['customers'], 120)

    def test_contact_pairs_remain_unique_with_endogenous_senders(self):
        sim = ExperienceSimulation(dynamics=PositiveConfig(periods=16, record_agents=False)).run()
        pairs = [(e['sender'], e['receiver']) for e in sim.events]
        self.assertEqual(len(pairs), len(set(pairs)))
        self.assertTrue(any(not sim.agents[e['sender']].initial_promoter for e in sim.events))
        self.assertTrue(all(sim.agents[e['receiver']].purchase_time is None or
                            e['period'] <= sim.agents[e['receiver']].purchase_time for e in sim.events))


class ReproducibilityAndIntegrityTests(unittest.TestCase):
    def test_reverse_order_including_new_promoters_is_identical(self):
        dyn = PositiveConfig(periods=12, record_agents=False)
        normal = ExperienceSimulation(dynamics=dyn).run()
        reverse = ExperienceSimulation(dynamics=dyn)
        for _ in range(dyn.periods):
            reverse.step(list(reversed(reverse.next_sender_ids())))
        reverse.validate()
        for key in ('agents', 'events', 'decisions', 'experience_events', 'activation_events', 'system'):
            self.assertEqual(getattr(normal, key), getattr(reverse, key), key)

    def test_chunked_execution_matches_full_run(self):
        a, _, _ = chain_sim()
        b, _, _ = chain_sim()
        a.run()
        b.run(until=1).run(until=2).run(until=3).run()
        self.assertEqual(a.agent_history, b.agent_history)
        self.assertEqual(a.activation_events, b.activation_events)
        self.assertEqual(a.system, b.system)

    def test_recording_does_not_change_trajectory(self):
        a, _, _ = chain_sim(record_agents=True)
        b, _, _ = chain_sim(record_agents=False)
        a.run(); b.run()
        self.assertEqual(a.system, b.system)
        self.assertEqual(a.agents, b.agents)
        self.assertEqual(len(a.agent_history), 6 * 11)
        self.assertFalse(b.agent_history)

    def test_disabling_disposition_preserves_m2_wom_and_purchases(self):
        dyn = PositiveConfig(periods=8, record_agents=False)
        m2 = PositiveSimulation(dynamics=dyn).run()
        m3 = ExperienceSimulation(dynamics=dyn,
                                 experience=ExperienceConfig(promoter_disposition_probability=0)).run()
        self.assertEqual(m2.events, m3.events)
        self.assertEqual(m2.decisions, m3.decisions)
        self.assertTrue(m3.experience_events)

    def test_bad_experience_draw_rolls_back_whole_period(self):
        def draw(agent, period, mechanism, slot):
            return math.nan if mechanism == 'positive_disposition' else 0
        sim, _, _ = chain_sim(draw=draw)
        sim.run(until=1)
        before = deepcopy(sim.state)
        history = deepcopy(sim.agent_history)
        with self.assertRaises(ValueError):
            sim.step()
        self.assertEqual(sim.state, before)
        self.assertEqual(sim.agent_history, history)
        self.assertFalse(sim.experience_events)
        sim.validate()

    def test_bad_purchase_draw_after_activation_rolls_back_lifecycle(self):
        def draw(agent, period, mechanism, slot):
            return math.nan if period == 3 and mechanism == 'purchase' else 0
        sim, _, _ = chain_sim(draw=draw)
        sim.run(until=2)
        before = deepcopy(sim.state)
        with self.assertRaises(ValueError):
            sim.step()
        self.assertEqual(sim.state, before)
        self.assertFalse(sim.activation_events)
        sim.validate()

    def test_invalid_sender_order_does_not_commit_activation(self):
        sim, _, _ = chain_sim()
        sim.run(until=2)
        before = deepcopy(sim.state)
        with self.assertRaises(ValueError):
            sim.step([])
        self.assertEqual(sim.state, before)
        self.assertFalse(sim.activation_events)
        sim.step(sim.next_sender_ids())
        sim.validate()

    def test_zero_horizon_and_negative_wom_guard(self):
        sim, _, _ = chain_sim(periods=0)
        sim.run()
        self.assertEqual(len(sim.system), 1)
        with self.assertRaises(ValueError):
            sim.step()
        with self.assertRaises(ValueError):
            ExperienceSimulation(initialize(Config()))

    def test_initial_state_not_mutated(self):
        initial, _, _ = chain()
        before = deepcopy(initial)
        ExperienceSimulation(initial, PositiveConfig(periods=5), CERTAIN, accept).run()
        self.assertEqual(initial, before)

    def test_corrupt_lifecycle_and_genealogy_are_detected(self):
        def repeated_experience(s):
            s.experience_events.append(dict(s.experience_events[0]))
        def missing_activation(s):
            s.activation_events.pop()
        def wrong_generation(s):
            s.agents[s.activation_events[0]['agent']].generation = 77
        def wrong_satisfaction(s):
            s.agents[s.experience_events[0]['agent']].satisfaction = .9
        def wrong_flow(s):
            s.system[3]['new_promoters'] = 77
        for corrupt in (repeated_experience, missing_activation, wrong_generation, wrong_satisfaction, wrong_flow):
            with self.subTest(corrupt=corrupt.__name__):
                sim, _, _ = chain_sim()
                sim.run()
                corrupt(sim)
                with self.assertRaises(ValueError):
                    sim.validate()

    def test_active_stock_equals_initial_plus_entries_minus_exits(self):
        sim, _, _ = chain_sim()
        sim.run()
        active = 1
        for r in sim.system:
            active += r['new_promoters'] - r['deactivated_promoters']
            self.assertEqual(r['promoter_active'], active)
            self.assertEqual(r['customers'] + r['susceptibles'], 6)


class ExperienceExportTests(unittest.TestCase):
    def test_ledgers_and_lineage_reconcile(self):
        sim, _, _ = chain_sim()
        sim.run()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'run'
            export_experience_simulation(sim, path)
            verify_export(path)
            def read(name):
                with (path / name).open() as f:
                    return list(csv.DictReader(f))
            self.assertEqual(len(read('experience_events.csv')), 4)
            attempts = read('activation_events.csv')
            self.assertEqual(len(attempts), 4)
            self.assertEqual(sum(e['activated'] == 'True' for e in attempts), 3)
            self.assertEqual(len(read('lineage.csv')), len(read('purchases.csv')))
            self.assertEqual(read('lineage.csv')[-1]['activation_status'], 'blocked')
            manifest = json.loads((path / 'manifest.json').read_text())
            self.assertIn('M3', manifest['scope'])
            self.assertIn('experience_config.json', manifest['files_sha256'])

    def test_empty_ledgers_keep_headers(self):
        sim, _, _ = chain_sim(periods=0)
        sim.run()
        with tempfile.TemporaryDirectory() as tmp:
            export_experience_simulation(sim, tmp)
            for name in ('experience_events.csv', 'activation_events.csv', 'lineage.csv'):
                self.assertEqual(len((Path(tmp) / name).read_text().splitlines()), 1)

    def test_configuration_export_recreates_all_ledgers(self):
        a = ExperienceSimulation(dynamics=PositiveConfig(periods=10, record_agents=False)).run()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_experience_simulation(a, root)
            def read(name):
                return json.loads((root / name).read_text())
            b = ExperienceSimulation(initialize(Config(**read('initial_state/config.json'))),
                                     PositiveConfig(**read('dynamics_config.json')),
                                     ExperienceConfig(**read('experience_config.json'))).run()
            for key in ('events', 'decisions', 'experience_events', 'activation_events', 'system'):
                self.assertEqual(getattr(a, key), getattr(b, key), key)

    def test_cli_is_identical_across_process_hash_seeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / 'one', Path(tmp) / 'two']
            for path, seed in zip(paths, ('31', '92')):
                proc = subprocess.run([sys.executable, '-m', 'article8', '--mode', 'experience',
                                       '--negative-off', '--periods', '6', '--no-agent-history', '--out', str(path)],
                                      env={**os.environ, 'PYTHONHASHSEED': seed},
                                      capture_output=True, text=True, check=True)
                self.assertTrue(json.loads(proc.stdout)['new_promoter_formation_enabled'])
            contents = [{str(p.relative_to(path)): p.read_bytes() for p in path.rglob('*') if p.is_file()}
                        for path in paths]
            self.assertEqual(contents[0], contents[1])

    def test_experience_config_option_and_mode_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'experience.json'
            config.write_text(json.dumps(asdict(replace(CERTAIN, promoter_disposition_probability=0))))
            args = [sys.executable, '-m', 'article8', '--negative-off', '--periods', '3',
                    '--experience-config', str(config), '--out', str(Path(tmp) / 'run')]
            bad = subprocess.run(args + ['--mode', 'positive'], capture_output=True, text=True)
            self.assertNotEqual(bad.returncode, 0)
            good = subprocess.run(args + ['--mode', 'experience'], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(good.stdout)['cumulative_new_promoters'], 0)

    def test_no_overwrite_and_lifecycle_checksum_validation(self):
        sim, _, _ = chain_sim()
        sim.run()
        with tempfile.TemporaryDirectory() as tmp:
            export_experience_simulation(sim, tmp)
            with self.assertRaises(FileExistsError):
                export_experience_simulation(sim, tmp)
            (Path(tmp) / 'activation_events.csv').write_text('altered')
            with self.assertRaises(ValueError):
                verify_export(tmp)


if __name__ == '__main__':
    unittest.main(verbosity=2)
