"""Mechanistic fixtures and regression tests for positive WOM and purchase."""
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
from article8.export import export_positive_simulation, verify_export
from article8.model import Commercial, Experience, Traits, WOM, initialize, make_environment
from article8.network import Network
from article8.positive import PositiveConfig, PositiveSimulation, adoption_probability


def fixture(two_promoters=False, target_count=1):
    """Six people; one or two promoters linked only to known susceptible targets."""
    cfg = Config(n=6, communities=2, initial_customers=2, initial_detractors=0,
                 promoter_share=1.0 if two_promoters else .5, positive_energy=1,
                 negative_wom_enabled=False, p_within=1, p_between=1)
    env = make_environment(cfg)
    raw = initialize(cfg, env)
    senders = sorted(a.id for a in raw.agents if a.initial_promoter)
    targets = sorted(a.id for a in raw.agents if not a.initial_customer)[:target_count]
    adj = [set() for _ in range(6)]
    for i in senders:
        for j in targets:
            adj[i].add(j); adj[j].add(i)
    env = replace(env, network=Network(env.network.community, tuple(frozenset(x) for x in adj)),
                  traits=tuple(Traits(.5, .5, 1) for _ in range(6)))
    return initialize(cfg, env), senders, targets


def accept(agent, period, mechanism, slot):
    return 0.0


def reject_purchase(agent, period, mechanism, slot):
    return .999999 if mechanism == "purchase" else 0.0


class PositiveConfigTests(unittest.TestCase):
    def test_invalid_dynamics_rejected(self):
        for change in ({"periods": -1}, {"opportunities": True}, {"memory_retention": 1.1},
                       {"opportunity_factor": math.nan}, {"intercept": math.inf},
                       {"positive_coefficient": -1}, {"record_agents": 1}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                replace(PositiveConfig(), **change).validate()

    def test_negative_mechanism_must_be_explicitly_disabled(self):
        with self.assertRaises(ValueError):
            PositiveSimulation(initialize(Config()))

    def test_adoption_probability_matches_hand_calculation(self):
        expected = 1 / (1 + math.exp(-(-2 + 1.5*.5 + 1.5*.5 + 1.2*(1-math.exp(-2)))))
        self.assertAlmostEqual(adoption_probability(.5, .5, 2, True, PositiveConfig()), expected)

    def test_old_influence_cannot_open_purchase_gate(self):
        self.assertEqual(adoption_probability(1, 1, 1000, False, replace(PositiveConfig(), intercept=1000)), 0)

    def test_probability_bounded_monotone_and_numerically_stable(self):
        values = [adoption_probability(.5, .5, x, True, PositiveConfig()) for x in (0, .1, 1, 10, 1000)]
        self.assertEqual(values, sorted(values))
        self.assertTrue(all(0 <= x <= 1 for x in values))
        self.assertEqual(adoption_probability(.5, .5, 1, True, replace(PositiveConfig(), intercept=-1000)), 0)
        self.assertEqual(adoption_probability(.5, .5, 1, True, replace(PositiveConfig(), intercept=1000)), 1)


class ContactAndPurchaseTests(unittest.TestCase):
    def test_two_messages_one_receiver_one_purchase(self):
        initial, senders, targets = fixture(two_promoters=True)
        sim = PositiveSimulation(initial, PositiveConfig(periods=1, opportunities=1, opportunity_factor=1), accept).run()
        self.assertEqual(len(sim.events), 2)
        self.assertEqual(len(sim.decisions), 1)
        self.assertEqual(sim.decisions[0]["new_positive_messages"], 2)
        self.assertEqual(sim.system[-1]["new_purchases"], 1)
        self.assertEqual(sim.system[-1]["cumulative_unique_positive_recipients"], 1)
        self.assertEqual(sim.system[-1]["cumulative_positive_redundancy"], .5)
        self.assertEqual(sum(e["first_positive_reach"] for e in sim.events), 1)
        self.assertEqual(sim.agents[targets[0]].positive_memory, 2)
        self.assertTrue(all(e["receiver_positive_exposures_before_period"] == 0 for e in sim.events))

    def test_equal_credibility_attribution_uses_smallest_id(self):
        initial, senders, targets = fixture(two_promoters=True)
        sim = PositiveSimulation(initial, PositiveConfig(periods=1), accept).run()
        self.assertEqual(sim.agents[targets[0]].parent, min(senders))
        self.assertEqual(sum(e["credited_purchase_parent"] for e in sim.events), 1)

    def test_higher_credibility_attribution_precedes_id_tiebreak(self):
        initial, senders, targets = fixture(two_promoters=True)
        traits = list(initial.environment.traits)
        traits[min(senders)] = Traits(.5, .5, .6)
        env = replace(initial.environment, traits=tuple(traits))
        initial = initialize(initial.config, env)
        sim = PositiveSimulation(initial, PositiveConfig(periods=1), accept).run()
        self.assertEqual(sim.agents[targets[0]].parent, max(senders))

    def test_opportunity_budget_without_replacement(self):
        initial, senders, targets = fixture(target_count=3)
        sim = PositiveSimulation(initial, PositiveConfig(periods=5, opportunities=2, opportunity_factor=1), reject_purchase).run()
        self.assertEqual([r["positive_events"] for r in sim.system], [0, 2, 1, 0, 0, 0])
        self.assertEqual({e["receiver"] for e in sim.events}, set(targets))
        self.assertEqual(len({(e["sender"], e["receiver"]) for e in sim.events}), 3)

    def test_rejected_purchase_does_not_restore_sender_contact(self):
        initial, senders, targets = fixture()
        sim = PositiveSimulation(initial, PositiveConfig(periods=20), reject_purchase).run()
        self.assertEqual(len(sim.events), 1)
        self.assertEqual(len(sim.decisions), 1)
        self.assertEqual(sim.agents[targets[0]].commercial, Commercial.SUSCEPTIBLE)
        self.assertEqual(sim.agents[senders[0]].wom, WOM.PROMOTER_FATIGUED)
        self.assertEqual(sim.agents[senders[0]].inactivity_reasons, ("contacts_exhausted",))
        self.assertEqual(sim.agents[senders[0]].positive_energy, 1)

    def test_later_message_from_other_sender_can_trigger_purchase(self):
        initial, senders, targets = fixture(two_promoters=True)
        def draw(agent, period, mechanism, slot):
            if mechanism == "positive_opportunity":
                return 0 if (agent == senders[0] and period == 1) or (agent == senders[1] and period == 2) else .99
            if mechanism == "purchase":
                return .99 if period == 1 else 0
            return 0
        sim = PositiveSimulation(initial, PositiveConfig(periods=3, opportunities=1), draw).run()
        self.assertEqual(len(sim.events), 2)
        self.assertEqual([d["adopted"] for d in sim.decisions], [False, True])
        self.assertEqual(sim.decisions[1]["positive_memory_after"], 1.5)
        self.assertEqual(sim.agents[targets[0]].parent, senders[1])
        self.assertEqual(sim.agents[targets[0]].purchase_time, 2)
        self.assertEqual(sim.system[-1]["cumulative_unique_positive_recipients"], 1)

    def test_positive_memory_decays_without_spontaneous_purchase(self):
        initial, _, targets = fixture()
        def draw(agent, period, mechanism, slot):
            return .99 if mechanism == "purchase" and period == 1 else 0
        sim = PositiveSimulation(initial, PositiveConfig(periods=4, memory_retention=.5), draw).run()
        self.assertEqual(sim.agents[targets[0]].positive_memory, .125)
        self.assertEqual(len(sim.decisions), 1)
        self.assertEqual(sim.system[-1]["cumulative_new_purchases"], 0)

    def test_memory_zero_and_one_extremes(self):
        for rho, expected in ((0, 0), (1, 1)):
            initial, _, targets = fixture()
            sim = PositiveSimulation(initial, PositiveConfig(periods=3, memory_retention=rho), reject_purchase).run()
            self.assertEqual(sim.agents[targets[0]].positive_memory, expected)

    def test_purchase_blocks_all_later_contacts(self):
        initial, senders, targets = fixture(two_promoters=True)
        def draw(agent, period, mechanism, slot):
            if mechanism == "positive_opportunity" and agent == senders[1] and period == 1:
                return .99
            return 0
        sim = PositiveSimulation(initial, PositiveConfig(periods=4, opportunities=1), draw).run()
        self.assertEqual(len(sim.events), 1)
        self.assertEqual(len(sim.decisions), 1)
        self.assertEqual(sim.agents[targets[0]].purchase_time, 1)
        self.assertTrue(all(sim.agents[i].wom == WOM.PROMOTER_FATIGUED for i in senders))

    def test_new_customer_stays_pending_and_never_emits(self):
        sim = PositiveSimulation(dynamics=PositiveConfig(periods=10, record_agents=False), draw=accept).run()
        bought = [a for a in sim.agents if not a.initial_customer and a.purchase_time is not None]
        self.assertTrue(bought)
        for a in bought:
            self.assertEqual(a.commercial, Commercial.PENDING)
            self.assertEqual(a.experience, Experience.UNEVALUATED)
            self.assertIsNone(a.satisfaction)
            self.assertIsNone(a.experience_time)
            self.assertIsNone(a.generation)
            self.assertEqual(a.wom, WOM.NONE)
            self.assertFalse(a.contacted_positive)
        self.assertTrue(all(sim.agents[e["sender"]].initial_promoter for e in sim.events))

    def test_strict_purchase_threshold(self):
        initial, _, targets = fixture()
        p = adoption_probability(.5, .5, 1, True, PositiveConfig())
        def draw(agent, period, mechanism, slot):
            return p if mechanism == "purchase" else 0
        sim = PositiveSimulation(initial, PositiveConfig(periods=1), draw).run()
        self.assertFalse(sim.decisions[0]["adopted"])
        self.assertEqual(sim.agents[targets[0]].commercial, Commercial.SUSCEPTIBLE)

    def test_invalid_random_draw_fails_without_partial_commit(self):
        initial, _, _ = fixture()
        def bad(agent, period, mechanism, slot):
            return math.nan if mechanism == "purchase" else 0
        sim = PositiveSimulation(initial, PositiveConfig(periods=1), bad)
        before = deepcopy(sim.agents)
        with self.assertRaises(ValueError):
            sim.step()
        self.assertEqual(sim.agents, before)
        self.assertEqual(sim.time, 0)
        self.assertFalse(sim.events)


class BoundaryAndReproducibilityTests(unittest.TestCase):
    def test_zero_sources_energy_opportunities_and_contacts(self):
        cases = [(replace(Config(), negative_wom_enabled=False, promoter_share=0), PositiveConfig(periods=4)),
                 (replace(Config(), negative_wom_enabled=False, positive_energy=0), PositiveConfig(periods=4)),
                 (replace(Config(), negative_wom_enabled=False, p_within=0, p_between=0), PositiveConfig(periods=4)),
                 (replace(Config(), negative_wom_enabled=False, initial_customers=600), PositiveConfig(periods=4)),
                 (replace(Config(), negative_wom_enabled=False), PositiveConfig(periods=4, opportunities=0)),
                 (replace(Config(), negative_wom_enabled=False), PositiveConfig(periods=4, opportunity_factor=0))]
        for cfg, dyn in cases:
            with self.subTest(cfg=cfg, dyn=dyn):
                sim = PositiveSimulation(initialize(cfg), dyn, accept).run()
                self.assertFalse(sim.events)
                self.assertFalse(sim.decisions)
                self.assertEqual(sim.system[-1]["customers"], cfg.initial_customers)

    def test_no_intercommunity_contacts_when_bridges_absent(self):
        cfg = replace(Config(), negative_wom_enabled=False, p_between=0)
        sim = PositiveSimulation(initialize(cfg), PositiveConfig(periods=6, record_agents=False)).run()
        self.assertTrue(sim.events)
        self.assertTrue(all(e["sender_community"] == e["receiver_community"] for e in sim.events))

    def test_reversed_sender_order_gives_identical_events_decisions_states(self):
        cfg = replace(Config(), negative_wom_enabled=False)
        initial = initialize(cfg)
        a = PositiveSimulation(initial, PositiveConfig(periods=10, record_agents=False)).run()
        b = PositiveSimulation(initial, PositiveConfig(periods=10, record_agents=False))
        for _ in range(10):
            order = [x.id for x in b.agents if x.wom == WOM.PROMOTER_ACTIVE]
            b.step(list(reversed(order)))
        b.validate()
        self.assertEqual(a.events, b.events)
        self.assertEqual(a.decisions, b.decisions)
        self.assertEqual(a.system, b.system)
        self.assertEqual(a.agents, b.agents)

    def test_chunked_run_matches_contiguous_run(self):
        dyn = PositiveConfig(periods=8, record_agents=False)
        a = PositiveSimulation(dynamics=dyn).run()
        b = PositiveSimulation(dynamics=dyn).run(until=3).run()
        self.assertEqual(a.events, b.events)
        self.assertEqual(a.system, b.system)

    def test_recording_agent_history_does_not_change_dynamics(self):
        a = PositiveSimulation(dynamics=PositiveConfig(periods=3)).run()
        b = PositiveSimulation(dynamics=PositiveConfig(periods=3, record_agents=False)).run()
        self.assertEqual(a.events, b.events)
        self.assertEqual(a.system, b.system)
        self.assertEqual(len(a.agent_history), 600 * 4)
        self.assertFalse(b.agent_history)

    def test_initial_state_is_not_mutated(self):
        initial = initialize(Config(negative_wom_enabled=False))
        before = deepcopy(initial)
        PositiveSimulation(initial, PositiveConfig(periods=3, record_agents=False)).run()
        self.assertEqual(initial, before)

    def test_horizon_zero_and_invalid_orders(self):
        sim = PositiveSimulation(dynamics=PositiveConfig(periods=0)).run()
        self.assertEqual(len(sim.system), 1)
        with self.assertRaises(ValueError):
            sim.step()
        sim = PositiveSimulation(dynamics=PositiveConfig(periods=2))
        with self.assertRaises(ValueError):
            sim.step([])
        self.assertEqual(sim.time, 0)
        with self.assertRaises(ValueError):
            sim.run(until=3)

    def test_independent_run_recreates_same_ledger(self):
        a = PositiveSimulation(dynamics=PositiveConfig(periods=6, record_agents=False)).run()
        b = PositiveSimulation(dynamics=PositiveConfig(periods=6, record_agents=False)).run()
        self.assertEqual(a.events, b.events)
        self.assertEqual(a.decisions, b.decisions)

    def test_corrupted_event_or_state_detected(self):
        initial, _, _ = fixture()
        sim = PositiveSimulation(initial, PositiveConfig(periods=1), accept).run()
        sim.events.append(dict(sim.events[0]))
        with self.assertRaises(ValueError):
            sim.validate()
        sim = PositiveSimulation(initial, PositiveConfig(periods=1), accept).run()
        sim.agents[sim.events[0]["receiver"]].positive_exposures += 1
        with self.assertRaises(ValueError):
            sim.validate()


class PositiveExportTests(unittest.TestCase):
    def test_recover_csv_ledgers_and_reconcile(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            sim = PositiveSimulation(dynamics=PositiveConfig(periods=4)).run()
            export_positive_simulation(sim, root)
            verify_export(root)
            with (root / "purchases.csv").open() as f:
                purchases = list(csv.DictReader(f))
            with (root / "wom_events.csv").open() as f:
                events = list(csv.DictReader(f))
            with (root / "system_period.csv").open() as f:
                periods = list(csv.DictReader(f))
            self.assertEqual(len(purchases), len({r["receiver"] for r in purchases}))
            self.assertEqual(sum(int(r["new_purchases"]) for r in periods), len(purchases))
            self.assertEqual(sum(int(r["positive_events"]) for r in periods), len(events))
            with (root / "agent_period.csv").open() as f:
                self.assertEqual(len(list(csv.DictReader(f))), 600 * 5)

    def test_empty_ledgers_have_headers_and_undefined_ratios(self):
        with tempfile.TemporaryDirectory() as tmp:
            initial = initialize(Config(promoter_share=0, negative_wom_enabled=False))
            sim = PositiveSimulation(initial, PositiveConfig(periods=2, record_agents=False)).run()
            root = Path(tmp) / "run"
            export_positive_simulation(sim, root)
            verify_export(root)
            self.assertEqual(len((root / "wom_events.csv").read_text().splitlines()), 1)
            self.assertEqual(len((root / "purchases.csv").read_text().splitlines()), 1)
            self.assertIsNone(sim.summary()["reproduction_ratio"])
            self.assertEqual(sim.summary()["diffusion_class"], "not_evaluated_m2")

    def test_no_overwrite_and_nested_checksum_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            sim = PositiveSimulation(dynamics=PositiveConfig(periods=1, record_agents=False)).run()
            root = Path(tmp) / "run"
            export_positive_simulation(sim, root)
            with self.assertRaises(FileExistsError):
                export_positive_simulation(sim, root)
            (root / "initial_state" / "config.json").write_text('{}')
            with self.assertRaises(ValueError):
                verify_export(root)

    def test_serialized_configuration_reproduces_dynamics(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = PositiveSimulation(dynamics=PositiveConfig(periods=3, opportunities=1, record_agents=False)).run()
            root = Path(tmp) / "run"
            export_positive_simulation(a, root)
            cfg = Config(**json.loads((root / "initial_state/config.json").read_text()))
            dyn = PositiveConfig(**json.loads((root / "dynamics_config.json").read_text()))
            b = PositiveSimulation(initialize(cfg), dyn).run()
            self.assertEqual(a.events, b.events)
            self.assertEqual(a.system, b.system)

    def test_cli_results_byte_identical_across_process_hash_seeds(self):
        with tempfile.TemporaryDirectory() as tmp:
            paths = [Path(tmp) / 'one', Path(tmp) / 'two']
            for path, hash_seed in zip(paths, ('13', '79')):
                completed = subprocess.run([sys.executable, '-m', 'article8', '--mode', 'positive',
                                            '--negative-off', '--periods', '3', '--out', str(path)],
                                           env={**os.environ, 'PYTHONHASHSEED': hash_seed},
                                           capture_output=True, text=True, check=True)
                self.assertEqual(json.loads(completed.stdout)['completed_periods'], 3)
            contents = [{str(p.relative_to(path)): p.read_bytes() for p in path.rglob('*') if p.is_file()} for path in paths]
            self.assertEqual(contents[0], contents[1])


if __name__ == '__main__':
    unittest.main(verbosity=2)
