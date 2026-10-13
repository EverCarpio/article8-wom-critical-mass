"""Energy arithmetic, scheduling, exclusive fatigue causes and reproducible exports."""
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
from unittest.mock import patch

from article8.config import Config
from article8.energy import EnergyConfig, EnergySimulation, energy_after
from article8.experience import ExperienceConfig, ExperienceSimulation
from article8.export import export_energy_simulation, verify_export
from article8.model import Experience, WOM, initialize
from article8.positive import PositiveConfig
from test_m2 import fixture, accept, reject_purchase
from test_m3 import chain, CERTAIN


def star_sim(targets=3, initial_energy=1, periods=4, opportunities=2,
             energy=EnergyConfig(), draw=accept, experience=CERTAIN):
    initial, roots, targets = fixture(target_count=targets)
    initial = initialize(replace(initial.config, positive_energy=initial_energy), initial.environment)
    return (EnergySimulation(initial, PositiveConfig(periods=periods, opportunities=opportunities),
                             experience, energy, draw), roots[0], targets)


class EnergyRuleTests(unittest.TestCase):
    def test_defaults_match_specification(self):
        self.assertEqual(asdict(EnergyConfig()), {'decay': .06, 'message_cost': .04})

    def test_hand_calculated_decay_plus_message_cost(self):
        self.assertAlmostEqual(energy_after(.6, 2), .484)
        self.assertAlmostEqual(energy_after(.6, 0), .564)

    def test_clipping_and_parameter_extremes(self):
        self.assertEqual(energy_after(.1, 2, EnergyConfig(decay=0, message_cost=.1)), 0)
        self.assertEqual(energy_after(.6, 0, EnergyConfig(decay=1)), 0)
        self.assertEqual(energy_after(.6, 2, EnergyConfig(decay=0, message_cost=0)), .6)

    def test_invalid_configuration_and_inputs_rejected(self):
        for key in ('decay', 'message_cost'):
            for value in (-.01, 1.01, math.nan, math.inf, True, '0.06'):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    replace(EnergyConfig(), **{key: value}).validate()
        for energy, messages in ((math.nan, 1), (-.1, 1), (1.1, 1), (True, 1), (.6, -1), (.6, True), (.6, 1.5)):
            with self.assertRaises(ValueError):
                energy_after(energy, messages)


class TimingAndFatigueTests(unittest.TestCase):
    def test_all_opportunities_use_start_energy_even_when_cost_exceeds_it(self):
        def draw(agent, period, mechanism, slot):
            return .075 if mechanism == 'positive_opportunity' else .99 if mechanism == 'purchase' else 0
        sim, root, _ = star_sim(initial_energy=.1, periods=1, energy=EnergyConfig(0, .1), draw=draw)
        sim.run()
        self.assertEqual(len(sim.events), 2)  # p=.8*.1=.08 for BOTH slots.
        self.assertTrue(all(e['sender_energy'] == .1 for e in sim.events))
        self.assertEqual(sim.agents[root].positive_energy, 0)
        self.assertEqual(sim.agents[root].inactivity_reasons, ('energy_exhausted',))
        row = sim.energy_updates[0]
        self.assertEqual(row['message_cost_requested'], .2)
        self.assertEqual(row['realized_loss'], .1)

    def test_failed_opportunities_cost_no_messages_but_time_still_decays(self):
        def draw(agent, period, mechanism, slot):
            return .99
        sim, root, _ = star_sim(periods=1, draw=draw)
        sim.run()
        self.assertFalse(sim.events)
        self.assertEqual(sim.energy_updates[0]['messages_sent'], 0)
        self.assertEqual(sim.energy_updates[0]['message_cost_requested'], 0)
        self.assertAlmostEqual(sim.agents[root].positive_energy, .94)

    def test_zero_opportunities_still_decay_active_energy(self):
        sim, root, _ = star_sim(periods=2, opportunities=0)
        sim.run()
        self.assertAlmostEqual(sim.agents[root].positive_energy, .94 ** 2)
        self.assertEqual(len(sim.energy_updates), 2)
        self.assertFalse(sim.events)

    def test_cost_counts_only_actual_messages_when_contacts_run_out(self):
        sim, root, _ = star_sim(targets=1, periods=1)
        sim.run()
        self.assertEqual(sim.energy_updates[0]['messages_sent'], 1)
        self.assertAlmostEqual(sim.agents[root].positive_energy, .9)
        self.assertEqual(sim.agents[root].inactivity_reasons, ('contacts_exhausted',))

    def test_rejection_adds_no_extra_cost_and_purchase_gives_no_energy_reward(self):
        accepted, root, _ = star_sim(targets=3, periods=1, opportunities=1, draw=accept)
        rejected, _, _ = star_sim(targets=3, periods=1, opportunities=1, draw=reject_purchase)
        accepted.run(); rejected.run()
        self.assertNotEqual(accepted.decisions[0]['adopted'], rejected.decisions[0]['adopted'])
        self.assertEqual(accepted.agents[root].positive_energy, rejected.agents[root].positive_energy)
        self.assertAlmostEqual(accepted.agents[root].positive_energy, .9)

    def test_exact_threshold_deactivates_and_just_above_remains_active(self):
        for initial_energy, expected_wom in ((.1, WOM.PROMOTER_FATIGUED), (.100001, WOM.PROMOTER_ACTIVE)):
            sim, root, _ = star_sim(initial_energy=initial_energy, periods=1, opportunities=0,
                                     energy=EnergyConfig(.5, 0))
            sim.run()
            self.assertEqual(sim.agents[root].wom, expected_wom)
            if initial_energy == .1:
                self.assertEqual(sim.agents[root].positive_energy, .05)
                self.assertEqual(sim.agents[root].inactivity_reasons, ('energy_exhausted',))

    def test_both_causes_are_recorded_without_double_counting_exits(self):
        sim, root, _ = star_sim(targets=1, initial_energy=.1, periods=2, energy=EnergyConfig(0, .1))
        sim.run()
        self.assertEqual(sim.agents[root].inactivity_reasons, ('energy_exhausted', 'contacts_exhausted'))
        row = sim.system[1]
        self.assertEqual(row['deactivated_promoters'], 1)
        self.assertEqual(row['deactivated_both'], 1)
        self.assertEqual(row['deactivated_energy_only'] + row['deactivated_contacts_only'], 0)
        self.assertEqual(row['deactivated_by_energy'], 1)
        self.assertEqual(row['deactivated_by_contacts'], 1)

    def test_fatigue_preserves_satisfaction_and_eligibility(self):
        sim, root, _ = star_sim(initial_energy=.1, periods=2, opportunities=0, energy=EnergyConfig(1, 0))
        sim.run()
        a = sim.agents[root]
        self.assertEqual(a.wom, WOM.PROMOTER_FATIGUED)
        self.assertEqual(a.experience, Experience.SATISFIED)
        self.assertEqual(a.satisfaction, 1)
        self.assertTrue(a.positive_eligible)

    def test_energy_freezes_after_contact_deactivation(self):
        sim, root, _ = star_sim(targets=1, periods=8)
        sim.run()
        self.assertAlmostEqual(sim.agents[root].positive_energy, .9)
        self.assertEqual(sum(r['agent'] == root for r in sim.energy_updates), 1)
        history = [r for r in sim.agent_history if r['id'] == root and r['period'] >= 1]
        self.assertTrue(all(r['positive_energy'] == sim.agents[root].positive_energy for r in history))
        self.assertEqual(sim.system[-1]['positive_energy_active'], 0)
        self.assertGreater(sim.system[-1]['positive_energy_total'], 0)

    def test_energy_fatigue_freezes_and_never_reactivates_despite_contacts(self):
        sim, root, _ = star_sim(initial_energy=.1, periods=8, opportunities=0, energy=EnergyConfig(.5, 0))
        sim.run()
        self.assertEqual(sim.agents[root].positive_energy, .05)
        self.assertEqual(sim.agents[root].deactivation_time, 1)
        self.assertEqual(len(sim.energy_updates), 1)
        self.assertTrue(sim.state.eligible_contacts(root, 'positive'))
        self.assertTrue(all(r['new_promoters'] == 0 for r in sim.system))

    def test_initially_inactive_promoters_are_never_charged(self):
        for energy in (0, .05):
            sim, root, _ = star_sim(initial_energy=energy, periods=4)
            sim.run()
            self.assertEqual(sim.agents[root].positive_energy, energy)
            self.assertFalse(sim.energy_updates)
            self.assertEqual(sum(r['deactivated_promoters'] for r in sim.system), 0)
        cfg = Config(negative_wom_enabled=False, p_within=0, p_between=0)
        sim = EnergySimulation(initialize(cfg), PositiveConfig(periods=4, record_agents=False)).run()
        self.assertFalse(sim.energy_updates)
        self.assertEqual(sim.system[0]['positive_energy_total'], sim.system[-1]['positive_energy_total'])

    def test_new_promoter_has_no_decay_before_activation_and_is_charged_on_activation(self):
        initial, _, targets = chain()
        sim = EnergySimulation(initial, PositiveConfig(periods=3, opportunities=1), CERTAIN,
                               EnergyConfig(.5, .04), accept)
        sim.run(until=2)
        self.assertEqual(sim.agents[targets[0]].positive_energy, .6)
        self.assertFalse(any(r['agent'] == targets[0] for r in sim.energy_updates))
        sim.run()
        row = next(r for r in sim.energy_updates if r['agent'] == targets[0])
        self.assertEqual(row['energy_before'], .6)
        self.assertAlmostEqual(row['energy_after'], .26)
        self.assertTrue(row['activated_this_period'])
        self.assertEqual(row['period'], 3)

    def test_child_activates_after_parent_energy_reaches_zero(self):
        initial, root, targets = chain()
        sim = EnergySimulation(initial, PositiveConfig(periods=5, opportunities=1), CERTAIN,
                               EnergyConfig(0, 1), accept).run()
        self.assertEqual(sim.agents[root].positive_energy, 0)
        self.assertEqual(sim.agents[root].deactivation_time, 1)
        self.assertEqual(sim.agents[targets[0]].activation_time, 3)
        self.assertEqual(sim.agents[targets[1]].generation, 2)
        self.assertEqual(sim.agents[targets[2]].purchase_time, 5)

    def test_blocked_potential_energy_is_frozen_without_update(self):
        initial, _, targets = chain()
        sim = EnergySimulation(initial, PositiveConfig(periods=6, opportunities=1),
                               replace(CERTAIN, new_promoter_energy=.05), EnergyConfig(), accept).run()
        a = sim.agents[targets[0]]
        self.assertEqual(a.wom, WOM.PROMOTER_POTENTIAL)
        self.assertEqual(a.positive_energy, .05)
        self.assertFalse(any(r['agent'] == a.id for r in sim.energy_updates))
        self.assertEqual(len(sim.activation_events), 1)

    def test_cause_is_measured_at_deactivation_and_not_changed_later(self):
        initial, roots, targets = fixture(two_promoters=True, target_count=2)
        initial = initialize(replace(initial.config, positive_energy=.1), initial.environment)
        def draw(agent, period, mechanism, slot):
            if agent == roots[1] and period == 1 and mechanism == 'positive_opportunity':
                return .99
            return 0
        sim = EnergySimulation(initial, PositiveConfig(periods=4, opportunities=1), CERTAIN,
                               EnergyConfig(0, .1), draw).run()
        first = sim.agents[roots[0]]
        self.assertFalse(sim.state.eligible_contacts(first.id, 'positive'))
        self.assertEqual(first.inactivity_reasons, ('energy_exhausted',))
        row = next(r for r in sim.energy_updates if r['agent'] == first.id)
        self.assertEqual(row['remaining_contacts'], 1)
        self.assertFalse(row['contacts_exhausted'])

    def test_declining_energy_changes_next_period_opportunity_probability(self):
        def draw(agent, period, mechanism, slot):
            return .3 if mechanism == 'positive_opportunity' else .99 if mechanism == 'purchase' else 0
        sim, root, _ = star_sim(targets=4, periods=4, opportunities=1, energy=EnergyConfig(.5, 0), draw=draw)
        sim.run()
        self.assertEqual([e['period'] for e in sim.events], [1, 2])
        self.assertEqual([r['messages_sent'] for r in sim.energy_updates], [1, 1, 0, 0])
        self.assertEqual(sim.agents[root].positive_energy, .0625)

    def test_inactive_detractors_and_nonpromoters_keep_their_energy(self):
        sim = EnergySimulation(dynamics=PositiveConfig(periods=3, record_agents=False)).run()
        self.assertTrue(any(a.initial_detractor for a in sim.agents))
        for a, old in zip(sim.agents, sim.initial.agents):
            self.assertEqual(a.negative_energy, old.negative_energy)
            if a.initial_customer and not a.initial_promoter:
                self.assertEqual(a.positive_energy, 0)
        self.assertEqual(sum(r['negative_events'] for r in sim.system), 0)


class EnergyIntegrityTests(unittest.TestCase):
    def test_disabling_decay_and_cost_exactly_recovers_m3(self):
        dyn = PositiveConfig(periods=10, record_agents=False)
        m3 = ExperienceSimulation(dynamics=dyn).run()
        m4 = EnergySimulation(dynamics=dyn, energy=EnergyConfig(0, 0)).run()
        for key in ('agents', 'events', 'decisions', 'experience_events', 'activation_events'):
            self.assertEqual(getattr(m3, key), getattr(m4, key), key)
        for a, b in zip(m3.system, m4.system):
            self.assertEqual({k:v for k,v in a.items() if k != 'diffusion_class'},
                             {k:b[k] for k in a if k != 'diffusion_class'})

    def test_reverse_sender_order_keeps_all_ledgers_identical(self):
        dyn = PositiveConfig(periods=12, record_agents=False)
        a = EnergySimulation(dynamics=dyn).run()
        b = EnergySimulation(dynamics=dyn)
        for _ in range(dyn.periods):
            b.step(list(reversed(b.next_sender_ids())))
        b.validate()
        for key in ('events', 'energy_updates', 'experience_events', 'activation_events', 'system', 'agents'):
            self.assertEqual(getattr(a, key), getattr(b, key), key)

    def test_chunked_run_and_history_setting_do_not_change_dynamics(self):
        initial, _, _ = chain()
        a = EnergySimulation(initial, PositiveConfig(periods=8, opportunities=1), CERTAIN, draw=accept).run()
        b = EnergySimulation(initial, PositiveConfig(periods=8, opportunities=1, record_agents=False), CERTAIN, draw=accept)
        b.run(until=2).run(until=3).run()
        self.assertEqual(a.energy_updates, b.energy_updates)
        self.assertEqual(a.system, b.system)
        self.assertEqual(a.agents, b.agents)
        self.assertFalse(b.agent_history)

    def test_energy_balance_includes_new_potential_endowments_and_clipping(self):
        initial, _, _ = chain()
        sim = EnergySimulation(initial, PositiveConfig(periods=8, opportunities=1), CERTAIN,
                               EnergyConfig(.06, 1), accept).run()
        total = sim.system[0]['positive_energy_total']
        for row in sim.system[1:]:
            total += row['positive_energy_assigned'] - row['positive_energy_loss']
            self.assertAlmostEqual(total, row['positive_energy_total'])
            self.assertEqual(row['deactivated_promoters'], row['deactivated_energy_only'] +
                             row['deactivated_contacts_only'] + row['deactivated_both'])
        self.assertTrue(any(r['message_cost_requested'] > r['energy_after_decay'] for r in sim.energy_updates))

    def test_failure_after_energy_update_rolls_back_entire_period(self):
        sim, _, _ = star_sim(periods=1)
        before = deepcopy(sim.state)
        with patch.object(sim, '_system_row', side_effect=ValueError('injected post-close failure')):
            with self.assertRaises(ValueError):
                sim.step()
        self.assertEqual(sim.state, before)
        self.assertFalse(sim.energy_updates or sim.events or sim.decisions)
        self.assertEqual(len(sim.system), 1)
        sim.validate()
        sim.run()
        self.assertTrue(sim.energy_updates)

    def test_corrupt_energy_equation_missing_period_or_cause_detected(self):
        def wrong_end(s):
            s.energy_updates[0]['energy_after'] += .1
        def missing(s):
            s.energy_updates.pop(0)
        def repeated(s):
            s.energy_updates.append(dict(s.energy_updates[0]))
        def wrong_cause(s):
            s.energy_updates[0]['energy_exhausted'] = True
        def changed_frozen_energy(s):
            s.agents[s.energy_updates[0]['agent']].positive_energy += .001
        def wrong_system(s):
            s.system[1]['positive_energy_total'] += .1
        for corrupt in (wrong_end, missing, repeated, wrong_cause, changed_frozen_energy, wrong_system):
            with self.subTest(corrupt=corrupt.__name__):
                sim, _, _ = star_sim(targets=1)
                sim.run()
                corrupt(sim)
                with self.assertRaises(ValueError):
                    sim.validate()

    def test_event_must_record_start_energy_not_final_energy(self):
        sim, root, _ = star_sim(periods=1)
        sim.run()
        sim.events[0]['sender_energy'] = sim.agents[root].positive_energy
        with self.assertRaises(ValueError):
            sim.validate()

    def test_zero_horizon_zero_sources_and_negative_guard(self):
        zero, _, _ = star_sim(periods=0)
        zero.run()
        self.assertFalse(zero.energy_updates)
        with self.assertRaises(ValueError):
            zero.step()
        cfg = Config(negative_wom_enabled=False, promoter_share=0)
        no_sources = EnergySimulation(initialize(cfg), PositiveConfig(periods=4, record_agents=False)).run()
        self.assertFalse(no_sources.energy_updates or no_sources.events)
        self.assertEqual(no_sources.summary()['positive_energy_total'], 0)
        with self.assertRaises(ValueError):
            EnergySimulation(initialize(Config()))

    def test_initial_state_is_not_modified(self):
        initial, _, _ = chain()
        old = deepcopy(initial)
        EnergySimulation(initial, PositiveConfig(periods=6), CERTAIN, draw=accept).run()
        self.assertEqual(initial, old)


class EnergyExportTests(unittest.TestCase):
    def test_energy_and_deactivation_ledgers_reconcile(self):
        sim, _, _ = star_sim(targets=1, initial_energy=.1, energy=EnergyConfig(0, .1))
        sim.run()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_energy_simulation(sim, root)
            verify_export(root)
            with (root / 'energy_period.csv').open() as f:
                updates = list(csv.DictReader(f))
            with (root / 'deactivation_events.csv').open() as f:
                exits = list(csv.DictReader(f))
            self.assertEqual(len(updates), len(sim.energy_updates))
            self.assertEqual(len(exits), sum(r['deactivated_promoters'] for r in sim.system))
            self.assertEqual(exits[0]['energy_exhausted'], 'True')
            self.assertEqual(exits[0]['contacts_exhausted'], 'True')
            self.assertIn('M4', json.loads((root / 'manifest.json').read_text())['scope'])

    def test_configuration_export_recreates_all_ledgers(self):
        a = EnergySimulation(dynamics=PositiveConfig(periods=8, record_agents=False), energy=EnergyConfig(.12, .08)).run()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            export_energy_simulation(a, root)
            def read(name):
                return json.loads((root / name).read_text())
            b = EnergySimulation(initialize(Config(**read('initial_state/config.json'))),
                                 PositiveConfig(**read('dynamics_config.json')),
                                 ExperienceConfig(**read('experience_config.json')),
                                 EnergyConfig(**read('energy_config.json'))).run()
            for key in ('events', 'energy_updates', 'experience_events', 'activation_events', 'system'):
                self.assertEqual(getattr(a, key), getattr(b, key), key)

    def test_empty_ledgers_headers_and_no_overwrite(self):
        sim, _, _ = star_sim(periods=0)
        sim.run()
        with tempfile.TemporaryDirectory() as tmp:
            export_energy_simulation(sim, tmp)
            for name in ('energy_period.csv', 'deactivation_events.csv'):
                self.assertEqual(len((Path(tmp) / name).read_text().splitlines()), 1)
            with self.assertRaises(FileExistsError):
                export_energy_simulation(sim, tmp)

    def test_energy_ledger_integrity_is_checked(self):
        sim, _, _ = star_sim(periods=1)
        sim.run()
        with tempfile.TemporaryDirectory() as tmp:
            export_energy_simulation(sim, tmp)
            (Path(tmp) / 'energy_period.csv').write_text('altered')
            with self.assertRaises(ValueError):
                verify_export(tmp)

    def test_cli_byte_identical_between_hash_seeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / 'one', Path(tmp) / 'two']
            for path, seed in zip(paths, ('22', '83')):
                run = subprocess.run([sys.executable, '-m', 'article8', '--mode', 'energy', '--negative-off',
                                      '--periods', '6', '--no-agent-history', '--out', str(path)],
                                     env={**os.environ, 'PYTHONHASHSEED': seed}, capture_output=True, text=True, check=True)
                self.assertTrue(json.loads(run.stdout)['energy_dynamics_enabled'])
            contents = [{str(p.relative_to(path)): p.read_bytes() for p in path.rglob('*') if p.is_file()} for path in paths]
            self.assertEqual(contents[0], contents[1])

    def test_cli_energy_config_and_mode_guard(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = Path(tmp) / 'energy.json'
            config.write_text(json.dumps(asdict(EnergyConfig(1, 0))))
            args = [sys.executable, '-m', 'article8', '--negative-off', '--periods', '2', '--no-agent-history',
                    '--energy-config', str(config), '--out', str(Path(tmp) / 'run')]
            for mode in ('initial', 'positive', 'experience'):
                bad = subprocess.run(args + ['--mode', mode], capture_output=True, text=True)
                self.assertNotEqual(bad.returncode, 0)
            good = subprocess.run(args + ['--mode', 'energy'], capture_output=True, text=True, check=True)
            self.assertEqual(json.loads(good.stdout)['cumulative_deactivated_by_energy'], 18)


if __name__ == '__main__':
    unittest.main(verbosity=2)
